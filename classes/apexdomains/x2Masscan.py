import os
import subprocess

class ExecMasscan:
    #1. Constructor __init__ y getters
    #Le pasamos los dos archivos por defecto que tendrá
    def __init__(self, masscan_results_file="files/masscanResults.txt", ips_file="files/ips.txt", masscan_rate=8000, interfaz_de_red="tun0"):
        self.masscan_results_file = masscan_results_file #Archivo donde se guardarán los resultados de masscan
        self.ips_file = ips_file #Archivo donde están las subnets a escanear
        self.masscan_rate = masscan_rate #Peticiones por segundo que hará masscan a un puerto hasta que conteste
        self.interfaz_de_red = interfaz_de_red #Interfaz de red por la que se ejecutará masscan, en este caso, tun0 (VPN)


    #2. check_and_create_files
    #Le pasamos un array de archivos a crear en caso de no estar creados ya
    def check_and_create_files(self, *file_paths):
        for file_path in file_paths:
            if not os.path.exists(file_path):
                with open(file_path, "w") as file:
                    pass 
    

    #3. exec_masscan
    # Función que ejecuta masscan contra las subnets definidas en files/ips.txt
    def exec_masscan(self):
        print("Ejecutando masscan...")
        try:
            command = f"sudo masscan -p443 --rate {self.masscan_rate} --wait 0 -e {self.interfaz_de_red} -sS -n -Pn -iL {self.ips_file} -oH {self.masscan_results_file} > /dev/null 2>&1"
            subprocess.run(command, shell=True, check=True)
        
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar masscan: {e}")

        except Exception as e:
            print(f"Error inesperado al ejecutar masscan {e}")


    #Main
    #Esta función llama a las demás subfunciones
    def main(self):
        self.check_and_create_files(self.masscan_results_file, self.ips_file)
        self.exec_masscan()