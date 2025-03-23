from tld import get_fld
import os
import asyncio
import aiodns
import subprocess
import json
import re

class SubdomainsPassive:
    #1. Constructor __init__
    #Le pasamos el diccionario ip_and_CN
    def __init__(self, subdomains_file="files/assetfinder.txt", ip_and_CN=None, sorted=5, list_domains=None, subdomains=None):
        self.subdomains_file = subdomains_file
        self.ip_and_CN = {}
        self.sorted = sorted
        self.list_domains = list_domains
        self.subdomains = []

    
    #2. exec_assetfinder
    #Ejecutamos assetfinder sobre los first_level domains y volcamos los resultados a self.subdomains_file
    def exec_assetfinder(self, list_domains):
        #Comprobamos si el archivo self.subdomains_file existe. Si existe lo borramos
        if os.path.exists(self.subdomains_file):
            os.remove(self.subdomains_file)
        
        #Ahora para cada fld que hemos encontrado, ejecutamos assetfinder y guardamos los subdominios en self.subdomains_file
        for fld in list_domains:
            os.system(f"assetfinder --subs-only {fld} >> {self.subdomains_file}")


    #3. exec_subfinder
    #Ejecutamos subfinder sobre los dominios y volcamos los resultados a self.subdomains_file
    def exec_subfinder(self, list_domains):
        #Ahora para cada fld que hemos encontrado, ejecutamos subfinder y guardamos los subdominios en self.subdomains_file
        for fld in list_domains:
            os.system(f"subfinder -d {fld} -all -silent >> {self.subdomains_file}")


    #4. get_subdomains
    #Ponemos los subdominios de files/assetfinder.txt en una lista (self.subdomains)
    def get_subdomains(self):
        with open(self.subdomains_file, "r") as f:
            subs = f.read().splitlines()
        
        return subs

    
    #5. resolve_dns
    #En esta función resolveremos con DNS las IPs de los subdominios enumerados en self.subdomains()

    # 5.1. resolve_subdomain -> función que resuelve el DNS
    async def resolve_subdomain(self, resolver, subdomain):
        try:
            domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(domain_pattern, subdomain) is not None:
                result = await resolver.query(subdomain, 'A')
                return {subdomain: [r.host for r in result]}
        except aiodns.error.DNSError as e:
            return {subdomain: f"Error: {e}"}
        return {}
            
    # 5.2. resolve_subdomains_concurrently -> función que llamará a resolve_subdomain de forma concurrente
    async def resolve_subdomains_concurrently(self):
        resolver = aiodns.DNSResolver()
        tasks = [self.resolve_subdomain(resolver, sub) for sub in self.subdomains]
        results = await asyncio.gather(*tasks)

        # Filtramos None y solo fusionamos los resultados válidos
        filtered_results = [result for result in results if result is not None]

        # Fusionamos los diccionarios individuales en un solo diccionario de resultados
        merged_results = {k: v for d in filtered_results for k, v in d.items()}
        return merged_results


    #6. separate_subdomains -> Separamos los subdominios según si contestan al DNS o no
    def separate_subdomains(self, subdomains_dns):
        subdomains_dns_answer = {}
        subdomains_dns_noanswer = {}

        for key,value in subdomains_dns.items():
            if "Error" in value:
                subdomains_dns_noanswer[key] = value
            else:
                subdomains_dns_answer[key] = value

        return subdomains_dns_answer,subdomains_dns_noanswer


    #7. create_structure -> Creamos la estructura ip_and_CN teniendo en cuenta los subdominios que han contestado a las consultas DNS
    def create_structure(self, subdomains_dns_answer):
        #Para cada entrada de subdomains_dns_answer pillamos cada IP de la lista
        for subdomain, ip in subdomains_dns_answer.items():
            for ip in ip:
                if ip not in self.ip_and_CN:
                    #Si la IP no está en ip_and_CN, creamos una entrada para esta IP con el subdominio como CN
                    self.ip_and_CN[ip] = {'CN':subdomain, 'SAN':[], 'Ports':[]}
                else:
                    #Si la IP ya está en ip_and_CN, miramos que el subdominio no esté como CN o en los SAN y lo añadimos
                    if subdomain != self.ip_and_CN[ip]['CN'] and subdomain not in self.ip_and_CN[ip]['SAN']:
                        if "www." in subdomain:
                            if subdomain.split("www.",1)[1] not in self.ip_and_CN[ip]['SAN'] and subdomain.split("www.",1)[1] != self.ip_and_CN[ip]['CN']:
                                self.ip_and_CN[ip]['SAN'].append(subdomain)
                        else:
                            self.ip_and_CN[ip]['SAN'].append(subdomain)


    #Main
    async def main(self):
        print("Recopilando subdominios de forma pasiva...")

        #Ejecutamos assetfinder para cada fld
        self.exec_assetfinder(self.list_domains)

        #Ejecutamos subfinder para cada fld
        self.exec_subfinder(self.list_domains)

        #Recopilamos los subdominios enumerados en una lista (self.subdomains)
        self.subdomains = self.get_subdomains()
        
        #Resolvemos el DNS de los subdominios
        print("Resolviendo el DNS de los subdominios recopilados...")
        subdomains_dns = await self.resolve_subdomains_concurrently()
        
        #Separamos los subdominios en listas según si contestan al DNS o no
        subdomains_dns_answer, subdomains_dns_noanswer = self.separate_subdomains(subdomains_dns)
        
        #Creamos la estructura ip_and_CN
        self.create_structure(subdomains_dns_answer)

        
        return self.ip_and_CN, subdomains_dns_noanswer