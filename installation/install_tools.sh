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
      git clone https://github.com/s0md3v/smap.git
      cd smap
      go build ./cmd/smap
      sudo mv smap /usr/local/bin/
      cd ..
      ;;
    "assetfinder")
      git clone https://github.com/tomnomnom/assetfinder.git
      cd assetfinder
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
      git clone https://github.com/projectdiscovery/subfinder.git
      cd subfinder/v2/cmd/subfinder
      go build
      sudo mv subfinder /usr/local/bin/
      cd ../../..
      ;;
    *)
      echo "Herramienta desconocida: $tool"
      ;;
  esac
done < tools.txt

echo "Instalación completada."