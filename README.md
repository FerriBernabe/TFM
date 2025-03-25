Esta herramienta pretende enumerar los servicios web de una organización, presentando los datos recopilados en una interfaz web. Para lograrlo, combina técnicas de eumeración pasivas y activas, aprovechando datos de fuentes abiertas también. Si se quiere saber más sobre las técnicas que se usan y como ha sido creada la herramienta se puede leer la documentación. Si solo se desea ejecutar la herramienta, en este apartado explicaré como instalarla y ejecutarla con sus distintos modos de ejecución.

## Instalación
La herramienta usa otras herramientas externas y tiene algunas dependencias en cuanto a librerías, es por este motivo que se han creado algunos archivos de instalación.
Para instalar la herramienta hay que seguir los siguientes pasos:
1. Clonar el repositorio:
   
![image](https://github.com/user-attachments/assets/8112d149-76cf-4ddf-ae75-cbd6ff0c2c26)

2. Acceder a la carpeta “installation”:
   
![image](https://github.com/user-attachments/assets/c74c04e3-a427-48bf-a433-2c3dfeab52b5)

3. Instalar los “requirements”:
   
![image](https://github.com/user-attachments/assets/6f285d78-9a4a-49d9-a1af-538e7ce4d104)

4. Ejecutar el script “install_tools.sh”:
   
![image](https://github.com/user-attachments/assets/33a30ae7-600c-45ed-9dd8-9610d8b2827f)

![image](https://github.com/user-attachments/assets/4bc6ba02-b39c-431c-b25b-a90524ee717b)


## Ejecución
En primer lugar, cabe destacar que dependiendo de la interfaz de red que se quiera usar (para ejecutar Masscan) se deberá hacer un pequeño cambio en una variable del código. Como Masscan hace muchas peticiones por segundo debido al rate que se le da, se recomienda usar una VPN para ejecutar la herramienta. Por este motivo, por defecto, la herramienta usar la interfaz tun0 para esta clase. Si se desea usar otra interfaz, por ejemplo "enp0s3", se deberá hacer el cambio de la siguiente forma:

![image](https://github.com/user-attachments/assets/49cf699f-5a0a-4ce5-a15b-7c6f0e325167)

### Modo de ejecución por nombre
En este modo de ejecución, el analista proporciona el nombre de la organización y la herramienta enumerará las redes IPv4 de esta. La herramienta se apoya en las páginas de bgp.he.net y bgpview.io, por lo que es recomendable echarle un ojo a estas páginas antes de ejecutar la herramienta. Para evitar falsos positivos, podríamos mirar en bgp.he.net, por ejemplo, si buscamos "booking":

![image](https://github.com/user-attachments/assets/90a0fab0-67e4-49bd-b877-b12f175c59b2)

Si quisiéramos enumerar solo las redes de "Booking.com BV":

![image](https://github.com/user-attachments/assets/0feb1220-e1b2-4c81-98cb-6c18c64b2214)

Por tanto, la cadena que se le pasa a la herramienta se podría ver de estas formas en ambos casos:

![image](https://github.com/user-attachments/assets/1b74a73a-882e-4f40-9b3d-5af7a0571a7a)
![image](https://github.com/user-attachments/assets/5967d26e-a742-45ef-9bf2-da2666dfd89e)

El resultado final si la herramienta se ejecuta correctamente será el siguiente:

![image](https://github.com/user-attachments/assets/2484cf4a-3ddb-47e0-926e-6c0068f77096)


En cuanto a los modos de ejecución, el corto se limitará a escanear las redes IPv4 pero no enumerará subdominios fuera de estas redes ni tampoco intentará encontrar virtual hosts de forma pasiva. El modo medio escaneará las redes IPv4, enumerará subdominios estén o no dentro de estas redes, pero no empleará técnicas para encontrar virtual hosts de forma pasiva. Finalmente, el modo largo hará todos los pasos, intentando encontrar virtual hosts basados en relaciones de certificados y en semejanza. 

### Modo de ejecución proporcionando las redes IPv4
Si no se quiere pasar el nombre de la organización ya sea porque no se encuentra la cadena exacta a usar o porque solo se quiere enumerar alguna red IPv4 en concreto, se pueden proporcionar las redes a analizar en el archivo "files/ips.txt". Por ejemplo:

![image](https://github.com/user-attachments/assets/0f39bd5c-d335-4858-8636-39e7fc2e6280)

La ejecución de este modo se verá de la siguiente forma:

![image](https://github.com/user-attachments/assets/25909ed5-8d61-4c2a-91f1-afce302c8cc8)

### Modo de ejecución proporcionando dominios
En este modo de ejecución el analista proporciona los dominios a analizar y la herramienta expandirá la superfície de ataque, encotrando subdominios y también virtual hosts de forma pseudo-pasiva (si se selecciona el método de ejecución largo).
El analista tendrá que proporcionar los dominios en el archivo "files/subdomains.txt":

![image](https://github.com/user-attachments/assets/28fa41a4-1cf2-45c4-852b-7c06c4680e8c)

La ejecución de este modo se ve de la siguiente forma:

![image](https://github.com/user-attachments/assets/9b59561d-6a0d-4f3d-8244-5775dc473aca)



