#!/bin/bash

# Instalar dependencias básicas
sudo apt update
sudo apt install -y git

# Preguntar al usuario si quiere instalar la última versión de Go
read -p "¿Quieres instalar la última versión de Go? (s/n): " respuesta
if [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ]; then
    echo "Instalando Go 1.22.1..."
    wget https://go.dev/dl/go1.22.1.linux-amd64.tar.gz
    sudo tar -C /usr/local -xzf go1.22.1.linux-amd64.tar.gz
    rm go1.22.1.linux-amd64.tar.gz
    export PATH=/usr/local/go/bin:$PATH
else
    echo "Usando la versión de Go existente en el sistema..."
fi

# Verificar versión de Go
go version

# Leer el archivo tools.txt
while IFS= read -r tool; do
  case $tool in
    "masscan")
      sudo apt install -y masscan || {
        git clone https://github.com/robertdavidgraham/masscan.git
        cd masscan
        make
        sudo make install
        cd ..
      }
      ;;
    "smap")
      git clone https://github.com/s0md3v/smap.git
      cd smap
      go build ./cmd/smap
      sudo mv smap /usr/local/bin/
      cd ..
      ;;
    "assetfinder")
      git clone https://github.com/tomnomnom/assetfinder.git
      cd assetfinder
      go mod init github.com/tomnomnom/assetfinder
      go build
      sudo mv assetfinder /usr/local/bin/
      cd ..
      ;;
    "certgraph")
      git clone https://github.com/lanrat/certgraph.git
      cd certgraph
      go build
      sudo mv certgraph /usr/local/bin/
      cd ..
      ;;
    "subfinder")
      go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
      sudo mv ~/go/bin/subfinder /usr/local/bin/ || echo "Error moviendo subfinder, verifica ~/go/bin/"
      ;;
    *)
      echo "Herramienta desconocida: $tool"
      ;;
  esac
done < tools.txt

echo "Instalación completada."