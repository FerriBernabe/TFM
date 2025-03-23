import asyncio
import os
import re
import sqlite3
import json
import time

from classes.apexdomains.x1GetNets import GetNets
from classes.apexdomains.x2Masscan import ExecMasscan
from classes.apexdomains.x3TLSDomains import ExtractTLSDomains
from classes.apexdomains.x4Smap import Smap
from classes.apexdomains.x5GetSubdomainsPassive import SubdomainsPassive
from classes.apexdomains.x6GetVhostsPassive import VhostsPassive
from classes.apexdomains.x7CheckWebPorts import WebPorts

async def main():
    # Pedir método de ejecución al inicio
    metodo = input("Elija método de ejecución (1: corto, 2: medio, 3: largo): ").strip()
    while metodo not in ['1', '2', '3']:
        print("Opción inválida. Por favor, elija 1, 2 o 3.")
        metodo = input("Elija método de ejecución (1: corto, 2: medio, 3: largo): ").strip()

    # Preguntar si usar GetNets o el archivo ips.txt
    use_GetNets = input("Encontrar subnets (0) / Usar redes definidas en files/ips.txt (1): ")
    ips_file = "files/ips.txt"
    masscan_results_file = "files/masscanResults.txt"

    if use_GetNets == "0":
        # Ejecutamos GetNets y volcamos las subnets si las hemos encontrado en files/ips.txt
        companyName = input("Nombre de la empresa: ")
        get_nets = GetNets(f"{companyName}")
        subnets = []
        subnets = await get_nets.main()
        
        if len(subnets) == 0:
            print("No se han encontrado subnets para ese nombre. Pon otro nombre o pon las redes directamente en files/ips.txt")
            return
        else:
            with open(ips_file, "w") as file:
                [file.write(f"{subnet}\n") for subnet in subnets]
                print("Subnets encontradas!")
    
    elif use_GetNets == "1":
        # Miramos que el archivo exista
        if os.path.exists(ips_file):
            with open(ips_file, "r") as file:
                # Miramos que el archivo tenga contenido
                if len(file.read()) == 0:
                    print("El archivo files/ips.txt no tiene contenido!")
                    return
                else:
                    # Comprobamos que cada línea sea un rango de red IPV4 válido
                    with open(ips_file, "r") as file:
                        content = file.read()

                    # Comprobamos que cada línea sea una IP válida y si no lo es la eliminamos del archivo
                    ip_pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}"
                    ip_nets = re.findall(ip_pattern, content)
                    with open(ips_file, "w") as file:
                        [file.write(f"{subnet}\n") for subnet in ip_nets]
        else:
            print("El archivo files/ips.txt no existe!")
            return

    # Ejecutamos masscan para ver los hosts con puerto 443 activos
    exec_masscan = ExecMasscan()
    exec_masscan.main()

    # Extraemos dominios usando TLS
    extract_tlsdomains = ExtractTLSDomains(ips_file=ips_file, masscan_results_file=masscan_results_file)
    ip_and_CN = await extract_tlsdomains.main()

    # Extraemos info pasiva usando Smap (común a todos los métodos)
    smap = Smap(ip_and_CN=ip_and_CN)
    ip_and_CN = smap.main()

    # Lógica condicional según el método elegido
    if metodo in ['2', '3']:
        # Extraemos subdominios de forma pasiva (para métodos 2 y 3)
        subdomainspassive = SubdomainsPassive(ip_and_CN=ip_and_CN)
        ip_and_CN, subdomains_dns_noanswer = await subdomainspassive.main()

    if metodo == '3':
        # Extraemos vhosts de forma pasiva (solo para método 3)
        vhostspassive = VhostsPassive(ip_and_CN=ip_and_CN, subdomains_dns_noanswer=subdomains_dns_noanswer)
        ip_and_CN = await vhostspassive.main()

    # Extraemos información de los puertos web (final para todos los métodos)
    webports = WebPorts(ip_and_CN=ip_and_CN)
    web_responses = await webports.main()

    # Guardamos los datos en SQLite
    conn = sqlite3.connect("db/web_responses.db")
    cursor = conn.cursor()

    # Crear la tabla para almacenar las respuestas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses (
        ip TEXT,
        data JSON
    )
    ''')

    # Limpiar la tabla antes de insertar nuevos datos
    print("Borrando la base de datos anterior...")
    cursor.execute("DELETE FROM responses")
    conn.commit()

    # Insertar los datos en la base de datos
    for response in web_responses:
        for ip, data in response.items():
            json_data = json.dumps(data)  # Convertir a JSON
            cursor.execute("INSERT INTO responses (ip, data) VALUES (?, ?)", (ip, json_data))

    # Confirmar los cambios
    conn.commit()

    # Guardar los datos en un archivo JSON
    with open("db/web_responses.json", "w") as json_file:
        json.dump(web_responses, json_file, indent=4)

    # Cerrar la conexión
    conn.close()

    print("Datos guardados en la base de datos y archivo JSON.")

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Tiempo de ejecución: {execution_time:.2f} segundos")