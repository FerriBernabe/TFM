#La idea de este script es hacer requests a bgpview.io y bgp.he.net, para recolectar las redes de una empresa

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import re
import ipaddress

class GetNets:
    #1. Constructor
    def __init__(self, companyName, max_concurrent=60, timeout=3):
        self.companyName = companyName.strip()
        self.max_concurrent = max_concurrent
        self.timeout = timeout

    #2. Prepare_urls
    #En esta función prepararemos las URLs a pedir en bgpview.io y bgp.he.net
    def prepare_urls(self):
        #Primero cambiamos los espacios por "+" para cuando metamos la variable en la URL
        companyName_url = self.companyName.replace(" ", "+")

        #Después preparamos las url que vamos a visitar
        url_bgpview = f"https://bgpview.io/search/{companyName_url}#results-v4"
        url_bgphe = f"https://bgp.he.net/search?search%5Bsearch%5D={companyName_url}&commit=Search"

        return url_bgpview, url_bgphe

    #3. Search_bgpview
    #En esta función buscaremos en bgpview.io
    async def search_bgpview(self, url_bgpview):
        #Hacemos la request a bgpview.io
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url_bgpview, allow_redirects=True, timeout=self.timeout, ssl=False) as res:
                    response = await res.text(encoding="utf-8")
        
        #Sacamos las subnets con BeautifulSoup
        strainer = SoupStrainer("tr")
        soup_tr = BeautifulSoup(response, "html.parser", parse_only=strainer)

        subnets = []
        for tr in soup_tr.find_all("tr"):
            tds = tr.find_all("td") if len(tr.find_all("td")) != 0 else None
            if tds is not None and len(tds) > 1:
                a_tag = None
                a_tag = tds[1].find("a")
                if a_tag:
                    subnets.append(a_tag.text)
        return subnets

        
    #4. Search bgphe
    #En esta función buscaremos en bgp.he.net
    async def search_bgphe(self, url_bgphe, subnets):
        #Hacemos la request a bgp.he.net
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url_bgphe, allow_redirects=True, timeout=self.timeout, ssl=False) as res:
                    response = await res.text(encoding="utf-8")
        
        #Sacamos las subnets con BeautifulSoup
        strainer = SoupStrainer("tr")
        soup_tr = BeautifulSoup(response, "html.parser", parse_only=strainer)

        for tr in soup_tr.find_all("tr"):
            tds = tr.find_all("td") if len(tr.find_all("td")) != 0 else None
            if tds is not None and len(tds) > 2:
                a_tag = None
                if (tds[1].text == "Route"):
                    a_tag = tds[0].find("a")
                if a_tag:
                    subnets.append(a_tag.text)
        return subnets


    #5. sanitize_subnets
    #En esta función eliminamos los duplicados de la lista y aplicamos regexp para quedarnos con las subnets IPV4
    def sanitize_subnets(self, subnets):
        #Eliminamos duplicados de la lista
        temp_subnets = []
        temp_subnets = list(set(subnets))

        #Aplicamos regexp para quedarnos con las subnets IPV4
        final_list_subnets = []
        pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}"
        [final_list_subnets.append(subnet) if re.match(pattern, subnet) is not None else None for subnet in temp_subnets]

        return final_list_subnets

    
    #6. remove_subsubnets
    #En esta función eliminamos las redes que sean subnets de otras redes de la lista, de esta forma evitaremos IPs duplicadas

    def remove_subsubnets(self, subnets):
        # Convertimos los strings a objetos ipaddress.IPv4Network
        networks = sorted([ipaddress.IPv4Network(subnet) for subnet in subnets], key=lambda x: x.prefixlen)

        filtradas = []
        for net in networks:
            # Si ninguna red en la lista filtrada contiene la actual la añadimos
            if not any(net.subnet_of(subnet) for subnet in filtradas):
                filtradas.append(net)

        filtradas_str = [str(subnet) for subnet in filtradas]
        return filtradas_str


    #Main
    async def main(self):
        print("Buscando nets... ")
        #1. Preparamos las URLs que usaremos para hacer las llamadas a bgpview.io y bgp.he.net
        url_bgpview, url_bgphe = self.prepare_urls()

        #2. Hacemos la request a bgpview.io
        subnets = await self.search_bgpview(url_bgpview)
        
        #3. Hacemos la request a bgp.he.net
        subnets = await self.search_bgphe(url_bgphe, subnets)

        #4. Eliminamos duplicados y nos quedamos con las redes IPV4 solamente
        subnets = self.sanitize_subnets(subnets)

        #5. Eliminamos redes que son subnets de otras redes
        subnets = self.remove_subsubnets(subnets)

        return subnets