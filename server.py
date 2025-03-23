import subprocess

def run_script(script_name):
    """
    Ejecuta el script especificado usando subprocess.
    """
    try:
        print(f"Ejecutando {script_name}...")
        # Llama al script utilizando subprocess.run
        result = subprocess.run(["python3", script_name], check=True)
        if result.returncode == 0:
            print(f"{script_name} se ejecutó correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"Ocurrió un error al ejecutar {script_name}: {e}")
    except FileNotFoundError:
        print(f"No se encontró el archivo {script_name}. Asegúrate de que existe y está en el directorio actual.")

def main():
    """
    Función principal que solicita al usuario qué script ejecutar.
    """
    print("¿Qué script deseas ejecutar?")
    print("1. serverApexdomains.py")
    print("2. serverSubdomains.py")

    choice = input("Selecciona una opción (1/2): ").strip()

    if choice == "1":
        run_script("serverApexdomains.py")
    elif choice == "2":
        run_script("serverSubdomains.py")
    else:
        print("Opción no válida. Por favor, selecciona 1 o 2.")

if __name__ == "__main__":
    main()