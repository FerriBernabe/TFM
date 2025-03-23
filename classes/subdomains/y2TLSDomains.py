import re
import asyncio
import ssl
from OpenSSL import crypto

class ExtractTLSDomains:
    #1. Constructor __init__ y getters
    #Le pasamos los dos archivos por defecto que tendrá
    def __init__(self, ip_and_CN=None, chunk_size=2000, timeout=3, ssl_port=443):
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.ssl_port = ssl_port
        self.ip_and_CN = ip_and_CN


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
        try:
            #Recorremos las claves de ip_and_CN y llamamos a fetch_certificates para cada IP
            #Para mayor velocidad de requests http para obtener el TLS, usaremos aiohttp de forma concurrente
            #Haremos las peticiones por grupos, para no hacer todas las peticiones a la vez

            #Ponemos las IPs en una lista
            keys_list = list(self.ip_and_CN.keys())

            for i in range(0, len(keys_list), self.chunk_size):
                #Pillamos las IPs de chunk_size en chunk_size (2000 en 2000)
                chunk_of_ips = keys_list[i:i+self.chunk_size]

                if not chunk_of_ips:
                    break

                #Ahora haremos las peticiones HTTPS para obtener los certificados TLS y los CN y *SAN* 
                #Lo haremos de forma concurrente para mayor velocidad
                chunk_results = await asyncio.gather(*[self.fetch_certificates(ip) for ip in chunk_of_ips])

                #Ahora tratamos las respuestas de fetch_certificates para evitar duplicados en ip_and_CN
                for ip, cert_data in chunk_results:
                    #Si los CN coinciden, añadimos los SAN de cert_data que no estén duplicados
                    if self.ip_and_CN[ip]['CN'] == cert_data['CN']:
                        for subdomain in cert_data['SAN']:
                            if subdomain not in self.ip_and_CN[ip]['SAN']:
                                if "www." in subdomain:
                                    if subdomain.split("www.",1)[1] not in self.ip_and_CN[ip]['SAN'] and subdomain.split("www.",1)[1] != self.ip_and_CN[ip]['CN']:
                                        self.ip_and_CN[ip]['SAN'].append(subdomain)
                                else:
                                    self.ip_and_CN[ip]['SAN'].append(subdomain)
                    else:
                        #Si los CN no coinciden, ponemos como CN el de cert_data, añadimos el antiguo a los SAN (si no está) y añadimos los SAN de cert_data que no estén duplicados
                        cn_old = self.ip_and_CN[ip]['CN']
                        if cert_data['CN'] != ' ':
                            self.ip_and_CN[ip]['CN'] = cert_data['CN']

                            for subdomain in cert_data['SAN']:
                                if subdomain not in self.ip_and_CN[ip]['SAN']:
                                    if "www." in subdomain:
                                        if subdomain.split("www.",1)[1] not in self.ip_and_CN[ip]['SAN'] and subdomain.split("www.",1)[1] != self.ip_and_CN[ip]['CN']:
                                            self.ip_and_CN[ip]['SAN'].append(subdomain)
                                    else:
                                        self.ip_and_CN[ip]['SAN'].append(subdomain)

                        for subdomain in cert_data['SAN']:
                            if subdomain not in self.ip_and_CN[ip]['SAN']:
                                if "www." in subdomain:
                                    if subdomain.split("www.",1)[1] not in self.ip_and_CN[ip]['SAN'] and subdomain.split("www.",1)[1] != self.ip_and_CN[ip]['CN']:
                                        self.ip_and_CN[ip]['SAN'].append(subdomain)
                                else:
                                    self.ip_and_CN[ip]['SAN'].append(subdomain)

                    #Añadimos el puerto 443 en los Ports
                    self.ip_and_CN[ip]['Ports'].append(443)

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
    def clean_SAN(self):
        # Iteramos sobre el diccionario y limpiamos SANs
        for ip, data in self.ip_and_CN.items():
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


    #4. clean_CN
    #La idea de esta parte es limpiar los CN, comprobando que sean dominios válidos.
    def clean_CN(self):
        for ip, data in self.ip_and_CN.items():
            # Se obtiene el CN y se valida
            cn_value = data.get('CN', '')
            sanitized_cn = self.sanitize_domain(cn_value)
            # Si el CN no es válido, se asigna cadena vacía
            data['CN'] = sanitized_cn if sanitized_cn is not None else ''


    #Main
    async def main(self):
        await self.extract_domains()
        self.clean_SAN()
        self.clean_CN()
        return self.ip_and_CN