# FLUXA: Sistema de Control Semafórico Inteligente y Telemetría Edge

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/AI-YOLOv8%20%7C%20BYTETracker-008080?style=for-the-badge&logo=opencv&logoColor=white)
![Hardware](https://img.shields.io/badge/Hardware-Orange%20Pi%205%20(RK3588)-005500?style=for-the-badge)
![MCU](https://img.shields.io/badge/MCU-Arduino%20UNO%20R4-teal?style=for-the-badge&logo=arduino&logoColor=white)
![Database](https://img.shields.io/badge/Database-MariaDB%20%2F%20MySQL-brown?style=for-the-badge&logo=mariadb&logoColor=white)
![Web](https://img.shields.io/badge/Web-Flask%20%7C%20SCADA%20C5-004400?style=for-the-badge&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-Propietaria%20%2F%20Comercial-1b396a?style=for-the-badge)

**Tecnológico de Estudios Superiores de Coacalco (TESCo)**  
*División de Ingeniería en Sistemas Computacionales • Tecnológico Nacional de México (TecNM)*  
*Desarrollador Principal y Titular de Derechos: Moisés Emilio Martínez Arias*  
*Proyecto de Innovación Tecnológica y Emprendimiento en Movilidad Inteligente (Smart Mobility)*

[Manual Técnico para Desarrolladores](docs/MANUAL_TECNICO.md) • [Modelo de Negocio B2G y ROI](docs/MODELO_NEGOCIO_B2G.md) • [Plan de Entrenamiento](docs/PLAN_ENTRENAMIENTO.md) • [Especificación de APIs](#especificación-de-interfaces-web-y-apis)

</div>

---

## 1. Descripción General del Sistema

**FLUXA** es una plataforma de **Inteligencia y Orquestación Edge para Tráfico Urbano** diseñada para modernizar intersecciones viales sin requerir el reemplazo de los gabinetes electromecánicos ni cabezales semafóricos existentes.

El sistema opera como una **capa de control superpuesta (*Overlay Controller*)**, compatible con estándares normativos (NEMA TS2, Tipo 170/2070 o interfaces de relevadores directos vía microcontrolador o PLC):

* **Visión Computacional en el Borde (YOLOv8 + BYTETracker):** Cuantificación de colas vehiculares carril por carril y monitoreo de peatones con latencias de inferencia inferiores a **12 ms** en NPU Rockchip RK3588 (Orange Pi 5) o CPU x86/ARM64.
* **Prioridad de Transporte Público (TSP) y Corredores de Emergencia C5:** Ajuste dinámico de tiempos de verde asignando mayor peso al transporte masivo y despeje seguro de vía para vehículos de emergencia mediante intervalos normativos de Ámbar y Todo-Rojo.
* **Sustentabilidad y Analítica V2X:** Reducción de hasta un **60% en tiempos de ralentí vehicular**, mitigación de emisiones de CO₂ y emisión de telemetría de velocidad óptima (GLOSA / SPaT) para vehículos conectados.
* **Auditoría Forense de Infracciones:** Detección de cruces en fase roja con captura fotográfica automática, rotación FIFO de almacenamiento y persistencia asíncrona tolerante a fallos.

```
                  ┌───────────────────────────────────────────────────────────┐
                  │                      SISTEMA FLUXA                        │
                  ├─────────────────────────────┬─────────────────────────────┤
                  │     Semáforo Tradicional    │       FLUXA Edge AI         │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Asignación Fase │ 45s fijos (Calle vacía)     │ Dinámica (5s a 45s por cola)│
│ Prioridad Bus   │ Ninguna                     │ TSP Ponderado (Factor 4.0x) │
│ Huella de CO₂   │ Alta por ralentí inútil     │ Reducción de hasta el 60%   │
│ Emergencias C5  │ Manual o inexistente        │ Despeje Vial Seguro (C5)    │
│ Autos Conectados│ Desconectado                │ V2X Broadcast (SPaT/GLOSA)  │
│ Integración     │ Rígido                      │ Capa Overlay (NEMA / MCU)   │
└─────────────────┴─────────────────────────────┴─────────────────────────────┘
```

> [!IMPORTANT]
> **Arquitectura de Inferencia y Aceleración por Plataforma:**
> * **Aceleración NPU (Hardware Dedicado):** Disponible **única y exclusivamente en la computadora de placa reducida (SBC) Orange Pi 5 (SoC Rockchip RK3588 con 3 núcleos NPU de 6 TOPS)** bajo el sistema operativo **Armbian Linux**. En esta plataforma se ejecutan los modelos compilados y cuantizados en formato `.rknn` (`yolov8n.rknn`, `yolov8s.rknn`, `yolov8m.rknn`).
> * **Inferencia por CPU (PyTorch Estándar):** En todos los demás sistemas operativos y entornos de desarrollo/servidor sobre arquitectura **x86_64** (openSUSE Tumbleweed/Leap, Fedora, RHEL, Ubuntu, Debian), la inferencia de visión por computadora se ejecuta íntegramente a través de la **CPU** utilizando el modelo PyTorch estándar **`yolov8n.pt`**. Esto garantiza portabilidad total y despliegue inmediato sin requerir aceleradores propietarios.

## 2. Arquitectura de Ingeniería del Sistema

### 2.1. Arquitectura de Procesamiento y Telemetría

```mermaid
graph TD
    subgraph SENSORICA [Capa de Captura y Sensores]
        CAM[Camara Vial / RTSP / Video demo.mp4]
        CALL_BTN[Boton Peatonal / Mando C5]
    end

    subgraph PROCESAMIENTO [Procesamiento e Inferencia Edge]
        PRE[Normalizacion 640x640]
        INFER[Inferencia Dual: NPU RKNN / CPU PyTorch]
        POST[Postprocesamiento y NMS]
        TRACKER[BYTETracker - IDs Unicos]
        ROI[Filtro Espacial de ROIs]
        TSP[Ponderacion Matematica TSP]
    end

    subgraph FSM_CORE [Maquina de Estados Finitos]
        FSM[CoreSemaforo - FSM Adaptativa]
        CLEARANCE[Protocolo Despeje: Ambar y Todo-Rojo]
        EMERGENCY[Controlador de Emergencia C5]
        SUSTAIN[Calculo de CO2 y Ahorro Energetico]
    end

    subgraph HARDWARE_OUTPUT [Controladores Fisicos]
        ARDUINO[Arduino UNO R4 / PLC / Relevadores]
        LIGHTS[Cabezales Semaforicos Fisicos]
        CONTROLLER_EX[Controlador Existente NEMA / 170 / 2070]
    end

    subgraph SERVICIOS [Servicios Web y Base de Datos]
        MARIADB[(MariaDB - Persistencia Asincrona)]
        FLASK_API[Servidor Flask y API REST]
        SCADA[Consola SCADA C5 - /admin]
        PUBLIC_PORTAL[Portal Ciudadano y V2X - /]
        VIOLATIONS[Modulo Forense de Infracciones]
    end

    CAM --> PRE
    CALL_BTN --> FSM
    PRE --> INFER
    INFER --> POST
    POST --> TRACKER
    TRACKER --> ROI
    ROI --> TSP
    TSP --> FSM

    FSM --- CLEARANCE
    FSM --- EMERGENCY
    FSM --> SUSTAIN

    FSM -->|Comandos Seriales| ARDUINO
    ARDUINO --> LIGHTS
    ARDUINO -.->|Integracion Gabinete| CONTROLLER_EX

    FSM -->|Eventos y Telemetria| FLASK_API
    FSM -->|Cola Asincrona| MARIADB
    FSM -->|Deteccion Infracciones| VIOLATIONS

    FLASK_API --> SCADA
    FLASK_API --> PUBLIC_PORTAL
    VIOLATIONS --> MARIADB
```

### 2.2. Integración de Gabinete Industrial y Hardware Edge (*Overlay Controller*)

```mermaid
graph LR
    subgraph CAMPO [Intersección Vial]
        OPTIC[Cámara Vial HD Gran Angular]
        SIG_NS[Cabezales Semafóricos Norte-Sur]
        SIG_EO[Cabezales Semafóricos Este-Oeste]
        PED_BTN[Botonera Peatonal]
    end

    subgraph GABINETE [Gabinete NEMA IP66 - FLUXA Edge Appliance]
        direction TB
        PSU[Fuente MeanWell 12V/5V DC + Supresor de Picos]
        
        subgraph SBC [Cómputo Edge Acelerado]
            OPI5[Orange Pi 5 - SoC Rockchip RK3588]
            NPU_CORE[Tri-Core NPU 6 TOPS INT8]
            OS_ENGINE[Armbian Linux 24.04]
            OPI5 --- NPU_CORE
            OPI5 --- OS_ENGINE
        end
        
        subgraph MCU [Potencia y Watchdog Fail-Safe]
            ARD[Arduino UNO R4 / Microcontrolador]
            WDOG[Watchdog Temporizado - 3s]
            SSR[Banco Relevadores Estado Sólido Optoacoplados]
            ARD --- WDOG
            ARD --- SSR
        end
    end

    OPTIC -->|USB / RTSP| OPI5
    PED_BTN -->|GPIO| ARD
    OPI5 -->|Enlace Serial USB CDC /dev/ttyACM0| ARD
    SSR -->|120VAC / 24VDC| SIG_NS
    SSR -->|120VAC / 24VDC| SIG_EO
    PSU --> SBC
    PSU --> MCU
```

---

## 3. Especificaciones de Ingeniería

### 3.1. Inferencia Dual con Tolerancia a Fallos (NPU / CPU)

| Plataforma / Entorno | Hardware & Sistema Operativo | Motor de Inferencia | Modelo / Formato | Latencia Promedio |
| :--- | :--- | :--- | :--- | :--- |
| **Producción Edge (Objetivo Principal)** | Orange Pi 5 (RK3588 ARM64) • **Armbian 24.04** | **NPU RKNN Hardware** (3 Núcleos / 6 TOPS) | `yolov8n.rknn` (INT8) | **~3.4 ms a 14 ms** |
| **Desarrollo y Servidores x86_64** | openSUSE, Ubuntu, Fedora, Debian, RHEL (x86_64) | **CPU (PyTorch Engine)** | `yolov8n.pt` (FP32/INT8) | **~25 ms a 45 ms** |
| **Fail-Safe Fallback Automático** | Orange Pi 5 (en caso de contingencia NPU) | **CPU Fallback Automático** | `yolov8n.pt` | **~50 ms a 70 ms** |

* **Aceleración NPU Exclusiva para Orange Pi 5 (Armbian):** Los modelos cuantizados en formato INT8 (`yolov8n.rknn`, `yolov8s.rknn`, `yolov8m.rknn`) están diseñados específicamente para el chip Rockchip RK3588 bajo el sistema operativo **Armbian Linux**.
* **Inferencia por CPU en Arquitecturas x86_64:** En estaciones de trabajo, laptops y servidores bajo openSUSE, Ubuntu, Fedora o Debian, la ejecución se realiza enteramente vía CPU utilizando el modelo PyTorch estándar **`yolov8n.pt`**.
* **Fail-Safe Fallback Automático:** Si la librería `rknnlite`, el controlador del acelerador o el archivo `.rknn` presentan fallas en tiempo de ejecución en la Orange Pi 5, el sistema conmuta automáticamente y sin interrupción al motor PyTorch en CPU (`yolov8n.pt`).

### 3.2. Módulo Forense de Infracciones y Cuotas de Almacenamiento
* **Detección Espaciotemporal:** Validación automática de cruces vehiculares durante fase roja en carriles conflictivos.
* **Persistencia Multicapa:** Registro en MariaDB con respaldo simultáneo en búfer circular de memoria RAM y escaneo de disco para asegurar disponibilidad inmediata incluso sin base de datos.
* **Control de Almacenamiento:** Política FIFO automática con límites configurables (por defecto 300 capturas y 150 MB máximo) para proteger el almacenamiento del hardware en campo.

### 3.3. Seguridad Criptográfica y Gestión de Credenciales
* **Autenticación Basada en PBKDF2-SHA256:** Las credenciales del operador C5 se almacenan exclusivamente como hashes criptográficos en `instance/admin_credentials.json` con permisos de sistema `0600`.
* **Configuración Segregada:** Los archivos con credenciales locales (`config.json`, `.env`, `instance/`) se encuentran desindexados del repositorio. El proyecto distribuye la plantilla pública `config.example.json`.
* **Instalador Interactivo:** `install.sh` solicita contraseñas de forma segura durante el despliegue o genera cadenas aleatorias de alta entropía.

### 3.4. Resumen de Capacidades y Facilidades del Sistema

| Dimensión Técnica | Capacidad / Facilidad Implementada | Especificación de Ingeniería |
| :--- | :--- | :--- |
| **Inferencia Edge AI** | NPU Rockchip RK3588 (6 TOPS INT8) | Latencia sub-12ms, 30-60 FPS, modelos cuantizados `.rknn` con fallback en CPU PyTorch |
| **Rastreo Multiobjeto** | Algoritmo BYTETracker + Filtro de Kalman | Identificadores únicos persistentes (*Track IDs*) sin duplicación por oclusión |
| **Aforo por Carril** | Algoritmo Point-in-Polygon (Ray Casting) | Medición de colas en tiempo real por polígono de carril configurable en navegador |
| **Control Adaptativo** | FSM Dinámica con Prioridad TSP | Verde adaptativo (5s a 45s), autobuses ponderados $4.0\times$ y salto de fases vacías |
| **Seguridad Vial** | Protocolo Normativo de Despeje | Transiciones forzadas con Ámbar ($3.0\text{s}$) y Todo-Rojo ($2.0\text{s}$) garantizadas |
| **Resiliencia Fail-Safe** | Matriz de Contingencia Tri-Nivel | Conmutación NPU $\to$ CPU y Watchdog de hardware en MCU con ciclo de respaldo aislado |
| **Fiscalización** | Módulo Forense de Infracciones | Detección de cruce en luz roja, fotos JPEG con metadatos y rotación circular FIFO |
| **Centro de Mando C5** | Consola Web SCADA + MJPEG Stream | Mando de corredor de emergencia, telemetría de hardware, streaming y editor ROI Canvas |
| **Sustentabilidad** | Motor de Ahorro y Huella Ecológica | Cálculo continuo de litros de gasolina ahorrados y kilogramos de $\text{CO}_2$ mitigados |
| **Telemetría V2X** | Protocolos SPaT y GLOSA en JSON | Emisión de estado de fase y velocidad recomendada para vehículos conectados |
| **Auditoría Oficial** | Generador de Informes PDF | Dictámenes ejecutivos de aforo e incidencias con sello de verificación criptográfica |
| **Despliegue Universal**| Script Nativo `install.sh` + Docker | Soporte multiplataforma: Armbian 24.04, openSUSE, Fedora, RHEL, Ubuntu y Debian |

---

## 4. Catálogo de Topologías Viales Soportadas

| Topología CLI | Nombre del Cruce | Descripción Operativa |
| :--- | :--- | :--- |
| `4_way` | **4 Vías Clásica** | Intersección ortogonal de 4 accesos (Eje Norte-Sur vs Eje Este-Oeste). |
| `2_way` | **2 Vías / Avenida** | Avenida bidireccional continua con optimización de flujo por sentido (Zona A vs B). |
| `3_way_t` | **3 Vías Tipo T** | Intersección en T (Avenida Principal continua vs Calle Secundaria). |
| `4_way_protected` | **Giro Protegido** | 4 vías con fase exclusiva de flecha izquierda y salto inteligente de fase vacía (*Phase-skipping*). |
| `pedestrian` | **Cruce Peatonal** | Cruce *mid-block* con detección de demanda peatonal en banqueta y tiempos seguros de cruce. |

---

## 5. Instalación y Despliegue

### Método 1: Instalador Universal Nativo (Recomendado para Producción & Edge)
Compatible con **Armbian 24.04 (Orange Pi 5)**, **openSUSE (Tumbleweed, Leap 15+, SLES, MicroOS)**, **Fedora/RHEL**, **Ubuntu** y **Debian**:

```bash
git clone https://github.com/Pozole98/fluxa-smart-city.git
cd fluxa-smart-city
bash install.sh
```

El script detecta automáticamente el gestor de paquetes de tu distribución (`zypper`, `dnf`, `apt`), instala MariaDB, bibliotecas OpenGL/V4L2, dependencias de compilación, configura reglas `udev` de hardware, despliega el entorno virtual `.venv`, crea el acceso global `fluxa` y registra la unidad de servicio `systemd`.

Para desinstalar limpiamente:
```bash
bash uninstall.sh
```

---

### Método 2: Despliegue con Contenedores (Docker / Podman)
```bash
# Iniciar servicios en segundo plano
docker compose up -d

# Visualizar registros
docker compose logs -f
```

---

## 6. Ejecución del Sistema

### Ejecución por Línea de Comandos (CLI)
```bash
# Intersección de 4 vías en CPU con clip demo en puerto 5000
fluxa --topology 4_way --backend cpu --headless --video videos/demo.mp4 --port 5000

# Intersección en Orange Pi 5 (NPU RK3588 con aceleración por hardware)
fluxa --topology 4_way --backend rknn --headless --port 5000
```

### Control del Servicio de Gabinete Vial (Systemd)
```bash
sudo systemctl start fluxa      # Iniciar servicio
sudo systemctl stop fluxa       # Detener servicio
sudo systemctl restart fluxa    # Reiniciar servicio
journalctl -u fluxa -f          # Telemetría en tiempo real
```

---

## 7. Plataforma WebUI y Centro de Mando en Tiempo Real (Acceso y Operación)

El sistema **FLUXA** incorpora un servidor web de alto rendimiento (Flask 3.x multihilo) que expone dos interfaces gráficas completas, interactivas y responsivas, accesibles desde cualquier navegador moderno (**Google Chrome, Mozilla Firefox, Microsoft Edge, Safari**) en computadoras de escritorio, tablets, smartphones o videowalls de centros C5/C4, **sin requerir la instalación de ningún cliente o software adicional**:

* **URL de Acceso Local / Desarrollo:** `http://localhost:5000`
* **URL de Acceso en Red Local / Edge:** `http://<IP_DE_LA_ORANGE_PI_O_SERVIDOR>:5000`
* **Puerto Predeterminado:** `5000` (configurable mediante el parámetro `--port <NUMERO>`).

```
                              ┌─────────────────────────────────────────────────────────┐
                              │            SERVIDOR WEB FLUXA (PUERTO 5000)             │
                              └────────────────────────────┬────────────────────────────┘
                                                           │
                      ┌────────────────────────────────────┴────────────────────────────────────┐
                      ▼                                                                         ▼
   ┌─────────────────────────────────────┐                                   ┌─────────────────────────────────────┐
   │    PORTAL CIUDADANO ABIERTO ( / )   │                                   │     PORTAL DE ACCESO C5 ( /login )  │
   ├─────────────────────────────────────┤                                   ├─────────────────────────────────────┤
   │ • Estado del Semáforo en Tiempo Real│                                   │ • Autenticación Criptográfica       │
   │ • Conteo de Aforo por Carril en Vivo│                                   │ • Cifrado PBKDF2-SHA256             │
   │ • Calculadora de Ahorro de Gasolina │                                   │ • Control de Sesión HttpOnly        │
   │ • Mitigación de CO2 en Vivo         │                                   └──────────────────┬──────────────────┘
   │ • Telemetría V2X SPaT / GLOSA       │                                                      │ (Acceso Autorizado)
   └─────────────────────────────────────┘                                                      ▼
                                                                             ┌─────────────────────────────────────┐
                                                                             │   CENTRO DE MANDO SCADA C5 (/admin) │
                                                                             ├─────────────────────────────────────┤
                                                                             │ [1] Streaming MJPEG con Bounding Box│
                                                                             │ [2] Botón de Corredor de Emergencia │
                                                                             │ [3] Calibrador Visual ROI Canvas    │
                                                                             │ [4] Módulo Forense de Infracciones  │
                                                                             │ [5] Diagnóstico de Hardware Edge    │
                                                                             │ [6] Conmutador de Modelos y Cámaras │
                                                                             │ [7] Generador de Auditoría en PDF   │
                                                                             └─────────────────────────────────────┘
```

---

### 7.1. Portal Ciudadano de Movilidad Abierta (`http://<IP>:5000/`)
Interfaz pública de libre acceso diseñada para promover la transparencia vial y la movilidad inteligente:
* **Semáforo Visual Sincronizado:** Réplica gráfica interactiva que cambia de color (Verde, Ámbar, Rojo) en tiempo real en perfecta sincronía con el gabinete físico de la calle.
* **Temporizador Regresivo:** Muestra los segundos restantes de la fase activa calculados dinámicamente por la FSM según la demanda vehicular.
* **Aforo Carril por Carril:** Contadores de vehículos en aproximación (Norte-Sur, Este-Oeste, vueltas a la izquierda y peatones).
* **Métricas de Impacto Ambiental:** Indicadores en vivo de litros de combustible ahorrados y kilogramos de $\text{CO}_2$ mitigados acumulados en el día.
* **Asesor de Velocidad Óptima V2X (GLOSA):** Recomendación de velocidad de avance para cruzar en verde sin detenerse.

---

### 7.2. Centro de Mando SCADA C5 para Operadores (`http://<IP>:5000/admin`)
Panel de control operativo e industrial protegido mediante autenticación criptográfica PBKDF2-SHA256 (`/login`), que centraliza el monitoreo y control en tiempo real:

1. **Streaming de Video en Vivo con Detecciones IA:** Transmisión continua multipart MJPEG (`/video_feed`) en alta definición con superposición de bounding boxes, clases detectadas (auto, bus, camión, moto, peatón), identificadores únicos de BYTETracker y líneas de aforo.
2. **Mando de Corredor de Emergencia C5:** Botón prioritario para ambulancias, bomberos y patrullas. Al presionarlo, el sistema interrumpe el ciclo regular, ejecuta el protocolo normativo de despeje de seguridad (Ámbar $3\,\text{s}$ + Todo-Rojo $2\,\text{s}$) y otorga verde inmediato al eje de emergencia.
3. **Calibrador Visual de Regiones de Interés (ROI Canvas Studio):** Herramienta gráfica integrada en el navegador que permite arrastrar y redimensionar los polígonos de detección sobre el fotograma en vivo, guardando la calibración en caliente (`POST /api/config/full`) sin detener el servicio ni reiniciar el hardware.
4. **Módulo Forense de Infracciones en Luz Roja:** Pestaña con galería de capturas fotográficas en alta resolución de vehículos infractores, registrando fecha/hora exacta, carril, ID vehicular y enlace de visualización o descarga para auditoría legal.
5. **HUD de Diagnóstico de Hardware en Vivo:** Telemetría en tiempo real del uso de CPU (8 núcleos), temperatura del SoC en grados Celsius ($^\circ\text{C}$), uso de memoria RAM, espacio en disco y estado de los 3 núcleos de la NPU Rockchip RK3588.
6. **Conmutación en Caliente de Cámaras y Modelos:** Selectores interactivos para alternar al instante entre cámaras físicas (USB, MIPI CSI, RTSP) y videos demo, así como cambiar entre variantes de modelos YOLOv8 en memoria.
7. **Generador Oficial de Dictámenes e Informes PDF:** Botón de exportación inmediata del informe formal de auditoría vial (`/report/executive`) listo para imprimir o archivar con sello de certificación criptográfico.

---

### 7.3. Catálogo de Endpoints REST API

| Endpoint / Vista | Ruta | Nivel de Acceso | Método | Descripción |
| :--- | :--- | :--- | :---: | :--- |
| **Portal Ciudadano** | `/` | Público | `GET` | Visualización pública de tráfico, semáforo en vivo y métricas V2X/GLOSA. |
| **Portal de Login C5** | `/login` | Público | `GET, POST` | Autenticación criptográfica de operadores con protección contra fuerza bruta. |
| **Centro de Mando SCADA** | `/admin` | Operador C5 | `GET` | Consola central de monitoreo, control de emergencias y configuración. |
| **Calibrador ROI Canvas** | `/admin` (Modal) | Operador C5 | `POST` | Editor visual de polígonos de carril con actualización en caliente. |
| **Dictamen Oficial PDF** | `/report/executive` | Operador C5 | `GET` | Informe de auditoría vial y aforo listo para exportar a PDF (`Ctrl + P`). |
| **Streaming MJPEG** | `/video_feed` | Público | `GET` | Transmisión de video continua con cajas delimitadoras de IA y HUD. |
| **Snapshot de Fotograma** | `/api/frame/snapshot` | Público | `GET` | Captura JPEG congelada para el calibrador visual en navegador. |
| **Telemetría Global** | `/api/status` | Público | `GET` | Métricas de aforo, FPS, estado FSM, latencias y telemetría de hardware. |
| **Mando de Emergencias** | `/api/control` | Operador C5 | `POST` | Despacho de corredor verde prioritario para unidades de emergencia C5. |
| **Configuración Maestra** | `/api/config/full` | Operador C5 | `GET, POST` | Consulta y guardado en caliente de parámetros y geometrías de carril. |
| **Consulta Infracciones** | `/api/violations` | Operador C5 | `GET` | Listado de infracciones en luz roja con enlaces a fotografías de evidencia. |
| **Foto de Infracción** | `/api/violations/snapshot/<f>` | Operador C5 | `GET` | Visualización o descarga de fotografía forense de infracción en luz roja. |
| **Broadcast V2X SPaT** | `/api/v2x/spat` | Público | `GET` | Telemetría SPaT (*Signal Phase and Timing*) para vehículos conectados. |
| **KPIs de Sustentabilidad**| `/api/kpis/sustainability` | Público | `GET` | Litros de combustible ahorrados y $\text{CO}_2$ mitigado en tiempo real. |

---

## 8. Estructura del Repositorio

```text
yolov8_semaforo_advanced/
├── config.example.json       # Plantilla maestra de configuración (sanitizada)
├── main.py                   # Punto de entrada universal por CLI
├── requirements.txt          # Dependencias de Python
├── yolov8n.pt                # Pesos neuronales YOLOv8 Nano para CPU
├── models/                   # Modelos cuantizados (.rknn) para Orange Pi 5 NPU
├── docs/
│   ├── MANUAL_TECNICO.md     # Manual técnico detallado para ingeniería y desarrollo
│   ├── PLAN_ENTRENAMIENTO.md # Guía de entrenamiento, fine-tuning y cuantización RKNN
│   └── arquitectura.mmd      # Diagrama de arquitectura del sistema en Mermaid
├── logs/
│   └── violations/           # Fotografías de evidencia de infracciones en luz roja
├── videos/
│   └── demo.mp4              # Clip de video estándar para demostración y pruebas
├── src/                      # Módulos del núcleo del sistema
│   ├── cli.py                # Analizador CLI y presentación de consola
│   ├── core_semaforo.py      # Clase base de control semafórico, FSM, ROIs, TSP y fotomultas
│   ├── core_semaforo_rknn.py # Controlador para aceleración NPU RKNN con fallback a CPU
│   ├── db_manager.py         # Gestor asíncrono MariaDB con búfer local tolerante a fallos
│   ├── hardware_monitor.py   # Telemetría de hardware (CPU, temperatura, RAM, disco)
│   ├── api_server.py         # Servidor Web Flask, APIs REST, autenticación y streaming
│   ├── videostream.py        # Ingestión de video en hilo secundario con reconexión
│   ├── ui4_way_cpu.py / ui4_way.py
│   ├── ui2_way_cpu.py / ui2_way.py
│   ├── ui3_tee_cpu.py / ui3_tee.py
│   ├── ui4_protected_cpu.py / ui4_protected.py
│   └── ui_pedestrian_cpu.py / ui_pedestrian.py
├── systemd/
│   ├── fluxa.service         # Unidad de servicio systemd
│   └── install_service.sh    # Script de despliegue de servicio
└── templates/                # Plantillas Web (HTML5 / Vanilla CSS / JS)
    ├── index.html            # Consola SCADA C5 y Calibrador Visual Canvas
    ├── public.html           # Portal Ciudadano de Movilidad
    ├── login.html            # Portal de Autenticación C5
    └── report_executive.html # Reporte Oficial de Auditoría Vial en PDF
```

---

## 9. Propiedad Intelectual y Licenciamiento Comercial

Este software constituye una obra propietaria protegida por las leyes de Propiedad Intelectual aplicables (Ley Federal del Derecho de Autor / INDAUTOR y tratados internacionales de la OMPI).

**Todos los derechos morales y patrimoniales reservados © 2026.**  
Queda prohibida su reproducción, distribución, venta, ingeniería inversa o uso en licitaciones públicas sin la formalización de un contrato de licencia comercial.

* **Desarrollador Principal y Titular:** Moisés Emilio Martínez Arias
* **Institución de Respaldo Académico:** Tecnológico de Estudios Superiores de Coacalco (TESCo) • Tecnológico Nacional de México (TecNM)
* **División:** Ingeniería en Sistemas Computacionales
* **Modelo de Implementación:** Consultar [Modelo de Negocio B2G y Viabilidad Financiera](docs/MODELO_NEGOCIO_B2G.md) para detalles sobre adquisición de kits *Edge Appliance*, licenciamiento por intersección y convenios de vinculación tecnológica.
* **Licencia Completa:** Consultar el archivo [LICENSE.md](LICENSE.md).
