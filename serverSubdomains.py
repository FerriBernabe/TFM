import asyncio
import os
import re
import sqlite3
import json
import time

from classes.subdomains.y1GetSubdomainsPassive import SubdomainsPassive
from classes.subdomains.y2TLSDomains import ExtractTLSDomains
from classes.subdomains.y3Smap import Smap
from classes.subdomains.y4GetVhostsPassive import VhostsPassive
from classes.subdomains.y5CheckWebPorts import WebPorts

async def main():
    # Pedir método de ejecución al inicio
    metodo = input("Elija método de ejecución (1: corto, 2: largo): ").strip()
    while metodo not in ['1', '2']:
        print("Opción inválida. Por favor, elija 1 o 2")
        metodo = input("Elija método de ejecución (1: corto, 2: largo): ").strip()

    #Recopilamos los subdominios de files/subdomains.txt
    subdomains_file = "files/subdomains.txt"

    #Miramos que el archivo tenga contenido
    with open(subdomains_file, "r") as file:
        if len(file.read()) == 0:
            print("El archivo files/subdomains.txt no tiene contenido!")
            return
        else:
            #Comprobamos que cada línea sea un subdominio válido
            list_domains = []
            domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

            with open(subdomains_file, "r") as file:
                for line in file:
                    # Elimina espacios en blanco y verifica la línea
                    line = line.strip()
                    if re.match(domain_pattern, line):
                        list_domains.append(line)


    #Extraemos subdominios de forma pasiva (aunque los resolveremos via DNS)
    subdomainspassive = SubdomainsPassive(list_domains=list_domains)
    ip_and_CN, subdomains_dns_noanswer = await subdomainspassive.main()

    # Extraemos dominios usando TLS
    extract_tlsdomains = ExtractTLSDomains(ip_and_CN=ip_and_CN)
    ip_and_CN = await extract_tlsdomains.main()

    #Extraemos info pasiva usando Smap
    smap = Smap(ip_and_CN=ip_and_CN)
    ip_and_CN = smap.main()

    if metodo == '2':
        #Extraemos vhosts de forma pasiva
        vhostspassive = VhostsPassive(ip_and_CN=ip_and_CN, subdomains_dns_noanswer=subdomains_dns_noanswer)
        ip_and_CN = await vhostspassive.main()

    #Extraemos información de las puertos web
    webports = WebPorts(ip_and_CN=ip_and_CN)
    web_responses = await webports.main()

    #Guardamos los datos en sqlite
    # Conexión a SQLite (crea la base de datos si no existe)
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