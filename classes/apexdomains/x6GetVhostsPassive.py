import asyncio
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import re
import subprocess
import json
from math import floor, ceil

class VhostsPassive:
    #1. Constructor __init__
    #Le pasamos el diccionario ip_and_CN
    def __init__(self, limitconnector=20, timeoutconnector=3, subdomains_dns_noanswer=None, ip_and_CN=None):
        self.limitconnector = limitconnector
        self.timeoutconnector = timeoutconnector
        self.subdomains_dns_noanswer = subdomains_dns_noanswer or []
        self.ip_and_CN = ip_and_CN



    async def visit_crt(self, url, num_iterations):
        try:
            asociados = []

            #Añadimos el subdominio que buscamos a la lista de asociados
            subdomain = url.split("q=",1)[1]
            if subdomain is not None:
                asociados.append(subdomain)

            #Como crt.sh nos bloquea por intento de DoS, si i > 150, no haremos más peticiones inútiles
            if num_iterations > 0:
                return asociados

            #Hacemos la request a crt
            connector = aiohttp.TCPConnector(limit=self.limitconnector, ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, allow_redirects=True, timeout=self.timeoutconnector, ssl=False) as res:
                        response = await res.text(encoding="utf-8")
                        
            #Sacamos las subnets con BeautifulSoup
            strainer = SoupStrainer("tr")
            soup_tr = BeautifulSoup(response, "html.parser", parse_only=strainer)

            #Pillamos los CN y Matching de crt
            for tr in soup_tr.find_all("tr"):
                tds = tr.find_all("td") if len(tr.find_all("td")) != 0 else None
                if tds is not None:
                    for td in tds:
                        if "style" not in str(td) and "class" not in str(td):
                            domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                            if re.match(domain_pattern, str(td.text)) is not None:
                                if str(td.text) not in asociados:
                                    if "wwww." in str(td.text):
                                        td_corrected = str(td.text).split("www.",1)[1]
                                        if td_corrected not in asociados:
                                            asociados.append(td_corrected)
                                    else:
                                        asociados.append(str(td.text))

            return asociados

        except Exception as e:
            asociados = []

            #Añadimos el subdominio que buscamos a la lista de asociados
            subdomain = url.split("q=",1)[1]
            if subdomain is not None:
                asociados.append(subdomain)
            
            return asociados



    async def visit_crts(self):
        urls = []
        list_associated = []

        #Añadimos las urls a visitar (crt.sh) a la lista urls 
        for subdomain in self.subdomains_dns_noanswer:
            url = f"https://crt.sh/?q={subdomain}"
            urls.append(url)

        #Para mayor velocidad de requests http, usaremos aiohttp de forma concurrente
        #Haremos las peticiones por grupos, para no hacer todas las peticiones a la vez
        num_iterations = 0
        for i in range(0, len(urls), 150):
            #Pillamos las URLs de chunk_size en chunk_size (200 en 200)
            chunk_of_urls = urls[i:i+150]

            #Ahora haremos las peticiones HTTPS para obtener los asociados a cada subdominio 
            #Lo haremos de forma concurrente para mayor velocidad
            chunk_results = await asyncio.gather(*[self.visit_crt(url, num_iterations) for url in chunk_of_urls])
            list_associated.append(chunk_results)
            num_iterations += 1

        return list_associated



    async def exec_certgraph(self, subdomain):
        associated = [subdomain]

        #Ejecutamos el comando de certgraph
        command = f"certgraph -ct-expired -ct-subdomains -depth 1 -driver 'http' {subdomain}"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Esperamos el resultado del comando
        stdout, stderr = await process.communicate()

        #Añadimos los subdominios asociados enumerados a la lista
        for subdomain_associated in stdout.decode().split("\n"):
            domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(domain_pattern, subdomain_associated) is not None:
                if subdomain_associated not in associated and len(subdomain_associated) != 0:
                    if "www." in subdomain_associated:
                        if subdomain_associated.split("www.",1)[1] not in associated:
                            associated.append(subdomain_associated)
                    else:
                        associated.append(subdomain_associated)

        return associated



    async def exec_certgraphs(self):
        list_associated = []
        subdomains = []

        for subdomain in self.subdomains_dns_noanswer:
            subdomains.append(subdomain)

        for i in range(0, len(subdomains), 200):
            #Pillamos los subdominios de chunk_size en chunk_size (200 en 200)
            chunk_of_subdomains = subdomains[i:i+200]

            #Ejecutamos certgraph para obtener los asociados a cada subdominio
            #Lo haremos de forma concurrente para mayor velocidad
            chunk_results = await asyncio.gather(*[self.exec_certgraph(subdomain) for subdomain in chunk_of_subdomains])
            list_associated.append(chunk_results)

        return list_associated



    def join_lists(self, list1, list2):
        # Aplanamos los niveles intermedios para obtener listas de listas simples
        flat_list1 = [set(inner_list) for sublist in list1 for inner_list in sublist]
        flat_list2 = [set(inner_list) for sublist in list2 for inner_list in sublist]

        for set1 in flat_list1:
            merged = False
            for set2 in flat_list2:
                # Si hay intersección entre conjuntos, los combinamos
                if set1 & set2:
                    set2.update(set1)
                    merged = True
                    break
            if not merged:
                flat_list2.append(set1)

        # Convertimos los conjuntos de vuelta a listas para el resultado final
        return [list(s) for s in flat_list2]



    def clean_associated_list(self, list_associated):
        new_list_associated = []

        for lista in list_associated:
            # Convertir la lista en un conjunto para eliminar duplicados dentro de la lista
            normalized_lista = set(lista)

            # Verificar si ya existe una lista con los mismos elementos
            if all(normalized_lista != set(existing) for existing in new_list_associated):
                new_list_associated.append(lista)

        return new_list_associated



    def merge_associated_san(self, list_associated):
        new_list_associated = []

        # Recorremos los subdominios
        for subdomains in list_associated:
            trobat = False
            for subdomain in subdomains:
                # Miramos si el subdominio está en algún CN o SAN
                for entrada in self.ip_and_CN.values():
                    if subdomain == entrada['CN'] or subdomain in entrada['SAN']:
                        trobat = True
                        #Volcamos los subdominios en el SAN
                        for sub in subdomains:
                            if sub != entrada['CN'] and sub not in entrada['SAN']:
                                if "www." in sub:
                                    if sub.split("www.",1)[1] not in entrada['SAN'] and sub.split("www.",1)[1] != entrada['CN']:
                                        entrada['SAN'].append(sub)
                                else:
                                    entrada['SAN'].append(sub)

                        break  # Salir del bucle si encontramos coincidencia
                if trobat:
                    break  # Continuar con el siguiente grupo si ya se encontró
            if not trobat:
                new_list_associated.append(subdomains)

        return new_list_associated



    def jaro_distance(self, s1, s2):
        #Función que calcula la similitud de Jaro
        # If the s are equal
        if (s1 == s2):
            return 1.0
    
        # Length of two s
        len1 = len(s1)
        len2 = len(s2)
    
        # Maximum distance upto which matching
        # is allowed
        max_dist = floor(max(len1, len2) / 2) - 1
    
        # Count of matches
        match = 0
    
        # Hash for matches
        hash_s1 = [0] * len(s1)
        hash_s2 = [0] * len(s2)
    
        # Traverse through the first
        for i in range(len1):
    
            # Check if there is any matches
            for j in range(max(0, i - max_dist), 
                        min(len2, i + max_dist + 1)):
                
                # If there is a match
                if (s1[i] == s2[j] and hash_s2[j] == 0):
                    hash_s1[i] = 1
                    hash_s2[j] = 1
                    match += 1
                    break
    
        # If there is no match
        if (match == 0):
            return 0.0
    
        # Number of transpositions
        t = 0
        point = 0
    
        # Count number of occurrences
        # where two characters match but
        # there is a third matched character
        # in between the indices
        for i in range(len1):
            if (hash_s1[i]):
    
                # Find the next matched character
                # in second
                while (hash_s2[point] == 0):
                    point += 1
    
                if (s1[i] != s2[point]):
                    t += 1
                point += 1
        t = t//2
    
        # Return the Jaro Similarity
        return (match/ len1 + match / len2 +
                (match - t) / match)/ 3.0




    def check_similance(self, subdomain1, subdomain2):
        #Función que compara la similitud entre dos dominios
        
        #Primero tokenizamos los subdominios, quitando el tld y fld
        partsub1 = subdomain1.split('.')
        tokensub1 = '.'.join(partsub1[:-2]) if len(partsub1) > 2 else partsub1[0]

        partsub2 = subdomain2.split('.')
        tokensub2 = '.'.join(partsub2[:-2]) if len(partsub2) > 2 else partsub2[0]

        #Calculamos la similitud de Jaro de ambos tokens
        if (int(self.jaro_distance(tokensub1, tokensub2) * 100) > 90):
            return True
        else:
            return False



    async def visit_merklemap(self, subdomain):
        try:
            url = f"https://api.merklemap.com/search?query={subdomain}&page=0&type=distance&stream=true"
            asociados = [subdomain]

            #Hacemos la request a crt
            connector = aiohttp.TCPConnector(limit=self.limitconnector, ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, allow_redirects=True, timeout=self.timeoutconnector, ssl=False) as res:
                        response = await res.text(encoding="utf-8")
                        
            #Cargamos el json de la response
            json_response = json.loads(response)

            #Añadimos los hostnames y common names enumerados por merklemap
            for entrada in json_response['results']:
                domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if re.match(domain_pattern, entrada['domain']) is not None:
                    if entrada['domain'] not in asociados:
                        asociados.append(entrada['domain'])
                if re.match(domain_pattern, entrada['subject_common_name']) is not None:
                    if entrada['subject_common_name'] not in asociados:
                        asociados.append(entrada['subject_common_name'])
            return list(set(asociados))


        except Exception as e:
            return [subdomain]



    async def visit_merklemaps(self, list_associated):
        new_list_associated = []
        # Procesamos los subdominios en grupos de 200
        for i in range(0, len(list_associated), 5):
            chunk_of_associateds = list_associated[i:i + 5]

            # Listamos todas las tareas asíncronas para los subdominios en este chunk
            tasks = []
            for lista in chunk_of_associateds:
                for i,subdomain in enumerate(lista):
                    #Si es el primer subdominio de la lista, haremos la petición a merklemap
                    if i == 0:
                        tasks.append(self.visit_merklemap(subdomain))
                    else:
                        trobat = False
                        #Si no es el primer subdominio de su lista, solo haremos la petición a merklemap si no tiene ninguna similitud con los subdominios anteriores de la lista
                        for sub in lista[:i]:
                            if self.check_similance(sub, subdomain):
                                trobat = True
                                break
                        
                        if not trobat:
                            tasks.append(self.visit_merklemap(subdomain))

            # Ejecutamos las tareas concurrentemente
            chunk_results = await asyncio.gather(*tasks)

            # Procesamos los resultados obtenidos
            for list_result in chunk_results:
                #Miramos en qué lista de chunk_of_associateds está
                trobat = False
                for sub_result in list_result:
                    #Recorremos chunk_of_associateds
                    for chunk_of_associated in chunk_of_associateds:
                        if sub_result in chunk_of_associated:
                            lista_temp = list_result + chunk_of_associated
                            deduplicated_list = list(dict.fromkeys(lista_temp))
                            if deduplicated_list not in new_list_associated:
                                trobat = True
                                new_list_associated.append(deduplicated_list)
                                break

                    if trobat:
                        break

        return new_list_associated



    def merge_associated_by_similarity(self, list_associated):
        #Agruparemos las listas de asociados si hay algún subdominio similar entre ellas
        new_list_associated = []  # Lista final con las listas unidas según similitud

        for subdomains in list_associated:
            merged = False  # Indicador de si la lista actual se ha combinado con otra

            for group in new_list_associated:
                # Comprobar si algún subdominio del grupo es similar a los subdominios actuales
                if any(self.check_similance(sub1, sub2) for sub1 in subdomains for sub2 in group):
                    # Combinar las listas y eliminar duplicados
                    group.extend(subdomains)
                    group[:] = list(set(group))  # Deduplicar manteniendo el orden
                    merged = True
                    break

            # Si no se ha combinado con ninguna lista existente, añadir como nueva lista
            if not merged:
                new_list_associated.append(subdomains)

        return new_list_associated




    def merge_associated_san_by_similarity(self, list_associated):
        #Uniremos los subdominios asociados al san si cumplen con una similitud mínima
        new_list_associated = []

        # Recorremos los subdominios
        for subdomains in list_associated:
            trobat = False
            for subdomain in subdomains:
                # Miramos si el subdominio es similar a algún CN o SAN
                for entrada in self.ip_and_CN.values():
                    #Comprobamos si el subdominio es parecido al CN
                    if self.check_similance(subdomain, entrada['CN']):
                        trobat = True
                    else:
                        #Comprobamos si el subdominio es parecido a algún SAN
                        for san in entrada['SAN']:
                            if self.check_similance(subdomain, san):
                                trobat = True
                    
                    #Si el subdominio es parecido, volcamos los subdominios en el SAN
                    if trobat:
                        for sub in subdomains:
                            if sub != entrada['CN'] and sub not in entrada['SAN']:
                                if "www." in sub:
                                    if sub.split("www.",1)[1] not in entrada['SAN'] and sub.split("www.",1)[1] not in subdomains and sub.split("www.",1)[1] != entrada['CN']:
                                        entrada['SAN'].append(sub)
                                else:
                                    entrada['SAN'].append(sub)

                        break  # Salir del bucle si encontramos coincidencia

                if trobat:
                    break  # Continuar con el siguiente grupo si ya se encontró
            if not trobat:
                new_list_associated.append(subdomains)

        return new_list_associated



    async def main(self):
        print("Enumerando posibles vhosts de manera pasiva...")
        #Sacamos la lista de asociados de crt.sh
        list_associated_crt = await self.visit_crts()

        #Sacamos la lista de asociados con certgraphs
        list_associated_certgraph = await self.exec_certgraphs()
        
        #Juntamos ambas listas en una quitando duplicados
        list_associated = self.join_lists(list_associated_crt, list_associated_certgraph)
        
        #Limpiamos la lista de posibles listas duplicadas
        list_associated = self.clean_associated_list(list_associated)

        #Añadimos los vhosts a ip_and_CN
        list_associated = self.merge_associated_san(list_associated)

        #Retocamos la lista de asociados según si los subdominios son similares
        list_associated = self.merge_associated_by_similarity(list_associated)

        #Sacamos lista de asociados por distancia con merklemap
        list_associated = await self.visit_merklemaps(list_associated)

        #Limpiamos la lista de posibles listas duplicadas
        list_associated = self.clean_associated_list(list_associated)

        #Añadimos los vhosts a ip_and_CN
        list_associated = self.merge_associated_san(list_associated)

        #Añadimos los vhosts según la similitud de Jaro
        list_associated = self.merge_associated_san_by_similarity(list_associated)

        return self.ip_and_CN