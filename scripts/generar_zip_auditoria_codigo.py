#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar el ZIP ultra-ligero y optimizado para auditoría de código puro por Inteligencia Artificial.
Incluye exclusivamente:
- fluxapi/src/ (código Python: FSM, NPU RKNN, sync, telemetría, db, api, streaming)
- fluxapi/arduino/ (firmware C++ para Arduino UNO R4 Minima con watchdog de seguridad)
- fluxapi/tests/ (suite de pruebas unitarias y validación)
- fluxapi/systemd/ (servicio systemd para gabinete autónomo)
- fluxapi/main.py, config.example.json, requirements.txt
- MANIFESTO_AUDITORIA.md (manifiesto técnico enfocado en objetivos de auditoría)

Excluye 100% de binarios, PDFs, imágenes, y archivos HTML con base64 incrustado para evitar
la saturación del límite de contexto/caracteres del lector de la IA y proteger datos personales.
"""

import os
import zipfile
import shutil

BASE_DIR = '/home/moisesmartinez/PycharmProjects/yolov8srknn'
FLUXAPI_DIR = os.path.join(BASE_DIR, 'fluxapi')
ZIP_NAME = 'fluxa_codigo_fuente_auditoria.zip'
ZIP_PATH = os.path.join(BASE_DIR, ZIP_NAME)
ALT_ZIP_PATH = os.path.join(BASE_DIR, 'fluxa_proyecto_auditoria_ia.zip')
ARTIFACT_DIR = '/home/moisesmartinez/.gemini/antigravity-ide/brain/0effe450-ae21-42e7-945b-ab94acaa085d'
ARTIFACT_ZIP = os.path.join(ARTIFACT_DIR, ZIP_NAME)

MANIFESTO_CONTENT = """# 📋 FLUXA Smart Mobility — Manifiesto de Auditoría de Código Fuente para IA

Bienvenida, IA auditora. Este paquete comprimido contiene **exclusivamente el código fuente puro (Python, C++, Bash, Systemd y configuraciones clave)** de la plataforma FLUXA Smart Mobility.

Se han retirado deliberadamente todos los archivos binarios (.rknn, .onnx, .bin), videos, imágenes (.png, .jpg), documentos PDF y archivos HTML pesados con Base64, garantizando que el 100% del límite de lectura de caracteres/tokens se concentre en el código ejecutable y respetando la privacidad de datos.

---

## 🎯 Objetivos Específicos para esta Auditoría

Te solicitamos auditar a profundidad los siguientes 6 ejes críticos de ingeniería:

1. **Concurrencia, Bloqueos y Condiciones de Carrera (Race Conditions):**
   - Ingesta de video multihilo (`fluxapi/src/videostream.py`) y búferes compartidos.
   - Cola asíncrona de base de datos en segundo plano (`fluxapi/src/db_manager.py`).
   - Servidor Flask multihilo (`fluxapi/src/api_server.py`) interactuando con el ciclo del semáforo.

2. **Gestión de Memoria y Prevención de Fugas (Memory Leaks):**
   - Manejo de frames OpenCV (`cv2.VideoCapture`), matrices NumPy y tensores RKNN en ciclos continuos 24/7.
   - Búfer local SQLite/archivo en `db_manager.py` cuando se pierde conexión con MariaDB.

3. **Lógica de la Máquina de Estados Finitos (FSM) y Seguridad Vial:**
   - Transiciones de fases en `fluxapi/src/core_semaforo.py` y `fluxapi/src/core_semaforo_rknn.py`.
   - Garantía de tiempos mínimos de verde, intervalos de despeje (Ámbar y Todo-Rojo normativos).
   - Priorización del Transporte Público (TSP) y Corredor de Emergencia: verificación de que nunca provoquen estados conflictivos o colisiones.

4. **Firmware de Resiliencia Física en Microcontrolador (Arduino C++):**
   - `fluxapi/arduino/fluxa_2way_controller/fluxa_2way_controller.ino`.
   - Lógica de conmutación atómica de relevadores (invariante de nunca encender verdes simultáneos).
   - Watchdog serial fail-safe con temporizador de seguridad y conmutación a destello ámbar preventivo (NOM-034-SCT2-2011).

5. **Seguridad Web, API REST y Autenticación:**
   - Autenticación en `fluxapi/src/api_server.py` (PBKDF2-SHA256, tokens de sesión).
   - Sanitización de endpoints, validación de payloads JSON en `/api/roi`, `/api/emergency`, `/api/timing`.

6. **Despliegue y Recuperación en Edge Linux:**
   - Configuración de `fluxapi/systemd/fluxa.service` (políticas de reinicio `Restart=always`, límites de descriptores `LimitNOFILE`, variables de entorno).

---

## 🗂️ Estructura del Paquete Incluido

```text
fluxapi/
├── main.py                                     # Entrypoint principal de CLI
├── config.example.json                         # Esquema de configuración del sistema (umbrales, FSM, DB)
├── requirements.txt                            # Dependencias del runtime Python
│
├── src/                                        # CAPA 1: MOTOR DE ALGORITMOS Y BACKEND
│   ├── core_semaforo.py                        # FSM central, aforo carril por carril, lógica TSP y seguridad
│   ├── core_semaforo_rknn.py                   # Inferencia NPU multi-core para Rockchip RK3588 (6 TOPS)
│   ├── corridor_sync.py                        # Coordinación arterial y propagación de olas verdes
│   ├── hardware_monitor.py                     # Telemetría de hardware (CPU, NPU, RAM, térmica)
│   ├── db_manager.py                           # MariaDB asíncrono con tolerancia a desconexión
│   ├── videostream.py                          # Ingestión de cámara en hilo independiente con auto-reconexión
│   ├── api_server.py                           # API REST Flask, autenticación y streaming MJPEG
│   ├── cli.py                                  # Enrutador de comandos y argumentos de consola
│   ├── utils.py & utils_rknn.py                # Geometría de ROIs, IoU y utilidades matemáticas
│   └── ui*.py                                  # Controladores por topología vial (2 vías, 4 vías, tipo T, etc.)
│
├── arduino/                                    # CAPA 2: FIRMWARE PARA MICROCONTROLADOR INDUSTRIAL
│   └── fluxa_2way_controller/
│       └── fluxa_2way_controller.ino           # Firmware Arduino UNO R4 Minima (Watchdog 3s & fail-safe)
│
├── systemd/                                    # CAPA 3: SERVICIOS LINUX DE ARRANQUE EN GABINETE
│   ├── fluxa.service                           # Unidad systemd para autoarranque y supervisión
│   └── install_service.sh                      # Script de instalación y aprovisionamiento del daemon
│
└── tests/                                      # CAPA 4: SUITE DE PRUEBAS Y VALIDACIÓN
    ├── run_all_unit_tests.py                   # Ejecutor maestro de pruebas
    ├── test_fsm.py                             # Pruebas de la máquina de estados y tiempos
    ├── test_audit_full.py                      # Pruebas de auditoría integral
    ├── test_corridor.py                        # Pruebas de sincronización de corredores
    ├── test_boxes.py                           # Validación geométrica de cajas y polígonos
    └── test_opi5.py                            # Verificación en hardware Orange Pi 5
```

¡Adelante con la auditoría técnica línea por línea!
"""

def generar_zip():
    print("Iniciando empaquetado optimizado de código fuente...")
    
    # Lista ordenada de archivos para garantizar que los componentes más críticos
    # se almacenen al principio del archivo ZIP (así el extractor de la IA los lee primero).
    archivos_prioritarios_src = [
        'core_semaforo.py',
        'core_semaforo_rknn.py',
        'corridor_sync.py',
        'hardware_monitor.py',
        'videostream.py',
        'db_manager.py',
        'api_server.py',
        'cli.py',
        'utils.py',
        'utils_rknn.py',
        'analytics.py',
        'generate_demo_video.py',
        'ui2_way.py',
        'ui2_way_cpu.py',
        'ui3_tee.py',
        'ui3_tee_cpu.py',
        'ui4_way.py',
        'ui4_way_cpu.py',
        'ui4_protected.py',
        'ui4_protected_cpu.py',
        'ui_pedestrian.py',
        'ui_pedestrian_cpu.py',
        'ui4_nano.py',
        'ui4_nano_cpu.py',
        'ui4.py',
        'ui4_cpu.py'
    ]

    zip_entries = [] # lista de tuplas (path_absoluto, arcname_en_zip)

    # 1. Configuración y entrypoint raíz
    for fn in ['main.py', 'config.example.json', 'requirements.txt']:
        fp = os.path.join(FLUXAPI_DIR, fn)
        if os.path.exists(fp):
            zip_entries.append((fp, f'fluxapi/{fn}'))

    # 2. Archivos prioritarios de src/
    for fn in archivos_prioritarios_src:
        fp = os.path.join(FLUXAPI_DIR, 'src', fn)
        if os.path.exists(fp):
            zip_entries.append((fp, f'fluxapi/src/{fn}'))

    # 3. Resto de archivos de src/ si hubiera nuevos
    src_dir = os.path.join(FLUXAPI_DIR, 'src')
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if f.endswith('.pyc') or f.endswith('.pyo'):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, BASE_DIR)
            if not any(entry[0] == fp for entry in zip_entries):
                zip_entries.append((fp, rel))

    # 4. Arduino firmware
    arduino_dir = os.path.join(FLUXAPI_DIR, 'arduino')
    for root, dirs, files in os.walk(arduino_dir):
        for f in sorted(files):
            if f.endswith('.ino') or f.endswith('.h') or f.endswith('.cpp'):
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, BASE_DIR)
                zip_entries.append((fp, rel))

    # 5. Systemd services
    systemd_dir = os.path.join(FLUXAPI_DIR, 'systemd')
    for root, dirs, files in os.walk(systemd_dir):
        for f in sorted(files):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, BASE_DIR)
            zip_entries.append((fp, rel))

    # 6. Tests
    tests_dir = os.path.join(FLUXAPI_DIR, 'tests')
    for root, dirs, files in os.walk(tests_dir):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if f.endswith('.pyc') or f.endswith('.pyo'):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, BASE_DIR)
            zip_entries.append((fp, rel))

    print(f"Empaquetando {len(zip_entries)} archivos de código fuente...")

    # Crear el ZIP con máxima compresión
    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # 1. Escribir primero el manifiesto para que sea el primer texto extraído
        zf.writestr('MANIFESTO_AUDITORIA.md', MANIFESTO_CONTENT.strip() + '\n')
        
        # 2. Escribir cada archivo en el orden estructurado
        for fp, arcname in zip_entries:
            zf.write(fp, arcname)

    size_bytes = os.path.getsize(ZIP_PATH)
    size_kb = size_bytes / 1024
    print(f"✅ ZIP creado exitosamente: {ZIP_PATH}")
    print(f"📦 Tamaño total: {size_kb:.1f} KB ({size_bytes} bytes)")

    # Copiar también con el nombre anterior para conveniencia
    shutil.copy2(ZIP_PATH, ALT_ZIP_PATH)
    print(f"🔄 Actualizado también: {ALT_ZIP_PATH}")

    # Copiar al directorio de artefactos de la sesión actual
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    shutil.copy2(ZIP_PATH, ARTIFACT_ZIP)
    print(f"📁 Copia disponible en artefactos: {ARTIFACT_ZIP}")

    # Verificación de contenidos
    print("\n--- Verificación de Contenido del ZIP ---")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        info_list = zf.infolist()
        total_uncompressed = sum(i.file_size for i in info_list)
        print(f"Total de archivos en el archivo ZIP: {len(info_list)}")
        print(f"Tamaño total descomprimido: {total_uncompressed / 1024:.1f} KB")
        for i, info in enumerate(info_list, 1):
            print(f"  {i:02d}. {info.filename} ({info.file_size} bytes)")

if __name__ == '__main__':
    generar_zip()
