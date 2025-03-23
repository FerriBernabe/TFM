import subprocess
import re
import json
import os

class Smap:
    #1. Constructor __init__
    #Le pasamos el diccionario ip_and_CN
    def __init__(self, ips_file="files/ips_temp.txt", ip_and_CN=None):
        self.ips_file = ips_file
        self.ip_and_CN = ip_and_CN


    #fill_ips_temp -> Ponemos las IPs enumeradas en un archivo temporal
    def fill_ips_temp(self):
        # Verificar si el archivo existe antes de intentar eliminarlo
        if os.path.exists(self.ips_file):
            os.remove(self.ips_file)

        with open(self.ips_file, "w") as file:
            for key in self.ip_and_CN.keys():
                file.write(key + "\n")


    #2. gather_smap
    #La idea de la función es ejecutar smap sobre files/ips.txt para recopilar información de Shodan del objetivo y complementar la información que tenemos ya de las redes objetivo

    #2.1. exec_smap -> Ejecutamos smap sobre el fichero files/ips.txt
    def exec_smap(self):
        try:
            command = f"smap -iL {self.ips_file} -oJ - 2>/dev/null"
            resultado = subprocess.run(command, shell=True, capture_output=True, text=True)
            return resultado.stdout
        except Exception as e:
            print(f"Error en la función exec_smap: {e}")
        
        return None


    #2.2. add_ip_from_smap -> Añadimos a ip_and_CN el diccionario pillado de smap_output. Esta función se llamará cuando la ip de smap_output no exista en ip_and_cn
    def add_ip_from_smap(self, entrada_smap):
        try:
            dict_to_add = {"CN": None, "SAN": [], "Ports": []}
            san = []

            #Comprobamos que la IP sea válida
            ip_pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            if re.match(ip_pattern, entrada_smap['ip']) is not None:
                #Comprobamos que los hostnames sean correctos y los añadimos a dict_to_add
                    hostnames = entrada_smap['hostnames']
                    for i, hostname in enumerate(hostnames):
                        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        if re.match(domain_pattern, hostname) is not None:
                            if i == 0:
                                if "www." in hostname:
                                    hostname = hostname.split("www.",1)[1]
                                dict_to_add["CN"] = hostname
                            else:
                                if "www." in hostname:
                                    if hostname.split("www.",1)[1] not in san and hostname.split("www.",1)[1] != dict_to_add["CN"]:
                                        san.append(hostname)
                                else:
                                    san.append(hostname)
            
            dict_to_add['SAN'] = san
            
            #Añadimos los puertos al dict_to_add
            ports = []

            if len(entrada_smap['ports']) > 0:
                for port in entrada_smap['ports']:
                    ports.append(port['port'])
            else:
                ports = [443]

            dict_to_add["Ports"] = ports

            #Si el CN de dict_to_add no es None añadimos el dict_to_add a self.ip_and_CN, si no miramos si el SAN no está vacío y los ports no están vacíos y añadimos el dict_to_add a self.ip_and_CN
            if dict_to_add["CN"] is not None:
                self.ip_and_CN[entrada_smap['ip']] = dict_to_add
            else:
                if len(dict_to_add["SAN"]) > 0 or len(dict_to_add["Ports"]) > 0:
                    dict_to_add["CN"] = " "
                    self.ip_and_CN[entrada_smap['ip']] = dict_to_add

        except Exception as e:
            print(f"Error en la función add_ip_from_smap: {e}")

    
    #2.3. check_hostnames -> Comparamos los hostnames de entrada_smap con el CN y SAN que tenemos. Si ninguno de nuestros CN o SAN está en los hostnames devolveremos false. Si alguno existe en los hostnames, devolveremos true.
    def check_hostnames(self, entrada_smap):
        trobat = False
        cn = self.ip_and_CN[entrada_smap['ip']]['CN']
        san = self.ip_and_CN[entrada_smap['ip']]['SAN']
        hostnames = entrada_smap['hostnames']

        #Miramos si el CN está en los hostanmes
        if cn in hostnames:
            return True
        else:
            #Si no está el CN, miramos si algún SAN está en los hostnames
            for subdominio in san:
                if subdominio in hostnames:
                    return True
        
        #Si ni el CN ni los SAN estan en los hostnames, deolvemos False
        return False

    
    #2.4. add_hostnames -> Añadimos los hostnames que no estén en el SAN ni CN
    def add_hostnames(self, entrada_smap):
        ip_data = self.ip_and_CN[entrada_smap['ip']]
        cn = ip_data['CN']
        san = ip_data['SAN']

        # Expresión regular para validar dominios
        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        for hostname in entrada_smap['hostnames']:
            if not re.match(domain_pattern, hostname):
                continue  # Si el hostname no es válido, lo ignoramos
                
            if hostname != cn and hostname not in san:
                if "www." in hostname:
                    if hostname.split("www.",1)[1] not in san and hostname.split("www.",1)[1] != cn:
                        san.append(hostname)
                else:
                    san.append(hostname)


    #2.5. add_ports -> Añadimos los ports si hay, si no hay añadimos solo el 443 (enumerado antes con Masscan)
    def add_ports(self, entrada_smap):
        ip_data = self.ip_and_CN[entrada_smap['ip']]
        ports = []

        if len(entrada_smap['ports']) > 0:
            for port in entrada_smap['ports']:
                ports.append(port['port'])
            if 443 not in ports:
                ports.append(443)
            ip_data['Ports'] = ports
        else:
            ip_data['Ports'] = [443]

    
    #2.6 gather_smap
    def gather_smap(self):
        print("Ejecutando Smap...")
        #Ejecutamos el exec_smap
        smap_output = self.exec_smap()

        #Recorremos cada entrada del smap_output
        smap_json = json.loads(smap_output)
        for entrada_smap in smap_json:
            if entrada_smap['ip'] in self.ip_and_CN:
                #Miramos si el CN o los SAN de la ip están en los hostnames
                if self.check_hostnames(entrada_smap):
                    #Si el CN o SAN están en los hostnames, añadimos los hostnames que no estén en el SAN
                    self.add_hostnames(entrada_smap)
                    #Añadimos también los puertos
                    self.add_ports(entrada_smap)
                else:
                    #Si ni el CN ni los SAN están, le añadimos los puertos enumerados con smap y el puerto 443 si no está (enumerado con masscan a self.ip_and_CN)
                    ports = []

                    if len(entrada_smap['ports']) > 0:
                        for port in entrada_smap['ports']:
                            ports.append(port['port'])
                        if 443 not in ports:
                            ports.append(443)
                    else:
                        if 443 not in ports:
                            ports.append(443)
                    self.ip_and_CN[entrada_smap['ip']]['Ports'] = ports
            else:
                #Si la IP no está en nuestro diccionario la añadimos a self.ip_and_CN (llamando a la función add_ip_from_smap)
                self.add_ip_from_smap(entrada_smap)

        #Si Smap no ha detectado alguna IP, le ponemos el puerto 443 que le pertoca
        for data in self.ip_and_CN.values():
            if 'Ports' not in data:
                data['Ports'] = [443]

    

    #3. Unique_ips -> Función que limpia IPs distintas con la misma información (típico de balanceadores de carga)
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



    #Main
    def main(self):
        self.fill_ips_temp()
        self.gather_smap()
        self.unique_ips()
        
        #Eliminamos el archivo temporal
        if os.path.exists(self.ips_file):
            os.remove(self.ips_file)

        return self.ip_and_CN