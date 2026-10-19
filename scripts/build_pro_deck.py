#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador Pro de Presentaciones Oficiales InnovaTecNM 2026 - FLUXA Smart Mobility
Genera presentaciones profesionales con diseño gráfico moderno, imágenes reales,
diagramas oficiales, cronómetro interactivo y renderizado a PDF 16:9.
"""

import os
import base64
import json
import subprocess

BASE_DIR = '/home/fluxa/fluxa-smart-city'
LOGOS_DIR = os.path.join(BASE_DIR, 'logos')
OPT_DIR = os.path.join(BASE_DIR, 'presentaciones/assets_opt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'presentaciones')
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
USER_PDF_DIR = '/home/fluxa/presentaciones_pdf'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(USER_PDF_DIR, exist_ok=True)

def b64_img(folder, filename, mime="image/png"):
    p = os.path.join(folder, filename)
    if os.path.exists(p):
        with open(p, 'rb') as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

# Logos
tesco_b64 = b64_img(LOGOS_DIR, 'tesco.png')
tecnm_b64 = b64_img(LOGOS_DIR, 'tecnm.png')
sic_b64 = b64_img(LOGOS_DIR, 'sic.png')

# Asset Images
fluxa_logo = b64_img(OPT_DIR, 'fluxa_official_logo.png')
traffic_img = b64_img(OPT_DIR, 'traffic_congestion_mexico.jpg', 'image/jpeg')
opi5_img = b64_img(OPT_DIR, 'orange_pi_5_hardware.png')
yolo_img = b64_img(OPT_DIR, 'yolo_detection_boxes.jpg', 'image/jpeg')
scada_img = b64_img(OPT_DIR, 'scada_dashboard_full.jpg', 'image/jpeg')
capex_chart = b64_img(OPT_DIR, 'capex_benchmark_chart.png')
bom_chart = b64_img(OPT_DIR, 'bom_cost_pie_chart.png')
rev_chart = b64_img(OPT_DIR, 'revenue_ramp_chart.png')
failsafe_img = b64_img(OPT_DIR, 'fail_safe_matrix.png')
pytest_img = b64_img(OPT_DIR, 'pytest_suite_approved.png')
trl_chart = b64_img(OPT_DIR, 'trl_maturity_chart.png')
indautor_img = b64_img(OPT_DIR, 'indautor_facade.jpg', 'image/jpeg')
sct_diag = b64_img(OPT_DIR, 'sct_intersection_diagram.png')
b2g_funnel = b64_img(OPT_DIR, 'b2g_adoption_funnel.png')
report_pdf = b64_img(OPT_DIR, 'official_report_pdf.jpg', 'image/jpeg')
delay_chart = b64_img(OPT_DIR, 'delay_reduction_corridor.png')

def make_header(category="INDUSTRIA ELÉCTRICA Y ELECTRÓNICA"):
    return f"""
    <div class="slide-header">
        <div class="brand-cluster">
            <img src="{tecnm_b64}" alt="TecNM" class="logo-inst logo-tecnm">
            <img src="{tesco_b64}" alt="TESCo" class="logo-inst logo-tesco">
            <img src="{sic_b64}" alt="SIC" class="logo-inst logo-sic">
            <div class="brand-divider"></div>
            <img src="{fluxa_logo}" alt="FLUXA" class="logo-fluxa">
        </div>
        <div class="event-stamp">
            <div class="event-title">InnovaTecNM 2026 • Etapa Regional</div>
            <div class="event-sub">Región 5 • Folio: <span class="tag-folio">70785-17</span> | {category}</div>
        </div>
    </div>
    """

print("Assets ready.")
