from tld import get_fld
import os
import asyncio
import aiodns
import subprocess
import json
import re
from tld.exceptions import TldDomainNotFound

class SubdomainsPassive:
    #1. Constructor __init__
    #Le pasamos el diccionario ip_and_CN
    def __init__(self, subdomains_file="files/assetfinder.txt", ip_and_CN=None, sorted=5, subdomains=None):
        self.subdomains_file = subdomains_file
        self.ip_and_CN = ip_and_CN
        self.sorted = sorted
        self.subdomains = []


    #2. get_flds
    #En esta función encontraremos los dominios principales que hay en los CN y SAN y las veces que aparecen
    def get_flds(self):
        list_domains = {}

        for entrada in self.ip_and_CN.values():
            # Pillamos el dominio del CN
            if entrada['CN'].strip() != '':
                try:
                    cn_domain = get_fld(entrada['CN'], fix_protocol=True)
                    if cn_domain not in list_domains:
                        list_domains[cn_domain] = 1
                    else:
                        list_domains[cn_domain] += 1
                except TldDomainNotFound:
                    # Si el dominio no es válido, simplemente lo ignoramos
                    print(f"Advertencia: El dominio del CN '{entrada['CN']}' no es válido y se omite.")

            # Pillamos los dominios de los SAN
            for subdomain in entrada['SAN']:
                if subdomain.strip() != '':
                    try:
                        san_domain = get_fld(subdomain, fix_protocol=True)
                        if san_domain not in list_domains:
                            list_domains[san_domain] = 1
                        else:
                            list_domains[san_domain] += 1
                    except TldDomainNotFound:
                        # Si el dominio no es válido, simplemente lo ignoramos
                        print(f"Advertencia: El dominio del SAN '{subdomain}' no es válido y se omite.")

        # Ordenamos el diccionario según las veces que aparecen de mayor a menor y nos quedamos con los 5 más repetidos
        sorted_domains = dict(sorted(list_domains.items(), key=lambda item: item[1], reverse=True)[:self.sorted])

        return sorted_domains

    
    #3. exec_assetfinder
    #Ejecutamos assetfinder sobre los first_level domains y volcamos los resultados a self.subdomains_file
    def exec_assetfinder(self, list_domains):
        #Comprobamos si el archivo self.subdomains_file existe. Si existe lo borramos
        if os.path.exists(self.subdomains_file):
            with open(self.subdomains_file, "w") as f:
                f.write("")
        
        #Ahora para cada fld que hemos encontrado, ejecutamos assetfinder y guardamos los subdominios en self.subdomains_file
        for fld in list_domains:
            os.system(f"assetfinder --subs-only {fld} >> {self.subdomains_file}")

    
    #4. get_subdomains
    #Ponemos los subdominios de files/assetfinder.txt en una lista (self.subdomains)
    def get_subdomains(self):
        with open(self.subdomains_file, "r") as f:
            subs = f.read().splitlines()
        
        return subs


    #5. sanitize_subdomains
    #Quitamos los subdominios de la variable self.subdomains que aparezcan en los CN o SAN de self.ip_and_CN
    def sanitize_subdomains(self):
        new_subdomains = []
        
        #Recorremos los subdominios enumerados en self.subdomains
        for sub in self.subdomains:
            trobat = False
            #Recorremos el diccionario self.ip_and_CN
            for entrada in self.ip_and_CN.values():
                cn = entrada['CN']
                san = entrada['SAN']
                if (sub == cn) or (sub in san):
                    trobat = True
                    break
                else:
                    if "www." in sub:
                        if sub.split("www.",1)[1] in san or sub.split("www.",1)[1] == cn:
                            trobat = True
                            break
            
            #Si el subdominio no está en ningún cn o san lo añadimos a la variable sanetizada new_subdomains
            if not trobat:
                if sub not in new_subdomains:
                    domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    if re.match(domain_pattern, sub) is not None:
                        new_subdomains.append(sub)
        
        return new_subdomains


    #6. resolve_dns
    #En esta función resolveremos con DNS las IPs de los subdominios enumerados en self.subdomains()

    # 6.1. resolve_subdomain -> función que resuelve el DNS
    async def resolve_subdomain(self, resolver, subdomain):
        try:
            domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(domain_pattern, subdomain) is not None:
                result = await resolver.query(subdomain, 'A')
                return {subdomain: [r.host for r in result]}
        except aiodns.error.DNSError as e:
            return {subdomain: f"Error: {e}"}
        return {}
            
    # 6.2. resolve_subdomains_concurrently -> función que llamará a resolve_subdomain de forma concurrente
    async def resolve_subdomains_concurrently(self):
        resolver = aiodns.DNSResolver()
        tasks = [self.resolve_subdomain(resolver, sub) for sub in self.subdomains]
        results = await asyncio.gather(*tasks)

        # Filtramos None y solo fusionamos los resultados válidos
        filtered_results = [result for result in results if result is not None]

        # Fusionamos los diccionarios individuales en un solo diccionario de resultados
        merged_results = {k: v for d in filtered_results for k, v in d.items()}
        return merged_results


    #7. separate_subdomains -> Separamos los subdominios según si contestan al DNS o no
    def separate_subdomains(self, subdomains_dns):
        subdomains_dns_answer = {}
        subdomains_dns_noanswer = {}

        for key,value in subdomains_dns.items():
            if "Error" in value:
                subdomains_dns_noanswer[key] = value
            else:
                subdomains_dns_answer[key] = value

        return subdomains_dns_answer,subdomains_dns_noanswer


    #8. add_subdomains_dns_answer
    # La idea es que si la IP existe en self.ip_and_CN, añadiremos el subdominio como SAN (si la IP ya tiene CN). Si la IP no existe crearemos una nueva entrada llamando a smap

    #8.1. add_ip_exists -> Esta función se llamará si la ip ya existe en self.ip_and_CN, si la entrada tiene CN se añadirá el subdominio como SAN.
    def add_ip_exists(self, ip, subdomain):
        #Miramos si el self.ip_and_CN['ip'] existe, si no existe añadimos el subdominio como CN
        if self.ip_and_CN[ip]['CN'] == ' ':
            if "www." in subdomain:
                subdomain = subdomain.split("www.",1)[1]
            self.ip_and_CN[ip]['CN'] = subdomain
        else:
            #Si el subdominio existe, lo añadimos como SAN
            if subdomain != self.ip_and_CN[ip]['CN'] and subdomain not in self.ip_and_CN[ip]['SAN']:
                if "www." in subdomain:
                    if subdomain.split("www.",1)[1] not in self.ip_and_CN[ip]['SAN'] and subdomain.split("www.",1)[1] != self.ip_and_CN[ip]['CN']:
                        self.ip_and_CN[ip]['SAN'].append(subdomain)
                else:
                    self.ip_and_CN[ip]['SAN'].append(subdomain)


    #8.2. add_ip_no_exists -> Esta función se llamará si la ip no existe en self.ip_and_CN. Deberemos preparar una entrada válida para self.ip_and_CN
    def add_ip_no_exists(self, ip, subdomain):
        #Preparamos la entrada
        common_name = ' '
        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(domain_pattern, subdomain) is not None:
            common_name = subdomain
        dict_to_add = {"CN": common_name, "SAN": [], "Ports": []}

        #Llamamos a smap
        try:
            command = f"smap {ip} -oJ - 2>/dev/null"
            resultado = subprocess.run(command, shell=True, capture_output=True, text=True)
            smap_output = resultado.stdout
        except Exception as e:
            print(f"Error en la función exec_smap: {e}")

        entrada_smap = json.loads(smap_output)
        if len(entrada_smap) > 0:
            entrada_smap = entrada_smap[0]
            #Añadimos los puertos al dict_to_add
            ports = []

            if len(entrada_smap['ports']) > 0:
                for port in entrada_smap['ports']:
                    ports.append(port['port'])
            dict_to_add['Ports'] = ports

            #Añadimos los SAN al dict_to_add
            san = []
            #Comprobamos que la IP sea válida
            ip_pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            if re.match(ip_pattern, entrada_smap['ip']) is not None:
                #Comprobamos que los hostnames sean correctos y los añadimos a dict_to_add
                    hostnames = entrada_smap['hostnames']
                    for i, hostname in enumerate(hostnames):
                        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        if re.match(domain_pattern, hostname) is not None:
                            if hostname != common_name and hostname not in san:
                                if "www." in hostname:
                                    if hostname.split("www.",1)[1] not in entrada_smap['hostnames'] and hostname.split("www.",1)[1] != dict_to_add["CN"]:
                                        san.append(hostname)
                                else:
                                    san.append(hostname)
            
            dict_to_add['SAN'] = san

        self.ip_and_CN[ip] = dict_to_add


    #8.3. add_subdomains_dns_answer -> Lógica princpial de la función
    def add_subdomains_dns_answer(self, subdomains_dns_answer):
        #Recorremos el diccionario de subdomains_dns_answer 
        for subdomain, ips in subdomains_dns_answer.items():
            for ip in ips:
                if ip in self.ip_and_CN:
                    #Si la ip existe en self.ip_and_CN, llamamos a add_ip_exists
                    self.add_ip_exists(ip, subdomain)
                else:
                    #Si la ip no existe en self.ip_and_CN, llamamos a add_ip_no_exists
                    self.add_ip_no_exists(ip, subdomain)


    #9. Unique_ips -> Función que limpia IPs distintas con la misma información (típico de balanceadores de carga)
    def unique_ips(self):
        new_ip_and_CN = {}

        # Recorremos el diccionario ip_and_CN
        for ip, data in self.ip_and_CN.items():
            san = data['SAN']
            cn = data['CN']
            ports = data['Ports']

            hostnames = san + [cn]
            hostnames.sort()

            # Si el tamaño de SAN y CN es 0, añadimos directamente
            if len(san) == 0 and cn == ' ':
                if ip not in new_ip_and_CN:
                    new_ip_and_CN[ip] = data
            # Si hay SAN o CN, miramos que esta información no esté repetida en otra IP
            else:
                # Utilizamos una bandera para saber si encontramos una entrada con los mismos datos
                found_duplicate = False
                for new_data in new_ip_and_CN.values():
                    if new_data['CN'] == cn and new_data['SAN'] == san and new_data['Ports'] == ports:
                        found_duplicate = True
                        break  # Salimos del bucle ya que hemos encontrado el duplicado
                    else:
                        #Si tienen los mismos hostnames y puertos también lo consideramos duplicado
                        new_hostnames = new_data['SAN'] + [new_data['CN']]
                        new_hostnames.sort()
                        if hostnames == new_hostnames and new_data['Ports'] == ports:
                            found_duplicate = True
                            break  # Salimos del bucle ya que hemos encontrado el duplicado

                if not found_duplicate:
                    new_ip_and_CN[ip] = data

        self.ip_and_CN = new_ip_and_CN



    async def main(self):
        print("Recopilando subdominios de forma pasiva con assetfinder...")
        #Recopilamos los flds de ip_and_CN
        list_domains = self.get_flds()

        #Ejecutamos assetfinder para cada fld
        self.exec_assetfinder(list_domains)

        #Recopilamos los subdominios enumerados en una lista (self.subdomains)
        self.subdomains = self.get_subdomains()

        #Quitamos los subdominios que aparezcan en algún cn o san
        self.subdomains = self.sanitize_subdomains()
        
        #Resolvemos el DNS de los subdominios
        print("Resolviendo el DNS de los subdominios recopilados...")
        subdomains_dns = await self.resolve_subdomains_concurrently()
        
        #Separamos los subdominios en listas según si contestan al DNS o no
        subdomains_dns_answer, subdomains_dns_noanswer = self.separate_subdomains(subdomains_dns)
        
        #Añadimos los subdominios que contestan al DNS en self.ip_and_CN
        self.add_subdomains_dns_answer(subdomains_dns_answer)

        self.unique_ips()
        
        return self.ip_and_CN, subdomains_dns_noanswer