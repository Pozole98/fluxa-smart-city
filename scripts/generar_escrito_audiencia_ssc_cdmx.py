#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Generación del Escrito Libre Institucional (Formato Ejecutivo de 2 Páginas)
Dirigido al Lic. Pablo Vázquez Camacho, Secretario de Seguridad Ciudadana de la Ciudad de México.
Proyecto: FLUXA Smart Mobility • Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import sys
import base64
import subprocess
import shutil
from io import BytesIO
from PIL import Image

BASE_DIR = '/home/moisesmartinez/PycharmProjects/yolov8srknn'
FLUXAPI_DIR = os.path.join(BASE_DIR, 'fluxapi')
LOGOS_DIR = os.path.join(FLUXAPI_DIR, 'logos')
ASSETS_DIR = os.path.join(FLUXAPI_DIR, 'presentaciones', 'assets')
OUTPUT_HTML = os.path.join(BASE_DIR, 'Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.html')
OUTPUT_PDF = os.path.join(BASE_DIR, 'Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.pdf')
DOCS_PDF = os.path.join(FLUXAPI_DIR, 'docs', 'Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.pdf')
ARTIFACT_DIR = '/home/moisesmartinez/.gemini/antigravity-ide/brain/6a7fdd6a-c405-421b-802c-117d2df9d250'
ARTIFACT_PDF = os.path.join(ARTIFACT_DIR, 'Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.pdf')

def image_to_base64(path, max_width=450):
    if not os.path.exists(path):
        print(f"Advertencia: No existe {path}")
        return ""
    try:
        im = Image.open(path)
        w, h = im.size
        if w > max_width:
            new_h = int(h * (max_width / w))
            im = im.resize((max_width, new_h), Image.Resampling.LANCZOS)
            
        buf = BytesIO()
        im.save(buf, format='PNG', optimize=True)
        b64_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{b64_data}"
    except Exception as e:
        print(f"Error procesando {path}: {e}")
        return ""

print("Codificando logotipos institucionales...")
b64_tecnm = image_to_base64(os.path.join(LOGOS_DIR, 'tecnm.png'), max_width=420)
b64_tesco = image_to_base64(os.path.join(LOGOS_DIR, 'tesco.png'), max_width=420)
b64_fluxa = image_to_base64(os.path.join(ASSETS_DIR, 'fluxa_official_logo.png'), max_width=420)

html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Escrito Libre Institucional - Solicitud de Audiencia SSC CDMX - Proyecto FLUXA</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700;1,6..72,400&family=JetBrains+Mono:wght@400;600&display=swap');

@page {{
    size: letter;
    margin: 11mm 15mm 11mm 15mm;
}}

* {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
}}

body {{
    margin: 0;
    padding: 0;
    background-color: #ffffff;
    font-family: 'Newsreader', Georgia, 'Times New Roman', serif;
    font-size: 9.25pt;
    line-height: 1.37;
    color: #1e293b;
    -webkit-font-smoothing: antialiased;
}}

.page {{
    width: 100%;
    height: 256mm;
    max-height: 256mm;
    page-break-after: always;
    page-break-inside: avoid;
    position: relative;
    overflow: hidden;
    padding-bottom: 8mm;
}}

.page:last-child {{
    page-break-after: avoid;
}}

/* ==================== MEMBRETE INSTITUCIONAL ==================== */
.header-table {{
    width: 100%;
    border-collapse: collapse;
    border-bottom: 2px solid #1b396a;
    padding-bottom: 3px;
    margin-bottom: 5px;
}}

.header-table td {{
    vertical-align: middle;
    padding: 0 4px;
}}

.logo-cell-left {{
    width: 18%;
    text-align: left;
}}

.logo-cell-center {{
    width: 64%;
    text-align: center;
}}

.logo-cell-right {{
    width: 18%;
    text-align: right;
}}

.header-table img {{
    max-height: 38px;
    width: auto;
    display: inline-block;
}}

.inst-title-main {{
    font-family: 'Montserrat', sans-serif;
    font-size: 9.8pt;
    font-weight: 800;
    color: #1b396a;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin: 0;
}}

.inst-subtitle {{
    font-family: 'Montserrat', sans-serif;
    font-size: 7.3pt;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    margin: 1px 0 0 0;
    letter-spacing: 0.3px;
}}

.inst-lema {{
    font-family: 'Newsreader', serif;
    font-size: 6.9pt;
    font-style: italic;
    color: #64748b;
    margin: 1px 0 0 0;
}}

.sub-stripe {{
    height: 2.5px;
    background: linear-gradient(90deg, #1b396a 0%, #10b981 50%, #991b1b 100%);
    margin-top: 2px;
    border-radius: 2px;
}}

/* ==================== CUADRO DE METADATOS Y FOLIO ==================== */
.meta-box-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 5px 0 7px 0;
}}

.meta-box-table td {{
    vertical-align: top;
    padding: 0;
}}

.meta-left {{
    width: 50%;
}}

.meta-right {{
    width: 50%;
    text-align: right;
}}

.official-badge {{
    display: inline-block;
    font-family: 'Montserrat', sans-serif;
    background: #f1f5f9;
    border-left: 3.5px solid #1b396a;
    padding: 3px 7px;
    border-radius: 0 4px 4px 0;
    text-align: left;
    font-size: 7.3pt;
    line-height: 1.30;
    color: #1e293b;
}}

.official-badge strong {{
    color: #0f172a;
    font-weight: 700;
}}

.meta-right-card {{
    display: inline-block;
    font-family: 'Montserrat', sans-serif;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 3px 7px;
    text-align: right;
    font-size: 7.3pt;
    line-height: 1.30;
}}

.meta-right-card strong {{
    color: #1b396a;
}}

/* ==================== DESTINATARIO ==================== */
.addressee-card {{
    background: #ffffff;
    border-left: 4px solid #1b396a;
    padding: 3px 0 3px 8px;
    margin: 5px 0 7px 0;
    font-family: 'Montserrat', sans-serif;
}}

.addressee-name {{
    font-size: 9.8pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 0.3px;
    margin: 0;
    text-transform: uppercase;
}}

.addressee-charge {{
    font-size: 8.2pt;
    font-weight: 700;
    color: #1b396a;
    margin: 1px 0 0 0;
    text-transform: uppercase;
}}

.addressee-entity {{
    font-size: 7.9pt;
    font-weight: 500;
    color: #475569;
    margin: 1px 0 0 0;
}}

.addressee-presente {{
    font-size: 7.9pt;
    font-weight: 700;
    color: #0f172a;
    margin: 2px 0 0 0;
    letter-spacing: 1.5px;
}}

/* ==================== CUERPO DEL TEXTO LEGAL ==================== */
p.legal-body {{
    text-align: justify;
    text-justify: inter-word;
    margin: 5px 0;
    text-indent: 16pt;
    line-height: 1.36;
    font-size: 9.15pt;
}}

p.legal-body-noindent {{
    text-align: justify;
    text-justify: inter-word;
    margin: 4px 0;
    line-height: 1.35;
    font-size: 9.1pt;
}}

p.legal-body strong, p.legal-body-noindent strong {{
    font-family: 'Newsreader', serif;
    font-weight: 700;
    color: #0f172a;
}}

.highlight-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #0284c7;
    border-radius: 4px;
    padding: 5px 8px;
    margin: 5px 0;
    font-size: 8.75pt;
    line-height: 1.33;
}}

.prototype-callout {{
    background: #fffbeb;
    border: 1.5px solid #f59e0b;
    border-left: 4.5px solid #d97706;
    border-radius: 4px;
    padding: 5px 8px;
    margin: 4px 0 5px 0;
    font-size: 8.75pt;
    line-height: 1.33;
    color: #78350f;
}}

.prototype-callout strong {{
    color: #92400e;
    font-family: 'Montserrat', sans-serif;
}}

/* ==================== RESUMEN DE PILARES TÉCNICOS ==================== */
.pillars-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 4px 0 5px 0;
}}

.pillars-table td {{
    width: 33.33%;
    padding: 2.5px;
    vertical-align: top;
}}

.pillar-card {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px 6px;
    height: 100%;
    box-sizing: border-box;
}}

.pillar-title {{
    font-family: 'Montserrat', sans-serif;
    font-size: 7.5pt;
    font-weight: 700;
    color: #1b396a;
    text-transform: uppercase;
    margin-bottom: 2px;
}}

.pillar-desc {{
    font-size: 7.2pt;
    line-height: 1.25;
    color: #334155;
    text-align: justify;
}}

/* ==================== PETITORIOS ==================== */
.petitorio-list {{
    margin: 3px 0 5px 0;
    padding-left: 0;
    list-style: none;
}}

.petitorio-item {{
    text-align: justify;
    margin-bottom: 3.5px;
    padding-left: 17pt;
    text-indent: -17pt;
    font-size: 8.85pt;
    line-height: 1.30;
}}

.petitorio-num {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    color: #1b396a;
}}

/* ==================== FIRMAS Y RÚBRICAS ==================== */
.signature-section {{
    margin-top: 6px;
    width: 100%;
}}

.signature-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 5px;
}}

.signature-table td {{
    vertical-align: top;
    text-align: center;
    padding: 0 8px;
}}

.sig-line {{
    width: 82%;
    margin: 0 auto;
    border-top: 1.2px solid #334155;
    padding-top: 2px;
}}

.sig-name {{
    font-family: 'Montserrat', sans-serif;
    font-size: 8.3pt;
    font-weight: 800;
    color: #0f172a;
    text-transform: uppercase;
    margin: 0;
}}

.sig-charge {{
    font-family: 'Montserrat', sans-serif;
    font-size: 7.2pt;
    font-weight: 600;
    color: #1b396a;
    margin: 1px 0 0 0;
}}

.sig-inst {{
    font-family: 'Montserrat', sans-serif;
    font-size: 6.8pt;
    color: #64748b;
    margin: 1px 0 0 0;
}}

.team-grid-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 3.5px 7px;
    margin-top: 5px;
    font-family: 'Montserrat', sans-serif;
    font-size: 6.8pt;
    line-height: 1.32;
    color: #334155;
}}

.team-grid-card strong {{
    color: #0f172a;
}}

/* ==================== PIE DE PÁGINA ==================== */
.footer-table {{
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    border-collapse: collapse;
    border-top: 1px solid #cbd5e1;
    padding-top: 2px;
    font-family: 'Montserrat', sans-serif;
    font-size: 6.6pt;
    color: #64748b;
}}

.footer-table td {{
    padding: 2px 0 0 0;
}}

.footer-left {{
    text-align: left;
    width: 78%;
}}

.footer-right {{
    text-align: right;
    width: 22%;
    font-weight: 600;
    color: #1b396a;
}}
</style>
</head>
<body>

<!-- ========================================================================================= -->
<!-- PÁGINA 1: OFICIO DE ESCRITO LIBRE FORMAL (PROEMIO, FUNDAMENTO, PROBLEMÁTICA Y PROYECTO)   -->
<!-- ========================================================================================= -->
<div class="page">
    <table class="header-table">
        <tr>
            <td class="logo-cell-left"><img src="{b64_tecnm}" alt="TecNM"></td>
            <td class="logo-cell-center">
                <div class="inst-title-main">Tecnológico Nacional de México</div>
                <div class="inst-subtitle">Tecnológico de Estudios Superiores de Coacalco • División de Ingeniería en Sistemas Computacionales</div>
                <div class="inst-lema">"Por la excelencia en la educación tecnológica y la transformación social"</div>
            </td>
            <td class="logo-cell-right"><img src="{b64_tesco}" alt="TESCo"></td>
        </tr>
    </table>
    <div class="sub-stripe"></div>

    <table class="meta-box-table">
        <tr>
            <td class="meta-left">
                <div class="official-badge">
                    <strong>OFICIO NO.:</strong> TECNM-TESCO/DISC/FLUXA-2026/014<br>
                    <strong>EXPEDIENTE:</strong> Innovación Tecnológica / Movilidad Inteligente (InnovaTecNM: 70785-17)<br>
                    <strong>CARÁCTER:</strong> Petición Ciudadana Institucional (Art. 8° Constitucional)
                </div>
            </td>
            <td class="meta-right">
                <div class="meta-right-card">
                    <strong>LUGAR Y FECHA:</strong> Ciudad de México / Coacalco, a 12 de octubre de 2026<br>
                    <strong>ASUNTO:</strong> Solicitud de audiencia institucional para presentación y valoración técnica<br>
                    del prototipo de control semafórico inteligente "FLUXA", con fines de colaboración y prueba piloto.
                </div>
            </td>
        </tr>
    </table>

    <div class="addressee-card">
        <div class="addressee-name">LIC. PABLO VÁZQUEZ CAMACHO</div>
        <div class="addressee-charge">SECRETARIO DE SEGURIDAD CIUDADANA DE LA CIUDAD DE MÉXICO</div>
        <div class="addressee-entity">GOBIERNO DE LA CIUDAD DE MÉXICO</div>
        <div class="addressee-presente">P R E S E N T E .</div>
    </div>

    <p class="legal-body">
        El que suscribe, <strong>C. Moisés Emilio Martínez Arias</strong>, ciudadano mexicano, en mi carácter de desarrollador principal y titular de los derechos del proyecto de innovación tecnológica <strong>"FLUXA Smart Mobility"</strong>, estudiante de la División de Ingeniería en Sistemas Computacionales en el <strong>Tecnológico de Estudios Superiores de Coacalco (TESCo)</strong>, institución pública descentralizada adscrita al <strong>Tecnológico Nacional de México (TecNM)</strong>; compareciendo formalmente en representación del equipo multidisciplinario de desarrollo conformado por los CC. <strong>Diego Alejandro Huichapeño González</strong>, <strong>Ethan Rafael Flores Medina</strong>, <strong>Citlalli Rojas Rico</strong> y <strong>Jerazan Becerra Mendoza</strong>, y con la asesoría académica del <strong>Mtro. Roberto Carlos Muñoz Celaya</strong>; señalando como domicilio para oír y recibir toda clase de notificaciones el ubicado en <strong>Calle Ray-O-Vac #46A, Col. Fuentes de Ecatepec 2, C.P. 55050, Ecatepec de Morelos, Estado de México</strong>, con correo electrónico <code>martinezariasmoises@outlook.com</code> y número telefónico <strong>56-1164-3364</strong>; ante Usted, con el debido respeto y con fundamento en el <strong>Artículo 8° de la Constitución Política de los Estados Unidos Mexicanos</strong>, comparezco y expongo:
    </p>

    <p class="legal-body">
        Que acudo de manera pacífica, respetuosa y atenta a solicitar formalmente una <strong>AUDIENCIA INSTITUCIONAL DE TRABAJO</strong> ante Usted, o en su defecto ante los mandos técnicos y directivos que tenga a bien designar de la <strong>Subsecretaría de Control de Tránsito</strong>, de la <strong>Dirección General de Ingeniería de Tránsito</strong> y/o del <strong>Centro de Comando, Control, Cómputo, Comunicaciones y Contacto Ciudadano (C5)</strong> de la Ciudad de México, con el propósito de realizar la <strong>presentación y demostración técnica en vivo de nuestra propuesta tecnológica</strong>, y evaluar de manera conjunta la pertinencia de establecer un esquema de colaboración gubernamental para la realización de una <strong>prueba piloto experimental controlada</strong> en la red vial capitalina.
    </p>

    <div class="highlight-box">
        <strong>PLANTEAMIENTO DE LA PROBLEMÁTICA VIAL METROPOLITANA:</strong> La zona metropolitana del Valle de México enfrenta una severa saturación en sus arterias principales, donde la inmensa mayoría de las intersecciones continúan operando con controladores semafóricos rígidos de tiempo fijo ("ciegos" a la demanda real). Esta condición genera pérdidas anuales superiores a 3.5 mil millones de horas-hombre y elevadas emisiones por vehículos en ralentí. De manera crítica para la Secretaría a su digno cargo, <strong>entorpece el desplazamiento expedito de vehículos de emergencia (ERUM, Heroico Cuerpo de Bomberos y unidades policiales de la SSC)</strong> y del transporte público masivo. Tradicionalmente, la modernización semafórica ha sido monopolizada por marcas transnacionales que exigen demoler pavimentos para instalar sensores invasivos y cobran entre <strong>$350,000 y $750,000 pesos por cruce</strong>, lo que representa un costo sumamente elevado para el erario público.
    </div>

    <p class="legal-body">
        Frente a este desafío, en las aulas y laboratorios de la educación tecnológica pública nacional concebimos el <strong>Sistema FLUXA</strong>: una plataforma soberana de <strong>Control Semafórico Inteligente y Telemetría Edge AI</strong>, diseñada bajo una arquitectura de modernización superpuesta (<strong><em>Retrofit Overlay</em></strong>). Nuestra propuesta permite transformar cruces tradicionales en intersecciones inteligentes adaptativas <strong>conectándose directamente al gabinete, cabezales y cableado existentes en menos de 4 horas, sin requerir obra civil destructiva y reduciendo el costo de implementación en más de un 90%</strong> frente a las alternativas comerciales extranjeras.
    </p>

    <table class="footer-table">
        <tr>
            <td class="footer-left">
                Oficio TECNM-TESCO/DISC/FLUXA-2026/014 • Solicitud de Audiencia Institucional • Lic. Pablo Vázquez Camacho (SSC CDMX)
            </td>
            <td class="footer-right">
                Página 1 de 2
            </td>
        </tr>
    </table>
</div>

<!-- ========================================================================================= -->
<!-- PÁGINA 2: DECLARACIÓN PROTOTIPO FUNCIONAL, PETITORIOS FORMALES Y FIRMAS                   -->
<!-- ========================================================================================= -->
<div class="page">
    <table class="header-table">
        <tr>
            <td class="logo-cell-left"><img src="{b64_tecnm}" alt="TecNM"></td>
            <td class="logo-cell-center">
                <div class="inst-title-main">Tecnológico Nacional de México</div>
                <div class="inst-subtitle">Tecnológico de Estudios Superiores de Coacalco • División de Ingeniería en Sistemas Computacionales</div>
            </td>
            <td class="logo-cell-right"><img src="{b64_tesco}" alt="TESCo"></td>
        </tr>
    </table>
    <div class="sub-stripe"></div>

    <div class="prototype-callout">
        <strong>MANIFESTACIÓN EXPRESA SOBRE EL ESTADO ACTUAL DEL DESARROLLO (PROTOTIPO FUNCIONAL):</strong><br>
        Es imperativo para los suscritos manifestar con entera claridad y rigor ético ante esta Secretaría que la tecnología que ponemos a su consideración <strong>SE ENCUENTRA ACTUALMENTE EN ETAPA DE PROTOTIPO FUNCIONAL DE LABORATORIO Y BANCO DE PRUEBAS EXPERIMENTAL (Nivel de Madurez Tecnológica TRL 5 / TRL 6)</strong>. No nos presentamos ostentando un producto comercial terminado ni pretendemos una contratación comercial inmediata, sino la <strong>presentación formal de una innovación científica-tecnológica de base universitaria que ha demostrado plena viabilidad operativa en entorno simulado y banco de pruebas físico</strong>, buscando explorar el respaldo y colaboración institucional para transitar hacia su validación en campo real.
    </div>

    <table class="pillars-table">
        <tr>
            <td>
                <div class="pillar-card">
                    <div class="pillar-title">1. Visión Edge AI</div>
                    <div class="pillar-desc">
                        Inferencia neuronal local en tiempo real con modelos YOLOv8 cuantizados (NPU 6 TOPS, &lt;12ms, 30-60 FPS), operando de forma autónoma en el poste sin requerir internet ni nube.
                    </div>
                </div>
            </td>
            <td>
                <div class="pillar-card">
                    <div class="pillar-title">2. Mando Emergencias C5</div>
                    <div class="pillar-desc">
                        FSM adaptativa con priorización ponderada de transporte (TSP) y protocolo de "Corredor de Emergencia" para despeje vial seguro de ambulancias y patrullas con tiempos normados de Ámbar y Todo-Rojo.
                    </div>
                </div>
            </td>
            <td>
                <div class="pillar-card">
                    <div class="pillar-title">3. Resiliencia Fail-Safe</div>
                    <div class="pillar-desc">
                        Apego a la NOM-034-SCT2-2011 con watchdog en microcontrolador industrial (Arduino UNO R4 aislado); si la computadora sufriera anomalía, conmuta en 3s a destello preventivo.
                    </div>
                </div>
            </td>
        </tr>
    </table>

    <p class="legal-body-noindent" style="font-size: 8.85pt; margin-top: 2px;">
        Por lo anteriormente expuesto y fundado, a Usted, <strong>C. Secretario de Seguridad Ciudadana</strong>, respetuosamente solicito se sirva:
    </p>

    <ul class="petitorio-list">
        <li class="petitorio-item">
            <span class="petitorio-num">PRIMERO.</span> Tener por presentado en tiempo y forma el presente escrito libre al tenor del Artículo 8° de la Constitución Política de los Estados Unidos Mexicanos.
        </li>
        <li class="petitorio-item">
            <span class="petitorio-num">SEGUNDO.</span> Conceder una <strong>AUDIENCIA DE PRESENTACIÓN Y DEMOSTRACIÓN TÉCNICA EN VIVO DEL PROTOTIPO</strong> ante Usted, o ante los servidores públicos de la Subsecretaría de Control de Tránsito, de la Dirección General de Ingeniería de Tránsito y del C5 que tenga a bien designar, para exponer el funcionamiento del sistema.
        </li>
        <li class="petitorio-item">
            <span class="petitorio-num">TERCERO.</span> Instruir a las áreas correspondientes para evaluar la viabilidad de suscribir un <strong>Convenio de Vinculación Tecnológica</strong> entre la SSC y el TESCo (TecNM), a efecto de explorar la realización de una <strong>PRUEBA PILOTO EXPERIMENTAL CONTROLADA</strong> en un cruce designado por la SSC (en modalidad testigo o sombra, sin costo de adquisición tecnológica para la Secretaría).
        </li>
        <li class="petitorio-item">
            <span class="petitorio-num">CUARTO.</span> Brindarnos la valiosa orientación y retroalimentación técnica de los ingenieros de tránsito de la SSC para alinear los parámetros del prototipo a la normatividad y necesidades operativas de la Ciudad de México.
        </li>
        <li class="petitorio-item">
            <span class="petitorio-num">QUINTO.</span> Dictar la respuesta por escrito que en derecho corresponda a la presente petición, notificándola a los medios de contacto señalados en el proemio.
        </li>
    </ul>

    <div class="signature-section">
        <p style="text-align: center; margin: 2px 0; font-family: 'Montserrat', sans-serif; font-size: 7.7pt; font-weight: 700; color: #1e293b;">
            PROTESTO LO NECESARIO CONFORME A DERECHO<br>
            <span style="font-size: 6.7pt; font-weight: 500; color: #64748b;">"Por la Soberanía Tecnológica y la Innovación al Servicio de México"</span>
        </p>

        <table class="signature-table">
            <tr>
                <td style="width: 50%;">
                    <br>
                    <div class="sig-line"></div>
                    <div class="sig-name">C. Moisés Emilio Martínez Arias</div>
                    <div class="sig-charge">Desarrollador Principal y Titular del Proyecto FLUXA</div>
                    <div class="sig-inst">División de Ingeniería en Sistemas Computacionales • TESCo / TecNM</div>
                </td>
                <td style="width: 50%;">
                    <br>
                    <div class="sig-line"></div>
                    <div class="sig-name">Mtro. Roberto Carlos Muñoz Celaya</div>
                    <div class="sig-charge">Asesor Docente y de Vinculación Tecnológica</div>
                    <div class="sig-inst">División de Ingeniería en Sistemas Computacionales • TESCo / TecNM</div>
                </td>
            </tr>
        </table>

        <div class="team-grid-card">
            <strong>EQUIPO MULTIDISCIPLINARIO DE DESARROLLO (TESCo • TecNM):</strong>
            • Diego Huichapeño • Ethan Flores • Citlalli Rojas • Jerazan Becerra<br>
            <strong>Proyecto Registrado:</strong> Certamen Nacional de Innovación Tecnológica InnovaTecNM 2026 (Folio 70785-17).
        </div>
    </div>

    <table class="footer-table">
        <tr>
            <td class="footer-left">
                Oficio TECNM-TESCO/DISC/FLUXA-2026/014 • Solicitud de Audiencia Institucional • Lic. Pablo Vázquez Camacho (SSC CDMX)
            </td>
            <td class="footer-right">
                Página 2 de 2
            </td>
        </tr>
    </table>
</div>

</body>
</html>
"""

print(f"Escribiendo archivo HTML institucional en {OUTPUT_HTML}...")
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Compilando a PDF con Chromium Headless...")
cmd = [
    '/usr/bin/chromium-browser',
    '--headless',
    '--disable-gpu',
    '--run-all-compositor-stages-before-draw',
    f'--print-to-pdf={OUTPUT_PDF}',
    '--no-pdf-header-footer',
    f'file://{OUTPUT_HTML}'
]

res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if res.returncode != 0:
    print(f"Error generando PDF: {res.stderr}")
    sys.exit(1)

print(f"PDF generado con éxito: {OUTPUT_PDF}")

os.makedirs(os.path.dirname(DOCS_PDF), exist_ok=True)
shutil.copy2(OUTPUT_PDF, DOCS_PDF)
print(f"Copia creada en: {DOCS_PDF}")

os.makedirs(ARTIFACT_DIR, exist_ok=True)
shutil.copy2(OUTPUT_PDF, ARTIFACT_PDF)
print(f"Copia creada en artefactos: {ARTIFACT_PDF}")

pdfinfo_res = subprocess.run(['pdfinfo', OUTPUT_PDF], stdout=subprocess.PIPE, text=True)
print("=== METADATA DEL PDF ===")
print(pdfinfo_res.stdout)

SCRATCH_DIR = os.path.join(ARTIFACT_DIR, 'scratch')
os.makedirs(SCRATCH_DIR, exist_ok=True)
# Limpiar imágenes previas y re-renderizar
for f in os.listdir(SCRATCH_DIR):
    if f.endswith('.png'):
        try:
            os.remove(os.path.join(SCRATCH_DIR, f))
        except Exception:
            pass

pdftoppm_cmd = ['pdftoppm', '-png', '-r', '150', OUTPUT_PDF, os.path.join(SCRATCH_DIR, 'pagina')]
subprocess.run(pdftoppm_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"Páginas renderizadas a imágenes PNG en: {SCRATCH_DIR}")
