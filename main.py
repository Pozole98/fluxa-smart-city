#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Punto de entrada principal para la ejecución del sistema vía interfaz de línea de comandos (CLI).
Desarrollador Principal y Titular de Derechos: Moisés Emilio Martínez Arias
Todos los derechos reservados © 2026.
"""

import os
import sys
import logging

# Configuración del formato de registro para auditoría y telemetría
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Incorporar el directorio 'src' al path de resolución de módulos
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cli import ejecutar_cli

if __name__ == "__main__":
    ejecutar_cli()
