#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import base64
from PIL import Image

ASSETS_DIR = '/home/fluxa/fluxa-smart-city/presentaciones/assets'
OPT_DIR = '/home/fluxa/fluxa-smart-city/presentaciones/assets_opt'
os.makedirs(OPT_DIR, exist_ok=True)

files = [
    ('fluxa_official_logo.png', 400, 400, 'PNG'),
    ('traffic_congestion_mexico.png', 900, 600, 'JPEG'),
    ('orange_pi_5_hardware.png', 700, 700, 'PNG'),
    ('yolo_detection_boxes.png', 900, 506, 'JPEG'),
    ('scada_dashboard_full.png', 950, 534, 'JPEG'),
    ('capex_benchmark_chart.png', 800, 480, 'PNG'),
    ('bom_cost_pie_chart.png', 750, 600, 'PNG'),
    ('revenue_ramp_chart.png', 800, 480, 'PNG'),
    ('fail_safe_matrix.png', 900, 420, 'PNG'),
    ('pytest_suite_approved.png', 850, 430, 'PNG'),
    ('trl_maturity_chart.png', 800, 450, 'PNG'),
    ('indautor_facade.png', 750, 420, 'JPEG'),
    ('sct_intersection_diagram.png', 700, 500, 'PNG'),
    ('b2g_adoption_funnel.png', 800, 400, 'PNG'),
    ('official_report_pdf.png', 750, 650, 'JPEG'),
    ('delay_reduction_corridor.png', 800, 450, 'PNG')
]

for fname, max_w, max_h, fmt in files:
    src_p = os.path.join(ASSETS_DIR, fname)
    if os.path.exists(src_p):
        im = Image.open(src_p)
        if im.mode == 'RGBA' and fmt == 'JPEG':
            im = im.convert('RGB')
        im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        out_name = os.path.splitext(fname)[0] + ('.jpg' if fmt == 'JPEG' else '.png')
        dst_p = os.path.join(OPT_DIR, out_name)
        if fmt == 'JPEG':
            im.save(dst_p, 'JPEG', quality=85)
        else:
            im.save(dst_p, 'PNG', optimize=True)
        size_kb = os.path.getsize(dst_p) // 1024
        print(f"Optimized {fname} -> {out_name} ({size_kb} KB)")

print("All visual assets optimized successfully!")
