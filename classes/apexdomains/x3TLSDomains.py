import re
import asyncio
import ssl
from OpenSSL import crypto

class ExtractTLSDomains:
    #1. Constructor __init__ y getters
    #Le pasamos los dos archivos por defecto que tendrá
    def __init__(self, ips_file="files/ips.txt", masscan_results_file="files/masscanResults.txt", chunk_size=2000, timeout=3, ssl_port=443):
        self.ips_file = ips_file
        self.masscan_results_file = masscan_results_file
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.ssl_port = ssl_port
    

    #2. extract_domains
    #La idea será recopilar los dominios que encontremos en los certificados TLS de cada IP recopilada anteriormente con Masscan

    #2.1. fetch_certificate -> función que recopilará los CN de los certificados TLS
    async def fetch_certificates(self, ip):
        try:
            temp_dict = {"CN": None, "SAN": []}
            #Pillamos el certificado TLS y extreamos el Common Name
            cert = await asyncio.to_thread(ssl.get_server_certificate,(ip, self.ssl_port), timeout=self.timeout) #Llamamos a get_server_certificate via to_thread porque es síncrona, y to_thread la vuelve asíncrona
            cert_x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
            subject = cert_x509.get_subject()
            common_name = subject.CN
            if common_name is None:
                common_name = ' '
            if "www." in common_name:
                common_name = common_name.split("www.",1)[1]
            temp_dict['CN'] = common_name

            #Ahora extraemos los SAN
            for i in range(cert_x509.get_extension_count()):
                ext = cert_x509.get_extension(i)
                if ext.get_short_name() == b'subjectAltName':
                    # Obtener los SAN y dividirlos en una lista
                    san_list = str(ext).split(', ')
                    temp_dict['SAN'] = san_list
                    break

            return ip,temp_dict

        except Exception as e:
            #print(f"Error en TLSDomains en el fetch_certificate : {e}")
            pass
        
        return ip, {"CN": ' ', "SAN": []} #Esto es para que si no encuentra un Common Name o SAN, nos envíe la IP con un empty string ya que probablemente haremos peticiones al puerto HTTP después


    #2.2. extract_domains -> Función principal
    async def extract_domains(self):
        print("Recopilando certificados TLS...")
        #Vamos a recorrer cada IP con puerto 443 activa que hayamos encontrado con Masscan
        try:
            with open(self.masscan_results_file, "r") as file:
                content = file.read()

            #Comprobamos que cada línea de la variable content sea una IP válida
            ip_pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            ip_addresses = re.findall(ip_pattern, content)

            ip_and_CN = {}

            #Para mayor velocidad de requests http para obtener el TLS, usaremos aiohttp de forma concurrente
            #Haremos las peticiones por grupos, para no hacer todas las peticiones a la vez
            for i in range(0, len(ip_addresses), self.chunk_size):
                #Pillamos las IPs de chunk_size en chunk_size (2000 en 2000)
                chunk_of_ips = ip_addresses[i:i+self.chunk_size]

                #Ahora haremos las peticiones HTTPS para obtener los certificados TLS y los CN y *SAN* 
                #Lo haremos de forma concurrente para mayor velocidad
                chunk_results = await asyncio.gather(*[self.fetch_certificates(ip) for ip in chunk_of_ips])
                for ip, cert_data in chunk_results:
                    ip_and_CN[ip] = cert_data
            
            return ip_and_CN

        except Exception as e:
            print(f"Error en TLSDomains en la función principal : {e}")

    
    #3. clean_SAN
    #La idea de esta parte es limpiar los SAN, comprobando que sean dominios válidos. Además miraremos que no estén repetidos del CN.

    #3.1. sanitize_domains() -> Validamos que los dominios en los SAN sean válidos
    def sanitize_domain(self, domain):
        #Comprobamos si el dominio empieza por DNS: -> Suele ser típico de los certs
        coincidencias = ["DNS:"]
        for coincidencia in coincidencias:
            if coincidencia in domain:
                domain = domain.replace(coincidencia, '')
                break
        
        #Miramos si el dominio es válido
        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(domain_pattern, domain) is not None:
            return domain
        return None


    #3.2. check_san_cn() -> Validamos que el SAN no sea igual que el CN o que sea igual + www.
    def check_san_cn(self, cn, domain):
        web_domain = "www." + cn
        if domain != cn:
            if web_domain != domain:
                return domain
        return None


    #3.3 remove_web_san -> Borramos de la lista SAN los dominios que estén duplicados con www. delante
    def remove_web_san(self, checked_san):
        new_checked_san = []
        
        for subdomain in checked_san:
            if "www." in subdomain:
                if subdomain.split("www.",1)[1] not in checked_san:
                    new_checked_san.append(subdomain)
            else:
                new_checked_san.append(subdomain)
        
        return new_checked_san


    # 3.4. clean_SAN() -> Función principal
    def clean_SAN(self, ip_and_CN):
        # Iteramos sobre el diccionario y limpiamos SANs
        for ip, data in ip_and_CN.items():
            cleaned_san_list = []
            for san in data.get('SAN', []):
                sanitized_san = self.sanitize_domain(san)
                if sanitized_san is not None:
                    checked_san = self.check_san_cn(data['CN'], sanitized_san)
                    if checked_san is not None:
                        cleaned_san_list.append(checked_san)

            # Actualizamos la lista SAN limpia
            cleaned_san_list = self.remove_web_san(cleaned_san_list)
            data['SAN'] = cleaned_san_list
        
        return ip_and_CN


    #4. clean_CN
    #La idea de esta parte es limpiar los CN, comprobando que sean dominios válidos.
    def clean_CN(self, ip_and_CN):
        for ip, data in ip_and_CN.items():
            # Se obtiene el CN y se valida
            cn_value = data.get('CN', '')
            sanitized_cn = self.sanitize_domain(cn_value)
            # Si el CN no es válido, se asigna cadena vacía
            data['CN'] = sanitized_cn if sanitized_cn is not None else ''
        return ip_and_CN


    #Main
    async def main(self):
        ip_and_CN = await self.extract_domains()
        ip_and_CN = self.clean_SAN(ip_and_CN)
        ip_and_CN = self.clean_CN(ip_and_CN)
        return ip_and_CN