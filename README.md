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


