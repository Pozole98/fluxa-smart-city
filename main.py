#!/usr/bin/env python3
import os
import sys

# Asegurar que 'src' esté en el path de módulos
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cli import ejecutar_cli

if __name__ == "__main__":
    ejecutar_cli()
