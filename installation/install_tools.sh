#!/bin/bash

# Instalar dependencias básicas
sudo apt update
sudo apt install -y git golang

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
      go install github.com/s0md3v/smap@latest
      ;;
    "assetfinder")
      go install github.com/tomnomnom/assetfinder@latest
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
      ;;
    *)
      echo "Herramienta desconocida: $tool"
      ;;
  esac
done < tools.txt

echo "Instalación completada."
