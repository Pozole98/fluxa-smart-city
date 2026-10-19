#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script compilador de Presentaciones Oficiales InnovaTecNM 2026 para FLUXA
Genera los archivos HTML autoportantes con logos en Base64, gráficos SVG,
temporizador interactivo y notas del orador integradas.
"""

import os
import base64
import json

BASE_DIR = '/home/fluxa/fluxa-smart-city'
LOGOS_DIR = os.path.join(BASE_DIR, 'logos')
OUTPUT_DIR = os.path.join(BASE_DIR, 'presentaciones')
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

def get_base64(name):
    p = os.path.join(LOGOS_DIR, name)
    if os.path.exists(p):
        with open(p, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

tesco_img = get_base64('tesco.png')
tecnm_img = get_base64('tecnm.png')
sic_img = get_base64('sic.png')

print("Generando presentaciones...")
