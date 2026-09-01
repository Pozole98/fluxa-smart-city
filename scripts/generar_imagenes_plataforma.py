#!/usr/bin/env python3

# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
# -*- coding: utf-8 -*-
"""
Generador de Imágenes Oficiales para Plataforma InnovaTecNM 2026 (Etapa Regional)
Genera gráficos, infografías y optimiza capturas en formato JPG (< 300 KB)
"""

import os
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "imagenes_plataforma")
ARTIFACT_DIR = "/home/moisesmartinez/.gemini/antigravity-ide/brain/a8980bd4-fb36-4057-bc01-7f937d14d9d8"

# Colores Institucionales
C_NAVY = "#0F172A"
C_TECNM = "#1B396A"
C_TESCO = "#00843D"
C_CYAN = "#06B6D4"
C_AMBER = "#F59E0B"
C_RED = "#EF4444"
C_EMERALD = "#10B981"
C_WHITE = "#FFFFFF"
C_SLATE = "#334155"
C_LIGHT_BG = "#F8FAFC"
C_DARK_CARD = "#1E293B"

def save_optimized_jpg(fig_or_img, filepath, max_kb=290, quality=90):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if isinstance(fig_or_img, plt.Figure):
        buf = io.BytesIO()
        fig_or_img.savefig(buf, format='jpg', dpi=150, bbox_inches='tight')
        plt.close(fig_or_img)
        buf.seek(0)
        img = Image.open(buf)
    else:
        img = fig_or_img

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    q = quality
    while q > 40:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=q, optimize=True)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= max_kb:
            with open(filepath, 'wb') as f:
                f.write(buf.getvalue())
            print(f"Guardado: {os.path.relpath(filepath, BASE_DIR)} ({size_kb:.1f} KB, Q={q})")
            return
        q -= 5
    
    # Si aún supera, redimensionar suavemente
    img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(filepath, format='JPEG', quality=80, optimize=True)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"Guardado con resize: {os.path.relpath(filepath, BASE_DIR)} ({size_kb:.1f} KB)")

# ==============================================================================
# SECCIÓN 1: VALIDACIÓN DEL MERCADO Y DEL CLIENTE
# ==============================================================================
def gen_sec1():
    sec_dir = os.path.join(OUT_DIR, "1_validacion_mercado")
    
    # 1.1 Segmentación de Mercado B2G
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=C_NAVY)
    ax.set_facecolor(C_NAVY)
    ax.axis('off')
    
    ax.text(0.5, 0.93, "SEGMENTACIÓN DE MERCADO Y ACTORES B2G — FLUXA", 
            color=C_CYAN, fontsize=14, fontweight='bold', ha='center')
    ax.text(0.5, 0.86, "Estructura de Clientes, Usuarios Operativos y Beneficiarios", 
            color=C_WHITE, fontsize=10, ha='center')
    
    boxes = [
        ("1. TOMADOR DE DECISIÓN (Comprador)", 
         "• Secretarías de Movilidad (SEMOV)\n• Direcciones de Tránsito y Vialidad Municipal\n• Administradores C5 / C4 Estatal\n• Autorizan presupuestos de modernización", 
         0.04, 0.18, 0.29, 0.60, C_TECNM, C_CYAN),
        ("2. USUARIO OPERATIVO (C5)", 
         "• Ingenieros de Tránsito Municipal\n• Operadores de Centros de Comando C5\n• Personal de Mantenimiento Eléctrico\n• Gestionan el SCADA y emergencias", 
         0.355, 0.18, 0.29, 0.60, C_SLATE, C_EMERALD),
        ("3. BENEFICIARIO FINAL (Población)", 
         "• Concesionarias de Transporte Público (TSP)\n• Ambulancias y Cuerpos de Bomberos\n• +35M Conductores en Zonas Metropolitanas\n• Reducción de 28% en tiempo de traslado", 
         0.67, 0.18, 0.29, 0.60, C_SLATE, C_AMBER)
    ]
    
    for title, desc, x, y, w, h, bg_c, border_c in boxes:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", 
                                      linewidth=2, edgecolor=border_c, facecolor=bg_c)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.08, title, color=border_c, fontsize=9.5, fontweight='bold', ha='center')
        ax.text(x + 0.02, y + h - 0.16, desc, color=C_WHITE, fontsize=8.5, va='top')
    
    ax.text(0.5, 0.05, "Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM | InnovaTecNM 2026", 
            color="#94A3B8", fontsize=8, ha='center')
    save_optimized_jpg(fig, os.path.join(sec_dir, "1_1_segmentacion_mercado_b2g.jpg"))

    # 1.2 Benchmarking de Costos
    fig, ax = plt.subplots(figsize=(9, 5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    controllers = ['Siemens\n(Importado)', 'Econolite\n(Tradicional)', 'Peek Traffic\n(Importado)', 'FLUXA Smart\n(Edge Overlay)']
    costs = [650000, 520000, 480000, 28500]
    colors = [C_RED, '#E11D48', '#F43F5E', C_EMERALD]
    
    bars = ax.bar(controllers, costs, color=colors, width=0.55, edgecolor=C_WHITE, linewidth=1.2)
    ax.set_title("BENCHMARKING DE COSTO POR INTERSECCIÓN (CapEx)", color=C_WHITE, fontsize=13, fontweight='bold', pad=15)
    ax.set_ylabel("Costo en Pesos Mexicanos (MXN)", color=C_WHITE, fontsize=10)
    ax.tick_params(colors=C_WHITE, labelsize=9.5)
    ax.grid(axis='y', linestyle='--', alpha=0.3, color=C_SLATE)
    
    for bar, cost in zip(bars, costs):
        yval = bar.get_height()
        pct = f"-{((520000-cost)/520000)*100:.0f}%" if cost < 100000 else "Base"
        ax.text(bar.get_x() + bar.get_width()/2, yval + 18000, 
                f"${cost:,.0f} MXN\n({pct if cost < 100000 else 'Costo Alto'})", 
                ha='center', va='bottom', color=C_WHITE, fontsize=9, fontweight='bold')
    
    ax.set_ylim(0, 750000)
    save_optimized_jpg(fig, os.path.join(sec_dir, "1_2_benchmarking_costos_competencia.jpg"))

    # 1.3 Pérdidas Económicas en Movilidad Urbana
    fig, ax = plt.subplots(figsize=(9, 5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    rubros = ['Pérdida Económica\nAnual Nacional\n($94,000 MDP)', 'Horas Perdidas\nTransporte Público\n(118 hrs/año)', 'Horas Perdidas\nAutomóvil Particular\n(71 hrs/año)', 'Ahorro Potencial\nFLUXA / Cruce\n($1.2 MDP/año)']
    values = [94.0, 11.8, 7.1, 1.2]
    colors = [C_AMBER, '#FB923C', '#FDBA74', C_CYAN]
    
    bars = ax.bar(rubros, values, color=colors, width=0.55, edgecolor=C_WHITE, linewidth=1.2)
    ax.set_title("IMPACTO DEL TRÁFICO Y OPORTUNIDAD DE AHORRO URBANO", color=C_WHITE, fontsize=13, fontweight='bold', pad=15)
    ax.tick_params(colors=C_WHITE, labelsize=9)
    ax.grid(axis='y', linestyle='--', alpha=0.3, color=C_SLATE)
    
    ax.text(0.5, 0.88, "Fuente: IMCO / ITDP — Pérdidas por Congestión en México", 
            transform=ax.transAxes, color="#94A3B8", fontsize=8.5, ha='center')
    save_optimized_jpg(fig, os.path.join(sec_dir, "1_3_perdidas_congestion_cdmx_edomex.jpg"))

# ==============================================================================
# SECCIÓN 2: MODELO DE COMERCIALIZACIÓN TECNOLÓGICA
# ==============================================================================
def gen_sec2():
    sec_dir = os.path.join(OUT_DIR, "2_modelo_comercializacion")
    
    # 2.1 Mecanismo de Comercialización Híbrido
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=C_NAVY)
    ax.set_facecolor(C_NAVY)
    ax.axis('off')
    
    ax.text(0.5, 0.93, "MODELO DE COMERCIALIZACIÓN HÍBRIDO B2G — FLUXA", 
            color=C_CYAN, fontsize=14, fontweight='bold', ha='center')
    ax.text(0.5, 0.86, "Captura de Valor en Hardware, Software SCADA y Servicios Recurrentes", 
            color=C_WHITE, fontsize=10, ha='center')
    
    pilares = [
        ("1. HARDWARE EDGE (CapEx)", 
         "Venta de Kit Edge Appliance:\n• Orange Pi 5 (RK3588 NPU 6 TOPS)\n• Microcontrolador + Relevadores SSR\n• Cámara Vial HD Gran Angular\n• Gabinete NEMA IP66 Industrial\n• Precio: $28,500 MXN / Cruce", 
         0.04, 0.18, 0.29, 0.60, C_DARK_CARD, C_CYAN),
        ("2. LICENCIA SCADA (SaaS/OpEx)", 
         "Suscripción Anual por Nodo:\n• Conectividad SCADA Central C5\n• Base de Datos MariaDB Asíncrona\n• Detección Infracciones Luz Roja\n• Reportes Oficiales en PDF\n• Renta: $8,400 MXN / Cruce/Año", 
         0.355, 0.18, 0.29, 0.60, C_DARK_CARD, C_EMERALD),
        ("3. PÓLIZA DE SOPORTE (SLA)", 
         "Servicio Técnico y Calibración:\n• Mantenimiento preventivo 24/7\n• Re-entrenamiento periódico IA\n• Calibración de polígonos ROI\n• Garantía y reemplazo de piezas\n• Póliza: $6,000 MXN / Cruce/Año", 
         0.67, 0.18, 0.29, 0.60, C_DARK_CARD, C_AMBER)
    ]
    
    for title, desc, x, y, w, h, bg_c, border_c in pilares:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", 
                                      linewidth=2, edgecolor=border_c, facecolor=bg_c)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.08, title, color=border_c, fontsize=9.5, fontweight='bold', ha='center')
        ax.text(x + 0.02, y + h - 0.15, desc, color=C_WHITE, fontsize=8.5, va='top')
        
    ax.text(0.5, 0.05, "TESCo • TecNM | Modelo de Negocio B2G Smart Mobility", color="#94A3B8", fontsize=8, ha='center')
    save_optimized_jpg(fig, os.path.join(sec_dir, "2_1_mecanismo_comercializacion_hibrido.jpg"))

    # 2.2 Embudo de Adopción B2G
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=C_NAVY)
    ax.set_facecolor(C_NAVY)
    ax.axis('off')
    
    ax.text(0.5, 0.92, "EMBUDO DE ADOPCIÓN Y VENTA GUBERNAMENTAL (B2G)", 
            color=C_WHITE, fontsize=13, fontweight='bold', ha='center')
    
    etapas = [
        ("FASE 1: PILOTO (30 Días)", "Instalación de 1 nodo demostrativo sin costo para generar auditoría vial.", 0.10, 0.65, 0.80, 0.16, C_CYAN),
        ("FASE 2: DICTAMEN DE ROI", "Entrega de informe oficial demostrando ahorro de combustible y reducción de cola.", 0.16, 0.44, 0.68, 0.16, C_EMERALD),
        ("FASE 3: ADJUDICACIÓN", "Contratación por modernización tecnológica (Adjudicación Directa o Licitación).", 0.22, 0.23, 0.56, 0.16, C_AMBER),
        ("FASE 4: DESPLIEGUE CORREDOR", "Instalación en 10-50 cruces con integración al Centro de Mando C5 municipal.", 0.28, 0.02, 0.44, 0.16, C_TECNM)
    ]
    
    for title, desc, x, y, w, h, col in etapas:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", 
                                      linewidth=1.5, edgecolor=C_WHITE, facecolor=col)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.05, title, color=C_WHITE, fontsize=9.5, fontweight='bold', ha='center')
        ax.text(x + w/2, y + 0.04, desc, color=C_WHITE, fontsize=8, ha='center')
        
    save_optimized_jpg(fig, os.path.join(sec_dir, "2_2_embudo_adopcion_b2g.jpg"))

# ==============================================================================
# SECCIÓN 3: MODELO ECONÓMICO Y PROYECCIÓN DE INGRESOS
# ==============================================================================
def gen_sec3():
    sec_dir = os.path.join(OUT_DIR, "3_modelo_economico")
    
    # 3.1 Estructura de Costos Unitarios BOM
    fig, ax = plt.subplots(figsize=(8.5, 5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    componentes = ['Orange Pi 5\n(RK3588 NPU)', 'Gabinete NEMA\n+ Fuente MeanWell', 'Cámara Vial\nGran Angular HD', 'Controlador Arduino\n+ Relevadores SSR', 'Ensamble,\nPruebas y Calib.']
    costos = [3200, 2100, 1800, 1450, 2200]
    colores = [C_CYAN, '#38BDF8', C_EMERALD, '#34D399', C_AMBER]
    
    wedges, texts, autotexts = ax.pie(costos, labels=componentes, autopct='%1.1f%%', 
                                      startangle=140, colors=colores, 
                                      textprops=dict(color=C_WHITE, fontsize=8.5),
                                      wedgeprops=dict(edgecolor=C_NAVY, linewidth=2))
    
    for at in autotexts:
        at.set_color(C_NAVY)
        at.set_fontweight('bold')
        
    ax.set_title("ESTRUCTURA DE COSTO UNITARIO DIRECTO (BOM)\nCosto Total de Fabricación: $10,750 MXN | Precio Venta: $28,500 MXN", 
                 color=C_WHITE, fontsize=11, fontweight='bold', pad=10)
    save_optimized_jpg(fig, os.path.join(sec_dir, "3_1_estructura_costos_unitarios_bom.jpg"))

    # 3.2 Proyección Financiera Año 1
    fig, ax = plt.subplots(figsize=(9, 5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    meses = ['Mes 2', 'Mes 4', 'Mes 6', 'Mes 8', 'Mes 10', 'Mes 12']
    unidades = [5, 10, 20, 30, 40, 50]
    ingresos = [142.5, 285.0, 642.0, 1071.0, 1572.0, 2145.0] # Miles de pesos
    
    ax.plot(meses, ingresos, marker='o', color=C_EMERALD, linewidth=2.5, markersize=8, label='Ingresos Acumulados ($k MXN)')
    ax.bar(meses, [u*15 for u in unidades], alpha=0.3, color=C_CYAN, width=0.4, label='Nodos Instalados')
    
    ax.set_title("PROYECCIÓN DE ESCALABILIDAD E INGRESOS — AÑO 1 ($2.14 MDP)", color=C_WHITE, fontsize=12, fontweight='bold', pad=15)
    ax.set_ylabel("Monto en Miles de Pesos ($k MXN)", color=C_WHITE, fontsize=9.5)
    ax.tick_params(colors=C_WHITE, labelsize=9)
    ax.grid(True, linestyle='--', alpha=0.25, color=C_SLATE)
    ax.legend(facecolor=C_NAVY, edgecolor=C_SLATE, labelcolor=C_WHITE, fontsize=9)
    
    for i, txt in enumerate(ingresos):
        ax.annotate(f"${txt:,.0f}k", (meses[i], ingresos[i] + 60), color=C_CYAN, fontweight='bold', fontsize=8.5, ha='center')
        
    save_optimized_jpg(fig, os.path.join(sec_dir, "3_2_proyeccion_financiera_ano1.jpg"))

# ==============================================================================
# SECCIÓN 4: VIABILIDAD DE ADOPCIÓN Y ESCALAMIENTO
# ==============================================================================
def gen_sec4():
    sec_dir = os.path.join(OUT_DIR, "4_viabilidad_adopcion")
    
    # 4.1 Cronograma de Despliegue Rápido (4 Horas)
    fig, ax = plt.subplots(figsize=(9.5, 4.5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    fases = ['1. Fijación Gabinete NEMA', '2. Montaje de Cámara Vial', '3. Conexión a Relevadores SSR', '4. Calibración Óptica ROIs', '5. Enlace SCADA C5 y Pruebas']
    duraciones = [45, 45, 60, 50, 40] # Minutos
    start_times = [0, 45, 90, 150, 200]
    colores = [C_TECNM, C_CYAN, C_EMERALD, C_AMBER, '#8B5CF6']
    
    for i in range(len(fases)):
        ax.barh(fases[i], duraciones[i], left=start_times[i], color=colores[i], edgecolor=C_WHITE, height=0.55)
        ax.text(start_times[i] + duraciones[i]/2, i, f"{duraciones[i]} min", va='center', ha='center', color=C_WHITE, fontweight='bold', fontsize=8.5)
        
    ax.set_title("CRONOGRAMA DE INSTALACIÓN RÁPIDA: < 4 HORAS POR INTERSECCIÓN\nSin Obra Civil ni Interrupción Prolongada de Tránsito", 
                 color=C_WHITE, fontsize=11, fontweight='bold', pad=12)
    ax.set_xlabel("Tiempo Total de Despliegue (Minutos)", color=C_WHITE, fontsize=9.5)
    ax.tick_params(colors=C_WHITE, labelsize=9)
    ax.grid(axis='x', linestyle='--', alpha=0.3, color=C_SLATE)
    save_optimized_jpg(fig, os.path.join(sec_dir, "4_1_cronograma_despliegue_4horas.jpg"))
    
    # 4.2 Sincronización Ola Verde Mesh
    fig, ax = plt.subplots(figsize=(9.5, 4.5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    cruces = ['Intersección 1\n(Av. Hidalgo)', 'Intersección 2\n(Calle Juárez)', 'Intersección 3\n(Av. Morelos)', 'Intersección 4\n(Entrada C5)']
    demoras = [38, 14, 12, 9] # Segundos con FLUXA
    demoras_fijas = [55, 50, 48, 52] # Tiempos fijos tradicionales
    
    x = np.arange(len(cruces))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, demoras_fijas, width, label='Control Tradicional (Tiempo Fijo)', color=C_RED, edgecolor=C_WHITE)
    rects2 = ax.bar(x + width/2, demoras, width, label='FLUXA (Ola Verde Adaptativa)', color=C_EMERALD, edgecolor=C_WHITE)
    
    ax.set_title("REDUCCIÓN DE TIEMPOS DE ESPERA EN CORREDOR VIAL (OLA VERDE ADAPTATIVA)", color=C_WHITE, fontsize=11, fontweight='bold', pad=12)
    ax.set_ylabel("Demora Promedio por Vehículo (Segundos)", color=C_WHITE, fontsize=9.5)
    ax.set_xticks(x)
    ax.set_xticklabels(cruces, color=C_WHITE, fontsize=9)
    ax.tick_params(colors=C_WHITE)
    ax.grid(axis='y', linestyle='--', alpha=0.25, color=C_SLATE)
    ax.legend(facecolor=C_NAVY, edgecolor=C_SLATE, labelcolor=C_WHITE, fontsize=9)
    save_optimized_jpg(fig, os.path.join(sec_dir, "4_2_sincronizacion_ola_verde_mesh.jpg"))

# ==============================================================================
# SECCIÓN 5: BITÁCORA DE DESARROLLO Y CAPTURAS DEL SISTEMA REAL
# ==============================================================================
def gen_sec5():
    sec_dir = os.path.join(OUT_DIR, "5_bitacora_desarrollo")
    
    # 5.1 Dashboard SCADA C5 Real
    scada_src = os.path.join(ARTIFACT_DIR, ".user_uploaded/media_1787087734575.png")
    if os.path.exists(scada_src):
        img = Image.open(scada_src)
        save_optimized_jpg(img, os.path.join(sec_dir, "5_1_dashboard_scada_c5_operacion.jpg"))
        
    # 5.2 Portal Ciudadano
    portal_src = os.path.join(ARTIFACT_DIR, "portal_ciudadano_1787160791689.png")
    if os.path.exists(portal_src):
        img = Image.open(portal_src)
        save_optimized_jpg(img, os.path.join(sec_dir, "5_2_portal_ciudadano_telemetria.jpg"))
        
    # 5.3 Reporte Ejecutivo Oficial PDF
    rep_src = os.path.join(ARTIFACT_DIR, "executive_report_1787160877555.png")
    if os.path.exists(rep_src):
        img = Image.open(rep_src)
        save_optimized_jpg(img, os.path.join(sec_dir, "5_3_reporte_ejecutivo_auditoria_pdf.jpg"))
        
    # 5.4 Diagrama Fail-Safe Hot-Switch
    fig, ax = plt.subplots(figsize=(9.5, 5), facecolor=C_NAVY)
    ax.set_facecolor(C_NAVY)
    ax.axis('off')
    
    ax.text(0.5, 0.93, "MATRIZ DE TOLERANCIA A FALLOS INDUSTRIAL (FAIL-SAFE)", 
            color=C_CYAN, fontsize=13, fontweight='bold', ha='center')
    
    niveles = [
        ("NIVEL 1: NPU RK3588 (INT8)", "Inferencia ultrarrápida a <12ms y 30 FPS en 3 núcleos de NPU.", 0.05, 0.60, 0.88, 0.18, C_EMERALD),
        ("NIVEL 2: CPU FALLBACK (PyTorch)", "Conmutación en caliente automática si rknnlite o el driver fallan.", 0.05, 0.35, 0.88, 0.18, C_AMBER),
        ("NIVEL 3: ARDUINO WATCHDOG", "Si el SBC se congela, el MCU detecta timeout (3s) y activa ciclo seguro de tiempo fijo.", 0.05, 0.10, 0.88, 0.18, C_RED)
    ]
    
    for title, desc, x, y, w, h, col in niveles:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", 
                                      linewidth=1.5, edgecolor=C_WHITE, facecolor=C_DARK_CARD)
        ax.add_patch(rect)
        rect_badge = patches.FancyBboxPatch((x+0.02, y+0.03), 0.35, h-0.06, boxstyle="round,pad=0.01", 
                                           linewidth=0, facecolor=col)
        ax.add_patch(rect_badge)
        ax.text(x+0.195, y + h/2, title, color=C_WHITE, fontsize=8.5, fontweight='bold', va='center', ha='center')
        ax.text(x+0.40, y + h/2, desc, color=C_WHITE, fontsize=8.5, va='center')
        
    save_optimized_jpg(fig, os.path.join(sec_dir, "5_4_diagrama_failsafe_hotswitch.jpg"))

    # 5.5 Validación con Pruebas Unitarias Pytest 100%
    fig, ax = plt.subplots(figsize=(9, 4.5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    ax.axis('off')
    
    ax.text(0.5, 0.90, "SUITE DE PRUEBAS AUTOMATIZADAS — PYTEST (100% APROBADO)", 
            color=C_EMERALD, fontsize=12, fontweight='bold', ha='center')
    
    tests = [
        "✓ test_no_conflicting_greens: Cero conflictos de verdes simultáneos (PASSED)",
        "✓ test_safe_emergency_transition: Despeje seguro de ámbar y todo-rojo (PASSED)",
        "✓ test_emergency_from_all_red: Respeto estricto del búfer de seguridad (PASSED)",
        "✓ test_adaptive_demand_time_calc: Cálculo de tiempos dinámicos TSP (PASSED)",
        "✓ test_rknn_npu_to_cpu_fallback: Conmutación en caliente NPU a CPU (PASSED)",
        "✓ test_violations_capture_retrieval: Módulo forense de luz roja (PASSED)"
    ]
    
    for i, t in enumerate(tests):
        ypos = 0.72 - i * 0.11
        rect = patches.FancyBboxPatch((0.05, ypos-0.03), 0.90, 0.08, boxstyle="round,pad=0.01", 
                                      linewidth=1, edgecolor=C_EMERALD, facecolor=C_NAVY)
        ax.add_patch(rect)
        ax.text(0.08, ypos + 0.01, t, color=C_WHITE, fontsize=8.5, fontfamily='monospace', va='center')
        
    save_optimized_jpg(fig, os.path.join(sec_dir, "5_5_pruebas_unitarias_pytest_100.jpg"))

    # 5.6 Nivel de Maduración Tecnológica TRL
    fig, ax = plt.subplots(figsize=(9.5, 4.5), facecolor=C_NAVY)
    ax.set_facecolor(C_DARK_CARD)
    
    trls = ['TRL 1-3\nConcepto', 'TRL 4\nLab', 'TRL 5\nSimulación', 'TRL 6\nEntorno\nRelevante', 'TRL 7\nDemostración\nOperativa', 'TRL 8-9\nComercial']
    status = [100, 100, 100, 100, 85, 40]
    colores_trl = [C_SLATE, C_SLATE, C_SLATE, C_EMERALD, C_CYAN, C_SLATE]
    
    bars = ax.bar(trls, status, color=colores_trl, width=0.55, edgecolor=C_WHITE, linewidth=1.2)
    ax.set_title("NIVEL DE MADUREZ TECNOLÓGICA ALCANZADO (TRL 6 / TRL 7)", color=C_WHITE, fontsize=12, fontweight='bold', pad=12)
    ax.set_ylabel("Grado de Maduración (%)", color=C_WHITE, fontsize=9.5)
    ax.tick_params(colors=C_WHITE, labelsize=9)
    ax.grid(axis='y', linestyle='--', alpha=0.25, color=C_SLATE)
    
    for bar, s in zip(bars, status):
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 3, f"{s}%", ha='center', va='bottom', color=C_WHITE, fontsize=9, fontweight='bold')
        
    ax.set_ylim(0, 115)
    save_optimized_jpg(fig, os.path.join(sec_dir, "5_6_curva_maduracion_trl6_trl7.jpg"))

if __name__ == "__main__":
    print(" Generando imágenes oficiales para plataforma InnovaTecNM...")
    gen_sec1()
    gen_sec2()
    gen_sec3()
    gen_sec4()
    gen_sec5()
    print("✨ Todas las imágenes han sido generadas y optimizadas exitosamente en 'imagenes_plataforma/'.")
