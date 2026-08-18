#!/usr/bin/env python3
import os
import sys
import logging

# Configuración global de Logging Estructurado (P2.3)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Asegurar que 'src' esté en el path de módulos
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cli import ejecutar_cli

if __name__ == "__main__":
    ejecutar_cli()

