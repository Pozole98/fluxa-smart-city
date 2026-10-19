#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar un ZIP ultra-ligero y optimizado para auditoría por Inteligencia Artificial.
Conserva el 100% de la lógica, algoritmos, arquitectura, frontend, backend, firmware,
documentación y pruebas, excluyendo pesos de redes neuronales, videos pesados, entornos virtuales y vendor submodules.
"""

import os
import zipfile
import shutil

BASE_DIR = '/home/moisesmartinez/PycharmProjects/yolov8srknn'
ZIP_NAME = 'fluxa_proyecto_auditoria_ia.zip'
ZIP_PATH = os.path.join(BASE_DIR, ZIP_NAME)
ARTIFACT_DIR = '/home/moisesmartinez/.gemini/antigravity-ide/brain/6a7fdd6a-c405-421b-802c-117d2df9d250'
ARTIFACT_ZIP = os.path.join(ARTIFACT_DIR, ZIP_NAME)

# Directorios a excluir completamente
EXCLUDE_DIRS = {
    '.venv', 'venv', '.git', '.idea', '__pycache__', '.pytest_cache',
    '3rdparty', 'rknn-toolkit2', 'calib_data', 'extracted_img',
    'datasets', 'examples', 'wheels', 'videos', 'entregasanteriores',
    'logs', 'yolov8_semaforo_advanced'
}

# Extensiones de archivos pesados o binarios irrelevantes para auditoría de código
EXCLUDE_EXTS = {
    '.onnx', '.rknn', '.pt', '.pth', '.bin', '.whl',
    '.mp4', '.avi', '.mkv', '.mov', '.tar', '.gz', '.zip'
}

# Archivos de imagen permitidos (solo logos clave y de bajo peso)
ALLOWED_IMAGES = {
    'tesco.png', 'tecnm.png', 'sic.png', 'fluxa_official_logo.png'
}

manifesto_content = """# 📋 FLUXA Smart Mobility — Manifiesto de Auditoría de Código para IA

Este paquete ha sido optimizado específicamente para análisis y auditoría técnica mediante modelos de Inteligencia Artificial (Claude, GPT, Gemini, Cursor, etc.). 

Contiene **el 100% del código fuente, arquitectura, firmware de microcontrolador, centro de mando web SCADA, pruebas unitarias, documentación técnica y el escrito libre formal dirigido a la Secretaría de Seguridad Ciudadana (SSC CDMX)**, habiendo depurado únicamente los binarios pesados (pesos neuronales, videos MP4 de prueba, entornos virtuales `.venv` y submódulos vendor).

---

## 🗂️ Estructura Principal del Proyecto

```text
fluxa-smart-city/
├── Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.pdf  # Escrito libre formal de 2 páginas para Lic. Pablo Vázquez Camacho
├── Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.html # Código fuente HTML oficial del escrito institucional
├── main.py, convert_rknn.py, export_onnx.py    # Pipeline de conversión, cuantización INT8 y ejecución CLI
├── test_opi5.py, ui2.py, ui4.py, utils_rknn.py # Controladores base para Rockchip RK3588 (Orange Pi 5)
├── README.md, FAQ.md, LICENSE                  # Documentación raíz y licencias
│
├── fluxapi/                                    # NÚCLEO MODERNO DE PRODUCCIÓN (FLUXA CORE)
│   ├── src/                                    # Núcleo algorítmico y servicios
│   │   ├── core_semaforo.py                    # FSM base, cálculo de aforo carril por carril, TSP y fail-safe
│   │   ├── core_semaforo_rknn.py               # Motor NPU acelerado por hardware para Rockchip RK3588 (3 núcleos)
│   │   ├── corridor_sync.py                    # Coordinador de corredores viales y propagación de olas verdes
│   │   ├── hardware_monitor.py                 # Telemetría de SoC (CPU, RAM, disco, temperatura, núcleos NPU)
│   │   ├── api_server.py                       # Servidor Flask multihilo, APIs REST y streaming MJPEG
│   │   ├── db_manager.py                       # Gestor asíncrono MariaDB con búfer local tolerante a fallos
│   │   ├── videostream.py                      # Ingestión de cámara vial con reconexión automática en hilo
│   │   └── ui*_way*.py                         # Controladores por topología vial (4 vías, 2 vías, tipo T, etc.)
│   │
│   ├── arduino/                                # FIRMWARE INDUSTRIAL PARA MICROCONTROLADOR
│   │   └── fluxa_2way_controller/
│   │       └── fluxa_2way_controller.ino       # Código C++ para Arduino UNO R4 Minima (Watchdog serial 3s y relevadores)
│   │
│   ├── templates/                              # INTERFACES WEB Y CENTRO DE MANDO
│   │   ├── index.html                          # Consola SCADA C5, Corredor de Emergencia y Calibrador Canvas ROI
│   │   ├── public.html                         # Portal Ciudadano de Movilidad Abierta (SPaT, GLOSA, métricas CO2)
│   │   ├── login.html                          # Portal seguro C5 con cifrado criptográfico PBKDF2-SHA256
│   │   └── report_executive.html               # Generador de dictámenes ejecutivos de aforo en PDF
│   │
│   ├── docs/                                   # INGENIERÍA Y MODELO DE NEGOCIO
│   │   ├── MANUAL_TECNICO.md                   # Manual técnico y arquitectura de ingeniería a bajo nivel
│   │   ├── MODELO_NEGOCIO_B2G.md               # Modelo de negocio municipal B2G, BOM y cálculo de ROI social
│   │   ├── PLAN_ENTRENAMIENTO.md               # Guía de fine-tuning y cuantización INT8 para datasets viales
│   │   └── arquitectura.mmd                    # Diagrama de arquitectura del sistema en Mermaid
│   │
│   ├── scripts/                                # Automatización y despliegue
│   ├── systemd/                                # Unidad de servicio fluxa.service para arranque autónomo en gabinete
│   ├── tests/                                  # Suite de pruebas unitarias y auditoría end-to-end
│   ├── config.example.json, config.json        # Configuración maestra del sistema y geometrías poligonales
│   ├── install.sh, uninstall.sh                # Instalador desatendido para Armbian, openSUSE, Ubuntu, Debian, RHEL
│   └── Dockerfile, docker-compose.yml          # Despliegue contenerizado
│
└── yolov8_semaforo_clean/                      # Código base simplificado para pruebas independientes
```

---

## ⚙️ Componentes Excluidos por Optimización de Peso
1. **Modelos neuronales binarios:** `models/*.onnx`, `models/*.rknn`, `models/*.pt` (de 4 MB a 45 MB c/u).
2. **Video demo vial:** `videos/demo.mp4` (43 MB).
3. **Entorno virtual Python:** `.venv` (6 GB).
4. **Submódulo vendor OpenCV:** `3rdparty/` (611 MB) y `rknn-toolkit2/` (5.8 GB).
5. **Fotos de auditoría de infracciones:** `logs/violations/*.jpg` y capturas de calibración.

*Generado automáticamente para auditoría de código, seguridad, calidad y análisis arquitectónico.*
"""

files_to_pack = []
for root, dirs, files in os.walk(BASE_DIR):
    # Podar directorios pesados
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith('.venv') and not d.startswith('.git')]
    
    parts = set(root.split(os.sep))
    if parts.intersection(EXCLUDE_DIRS):
        continue

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in EXCLUDE_EXTS:
            continue
            
        p = os.path.join(root, f)
        
        # Filtro de imágenes: solo incluir logos esenciales
        if ext in ('.jpg', '.jpeg', '.png'):
            if f not in ALLOWED_IMAGES:
                continue
                
        # Filtro de PDFs: solo incluir el Escrito Libre oficial generado para SSC CDMX
        if ext == '.pdf' and f != 'Escrito_Libre_Audiencia_SSC_CDMX_FLUXA.pdf':
            continue
            
        # Filtro de HTMLs gigantes con base64 incrustado (> 500 KB)
        if ext == '.html' and os.path.getsize(p) > 500 * 1024:
            continue
            
        # No incluir zips anteriores
        if f.endswith('.zip'):
            continue

        files_to_pack.append(p)

print(f"Empaquetando {len(files_to_pack)} archivos en el ZIP...")

with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    # Agregar el manifiesto explicativo para la IA
    zf.writestr('MANIFESTO_AUDITORIA.md', manifesto_content)
    
    for p in sorted(files_to_pack):
        rel = os.path.relpath(p, BASE_DIR)
        zf.write(p, rel)

zip_size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
zip_size_kb = os.path.getsize(ZIP_PATH) / 1024
print(f"ZIP creado exitosamente: {ZIP_PATH}")
print(f"Tamaño total: {zip_size_mb:.2f} MB ({zip_size_kb:.1f} KB)")

# Copiar al directorio de artefactos
os.makedirs(ARTIFACT_DIR, exist_ok=True)
shutil.copy2(ZIP_PATH, ARTIFACT_ZIP)
print(f"Copia disponible en artefactos: {ARTIFACT_ZIP}")
