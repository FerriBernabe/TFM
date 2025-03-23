import asyncio
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import re
import json
import xml.etree.ElementTree as ET


class WebPorts:
    #1. Constructor __init__
    #Le pasamos el diccionario ip_and_CN
    def __init__(self, max_concurrent=200, timeout=2, chunk_size=500, semaphore_limit=100, ip_and_CN=None):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.ip_and_CN = ip_and_CN

    
    #2. is_valid_domain
    #Función que comprueba si un dominio es válido
    def is_valid_domain(self, hostname):
        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(domain_pattern, hostname) is not None


    #3. CheckSites
    #Función que se encargará de la lógica principal para hacer peticiones web a las distintas IPs y hostnames y guardar sus resultados

    #3.1. makeRequestIP
    #Función que hace peticiones http y https a la IP, en sus distintos puertos
    async def makeRequestIP(self, session, ports, ip):
        protocolos = ["http://", "https://"]

        #Si no hay puertos enumerados, haremos peticiones a los puertos 80 y 443
        if len(ports) == 0:
            ports = [80,443]

        result_final = []

        for protocolo in protocolos:
            for port in ports:
                if not (protocolo == "http://" and port == 443) and not (protocolo == "https://" and port == 80):
                    try:
                        if self.semaphore.locked():
                            await asyncio.sleep(1)
                        
                        #Preparamos la url con la IP
                        url = f"{protocolo}{ip}:{port}"

                        #Preparamos las variables a recolectar
                        redirected_domain=""
                        response_headers={}
                        first_300_words=""
                        title=""
                        status_code = ""

                        async with session.get(url, allow_redirects=True, timeout=self.timeout, ssl=False) as res:
                            status_code = res.status
                            response = await res.text(encoding="utf-8")
                            content_type = res.headers.get("Content-Type")
                            #Guardamos los headers
                            if res.headers is not None:
                                for key,value in res.headers.items():
                                    response_headers[key] = value.encode("utf-8", "surrogatepass").decode("utf-8")
                                
                            #Guardamos el redirect si lo hay
                            if res.history:
                                redirected_domain = str(res.url)

                            #Llenamos las variables segÃºn el Content-Type 
                            if response is not None and content_type is not None:
                                #Si content-type es xml
                                if "xml" in content_type:
                                    root = ET.fromstring(response)
                                    xmlwords = []
                                    count = 0

                                    for elem in root.iter():
                                        if elem.text:
                                            xmlwords.extend(elem.text.split())
                                            count += len(xmlwords)
                                            if count >= 300:
                                                break
                                    
                                    if xmlwords:
                                        first_300_words = " ".join(xmlwords[:300])
                                
                                #Si el content-type es HTML
                                elif "html" in content_type:
                                    strainer = SoupStrainer(["title", "body"])
                                    soup = BeautifulSoup(response, "html.parser", parse_only=strainer)
                                    title_tag = soup.title
                                    body_tag = soup.body

                                    if title_tag and title_tag.string:
                                        title = title_tag.string.strip()

                                    if body_tag:
                                        body_text = body_tag.get_text(separator=" ", strip=True)
                                        words = body_text.split()
                                        first_300_words = " ".join(words[:300])

                                    if not body_tag or not title_tag:
                                        words = response.split()
                                        first_300_words = " ".join(words[:300])

                                #Si el content-type es plain
                                elif "plain" in content_type:
                                    words = response.split()
                                    first_300_words = " ".join(words[:300])

                                #Si el content-type es json
                                elif "json" in content_type:
                                    first_300_words = response[:300]

                                #Diccionario resultado
                                result_dict = {
                                    "status_code" : status_code,
                                    "title":title.encode("utf-8", "surrogatepass").decode("utf-8"),
                                    "request":url,
                                    "redirected_url":redirected_domain,
                                    "port":str(port),
                                    "response_text":first_300_words,
                                    "response_headers":response_headers
                                }

                                result_final.append(result_dict)
            
                    except Exception as e:
                        #print(f"Error CheckWebPorts: {e}")
                        pass
                    
        return result_final


    
    #3.2. makeRequestDomain
    #Función que hace peticiones http y https a los dominios, en sus distintos puertos
    async def makeRequestDomain(self, session, ports, hostnames):
        #Filtramos domains no válidos
        valid_hostnames = []
        for hostname in hostnames:
            if self.is_valid_domain(hostname):
                valid_hostnames.append(hostname)

        #Función que hace peticiones http y https a la IP, en sus distintos puertos
        protocolos = ["http://", "https://"]

        #Si no hay puertos enumerados, haremos peticiones a los puertos 80 y 443
        if len(ports) == 0:
            ports = [80,443]

        #Variables de lógica
        result_final = []
        hostnames_answer = []
        hostnames_no_answer = []

        for protocolo in protocolos:
            for port in ports:
                if not (protocolo == "http://" and port == 443) and not (protocolo == "https://" and port == 80):
                    for hostname in valid_hostnames:
                        try:
                            if self.semaphore.locked():
                                await asyncio.sleep(1)
                            
                            #Preparamos la url con la IP
                            url = f"{protocolo}{hostname}:{port}"

                            #Preparamos las variables a recolectar
                            redirected_domain=""
                            response_headers={}
                            first_300_words=""
                            title=""
                            status_code = ""

                            async with session.get(url, allow_redirects=True, timeout=self.timeout, ssl=False) as res:
                                status_code = res.status
                                response = await res.text(encoding="utf-8")
                                content_type = res.headers.get("Content-Type")

                                #Guardamos los headers
                                if res.headers is not None:
                                    for key,value in res.headers.items():
                                        response_headers[key] = value.encode("utf-8", "surrogatepass").decode("utf-8")
                                    
                                #Guardamos el redirect si lo hay
                                if res.history:
                                    redirected_domain = str(res.url)

                                #Llenamos las variables segÃºn el Content-Type 
                                if response is not None and content_type is not None:
                                    #Si content-type es xml
                                    if "xml" in content_type:
                                        root = ET.fromstring(response)
                                        xmlwords = []
                                        count = 0

                                        for elem in root.iter():
                                            if elem.text:
                                                xmlwords.extend(elem.text.split())
                                                count += len(xmlwords)
                                                if count >= 300:
                                                    break
                                        
                                        if xmlwords:
                                            first_300_words = " ".join(xmlwords[:300])
                                    
                                    #Si el content-type es HTML
                                    elif "html" in content_type:
                                        strainer = SoupStrainer(["title", "body"])
                                        soup = BeautifulSoup(response, "html.parser", parse_only=strainer)
                                        title_tag = soup.title
                                        body_tag = soup.body

                                        if title_tag and title_tag.string:
                                            title = title_tag.string.strip()

                                        if body_tag:
                                            body_text = body_tag.get_text(separator=" ", strip=True)
                                            words = body_text.split()
                                            first_300_words = " ".join(words[:300])

                                        if not body_tag or not title_tag:
                                            words = response.split()
                                            first_300_words = " ".join(words[:300])

                                    #Si el content-type es plain
                                    elif "plain" in content_type:
                                        words = response.split()
                                        first_300_words = " ".join(words[:300])

                                    #Si el content-type es json
                                    elif "json" in content_type:
                                        first_300_words = response[:300]

                                    #Diccionario resultado
                                    result_dict = {
                                        "status_code" : status_code,
                                        "title":title.encode("utf-8", "surrogatepass").decode("utf-8"),
                                        "request":url,
                                        "redirected_url":redirected_domain,
                                        "port":str(port),
                                        "response_text":first_300_words,
                                        "response_headers":response_headers
                                    }

                                    result_final.append(result_dict)
                                    if hostname not in hostnames_answer:
                                        hostnames_answer.append(hostname)
                
                        except Exception as e:
                            #print(f"Error CheckWebPorts: {e}")
                            pass
        
        #Llenamos hostnames_no_answer
        for hostname in valid_hostnames:
            if hostname not in hostnames_answer:
                hostnames_no_answer.append(hostname)

        #Devolvemos el result final y hostnames_no_answer (que servirá después para hacer llamadas de vhosts)
        return result_final, hostnames_no_answer



    #3.3. makeRequestVhost
    #Función que hace peticiones http y https a los vhosts, en sus distintos puertos
    async def makeRequestVhost(self, session, ports, ip, hostnames_no_answer):
        protocolos = ["http://", "https://"]

        #Si no hay puertos enumerados, haremos peticiones a los puertos 80 y 443
        if len(ports) == 0:
            ports = [80,443]

        #Variables de lógica
        result_final = []

        for protocolo in protocolos:
            for port in ports:
                if not (protocolo == "http://" and port == 443) and not (protocolo == "https://" and port == 80):
                    for vhost in hostnames_no_answer:
                        try:
                            if self.semaphore.locked():
                                await asyncio.sleep(1)
                            
                            #Preparamos la url con la IP
                            url = f"{protocolo}{ip}:{port}"

                            #Preparamos las variables a recolectar
                            redirected_domain=""
                            response_headers={}
                            first_300_words=""
                            title=""
                            status_code = ""

                            #Preparamos los headers con el vhost
                            custom_headers = {
                                "Host": vhost
                            }

                            async with session.get(url, allow_redirects=True, timeout=self.timeout, ssl=False, headers=custom_headers) as res:
                                status_code = res.status

                                #Para evitar muchos falsos positivos, si el status_code es 404, devolveremos una lista vacía
                                if status_code == 404 or status_code == 400:
                                    return []

                                response = await res.text(encoding="utf-8")
                                content_type = res.headers.get("Content-Type")
                                #Guardamos los headers
                                if res.headers is not None:
                                    for key,value in res.headers.items():
                                        response_headers[key] = value.encode("utf-8", "surrogatepass").decode("utf-8")
                                    
                                #Guardamos el redirect si lo hay
                                if res.history:
                                    redirected_domain = str(res.url)

                                #Llenamos las variables segÃºn el Content-Type 
                                if response is not None and content_type is not None:
                                    #Si content-type es xml
                                    if "xml" in content_type:
                                        root = ET.fromstring(response)
                                        xmlwords = []
                                        count = 0

                                        for elem in root.iter():
                                            if elem.text:
                                                xmlwords.extend(elem.text.split())
                                                count += len(xmlwords)
                                                if count >= 300:
                                                    break
                                        
                                        if xmlwords:
                                            first_300_words = " ".join(xmlwords[:300])
                                    
                                    #Si el content-type es HTML
                                    elif "html" in content_type:
                                        strainer = SoupStrainer(["title", "body"])
                                        soup = BeautifulSoup(response, "html.parser", parse_only=strainer)
                                        title_tag = soup.title
                                        body_tag = soup.body

                                        if title_tag and title_tag.string:
                                            title = title_tag.string.strip()

                                        if body_tag:
                                            body_text = body_tag.get_text(separator=" ", strip=True)
                                            words = body_text.split()
                                            first_300_words = " ".join(words[:300])

                                        if not body_tag or not title_tag:
                                            words = response.split()
                                            first_300_words = " ".join(words[:300])

                                    #Si el content-type es plain
                                    elif "plain" in content_type:
                                        words = response.split()
                                        first_300_words = " ".join(words[:300])

                                    #Si el content-type es json
                                    elif "json" in content_type:
                                        first_300_words = response[:300]

                                    #Diccionario resultado
                                    result_dict = {
                                        "status_code" : status_code,
                                        "title":title.encode("utf-8", "surrogatepass").decode("utf-8"),
                                        "request - vhost":url + " - " + vhost,
                                        "redirected_url":redirected_domain,
                                        "port":str(port),
                                        "response_text":first_300_words,
                                        "response_headers":response_headers
                                    }

                                    result_final.append(result_dict)
                
                        except Exception as e:
                            #print(f"Error CheckWebPorts: {e}")
                            pass
        
        return result_final



    #3.4. checkSite
    #Función que llama a las anteriores para una entrada de ip_and_CN
    async def checkSite(self, session, ports, ip, hostnames):
        result_dict = {}

        #Llamamos a makeRequestIP
        res_ip = await self.makeRequestIP(session, ports, ip)

        #Llamamos a makeRequestDomain
        res_domain, hostnames_no_answer = await self.makeRequestDomain(session, ports, hostnames)

        #Llamamos a makeRequestVhost
        res_vhost = []
        if len(hostnames_no_answer) > 0:
            res_vhost = await self.makeRequestVhost(session, ports, ip, hostnames_no_answer)

        res_final = res_ip + res_domain + res_vhost

        result_dict[ip] = res_final

        return result_dict



    #3.5. checkSites
    #FUnción con la lógica principal para llamar a checkSite para cada entrada de ip_and_CN
    async def checkSites(self):
        all_responses = []

        for i in range(0, len(self.ip_and_CN), self.chunk_size):
            #Pillamos las IPs de chunk_size en chunk_size (200 en 200)
            connector = aiohttp.TCPConnector(limit=self.max_concurrent, ssl=False)

            #Llamamos a checkSItes de forma concurrente
            async with aiohttp.ClientSession(connector=connector) as session:
                chunk_responses = await asyncio.gather(
                    *[self.checkSite(session, data['Ports'], ip, list({data['CN']} | set(data['SAN']))) for ip, data in list(self.ip_and_CN.items())[i:i + self.chunk_size]]
                )

            all_responses.extend(chunk_responses)

        return all_responses



    #4. removeDuplicates

    def removeDuplicates(self, all_responses):
        new_responses = []

        seen_keys = set()  # Rastrea status_code, title y response_text globalmente
        seen_requests = set()  # Rastrea request o request - vhost globalmente

        for entrada1 in all_responses:
            for ip1, data_list1 in entrada1.items():
                new_data_list = []

                for data1 in data_list1:
                    # Normaliza y genera una clave única
                    unique_key = (
                        f"{data1.get('status_code', '')}|"
                        f"{data1.get('title', '').strip()}|"
                        f"{data1.get('response_text', '').strip()}"
                    )

                    # Obtiene request o request - vhost
                    request_value = data1.get('request') or data1.get('request - vhost')

                    # Si no hay request_value, lo ignoramos para evitar falsos positivos
                    if not request_value:
                        continue  

                    # Verifica duplicados a nivel global (entre todas las IPs)
                    if unique_key in seen_keys or request_value in seen_requests:
                        continue  

                    # Añadimos a los conjuntos para evitar duplicados en cualquier IP
                    seen_keys.add(unique_key)
                    seen_requests.add(request_value)
                    new_data_list.append(data1)

                if new_data_list:  # Evita añadir IPs sin datos
                    new_responses.append({ip1: new_data_list})

        return new_responses



    #Main
    async def main(self):
        print("Recopilando información de los puertos web...")

        #Recopilamos información de cada IP
        all_responses = await self.checkSites()

        #Quitamos respuestas duplicadas
        all_responses = self.removeDuplicates(all_responses)

        return all_responses