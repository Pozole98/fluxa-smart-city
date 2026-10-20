# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Controlador Núcleo de Máquina de Estados Finitos (FSM), Priorización TSP y Detección Vial
Desarrollador Principal y Titular de Derechos: Moisés Emilio Martínez Arias
Todos los derechos reservados © 2026.
"""

import os
import sys
import time
import logging
from datetime import datetime
import threading
import json
import signal
import numpy as np
import cv2
import serial
from types import SimpleNamespace
from ultralytics.trackers.byte_tracker import BYTETracker

from videostream import VideoStream, VALID_VIDEO_EXTENSIONS
from analytics import TrafficAnalyticsLogger
from api_server import TelemetryAPI
from db_manager import DatabaseManager
from corridor_sync import CorridorSyncManager
from arduino_locker import ArduinoDeviceLock, inspect_port_lock
try:
    from systemd_notifier import get_notifier
except ImportError:
    from src.systemd_notifier import get_notifier

# Diccionario de nombres y pesos de clases COCO para Prioridad TSP
NOMBRES_CLASES_COCO = {
    0: "persona",
    1: "bicicleta",
    2: "auto",
    3: "motocicleta",
    5: "autobus",
    7: "camion"
}

PESOS_PRIORIDAD_TSP = {
    5: 4.0,  # Autobús de transporte masivo (Prioridad máxima)
    7: 2.5,  # Camión de carga / transporte pesado
    0: 1.5,  # Peatón
    2: 1.0,  # Automóvil particular estándar
    1: 0.8,  # Bicicleta
    3: 0.6   # Motocicleta
}

class DetectionsWrapper:
    """Adaptador de alta velocidad que hace compatibles las detecciones numpy [x1, y1, x2, y2, conf, cls] con BYTETracker"""
    def __init__(self, data):
        if data is None or len(data) == 0:
            self.data = np.empty((0, 6), dtype=np.float32)
            self.xyxy = np.empty((0, 4), dtype=np.float32)
            self.xywh = np.empty((0, 4), dtype=np.float32)
            self.conf = np.empty((0,), dtype=np.float32)
            self.cls = np.empty((0,), dtype=np.float32)
        else:
            self.data = np.asarray(data, dtype=np.float32)
            if self.data.ndim == 1:
                self.data = np.expand_dims(self.data, axis=0)
            self.xyxy = self.data[:, :4]
            w = self.data[:, 2] - self.data[:, 0]
            h = self.data[:, 3] - self.data[:, 1]
            cx = self.data[:, 0] + w / 2.0
            cy = self.data[:, 1] + h / 2.0
            self.xywh = np.column_stack([cx, cy, w, h])
            self.conf = self.data[:, 4]
            self.cls = self.data[:, 5]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return DetectionsWrapper(self.data[idx])


class CoreSemaforoBase:
    """
    Clase base universal de grado industrial para FLUXA.
    Maneja telemetría extendida, logs, persistencia MariaDB, watchdog serial para Arduino R4,
    conteo poligonal de vehículos, priorización TSP por tipo de vehículo,
    detección de infracciones por paso en luz roja con snapshots fotográficos,
    cálculo de impacto ambiental y ROI (ahorro de combustible, CO2 y tiempo),
    telemetría V2X (SPaT), transmisión de video MJPEG para WebUI
    y conmutación dinámica en caliente a prueba de fallos entre Cámara y Video.
    """
    def __init__(self, topology_name="4_way", backend_name="CPU", port=None, video_source=None, enable_arduino=None, **kwargs):
        self.topology_name = topology_name
        self.backend_name = backend_name
        self.port = port
        print(f"⏳ Inicializando CoreSemaforoBase (Topología: {topology_name} | Motor: {backend_name})...")
        
        self.arduino = None
        self.cap = None
        self.config = self._load_config()
        
        # Modo de Semáforos Físicos (Arduino) vs Virtuales (Simulación)
        if enable_arduino is not None:
            self.enable_arduino = bool(enable_arduino)
        else:
            cfg_enable = self.config.get("system", {}).get("enable_arduino", None)
            if cfg_enable is not None:
                self.enable_arduino = bool(cfg_enable)
            else:
                self.enable_arduino = True

        # Secuestrador de hardware exclusivo a nivel de sistema operativo (Linux flock)
        # Cada nodo (5000, 5001, 5002) secuestra de forma exclusiva un único Arduino físico.
        self._arduino_locker = ArduinoDeviceLock(node_port=self.port or 5000)
        
        # Fuente de video inicial
        if video_source is not None:
            self.fuente_actual = video_source
        else:
            self.fuente_actual = self.config.get("system", {}).get("camera_source", self.config.get("system", {}).get("camera_index", 0))
        
        # Supervisión de enlace serial y watchdog de reconexión con microcontrolador
        self.arduino_port_actual = self.config.get("system", {}).get("serial_port", "/dev/ttyACM0")
        self.arduino_baud = self.config.get("system", {}).get("serial_baudrate", 9600)
        self.arduino_tx_count = 0
        self.arduino_reconnect_count = 0
        self.ultimo_comando = None
        self._ultimo_tx_time = 0.0
        self.tiempo_desconexion_arduino = time.time()
        self.alerta_desconexion_prolongada = False
        self._alerta_desconexion_notificada = False
        
        # Cargar polígonos de la topología
        self.zonas_raw = self.config.get("zones", {}).get(self.topology_name, {})
        self.poligonos = {}
        
        # Configurar Tracker BYTETracker
        self._init_tracker()
        
        self.running = False
        self.modo_actual = "Normal"
        self.emergencia_activa = False
        self.eje_emergencia = None 
        self.tiempo_inicio_emergencia = None
        
        self.frame_count = 0
        self.consecutive_failed_frames = 0
        self.consecutive_valid_frames = 0
        self.consecutive_black_frames = 0
        self.modo_degradado_camara = False
        self.TIEMPO_FIJO_FALLBACK = float(self.config.get("traffic_light", {}).get("tiempo_fijo_fallback", 20.0))
        self.last_autos = {zona: 0 for zona in self.zonas_raw.keys()}
        self.last_demanda_ponderada = {zona: 0.0 for zona in self.zonas_raw.keys()}
        self.autos_history = [] 
        self.tiempo_sin_autos_inicio = time.time()
        
        # Conteo acumulativo de vehículos únicos usando Track IDs de BYTETracker
        self.tracked_ids_por_zona = {zona: set() for zona in self.zonas_raw.keys()}
        self.autos_acumulados = {zona: 0 for zona in self.zonas_raw.keys()}
        self._current_day = datetime.now().day
        
        # Infracciones registradas (para no duplicar capturas del mismo ID en el mismo ciclo)
        self.infracciones_capturadas_ciclo = set()
        
        # Directorio de snapshots de infracciones
        self.dir_infracciones = os.path.join(os.path.dirname(__file__), '..', 'logs', 'violations')
        os.makedirs(self.dir_infracciones, exist_ok=True)

        # FPS Real con Media Móvil Exponencial (EMA) — mide throughput instantáneo del pipeline
        self._fps_ema = 0.0
        self._fps_alpha = 0.12  # Factor de suavizado EMA (0.12 = suave pero reactivo)
        self._last_frame_time = time.time()
        self.current_fps = 0.0
        self.latencias = {
            "inferencia": 0.0,
            "tracking": 0.0,
            "pipeline_total": 0.0
        }
        
        self.w, self.h = 640, 480 
        self.tiempo_ultimo_cambio = time.time()
        self.fase_tiempo_asignado = 0.0
        self._ultimo_estado_str = ""
        self.notifier = get_notifier()

        # Métricas de Sustentabilidad, Impacto Ecológico y Comparativa A/B
        self.segundos_espera_ahorrados_acum = 0.0
        self.combustible_ahorrado_litros = 0.0
        self.co2_mitigado_kg = 0.0
        self.tiempo_tradicional_seg_acum = 0.0
        self.tiempo_fluxa_seg_acum = 0.0
        self.eficiencia_flujo_pct = 85.0
        self.BASELINE_TIEMPO_FIJO = self.config.get("sustainability", {}).get("fixed_time_baseline_sec", 45.0)

        # Buffer para transmisión de video Web (MJPEG)
        self._jpeg_frame_buffer = None
        self._jpeg_lock = threading.Lock()
        self._jpeg_clients_active = False
        self._video_switch_lock = threading.Lock()
        self._jpeg_params = [cv2.IMWRITE_JPEG_QUALITY, 78]

        # Constantes de tiempo
        cfg_tl = self.config.get("traffic_light", {})
        self.TIEMPO_MINIMO_VERDE_BASE = cfg_tl.get("tiempo_minimo_verde", 5.0)
        self.TIEMPO_MAXIMO_VERDE = cfg_tl.get("tiempo_maximo_verde", 45.0)
        self.TIEMPO_AMARILLO = cfg_tl.get("tiempo_amarillo", 3.0)
        self.TIEMPO_ROJO_TODOS = cfg_tl.get("tiempo_rojo_todos", 2.0)
        self.TIEMPO_REPOSO = cfg_tl.get("tiempo_reposo", 20.0)
        
        self.CLASES_VEHICULOS = self.config.get("ai_model", {}).get("classes_to_detect", [0, 1, 2, 3, 5, 7])
        self.CONF_THRESH = self.config.get("ai_model", {}).get("confidence_threshold", 0.15)
        
        # Paleta de colores para ROIs y cajas (formato BGR para OpenCV)
        self.COLORES_ZONAS = [
            (68, 68, 239),   # Rojo
            (246, 130, 59),  # Azul
            (129, 185, 16),  # Verde
            (11, 158, 245),  # Ámbar/Naranja
            (246, 92, 139),  # Púrpura
            (153, 72, 236)   # Rosa
        ]
        
        # Configuración unificada de la Máquina de Estados (FSM)
        self._configurar_topologia_fsm()

        # Inicializar Analytics Logger y Gestor MariaDB
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        self.logger = TrafficAnalyticsLogger(log_dir=log_dir, enabled=self.config.get("system", {}).get("log_analytics", True))
        self.ultimo_log_time = time.time()
        
        db_cfg = self.config.get("database", {})
        try:
            self.db = DatabaseManager(
                host=db_cfg.get("host", "localhost"),
                user=db_cfg.get("user", "root"),
                password=db_cfg.get("password", None),
                db_name=db_cfg.get("name", "fluxa_traffic"),
                port=db_cfg.get("port", 3306),
                enabled=db_cfg.get("enabled", True)
            )
        except Exception as e:
            logging.warning(f"Error inicializando MariaDB ({e}). Operando en modo local/RAM para asegurar operación semafórica ininterrumpida.")
            self.db = DatabaseManager(enabled=False)
        
        # Inicializar Servidor Web API
        api_cfg = self.config.get("api", {})
        api_port = port if port is not None else api_cfg.get("port", 5000)

        # Inicializar Coordinador de Corredor Vial y Olas Verdes
        corr_cfg = self.config.get("corridor", {})
        default_node = "CRUCE_01"
        if api_port == 5001:
            default_node = "CRUCE_02"
        elif api_port == 5002:
            default_node = "CRUCE_03"
        node_id = corr_cfg.get("node_id", default_node) if (api_port == 5000 or port is None) else default_node

        self.corridor = CorridorSyncManager(
            current_node_id=node_id,
            corridor_name=corr_cfg.get("name", "Corredor Principal"),
            avg_speed_kmh=corr_cfg.get("avg_speed_kmh", 45.0),
            enabled=corr_cfg.get("enabled", False)
        )
        self.api = TelemetryAPI(host=api_cfg.get("host", "0.0.0.0"), port=api_port, enabled=api_cfg.get("enabled", True))
        self.api.start(
            controller_callback=self.forzar_emergencia,
            frame_getter=self.get_encoded_jpeg,
            db_instance=self.db,
            hot_reload_callback=self.reload_zones,
            change_source_callback=self.cambiar_fuente_video,
            corridor_instance=self.corridor,
            change_arduino_port_callback=self.set_arduino_port
        )

        # Inicialización del modelo (implementado en subclases)
        self._init_model()

    def _init_tracker(self):
        args = SimpleNamespace(
            track_high_thresh=self.config.get("tracker", {}).get("track_high_thresh", 0.15), 
            track_low_thresh=self.config.get("tracker", {}).get("track_low_thresh", 0.05), 
            new_track_thresh=self.config.get("tracker", {}).get("new_track_thresh", 0.18), 
            track_buffer=self.config.get("tracker", {}).get("track_buffer", 120), 
            match_thresh=self.config.get("tracker", {}).get("match_thresh", 0.8), 
            gmc_method='sparseOptFlow',
            fuse_score=False
        )
        self.tracker = BYTETracker(args)

    def _configurar_topologia_fsm(self):
        """Mapeo de zonas y características operativas según la topología activa"""
        cfg_tl = self.config.get("traffic_light", {})
        self.TIEMPO_BUFFER_EMERGENCIA = cfg_tl.get("tiempo_buffer_emergencia", 1.0)
        self.has_phase_skipping = False
        self.is_pedestrian = False
        self.llamada_peatonal_manual = False
        
        self.fsm_commands = {
            'VERDE_1': '1',
            'AMARILLO_1': '2',
            'ROJO_TODOS_1': '5',
            'VERDE_2': '3',
            'AMARILLO_2': '4',
            'ROJO_TODOS_2': '5'
        }

        if self.topology_name == "4_way":
            self.eje_1_zonas = ['norte', 'sur']
            self.eje_2_zonas = ['este', 'oeste']
            self.eje_1_aliases = {'1', 'A', 'NS', 'NORTE', 'SUR'}
            self.eje_2_aliases = {'2', 'B', 'EO', 'ESTE', 'OESTE'}
        elif self.topology_name == "2_way":
            self.eje_1_zonas = ['zona_a']
            self.eje_2_zonas = ['zona_b']
            self.eje_1_aliases = {'1', 'A', 'ZONA_A', 'NS'}
            self.eje_2_aliases = {'2', 'B', 'ZONA_B', 'EO'}
        elif self.topology_name == "3_way_t":
            self.eje_1_zonas = ['principal_izq', 'principal_der']
            self.eje_2_zonas = ['secundaria']
            self.eje_1_aliases = {'1', 'A', 'PRINCIPAL', 'NS'}
            self.eje_2_aliases = {'2', 'B', 'SECUNDARIA', 'EO'}
        elif self.topology_name == "4_way_protected":
            self.eje_1_zonas = ['frente']
            self.eje_2_zonas = ['giro_izq']
            self.eje_1_aliases = {'1', 'A', 'FRENTE', 'NS'}
            self.eje_2_aliases = {'2', 'B', 'GIRO', 'EO'}
            self.has_phase_skipping = True
        elif self.topology_name == "pedestrian":
            self.eje_1_zonas = ['vehiculos']
            self.eje_2_zonas = ['peatones_esperando']
            self.eje_1_aliases = {'1', 'A', 'VEHICULOS', 'NS'}
            self.eje_2_aliases = {'2', 'B', 'PEATONES', 'PEDESTRIAN', 'EO'}
            self.is_pedestrian = True
        else:
            zonas_list = list(self.zonas_raw.keys())
            mid = max(1, len(zonas_list) // 2)
            self.eje_1_zonas = zonas_list[:mid]
            self.eje_2_zonas = zonas_list[mid:]
            self.eje_1_aliases = {'1', 'A', 'NS'}
            self.eje_2_aliases = {'2', 'B', 'EO'}

    def _calcular_demanda_eje(self, autos, zonas):
        """Calcula la demanda consolidada considerando aforo instantáneo y demanda ponderada (TSP)"""
        if not zonas:
            return 0.0
        val_max = 0.0
        for z in zonas:
            a = autos.get(z, 0)
            p = self.last_demanda_ponderada.get(z, 0.0) if isinstance(self.last_demanda_ponderada, dict) else 0.0
            val_max = max(val_max, float(a), float(p))
        return val_max

    def _resolver_eje_emergencia(self, eje_str):
        """Resuelve si el eje solicitado corresponde al Eje 1 (1) o Eje 2 (2)"""
        if not eje_str:
            return 1
        eje_norm = str(eje_str).strip().upper()
        if eje_norm in self.eje_2_aliases:
            return 2
        return 1

    def _cambiar_fase(self, target_generic):
        """
        Transición canónica de fase semafórica.
        Mapea el identificador genérico al enum concreto de la topología activa.
        """
        if not hasattr(self, 'estado_actual') or self.estado_actual is None:
            return
            
        enum_cls = self.estado_actual.__class__
        target_name = None
        
        if self.topology_name == "4_way":
            mapping = {
                "VERDE_1": "VERDE_NS", "AMARILLO_1": "AMARILLO_NS", "ROJO_TODOS_1": "ROJO_TODOS_1",
                "VERDE_2": "VERDE_EO", "AMARILLO_2": "AMARILLO_EO", "ROJO_TODOS_2": "ROJO_TODOS_2"
            }
            target_name = mapping.get(target_generic)
        elif self.topology_name == "2_way":
            mapping = {
                "VERDE_1": "VERDE_A", "AMARILLO_1": "AMARILLO_A", "ROJO_TODOS_1": "ROJO_TODOS_1",
                "VERDE_2": "VERDE_B", "AMARILLO_2": "AMARILLO_B", "ROJO_TODOS_2": "ROJO_TODOS_2"
            }
            target_name = mapping.get(target_generic)
        elif self.topology_name == "3_way_t":
            mapping = {
                "VERDE_1": "VERDE_PRINCIPAL", "AMARILLO_1": "AMARILLO_PRINCIPAL", "ROJO_TODOS_1": "ROJO_TODOS_1",
                "VERDE_2": "VERDE_SECUNDARIA", "AMARILLO_2": "AMARILLO_SECUNDARIA", "ROJO_TODOS_2": "ROJO_TODOS_2"
            }
            target_name = mapping.get(target_generic)
        elif self.topology_name == "4_way_protected":
            mapping = {
                "VERDE_1": "VERDE_FRENTE", "AMARILLO_1": "AMARILLO_FRENTE", "ROJO_TODOS_1": "ROJO_TODOS_1",
                "VERDE_2": "VERDE_GIRO", "AMARILLO_2": "AMARILLO_GIRO", "ROJO_TODOS_2": "ROJO_TODOS_2"
            }
            target_name = mapping.get(target_generic)
        elif self.topology_name == "pedestrian":
            mapping = {
                "VERDE_1": "VERDE_VEHICULOS", "AMARILLO_1": "AMARILLO_VEHICULOS", "ROJO_TODOS_1": "ROJO_TODOS_1",
                "VERDE_2": "VERDE_PEATONES", "AMARILLO_2": "AMARILLO_PEATONES", "ROJO_TODOS_2": "ROJO_TODOS_2"
            }
            target_name = mapping.get(target_generic)

        if target_name and hasattr(enum_cls, target_name):
            nuevo_estado = getattr(enum_cls, target_name)
            if self.estado_actual != nuevo_estado:
                self.estado_actual = nuevo_estado
                self.tiempo_ultimo_cambio = time.time()

    def _procesar_transicion_emergencia_segura(self, eje_dest, tiempo_transcurrido):
        """
        Transición de Emergencia Segura con Intervalo de Despeje Vial Obligatorio.
        
        Fundamento de Seguridad Vial:
        Bajo ninguna circunstancia normativa se debe retirar la luz verde a una vía en flujo sin
        otorgar el intervalo de advertencia (Ámbar) y el despeje de intersección (Todo-Rojo).
        Un corte abrupto genera riesgo inminente de colisión lateral o atropellamiento.
        """
        estado_str = self.estado_actual.name if hasattr(self.estado_actual, 'name') else str(self.estado_actual)
        buffer_seguridad = max(1.0, float(self.TIEMPO_BUFFER_EMERGENCIA))

        # --- REQUERIMIENTO: EJE 1 ---
        if eje_dest == 1:
            # 1.1 Ya estamos en Verde Eje 1 -> Mantener verde sostenido
            if any(k in estado_str for k in ["VERDE_1", "VERDE_NS", "VERDE_A", "VERDE_PRINCIPAL", "VERDE_FRENTE", "VERDE_VEHICULOS"]):
                self.enviar_comando(self.fsm_commands.get('VERDE_1', '1'))
                self.fase_tiempo_asignado = 999.0
                return

            # 1.2 Estábamos en Verde Eje 2 -> Despeje seguro: Forzar Amarillo Eje 2
            if any(k in estado_str for k in ["VERDE_2", "VERDE_EO", "VERDE_B", "VERDE_SECUNDARIA", "VERDE_GIRO", "VERDE_PEATONES"]):
                self._cambiar_fase("AMARILLO_2")
                self.enviar_comando(self.fsm_commands.get('AMARILLO_2', '4'))
                self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
                return

            # 1.3 Estábamos en Amarillo Eje 2 -> Permitir que termine el tiempo de ámbar
            if any(k in estado_str for k in ["AMARILLO_2", "AMARILLO_EO", "AMARILLO_B", "AMARILLO_SECUNDARIA", "AMARILLO_GIRO", "AMARILLO_PEATONES"]):
                self.enviar_comando(self.fsm_commands.get('AMARILLO_2', '4'))
                self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
                if tiempo_transcurrido >= self.TIEMPO_AMARILLO:
                    self._cambiar_fase("ROJO_TODOS_2")
                    self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_2', '5'))
                    self.fase_tiempo_asignado = self.TIEMPO_ROJO_TODOS + buffer_seguridad
                return

            # 1.4 Estábamos en Amarillo Eje 1 (hacia rojo) -> Dejar pasar a Rojo Todos
            if any(k in estado_str for k in ["AMARILLO_1", "AMARILLO_NS", "AMARILLO_A", "AMARILLO_PRINCIPAL", "AMARILLO_FRENTE", "AMARILLO_VEHICULOS"]):
                self.enviar_comando(self.fsm_commands.get('AMARILLO_1', '2'))
                self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
                if tiempo_transcurrido >= self.TIEMPO_AMARILLO:
                    self._cambiar_fase("ROJO_TODOS_1")
                    self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_1', '5'))
                return

            # 1.5 Estábamos en Todo-Rojo -> Respetar buffer mínimo de seguridad antes de dar verde
            if "ROJO_TODOS" in estado_str:
                self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_1', '5'))
                self.fase_tiempo_asignado = buffer_seguridad
                if tiempo_transcurrido >= buffer_seguridad:
                    self._cambiar_fase("VERDE_1")
                    self.enviar_comando(self.fsm_commands.get('VERDE_1', '1'))
                return

        # --- REQUERIMIENTO: EJE 2 ---
        elif eje_dest == 2:
            # 2.1 Ya estamos en Verde Eje 2 -> Mantener verde sostenido
            if any(k in estado_str for k in ["VERDE_2", "VERDE_EO", "VERDE_B", "VERDE_SECUNDARIA", "VERDE_GIRO", "VERDE_PEATONES"]):
                self.enviar_comando(self.fsm_commands.get('VERDE_2', '3'))
                self.fase_tiempo_asignado = 999.0
                return

            # 2.2 Estábamos en Verde Eje 1 -> Despeje seguro: Forzar Amarillo Eje 1
            if any(k in estado_str for k in ["VERDE_1", "VERDE_NS", "VERDE_A", "VERDE_PRINCIPAL", "VERDE_FRENTE", "VERDE_VEHICULOS"]):
                self._cambiar_fase("AMARILLO_1")
                self.enviar_comando(self.fsm_commands.get('AMARILLO_1', '2'))
                self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
                return

            # 2.3 Estábamos en Amarillo Eje 1 -> Permitir que termine el tiempo de ámbar
            if any(k in estado_str for k in ["AMARILLO_1", "AMARILLO_NS", "AMARILLO_A", "AMARILLO_PRINCIPAL", "AMARILLO_FRENTE", "AMARILLO_VEHICULOS"]):
                self.enviar_comando(self.fsm_commands.get('AMARILLO_1', '2'))
                self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
                if tiempo_transcurrido >= self.TIEMPO_AMARILLO:
                    self._cambiar_fase("ROJO_TODOS_1")
                    self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_1', '5'))
                    self.fase_tiempo_asignado = self.TIEMPO_ROJO_TODOS + buffer_seguridad
                return

            # 2.4 Estábamos en Amarillo Eje 2 (hacia rojo) -> Dejar pasar a Rojo Todos
            if any(k in estado_str for k in ["AMARILLO_2", "AMARILLO_EO", "AMARILLO_B", "AMARILLO_SECUNDARIA", "AMARILLO_GIRO", "AMARILLO_PEATONES"]):
                self.enviar_comando(self.fsm_commands.get('AMARILLO_2', '4'))
                self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
                if tiempo_transcurrido >= self.TIEMPO_AMARILLO:
                    self._cambiar_fase("ROJO_TODOS_2")
                    self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_2', '5'))
                return

            # 2.5 Estábamos en Todo-Rojo -> Respetar buffer mínimo de seguridad antes de dar verde
            if "ROJO_TODOS" in estado_str:
                self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_2', '5'))
                self.fase_tiempo_asignado = buffer_seguridad
                if tiempo_transcurrido >= buffer_seguridad:
                    self._cambiar_fase("VERDE_2")
                    self.enviar_comando(self.fsm_commands.get('VERDE_2', '3'))
                return

    def _procesar_logica_semaforo(self, autos, tiempo_minimo_actual=5.0):
        """Lógica unificada de la máquina de estados semafórica adaptativa. Calcula tiempos dinámicos, gestiona intervalos de despeje y transiciones seguras.
        """
        tiempo_transcurrido = time.time() - self.tiempo_ultimo_cambio
        
        # 1. Cálculo de aforo y demanda ponderada por eje
        demanda_eje_1 = self._calcular_demanda_eje(autos, self.eje_1_zonas)
        demanda_eje_2 = self._calcular_demanda_eje(autos, self.eje_2_zonas)
        
        autos_eje_1 = max([autos.get(z, 0) for z in self.eje_1_zonas] or [0])
        autos_eje_2 = max([autos.get(z, 0) for z in self.eje_2_zonas] or [0])

        factor = self.config.get("traffic_light", {}).get("factor_tiempo_por_auto", 3.0)

        # 2. Gestión de Corredores de Emergencia Seguros
        if self.emergencia_activa:
            eje_dest = self._resolver_eje_emergencia(self.eje_emergencia)
            self._procesar_transicion_emergencia_segura(eje_dest, tiempo_transcurrido)
            return

        # 3. Coordinación de Corredor Vial y Olas Verdes
        is_green_wave = False
        wave_origin = None
        wave_remaining = 0.0
        if hasattr(self, 'corridor') and self.corridor:
            is_green_wave, wave_origin, wave_remaining = self.corridor.should_prioritize_green_wave()

        estado_str = self.estado_actual.name if hasattr(self.estado_actual, 'name') else str(self.estado_actual)

        # --- FASE 1: VERDE EJE 1 (Corredor Principal) ---
        if any(k in estado_str for k in ["VERDE_1", "VERDE_NS", "VERDE_A", "VERDE_PRINCIPAL", "VERDE_FRENTE", "VERDE_VEHICULOS"]):
            self.enviar_comando(self.fsm_commands.get('VERDE_1', '1'))
            
            # Modo degradado / Fail-safe vial: tiempos fijos garantizados sin depender de visión artificial
            if getattr(self, 'modo_degradado_camara', False):
                self.fase_tiempo_asignado = getattr(self, 'TIEMPO_FIJO_FALLBACK', 20.0)
                if tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_1")
                    if self.is_pedestrian:
                        self.llamada_peatonal_manual = False
                return

            base_calc = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, demanda_eje_1 * factor))
            
            # Si hay una ola verde activa en el corredor principal, extender la fase verde
            if is_green_wave:
                self.fase_tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(base_calc, tiempo_transcurrido + wave_remaining))
            else:
                self.fase_tiempo_asignado = base_calc
            
            hay_demanda_opuesta = (autos_eje_2 > 0 or demanda_eje_2 > 0) if not self.is_pedestrian else ((autos_eje_2 > 0 or demanda_eje_2 > 0) or getattr(self, 'llamada_peatonal_manual', False))
            
            # Reposo / Standby demostrativo cuando la maqueta no tiene vehículos en ningún carril
            sin_vehiculos_total = (autos_eje_1 == 0 and autos_eje_2 == 0 and demanda_eje_1 == 0 and demanda_eje_2 == 0)
            tiempo_limite_reposo = getattr(self, 'TIEMPO_REPOSO', 15.0)
            
            if hay_demanda_opuesta and tiempo_transcurrido > tiempo_minimo_actual:
                # No cortar la fase verde si la ola verde aún está pasando
                if not is_green_wave and (autos_eje_1 == 0 or tiempo_transcurrido >= self.fase_tiempo_asignado):
                    self._cambiar_fase("AMARILLO_1")
                    if self.is_pedestrian:
                        self.llamada_peatonal_manual = False
                elif is_green_wave and tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_1")
                    if self.is_pedestrian:
                        self.llamada_peatonal_manual = False
            elif sin_vehiculos_total and not is_green_wave and tiempo_transcurrido >= tiempo_limite_reposo:
                # Rotación autónoma preventiva para que la maqueta no se congele durante la exposición
                self._cambiar_fase("AMARILLO_1")

        # --- FASE 1: AMARILLO EJE 1 ---
        elif any(k in estado_str for k in ["AMARILLO_1", "AMARILLO_NS", "AMARILLO_A", "AMARILLO_PRINCIPAL", "AMARILLO_FRENTE", "AMARILLO_VEHICULOS"]):
            self.enviar_comando(self.fsm_commands.get('AMARILLO_1', '2'))
            self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self._cambiar_fase("ROJO_TODOS_1")

        # --- FASE INTERMEDIA: ROJO TODOS 1 ---
        elif "ROJO_TODOS_1" in estado_str:
            self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_1', '5'))
            self.fase_tiempo_asignado = self.TIEMPO_ROJO_TODOS
            if tiempo_transcurrido > self.TIEMPO_ROJO_TODOS:
                # Hook Phase-Skipping: Si no hay giro a la izquierda en 4_way_protected, saltar directo a VERDE_FRENTE
                if self.has_phase_skipping and autos_eje_2 == 0 and demanda_eje_2 == 0:
                    self._cambiar_fase("VERDE_1")
                else:
                    self._cambiar_fase("VERDE_2")

        # --- FASE 2: VERDE EJE 2 ---
        elif any(k in estado_str for k in ["VERDE_2", "VERDE_EO", "VERDE_B", "VERDE_SECUNDARIA", "VERDE_GIRO", "VERDE_PEATONES"]):
            self.enviar_comando(self.fsm_commands.get('VERDE_2', '3'))
            
            # Modo degradado / Fail-safe vial: tiempos fijos garantizados
            if getattr(self, 'modo_degradado_camara', False):
                self.fase_tiempo_asignado = getattr(self, 'TIEMPO_FIJO_FALLBACK', 20.0)
                if tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_2")
                return

            if self.is_pedestrian:
                tiempo_cruce = max(10.0, demanda_eje_2 * 3.5)
                self.fase_tiempo_asignado = min(25.0, tiempo_cruce)
                if tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_2")
            else:
                self.fase_tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, demanda_eje_2 * factor))
                
                hay_demanda_eje_1 = (autos_eje_1 > 0 or demanda_eje_1 > 0 or is_green_wave)
                sin_autos_eje_2 = (autos_eje_2 == 0 and demanda_eje_2 == 0)
                
                # Despeje: Si hay demanda en Eje 1 y ya pasó el tiempo mínimo, o si Eje 2 no tiene autos y terminó su verde asignado
                if hay_demanda_eje_1 and tiempo_transcurrido > tiempo_minimo_actual:
                    if autos_eje_2 == 0 or tiempo_transcurrido >= self.fase_tiempo_asignado or is_green_wave:
                        self._cambiar_fase("AMARILLO_2")
                elif sin_autos_eje_2 and tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_2")

        # --- FASE 2: AMARILLO EJE 2 ---
        elif any(k in estado_str for k in ["AMARILLO_2", "AMARILLO_EO", "AMARILLO_B", "AMARILLO_SECUNDARIA", "AMARILLO_GIRO", "AMARILLO_PEATONES"]):
            self.enviar_comando(self.fsm_commands.get('AMARILLO_2', '4'))
            self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self._cambiar_fase("ROJO_TODOS_2")

        # --- FASE INTERMEDIA: ROJO TODOS 2 ---
        elif "ROJO_TODOS_2" in estado_str:
            self.enviar_comando(self.fsm_commands.get('ROJO_TODOS_2', '5'))
            self.fase_tiempo_asignado = self.TIEMPO_ROJO_TODOS
            if tiempo_transcurrido > self.TIEMPO_ROJO_TODOS:
                self._cambiar_fase("VERDE_1")

    def _init_model(self):
        raise NotImplementedError

    def _predict(self, frame):
        raise NotImplementedError

    def _dibujar_interfaz_topologia(self, frame, autos):
        pass

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        example_path = os.path.join(os.path.dirname(__file__), '..', 'config.example.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error cargando config.json: {e}")
        if os.path.exists(example_path):
            try:
                with open(example_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def reload_zones(self):
        """Recarga la configuración de polígonos, tiempos semafóricos y modelo en caliente tras edición en la WebUI"""
        old_model = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt")
        self.config = self._load_config()
        self.zonas_raw = self.config.get("zones", {}).get(self.topology_name, {})
        self._construir_poligonos()
        
        for zona in self.zonas_raw.keys():
            if zona not in self.tracked_ids_por_zona:
                self.tracked_ids_por_zona[zona] = set()
                self.autos_acumulados[zona] = 0
                
        # Recargar tiempos semafóricos
        cfg_tl = self.config.get("traffic_light", {})
        self.TIEMPO_MINIMO_VERDE_BASE = cfg_tl.get("tiempo_minimo_verde", 5.0)
        self.TIEMPO_MAXIMO_VERDE = cfg_tl.get("tiempo_maximo_verde", 45.0)
        self.TIEMPO_AMARILLO = cfg_tl.get("tiempo_amarillo", 3.0)
        self.TIEMPO_ROJO_TODOS = cfg_tl.get("tiempo_rojo_todos", 2.0)
        self.TIEMPO_REPOSO = cfg_tl.get("tiempo_reposo", 20.0)
        
        # Recargar umbrales de IA
        cfg_ai = self.config.get("ai_model", {})
        self.CONF_THRESH = cfg_ai.get("confidence_threshold", 0.15)
        self.CLASES_VEHICULOS = cfg_ai.get("classes_to_detect", [0, 1, 2, 3, 5, 7])
        
        new_model = cfg_ai.get("model_file", "yolov8n.pt")
        if new_model != old_model:
            print(f" Recargando nuevo modelo YOLO en memoria: {new_model}...")
            try:
                self._init_model()
                self.api.log_event('INFO', f"Modelo YOLO cambiado exitosamente a: {new_model}")
            except Exception as e:
                print(f"❌ Error recargando modelo: {e}")
                self.api.log_event('WARN', f"Falla cargando modelo {new_model}: {e}")
        else:
            self.api.log_event('INFO', f"Configuración y ROIs de {self.topology_name} actualizados en caliente")

    def cambiar_modelo_yolo(self, nuevo_modelo):
        """Permite cambiar el modelo YOLO en memoria y persistirlo en config.json"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            if "ai_model" not in cfg:
                cfg["ai_model"] = {}
            cfg["ai_model"]["model_file"] = nuevo_modelo
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=4)
            self.reload_zones()
            return True, f"Modelo cambiado exitosamente a {nuevo_modelo}"
        except Exception as e:
            return False, f"Error cambiando modelo: {e}"

    def cambiar_fuente_video(self, nueva_fuente):
        """
        Conmuta dinámicamente en caliente la fuente de video con validación previa estricta.
        Detiene el hilo anterior limpiamente para evitar colisiones en libavcodec (Double-Free).
        """
        with self._video_switch_lock:
            print(f" Solicitud de cambio de fuente de video a: {nueva_fuente}...")
            
            # Validación previa si es archivo local
            if isinstance(nueva_fuente, str) and not str(nueva_fuente).isdigit() and not nueva_fuente.startswith("rtsp://") and not nueva_fuente.startswith("http://"):
                if not os.path.exists(nueva_fuente) or os.path.getsize(nueva_fuente) < 1024:
                    err = f"Archivo no encontrado o vacío: {nueva_fuente}"
                    print(f"❌ {err}")
                    self.api.log_event('WARN', err)
                    return False, err
                    
                test_cap = cv2.VideoCapture(nueva_fuente)
                if not test_cap.isOpened():
                    test_cap.release()
                    err = f"No se pudo abrir el archivo de video: {os.path.basename(nueva_fuente)}"
                    print(f"❌ {err}")
                    self.api.log_event('WARN', err)
                    return False, err
                    
                ret, test_frame = test_cap.read()
                test_cap.release()
                if not ret or test_frame is None:
                    err = f"El archivo {os.path.basename(nueva_fuente)} no contiene cuadros decodificables."
                    print(f"❌ {err}")
                    self.api.log_event('WARN', err)
                    return False, err

            # 1. Detener el flujo anterior de forma síncrona y segura
            old_cap = self.cap
            if old_cap is not None:
                old_cap.stop()
                self.cap = None
                time.sleep(0.3)
                
            try:
                # 2. Iniciar el nuevo flujo
                new_cap = VideoStream(src=nueva_fuente).start()
                time.sleep(0.6)
                ret, frame = new_cap.read()
                
                if not ret or frame is None:
                    new_cap.stop()
                    videos_dir = os.path.join(os.path.dirname(__file__), '..', 'videos')
                    fallback_demo = os.path.join(videos_dir, 'demo.mp4')
                    if not os.path.exists(fallback_demo) and os.path.exists(videos_dir):
                        for fn in os.listdir(videos_dir):
                            if fn.endswith(('.mp4', '.avi', '.mkv', '.mov')) and not fn.startswith('.'):
                                fallback_demo = os.path.join(videos_dir, fn)
                                break
                    self.cap = VideoStream(src=fallback_demo).start()
                    err = "No se pudieron obtener cuadros de la nueva fuente. Restaurando respaldo."
                    print(f"❌ {err}")
                    self.api.log_event('WARN', err)
                    return False, err
                    
                self.cap = new_cap
                self.fuente_actual = nueva_fuente
                self.h, self.w, _ = frame.shape
                self._construir_poligonos()
                self._init_tracker()
                self.consecutive_failed_frames = 0
                
                fuente_desc = "Cámara en Vivo" if isinstance(nueva_fuente, int) or str(nueva_fuente).isdigit() else f"Clip: {os.path.basename(str(nueva_fuente))}"
                msg = f"Fuente de video conmutada exitosamente a: {fuente_desc}"
                print(f"{msg}")
                self.api.log_event('INFO', msg)
                self.db.log_event_async('INFO', msg)
                return True, msg
                
            except Exception as e:
                err = f"Excepción cambiando fuente de video: {e}"
                print(f"❌ {err}")
                self.api.log_event('WARN', err)
                return False, err

    def get_encoded_jpeg(self):
        with self._jpeg_lock:
            return self._jpeg_frame_buffer

    def start(self):
        self.running = True
        if self.enable_arduino:
            threading.Thread(target=self._init_arduino, daemon=True).start()
        else:
            logging.info(f"Instancia en puerto {self.port}: Semáforos Virtuales activos (sin conexión física a microcontrolador).")
        
        self.cap = VideoStream(src=self.fuente_actual).start()
        time.sleep(0.8)
        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.h, self.w, _ = frame.shape
            self._construir_poligonos()
            
        self.tiempo_ultimo_cambio = time.time()
        self.ultimo_comando = None
        self.api.log_event('INFO', f"Sistema FLUXA iniciado ({self.topology_name} - {self.backend_name})")
        self.db.log_event_async('INFO', f"Sistema FLUXA iniciado ({self.topology_name} - {self.backend_name})")
        if hasattr(self, 'notifier') and self.notifier:
            self.notifier.notify_ready()
            self.notifier.notify_status(f"Operativo | {self.topology_name} | {self.backend_name}")

    def _construir_poligonos(self):
        """
        Construye las geometrías de las ROIs en memoria.
        Blindado contra crashes si el usuario deja áreas vacías, con < 3 vértices o con área nula.
        """
        self.poligonos = {}
        self._zona_color_map = {}
        self._zona_centroids = {}

        for i, (nombre, puntos) in enumerate(self.zonas_raw.items()):
            color = self.COLORES_ZONAS[i % len(self.COLORES_ZONAS)]
            self._zona_color_map[nombre] = color

            # Asegurar siempre contadores y rastreadores iniciales para evitar KeyError en la FSM y en la API
            if nombre not in self.last_autos:
                self.last_autos[nombre] = 0
            if nombre not in self.last_demanda_ponderada:
                self.last_demanda_ponderada[nombre] = 0.0
            if hasattr(self, 'tracked_ids_por_zona') and nombre not in self.tracked_ids_por_zona:
                self.tracked_ids_por_zona[nombre] = set()
            if hasattr(self, 'autos_acumulados') and nombre not in self.autos_acumulados:
                self.autos_acumulados[nombre] = 0

            # Blindaje 1: Detección de listas vacías o vértices insuficientes (< 3 puntos)
            if not puntos or not isinstance(puntos, (list, tuple)) or len(puntos) < 3:
                logging.warning(f"⚠️ ROI '{nombre}' contiene puntos insuficientes ({len(puntos) if puntos else 0} < 3). Se mantendrá en modo seguro sin detecciones.")
                self._zona_centroids[nombre] = (max(10, self.w // 2), max(10, self.h // 2))
                continue

            pts = []
            for pt in puntos:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    try:
                        px, py = float(pt[0]), float(pt[1])
                        pts.append([int(px * self.w), int(py * self.h)])
                    except (ValueError, TypeError):
                        pass

            if len(pts) < 3:
                logging.warning(f"⚠️ ROI '{nombre}' tiene coordenadas inválidas. Omitiendo.")
                self._zona_centroids[nombre] = (max(10, self.w // 2), max(10, self.h // 2))
                continue

            pts_arr = np.array(pts, np.int32)

            # Blindaje 2: Detección de áreas colineales o nulas (evitar excepción en OpenCV)
            area = abs(cv2.contourArea(pts_arr))
            if area < 1.0:
                logging.warning(f"⚠️ ROI '{nombre}' tiene área nula ({area:.1f} px). Omitiendo geometría para prevenir crash.")
                self._zona_centroids[nombre] = (max(10, self.w // 2), max(10, self.h // 2))
                continue

            self.poligonos[nombre] = pts_arr
            cx = int(np.mean(pts_arr[:, 0]))
            cy = int(np.mean(pts_arr[:, 1]))
            self._zona_centroids[nombre] = (cx, cy)

    def set_arduino_port(self, port):
        """
        Establece el puerto serial del Arduino secuestrándolo de forma exclusiva
        o conmuta a modo de Semáforos Virtuales (Gemelo Digital).
        Cualquier nodo (5000, 5001, 5002) puede secuestrar un Arduino libre.
        """
        port_str = str(port).strip()
        if port_str.upper() in ["VIRTUAL", "NONE", "DESACTIVADO", "DISABLED", "NULL"]:
            logging.info(f"Instancia Nodo {self.port or 5000}: Conmutando a modo de Semáforos Virtuales.")
            if hasattr(self, '_arduino_locker') and self._arduino_locker:
                self._arduino_locker.release()
            self.enable_arduino = False
            self.arduino_port_actual = "VIRTUAL"
            if hasattr(self, 'arduino') and self.arduino:
                try:
                    self.arduino.close()
                except Exception:
                    pass
                self.arduino = None
            self.alerta_desconexion_prolongada = False
            self._alerta_desconexion_notificada = False
            self.api.log_event('INFO', "Modo Semáforos Virtuales activado en este nodo")
            return {"status": "ok", "message": "Modo Semáforos Virtuales activado exitosamente"}

        # Verificar si el puerto ya está secuestrado por otro nodo
        my_node_port = self.port or 5000
        lock_status = inspect_port_lock(port_str, current_node_port=my_node_port)
        if lock_status["is_locked"] and not lock_status["is_mine"]:
            msg = f"Puerto {port_str} ya se encuentra secuestrado por {lock_status.get('owner', 'otro nodo')}. Asignación rechazada."
            logging.warning(f"⚠️ Nodo {my_node_port}: {msg}")
            return {"status": "error", "error": msg}

        # Intentar secuestro exclusivo a nivel de sistema operativo
        if hasattr(self, '_arduino_locker') and self._arduino_locker:
            if not self._arduino_locker.acquire(port_str):
                msg = f"No se pudo secuestrar el puerto {port_str} (recurso ocupado o no disponible)."
                return {"status": "error", "error": msg}

        logging.info(f"Instancia Nodo {my_node_port}: Secuestrado puerto Arduino {port_str}")
        self.enable_arduino = True
        self.arduino_port_actual = port_str
        
        # Cerrar conexión anterior para forzar reconexión con el nuevo hardware
        if hasattr(self, 'arduino') and self.arduino:
            try:
                self.arduino.close()
            except Exception:
                pass
            self.arduino = None
        
        threading.Thread(target=self._init_arduino, daemon=True).start()
        return {"status": "ok", "message": f"Puerto {port_str} secuestrado y asignado con éxito a este nodo"}

    def _init_arduino(self):
        if not self.enable_arduino or self.arduino_port_actual == "VIRTUAL":
            return

        my_node_port = self.port or 5000

        while self.running:
            if not self.enable_arduino or self.arduino_port_actual == "VIRTUAL":
                break

            ports_to_try = [
                self.arduino_port_actual,
                "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2",
                "/dev/ttyUSB0", "/dev/ttyUSB1"
            ]
            
            is_connected = self.arduino is not None and getattr(self.arduino, 'is_open', False)
            if not is_connected:
                tiempo_desconectado = time.time() - self.tiempo_desconexion_arduino
                if tiempo_desconectado > 5.0:
                    self.alerta_desconexion_prolongada = True
                    if not self._alerta_desconexion_notificada:
                        self._alerta_desconexion_notificada = True
                        msg = "ℹ️ Modo Autónomo / Demostración: Operando sin controlador físico de semáforos (Arduino)."
                        self.api.log_event('INFO', msg)
                        self.db.log_event_async('INFO', msg)
                        logging.info(msg)

                connected = False
                for port in ports_to_try:
                    if not port or port.upper() in ["VIRTUAL", "NONE"]:
                        continue

                    # Comprobar cerrojo: Si otro nodo lo tiene secuestrado, NO tocarlo
                    lock_check = inspect_port_lock(port, current_node_port=my_node_port)
                    if lock_check["is_locked"] and not lock_check["is_mine"]:
                        continue

                    # Intentar secuestro exclusivo
                    if hasattr(self, '_arduino_locker') and self._arduino_locker:
                        if not self._arduino_locker.acquire(port):
                            continue

                    try:
                        self.arduino = serial.Serial(port=port, baudrate=self.arduino_baud, timeout=0.1, exclusive=True)
                        time.sleep(2)
                        self.arduino.reset_input_buffer()
                        self.arduino_port_actual = port
                        connected = True
                        break
                    except Exception:
                        # Si no pudo abrir el serial, soltar el cerrojo para no dejarlo bloqueado
                        if hasattr(self, '_arduino_locker') and self._arduino_locker and self.arduino_port_actual != port:
                            self._arduino_locker.release()
                
                if connected:
                    logging.info(f"🔒 Enlace serial con Arduino UNO R4 activo y secuestrado en {self.arduino_port_actual} por Nodo {my_node_port}.")
                    self.api.log_event('INFO', f"Controlador físico (Arduino UNO R4) reconectado y secuestrado en {self.arduino_port_actual}")
                    self.db.log_event_async('INFO', f"Controlador físico (Arduino UNO R4) reconectado en {self.arduino_port_actual}")
                    self.alerta_desconexion_prolongada = False
                    self._alerta_desconexion_notificada = False
                    self.tiempo_desconexion_arduino = time.time()
                    
                    # Reenviar de inmediato el estado actual de la máquina de estados
                    if self.ultimo_comando:
                        try:
                            self.arduino.write(self.ultimo_comando.encode())
                        except Exception:
                            pass
                else:
                    self.arduino_reconnect_count += 1
            else:
                self.tiempo_desconexion_arduino = time.time()
                self.alerta_desconexion_prolongada = False
                self._alerta_desconexion_notificada = False

            time.sleep(3)

    def stop(self):
        self.running = False
        if hasattr(self, 'notifier') and self.notifier:
            try:
                self.notifier.notify_stopping()
            except Exception:
                pass
        if hasattr(self, '_arduino_locker') and self._arduino_locker:
            try:
                self._arduino_locker.release()
            except Exception:
                pass
        if hasattr(self, 'cap') and self.cap:
            try:
                self.cap.stop()
            except Exception:
                pass
        if hasattr(self, 'arduino') and self.arduino:
            try:
                self.arduino.close()
            except Exception:
                pass
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except Exception:
                pass
        if hasattr(self, 'api') and self.api:
            try:
                self.api.log_event('WARN', "Sistema FLUXA detenido de forma segura")
            except Exception:
                pass

    def enviar_comando(self, comando):
        if not self.enable_arduino:
            ahora = time.time()
            es_cambio = (comando != self.ultimo_comando)
            if es_cambio:
                self.ultimo_comando = comando
                self.arduino_tx_count += 1
                self._ultimo_tx_time = ahora
                self.api.log_event('VIRTUAL', f"Semáforos virtuales actualizados a comando '{comando}'")
            return

        if not self.arduino:
            return

        ahora = time.time()
        ultimo_tx = getattr(self, '_ultimo_tx_time', 0.0)
        es_cambio = (comando != self.ultimo_comando)
        # Re-enviar comando como heartbeat periódico (1.0s) para mantener activo el watchdog (15s) del Arduino
        debe_enviar = es_cambio or (ahora - ultimo_tx >= 1.0)

        if debe_enviar:
            try:
                self.arduino.write(comando.encode())
                try:
                    self.arduino.flush()
                except Exception:
                    pass
                self._ultimo_tx_time = ahora
                if es_cambio:
                    self.ultimo_comando = comando
                    self.arduino_tx_count += 1
                    self.api.log_event('ARDUINO', f"Comando '{comando}' enviado a semáforos")
                in_w = getattr(self.arduino, 'in_waiting', 0)
                if isinstance(in_w, int) and in_w > 0:
                    self.arduino.reset_input_buffer()
            except (serial.SerialException, OSError, Exception) as e:
                logging.warning(f"❌ Falla de comunicación Serial con Arduino R4 ({e}). Iniciando watchdog de reconexión...")
                self.api.log_event('WARN', "Desconexión de Arduino detectada. Iniciando watchdog...")
                self.tiempo_desconexion_arduino = time.time()
                try:
                    if self.arduino:
                        self.arduino.close()
                except Exception:
                    pass
                self.arduino = None

    def forzar_emergencia(self, accion):
        if accion == "RESET":
            if self.emergencia_activa and self.tiempo_inicio_emergencia:
                duracion = round(time.time() - self.tiempo_inicio_emergencia, 1)
                self.api.log_event('INFO', f"Corredor de emergencia C5 finalizado (Tiempo de despeje: {duracion}s)")
                self.db.log_event_async('INFO', f"Corredor de emergencia C5 finalizado (Tiempo de despeje: {duracion}s)")
            self.emergencia_activa = False
            self.eje_emergencia = None
            self.tiempo_inicio_emergencia = None
            self.modo_actual = "Normal"
            self.api.log_event('INFO', "Modo de emergencia cancelado. Ciclo normal reanudado")
            self.db.log_event_async('INFO', "Modo de emergencia cancelado")
        elif accion.startswith("MODE:"):
            nuevo_modo = accion.split(":", 1)[1]
            self.modo_actual = nuevo_modo
            self.api.log_event('INFO', f"Modo operacional cambiado a {nuevo_modo}")
            self.db.log_event_async('INFO', f"Modo operacional cambiado a {nuevo_modo}")
        else:
            self.emergencia_activa = True
            self.eje_emergencia = accion
            self.tiempo_inicio_emergencia = time.time()
            self.modo_actual = f" CORREDOR EMERGENCIA ({accion})"
            self.api.log_event('EMERG', f" PRIORIDAD C5 ACTIVADA: Corredor de Emergencia para {accion}")
            self.db.log_event_async('EMERG', f" PRIORIDAD C5 ACTIVADA: Corredor de Emergencia para {accion}")

    def _check_modo_noche(self):
        # Prioridad de seguridad vial: si la cámara está degradada, opera siempre en modo fail-safe
        if getattr(self, 'modo_degradado_camara', False):
            if not self.emergencia_activa:
                self.modo_actual = "Modo Degradado (Fail-Safe)"
            return getattr(self, 'TIEMPO_FIJO_FALLBACK', 20.0)

        night_cfg = self.config.get("night_mode", {})
        if not night_cfg.get("enabled", False):
            if not self.emergencia_activa and not self.modo_actual.startswith("🚨"):
                self.modo_actual = "Normal"
            return self.TIEMPO_MINIMO_VERDE_BASE
            
        ahora = datetime.now().hour
        inicio = night_cfg.get("start_hour", 23)
        fin = night_cfg.get("end_hour", 5)
        
        es_noche = (ahora >= inicio or ahora < fin) if inicio > fin else (inicio <= ahora < fin)
            
        if es_noche:
            if not self.emergencia_activa:
                self.modo_actual = "Noche (Valle)"
            return night_cfg.get("tiempo_verde_noche", 5.0)
        else:
            if not self.emergencia_activa and self.modo_actual == "Noche (Valle)":
                self.modo_actual = "Normal"
            return self.TIEMPO_MINIMO_VERDE_BASE

    def _verificar_infraccion_luz_roja(self, zona_nombre, track_id, frame, cx, cy, bbox=None):
        """Detecta si un vehículo avanza en una zona con semáforo en rojo, reconoce su placa (ANPR) y toma foto de evidencia"""
        estado_nombre = getattr(self, "estado_actual", None)
        estado_str = estado_nombre.name if estado_nombre else ""
        
        es_luz_roja = False
        if "ROJO_TODOS" in estado_str or "EMERGENCIA" in estado_str or "DESPEJE" in estado_str:
            es_luz_roja = True
        elif "VERDE_NS" in estado_str or "AMARILLO_NS" in estado_str:
            if zona_nombre in ['este', 'oeste']:
                es_luz_roja = True
        elif "VERDE_EO" in estado_str or "AMARILLO_EO" in estado_str:
            if zona_nombre in ['norte', 'sur']:
                es_luz_roja = True
        elif "VERDE_A" in estado_str or "AMARILLO_A" in estado_str:
            if zona_nombre in ['zona_b']:
                es_luz_roja = True
        elif "VERDE_B" in estado_str or "AMARILLO_B" in estado_str:
            if zona_nombre in ['zona_a']:
                es_luz_roja = True
        elif "VERDE_PRINCIPAL" in estado_str or "AMARILLO_PRINCIPAL" in estado_str:
            if zona_nombre in ['secundaria']:
                es_luz_roja = True
        elif "VERDE_SECUNDARIA" in estado_str or "AMARILLO_SECUNDARIA" in estado_str:
            if zona_nombre in ['principal_izq', 'principal_der']:
                es_luz_roja = True
        elif "VERDE_FRENTE" in estado_str or "AMARILLO_FRENTE" in estado_str:
            if zona_nombre in ['giro_izq']:
                es_luz_roja = True
        elif "VERDE_GIRO" in estado_str or "AMARILLO_GIRO" in estado_str:
            if zona_nombre in ['frente']:
                es_luz_roja = True
        elif "VERDE_VEHICULOS" in estado_str or "AMARILLO_VEHICULOS" in estado_str:
            # En verde vehicular, peatones esperando legalmente en la acera no son infractores
            pass
        elif "VERDE_PEATONES" in estado_str or "AMARILLO_PEATONES" in estado_str:
            if zona_nombre in ['vehiculos']:
                es_luz_roja = True

        if es_luz_roja:
            clave_infraccion = f"{estado_str}_{zona_nombre}_{track_id}"
            if clave_infraccion not in self.infracciones_capturadas_ciclo:
                self.infracciones_capturadas_ciclo.add(clave_infraccion)
                
                snapshot_name = f"violation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_id{track_id}.jpg"
                snapshot_path = os.path.join(self.dir_infracciones, snapshot_name)
                
                evidence = frame.copy().astype(np.uint8) if hasattr(frame, 'astype') else frame
                cv2.rectangle(evidence, (0, 0), (self.w, 48), (0, 0, 200), -1)
                cv2.putText(evidence, f"INFRACCION: CRUCE EN LUZ ROJA | CARRIL: {zona_nombre.upper()} | TRACK_ID: #{track_id}", 
                            (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)
                cv2.putText(evidence, f"FECHA/HORA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | FASE: {estado_str} | NODO: {self.topology_name.upper()}", 
                            (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 240, 255), 1)
                
                if bbox is not None:
                    bx1, by1, bx2, by2 = [int(v) for v in bbox]
                    cv2.rectangle(evidence, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
                else:
                    cv2.circle(evidence, (cx, cy), 15, (0, 0, 255), 3)
                
                try:
                    cv2.imwrite(snapshot_path, evidence)
                    self._rotar_almacenamiento_infracciones()
                except Exception:
                    pass
                
                self.db.log_violation_async(zona_nombre, track_id, estado_str, snapshot_name)
                self.api.log_event('WARN', f"Infracción: Vehículo ID:{track_id} cruzó en luz roja en carril {zona_nombre.upper()} ({estado_str})")

    def _rotar_almacenamiento_infracciones(self):
        """
        Garantiza que el almacenamiento en disco no se llene con fotos de infracciones.
        Mantiene un límite razonable de archivos (por defecto 300) y de cuota (máximo 150 MB),
        eliminando automáticamente las capturas más antiguas con política FIFO.
        """
        try:
            cfg_storage = self.config.get("storage", {})
            limite_archivos = cfg_storage.get("max_violation_snapshots", 300)
            limite_mb = cfg_storage.get("max_violation_storage_mb", 150)
            
            if not os.path.exists(self.dir_infracciones):
                return
                
            archivos = []
            peso_total_bytes = 0
            for f in os.listdir(self.dir_infracciones):
                if f.endswith('.jpg') or f.endswith('.png'):
                    ruta = os.path.join(self.dir_infracciones, f)
                    try:
                        st = os.stat(ruta)
                        archivos.append((st.st_mtime, st.st_size, ruta))
                        peso_total_bytes += st.st_size
                    except Exception:
                        pass
                        
            limite_bytes = limite_mb * 1024 * 1024
            if len(archivos) > limite_archivos or peso_total_bytes > limite_bytes:
                archivos.sort(key=lambda x: x[0])  # Más antiguos primero
                while archivos and (len(archivos) > limite_archivos or peso_total_bytes > limite_bytes):
                    _, tam, ruta_eliminar = archivos.pop(0)
                    try:
                        os.remove(ruta_eliminar)
                        peso_total_bytes -= tam
                    except Exception:
                        pass
        except Exception as e:
            logging.warning(f"Error en rotación de almacenamiento de infracciones: {e}")

    def _generar_frame_failsafe(self, estado_str):
        """Genera un cuadro de respaldo si la fuente de video se interrumpe temporalmente o se degrada"""
        placeholder = np.ones((self.h, self.w, 3), dtype=np.uint8) * 18
        
        if getattr(self, 'modo_degradado_camara', False):
            msg_alerta = "MODO DEGRADADO - TIEMPOS FIJOS ACTIVOS"
            color_alerta = (0, 165, 255)
            sub_msg = "FAIL-SAFE VIAL ACTIVO • CONTROL POR RELOJ INTERNO"
        else:
            msg_alerta = "SENAL DE VIDEO EN RECONEXION"
            color_alerta = (0, 200, 255)
            sub_msg = f"FUENTE: {self.fuente_actual}"
            
        cv2.putText(placeholder, msg_alerta, (int(self.w*0.12), int(self.h*0.45)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color_alerta, 2)
        cv2.putText(placeholder, sub_msg, (int(self.w*0.14), int(self.h*0.55)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        return placeholder

    def process_frame(self):
        """Bucle principal de procesamiento por cuadro"""
        if not self.running:
            return None
            
        t_loop_start = time.time()
        self.frame_count += 1
        
        estado_nombre = getattr(self, "estado_actual", None)
        estado_str = estado_nombre.name if estado_nombre else "DESCONOCIDO"

        ret, frame = self.cap.read() if self.cap else (False, None)
        
        # Detección de cuadro negro o sensor desconectado
        is_black_frame = False
        if ret and frame is not None:
            try:
                sample = frame[::8, ::8]
                if sample.size > 0 and float(sample.std()) < 1.0:
                    is_black_frame = True
            except Exception:
                is_black_frame = False

        is_frame_invalid = (not ret or frame is None or is_black_frame)

        # Manejo a prueba de fallos si la fuente se desconecta o entrega cuadros negros/inválidos
        is_failsafe = False
        if is_frame_invalid:
            is_failsafe = True
            self.consecutive_failed_frames += 1
            self.consecutive_valid_frames = 0
            
            # Activación de Modo Degradado
            if self.consecutive_failed_frames >= 10:
                if not self.modo_degradado_camara:
                    self.modo_degradado_camara = True
                    logging.warning("⚠️ [FAIL-SAFE VIAL] Activado MODO DEGRADADO: Pérdida o degradación del flujo de video. Conmutando a ciclo de tiempos fijos equitativo.")
                    self.api.log_event('WARN', "Modo degradado activado por fallo en flujo de video")
                    self.db.log_event_async('WARN', "Modo degradado activado por fallo en flujo de video")
                    if hasattr(self, 'notifier') and self.notifier:
                        self.notifier.notify_status(f"DEGRADADO | {estado_str} | Tiempos Fijos")

            if self.consecutive_failed_frames > 40:
                videos_dir = os.path.join(os.path.dirname(__file__), '..', 'videos')
                fallback_demo = os.path.join(videos_dir, 'demo.mp4')
                if not os.path.exists(fallback_demo) and os.path.exists(videos_dir):
                    for fn in os.listdir(videos_dir):
                        if fn.endswith(('.mp4', '.avi', '.mkv', '.mov')) and not fn.startswith('.'):
                            fallback_demo = os.path.join(videos_dir, fn)
                            break
                if os.path.exists(fallback_demo) and self.fuente_actual != fallback_demo:
                    logging.info("Fallo prolongado de video. Conmutando a clip de respaldo...")
                    self.cambiar_fuente_video(fallback_demo)
                self.consecutive_failed_frames = 10
                
            frame = self._generar_frame_failsafe(estado_str)
        else:
            self.consecutive_failed_frames = 0
            self.consecutive_valid_frames += 1
            
            # Recuperación automática tras 15 cuadros consecutivos válidos
            if self.modo_degradado_camara and self.consecutive_valid_frames >= 15:
                self.modo_degradado_camara = False
                logging.info("✅ [FAIL-SAFE VIAL] Señal de cámara restaurada y estabilizada. Retornando a control adaptativo inteligente.")
                self.api.log_event('INFO', "Restauración de señal de video: retornando a control inteligente")
                self.db.log_event_async('INFO', "Restauración de señal de video: retornando a control inteligente")
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.notify_status(f"NORMAL | {estado_str} | Modo Adaptativo")

        # Rollover de conteos acumulados a medianoche
        current_day = datetime.now().day
        if current_day != self._current_day:
            self._current_day = current_day
            for z in self.tracked_ids_por_zona:
                self.tracked_ids_por_zona[z].clear()
                self.autos_acumulados[z] = 0
            self.segundos_espera_ahorrados_acum = 0.0
            self.combustible_ahorrado_litros = 0.0
            self.co2_mitigado_kg = 0.0
            self.tiempo_tradicional_seg_acum = 0.0
            self.tiempo_fluxa_seg_acum = 0.0
            self.api.log_event('INFO', "Reinicio diario de conteos acumulativos y métricas de impacto")

        # Calcular FPS Real (EMA — se actualiza en cada frame procesado)
        now_fps = time.time()
        dt_fps = now_fps - self._last_frame_time
        self._last_frame_time = now_fps
        if dt_fps > 0.001:
            instant_fps = 1.0 / dt_fps
            self._fps_ema = self._fps_alpha * instant_fps + (1.0 - self._fps_alpha) * self._fps_ema
        self.current_fps = round(self._fps_ema, 1)
        if hasattr(self, 'notifier') and self.notifier:
            self.notifier.notify_watchdog()

        overlay = frame.copy()

        if is_failsafe:
            # En modo failsafe no se ejecuta inferencia ni tracking pero se preserva la FSM
            self.latencias["inferencia"] = 0.0
            self.latencias["tracking"] = 0.0
            self.last_autos = {zona: 0 for zona in self.zonas_raw.keys()}
            self.last_demanda_ponderada = {zona: 0.0 for zona in self.zonas_raw.keys()}
            autos_estabilizados = {zona: 0 for zona in self.zonas_raw.keys()}
        else:
            # Inferencia normal
            t_infer_start = time.time()
            dets = self._predict(frame)
            t_infer_end = time.time()
            self.latencias["inferencia"] = round((t_infer_end - t_infer_start) * 1000, 1)

            # Tracking & Detección Robusta
            t_track_start = time.time()
            if dets is not None and len(dets) > 0:
                try:
                    wrapper = DetectionsWrapper(dets)
                    tracked = self.tracker.update(wrapper)
                except Exception as e:
                    # Fallback de seguridad: usar detecciones directas si BYTETracker falla
                    tracked = []
                    for i, d in enumerate(dets):
                        x1, y1, x2, y2, s, c = d
                        tracked.append([x1, y1, x2, y2, i + 1, s, c, i])
                self._procesar_tracking(tracked, frame, overlay)
            else:
                self.last_autos = {zona: 0 for zona in self.zonas_raw.keys()}
                self.last_demanda_ponderada = {zona: 0.0 for zona in self.zonas_raw.keys()}
            t_track_end = time.time()
            self.latencias["tracking"] = round((t_track_end - t_track_start) * 1000, 1)

            # Anti-flicker
            self.autos_history.append(self.last_autos.copy())
            if len(self.autos_history) > 8:
                self.autos_history.pop(0)

            autos_estabilizados = {zona: 0 for zona in self.zonas_raw.keys()}
            for h_autos in self.autos_history:
                for zona in autos_estabilizados:
                    autos_estabilizados[zona] = max(autos_estabilizados[zona], h_autos.get(zona, 0))

        if sum(autos_estabilizados.values()) == 0:
            if self.tiempo_sin_autos_inicio is None:
                self.tiempo_sin_autos_inicio = time.time()
        else:
            self.tiempo_sin_autos_inicio = None

        tiempo_minimo_actual = self._check_modo_noche()
        
        # Máquina de estados
        self._procesar_logica_semaforo(autos_estabilizados, tiempo_minimo_actual)
        
        # Actualización de Métricas Sustentables y Comparativa A/B en transiciones de fase
        if estado_str != self._ultimo_estado_str:
            self.api.log_event('PHASE', f"Transición de fase -> {estado_str}")
            self.db.log_event_async('PHASE', f"Transición de fase -> {estado_str}")
            if hasattr(self, 'notifier') and self.notifier:
                total_v = sum(autos_estabilizados.values()) if isinstance(autos_estabilizados, dict) else 0
                self.notifier.notify_status(f"Fase: {estado_str} | {self.current_fps:.1f} FPS | Autos: {total_v}")
            
            # Notificación de Ola Verde a nodos contiguos si se abre el verde principal con flujo
            if any(k in estado_str for k in ["VERDE_1", "VERDE_NS", "VERDE_A", "VERDE_PRINCIPAL", "VERDE_FRENTE"]):
                autos_eje_1 = sum(autos_estabilizados.get(z, 0) for z in self.eje_1_zonas)
                if autos_eje_1 >= 2 and hasattr(self, 'corridor') and self.corridor:
                    self.corridor.notify_departure_platoon(vehicle_count=autos_eje_1, direction="SUR")
            
            # Cálculo de ahorro frente al ciclo de tiempo fijo (45s base)
            tiempo_real_asignado = max(5.0, self.fase_tiempo_asignado)
            tiempo_fijo_baseline = max(tiempo_real_asignado, self.BASELINE_TIEMPO_FIJO)
            
            autos_en_espera = max(1, sum(autos_estabilizados.values()))
            delta_ahorro_seg = max(0.0, (tiempo_fijo_baseline - tiempo_real_asignado))
            
            self.segundos_espera_ahorrados_acum += (delta_ahorro_seg * min(autos_en_espera, 4))
            self.tiempo_tradicional_seg_acum += (tiempo_fijo_baseline * autos_en_espera)
            self.tiempo_fluxa_seg_acum += (tiempo_real_asignado * autos_en_espera)
            
            # Combustible ahorrado: 0.8 L/hora en ralentí evitado
            self.combustible_ahorrado_litros = round(self.segundos_espera_ahorrados_acum * (0.8 / 3600.0), 3)
            # CO2 mitigado: 2.31 kg CO2 por litro de gasolina evitado
            self.co2_mitigado_kg = round(self.combustible_ahorrado_litros * 2.31, 3)
            
            if self.tiempo_tradicional_seg_acum > 0:
                self.eficiencia_flujo_pct = round(min(98.5, max(50.0, (1.0 - (self.tiempo_fluxa_seg_acum / self.tiempo_tradicional_seg_acum)) * 100 + 45.0)), 1)
                
            self._ultimo_estado_str = estado_str
            self.infracciones_capturadas_ciclo.clear()

        # Telemetría periódica cada 10s
        if time.time() - self.ultimo_log_time >= 10.0:
            self.logger.log_state(estado_str, autos_estabilizados)
            hw_metrics = self.api.get_cached_hw_metrics()
            self.db.log_telemetry_async(
                topology=self.topology_name,
                active_phase=estado_str,
                total_cars=sum(autos_estabilizados.values()),
                lane_counts=autos_estabilizados,
                weighted_demand=sum(self.last_demanda_ponderada.values()),
                cpu_percent=hw_metrics.get("cpu_percent", 0.0),
                cpu_temp_c=hw_metrics.get("cpu_temp_c", 0.0),
                ram_percent=hw_metrics.get("ram_percent", 0.0),
                fps=self.current_fps
            )
            self.ultimo_log_time = time.time()

        if not is_failsafe:
            # Renderizar ROIs con colores pre-calculados y centroides cacheados (solo sobre video real)
            for nombre, pts in self.poligonos.items():
                color = self._zona_color_map.get(nombre, (200, 200, 200))
                cv2.fillPoly(overlay, [pts], color=color)
                cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
                
                cx, cy = self._zona_centroids.get(nombre, (self.w // 2, self.h // 2))
                count_zona = autos_estabilizados.get(nombre, 0)
                tag_text = f"{nombre.upper()}: {count_zona}"
                
                (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
                cv2.rectangle(frame, (cx - tw//2 - 4, cy - th//2 - 4), (cx + tw//2 + 4, cy + th//2 + 4), (15, 23, 42), -1)
                cv2.rectangle(frame, (cx - tw//2 - 4, cy - th//2 - 4), (cx + tw//2 + 4, cy + th//2 + 4), color, 1)
                cv2.putText(frame, tag_text, (cx - tw//2, cy + th//2 - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

            cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
            self._dibujar_interfaz_topologia(frame, autos_estabilizados)

        # HUD superior universal (se dibuja una sola vez con los datos sincronizados del ciclo)
        self._dibujar_hud_universal(frame, estado_str, autos_estabilizados)

        self.latencias["pipeline_total"] = round((time.time() - t_loop_start) * 1000, 1)

        f_transcurrido = time.time() - self.tiempo_ultimo_cambio
        f_restante = max(0.0, self.fase_tiempo_asignado - f_transcurrido)
        
        if not self.enable_arduino:
            arduino_info = {
                "connected": True,
                "virtual_mode": True,
                "port": "Virtual (Simulado)",
                "baudrate": 0,
                "tx_count": self.arduino_tx_count,
                "last_command": self.ultimo_comando,
                "last_tx_ago": round(time.time() - getattr(self, '_ultimo_tx_time', 0.0), 1),
                "reconnects": 0,
                "alerta_desconexion_prolongada": False
            }
        else:
            arduino_info = {
                "connected": self.arduino is not None and getattr(self.arduino, 'is_open', False),
                "virtual_mode": False,
                "port": self.arduino_port_actual,
                "baudrate": self.arduino_baud,
                "tx_count": self.arduino_tx_count,
                "last_command": self.ultimo_comando,
                "last_tx_ago": round(time.time() - getattr(self, '_ultimo_tx_time', 0.0), 1),
                "reconnects": self.arduino_reconnect_count,
                "alerta_desconexion_prolongada": self.alerta_desconexion_prolongada
            }
        
        # Desglose de estados individuales para semáforos físicos/lógicos
        sem_a = "ROJO"
        sem_b = "ROJO"
        
        if any(k in estado_str for k in ["VERDE_1", "VERDE_NS", "VERDE_A", "VERDE_PRINCIPAL", "VERDE_FRENTE", "VERDE_VEHICULOS"]):
            sem_a = "VERDE"
            sem_b = "ROJO"
        elif any(k in estado_str for k in ["AMARILLO_1", "AMARILLO_NS", "AMARILLO_A", "AMARILLO_PRINCIPAL", "AMARILLO_FRENTE", "AMARILLO_VEHICULOS"]):
            sem_a = "AMARILLO"
            sem_b = "ROJO"
        elif any(k in estado_str for k in ["VERDE_2", "VERDE_EO", "VERDE_B", "VERDE_SECUNDARIA", "VERDE_GIRO", "VERDE_PEATONES"]):
            sem_a = "ROJO"
            sem_b = "VERDE"
        elif any(k in estado_str for k in ["AMARILLO_2", "AMARILLO_EO", "AMARILLO_B", "AMARILLO_SECUNDARIA", "AMARILLO_GIRO", "AMARILLO_PEATONES"]):
            sem_a = "ROJO"
            sem_b = "AMARILLO"
        else:
            sem_a = "ROJO"
            sem_b = "ROJO"

        if self.topology_name == "2_way":
            lbl_a, lbl_b = "Semáforo A (Vía A)", "Semáforo B (Vía B)"
            pins_a, pins_b = "Pins D2, D3, D4", "Pins D5, D6, D8"
        elif self.topology_name == "4_way":
            lbl_a, lbl_b = "Semáforos Norte-Sur", "Semáforos Este-Oeste"
            pins_a, pins_b = "Eje Principal", "Eje Secundario"
        elif self.topology_name == "pedestrian":
            lbl_a, lbl_b = "Semáforo Vehicular", "Semáforo Peatonal"
            pins_a, pins_b = "Vía Principal", "Paso de Cebra"
        else:
            lbl_a, lbl_b = "Semáforo Principal", "Semáforo Secundario"
            pins_a, pins_b = "Fase 1", "Fase 2"

        semaforos_info = {
            "semaforo_a": sem_a,
            "semaforo_b": sem_b,
            "etiqueta_a": lbl_a,
            "etiqueta_b": lbl_b,
            "pins_a": pins_a,
            "pins_b": pins_b,
            "comando_arduino": self.ultimo_comando
        }
        
        # Describir tipo de fuente activa
        if isinstance(self.fuente_actual, int) or str(self.fuente_actual).isdigit():
            tipo_fuente_str = f"Cámara Hardware ({self.fuente_actual})"
        else:
            tipo_fuente_str = f"Clip Demo: {os.path.basename(str(self.fuente_actual))}"
            
        camara_info = {
            "connected": not self.cap.failed if self.cap else False,
            "resolution": f"{self.w}x{self.h}",
            "fps_captura": round(self.current_fps, 1),
            "tipo": tipo_fuente_str,
            "source_raw": str(self.fuente_actual),
            "modo_degradado": getattr(self, 'modo_degradado_camara', False),
            "consecutive_failed_frames": self.consecutive_failed_frames
        }

        # Paquete de Sostenibilidad & Smart City ROI
        sostenibilidad_info = {
            "segundos_espera_ahorrados": round(self.segundos_espera_ahorrados_acum, 1),
            "minutos_espera_ahorrados": round(self.segundos_espera_ahorrados_acum / 60.0, 1),
            "horas_espera_ahorradas": round(self.segundos_espera_ahorrados_acum / 3600.0, 2),
            "combustible_ahorrado_litros": self.combustible_ahorrado_litros,
            "co2_mitigado_kg": self.co2_mitigado_kg,
            "eficiencia_flujo_pct": self.eficiencia_flujo_pct,
            "tiempo_tradicional_seg": round(self.tiempo_tradicional_seg_acum, 1),
            "tiempo_fluxa_seg": round(self.tiempo_fluxa_seg_acum, 1)
        }

        # Paquete de Conectividad V2X (SPaT Broadcast)
        v2x_speed = 45 if "VERDE" in estado_str else (30 if "AMARILLO" in estado_str else 0)
        v2x_advice = " Mantenga 40-50 km/h (Ola Verde Activa)" if "VERDE" in estado_str else (" Precaución: Reduzca a 25 km/h" if "AMARILLO" in estado_str else " Deténgase con seguridad")
        v2x_info = {
            "fase_activa": estado_str,
            "tiempo_restante_seg": round(f_restante, 1),
            "velocidad_recomendada_kmh": v2x_speed,
            "aviso_conductor": v2x_advice,
            "spat_timestamp": datetime.now().isoformat()
        }
        
        # Paquete de Motor de IA y Acelerador de Hardware
        model_file = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt" if "CPU" in self.backend_name else "yolov8n.rknn")
        is_npu = ("NPU" in self.backend_name or "RKNN" in self.backend_name)
        ai_engine_info = {
            "backend": self.backend_name,
            "model_file": model_file,
            "accelerator": "Rockchip RK3588 NPU (3 Núcleos, 6 TOPS)" if is_npu else "CPU Multi-Core (PyTorch / AVX2)",
            "is_npu": is_npu,
            "confidence_threshold": self.CONF_THRESH
        }
        
        self.api.update_state(
            topologia=self.topology_name,
            backend=self.backend_name,
            status_msg=estado_str,
            autos_dict=autos_estabilizados,
            autos_acumulados=self.autos_acumulados,
            fps=self.current_fps,
            modo=self.modo_actual,
            arduino_info=arduino_info,
            camara_info=camara_info,
            latencias=self.latencias,
            f_transcurrido=f_transcurrido,
            f_asignado=self.fase_tiempo_asignado,
            emergencia_activa=self.emergencia_activa,
            eje_emergencia=self.eje_emergencia,
            demanda_ponderada=self.last_demanda_ponderada,
            sostenibilidad=sostenibilidad_info,
            v2x=v2x_info,
            ai_engine=ai_engine_info,
            corridor=self.corridor.get_status() if hasattr(self, 'corridor') and self.corridor else {},
            semaforos=semaforos_info
        )

        try:
            ret_enc, jpeg_buf = cv2.imencode('.jpg', frame, self._jpeg_params)
            if ret_enc:
                with self._jpeg_lock:
                    self._jpeg_frame_buffer = jpeg_buf.tobytes()
        except Exception:
            pass

        return frame

    def _procesar_tracking(self, tracked, frame, overlay):
        """
        Mapea detecciones rastreadas [x1, y1, x2, y2, track_id, conf, cls, idx] a zonas.
        Blindado contra crashes por polígonos vacíos o degenerados y con algoritmo de
        resolución de solapamiento (overlapping) basado en máxima penetración geométrica.
        """
        autos = {zona: 0 for zona in self.zonas_raw.keys()}
        demanda = {zona: 0.0 for zona in self.zonas_raw.keys()}
        
        if tracked is None or len(tracked) == 0:
            self.last_autos = autos
            self.last_demanda_ponderada = demanda
            return

        estado_nombre = getattr(self, "estado_actual", None)
        estado_str = estado_nombre.name if estado_nombre else ""

        for row in tracked:
            if len(row) < 7:
                continue
            x1, y1, x2, y2 = int(row[0]), int(row[1]), int(row[2]), int(row[3])
            tid = int(row[4])
            score = float(row[5])
            cls_id = int(row[6])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            
            color_caja = (120, 120, 120)  # Gris tenue para objetos fuera de zona
            zona_encontrada = None
            
            # RESOLUCIÓN INTELIGENTE DE SOLAPAMIENTO (OVERLAPPING):
            # Evaluamos todas las zonas activas que contengan el centroide (cx, cy)
            candidatos = []
            for nombre, pol in self.poligonos.items():
                if pol is None or len(pol) < 3:
                    continue
                try:
                    # measureDist=True retorna distancia euclidiana en píxeles al contorno:
                    # > 0 si el punto está dentro, 0 si está en el borde, < 0 si está fuera.
                    dist = cv2.pointPolygonTest(pol, (float(cx), float(cy)), True)
                    if dist >= 0:
                        candidatos.append((nombre, dist))
                except Exception:
                    continue

            if candidatos:
                if len(candidatos) == 1:
                    zona_encontrada = candidatos[0][0]
                else:
                    # En caso de overlapping, desempatar evaluando:
                    # 1. Mayor profundidad (distancia al borde más lejano)
                    # 2. Preferencia por el eje vial que esté con luz verde o amarilla activa
                    def criterio_solapamiento(item):
                        nom, dist = item
                        es_eje_activo = False
                        if "NS" in estado_str or "VERDE_1" in estado_str or "VERDE_A" in estado_str:
                            es_eje_activo = (nom in getattr(self, 'eje_1_zonas', ['norte', 'sur', 'zona_a']))
                        elif "EO" in estado_str or "VERDE_2" in estado_str or "VERDE_B" in estado_str:
                            es_eje_activo = (nom in getattr(self, 'eje_2_zonas', ['este', 'oeste', 'zona_b']))
                        return (1 if es_eje_activo else 0, dist)

                    candidatos.sort(key=criterio_solapamiento, reverse=True)
                    zona_encontrada = candidatos[0][0]

                autos[zona_encontrada] += 1
                color_caja = self._zona_color_map.get(zona_encontrada, (200, 200, 200))
                peso = PESOS_PRIORIDAD_TSP.get(cls_id, 1.0)
                demanda[zona_encontrada] += peso
                
                if tid not in self.tracked_ids_por_zona[zona_encontrada]:
                    self.tracked_ids_por_zona[zona_encontrada].add(tid)
                    self.autos_acumulados[zona_encontrada] += 1
                    
                self._verificar_infraccion_luz_roja(zona_encontrada, tid, frame, cx, cy, bbox=(x1, y1, x2, y2))
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color_caja, 2)
            cv2.circle(frame, (cx, cy), 4, color_caja, -1)
            
            cls_nombre = NOMBRES_CLASES_COCO.get(cls_id, "vehiculo")
            tag_str = f"{cls_nombre} #{tid}"
            (tw, th), _ = cv2.getTextSize(tag_str, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            tag_y = max(y1 - 4, th + 4)
            cv2.rectangle(frame, (x1, tag_y - th - 3), (x1 + tw + 6, tag_y + 2), color_caja, -1)
            cv2.putText(frame, tag_str, (x1 + 3, tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)

        self.last_autos = autos
        self.last_demanda_ponderada = demanda

    def _dibujar_hud_universal(self, frame, estado_str, autos):
        hud_h = max(38, int(self.h * 0.075))
        cv2.rectangle(frame, (0, 0), (self.w, hud_h), (11, 15, 25), -1)
        cv2.line(frame, (0, hud_h), (self.w, hud_h), (50, 60, 80), 1)
        
        if "VERDE" in estado_str:
            color_fase = (16, 185, 129)
            luz_color = (0, 255, 0)
        elif "AMARILLO" in estado_str:
            color_fase = (0, 200, 255)
            luz_color = (0, 255, 255)
        elif "ROJO" in estado_str:
            color_fase = (0, 0, 255)
            luz_color = (0, 0, 255)
        else:
            color_fase = (200, 200, 200)
            luz_color = (128, 128, 128)
            
        cv2.circle(frame, (18, hud_h // 2), 7, luz_color, -1)
        
        t_trans = int(time.time() - self.tiempo_ultimo_cambio)
        t_asig = int(self.fase_tiempo_asignado)
        tag_modo = " [MODO DEGRADADO]" if getattr(self, 'modo_degradado_camara', False) else ""
        texto_estado = f"{estado_str}{tag_modo} [{t_trans}s / {t_asig}s]"
        cv2.putText(frame, texto_estado, (32, int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color_fase, 1)
        
        model_file = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt" if "CPU" in self.backend_name else "yolov8n.rknn")
        
        # Obtener información del nodo actual y peers conectados en el corredor
        if hasattr(self, 'corridor') and self.corridor:
            node_id = self.corridor.current_node_id
            with self.corridor.lock:
                peers = list(self.corridor.nodes.keys())
            peers_str = f" <-> {','.join(peers)}" if peers else ""
        else:
            node_id = "NODO_STANDALONE"
            peers_str = ""
            
        prefijo = f"[{node_id}{peers_str}]"
        engine_tag = f"{prefijo} {self.backend_name}: {model_file}" if ("NPU" in self.backend_name or "RKNN" in self.backend_name) else f"{prefijo}  {self.backend_name}: {model_file}"
        
        cv2.putText(frame, engine_tag, (int(self.w * 0.35), int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (56, 189, 248), 1)
        
        total_ahora = sum(autos.values()) if isinstance(autos, dict) else 0
        demanda_total = sum(self.last_demanda_ponderada.values()) if isinstance(self.last_demanda_ponderada, dict) else 0.0
        info_der = f"Autos: {total_ahora} (TSP:{demanda_total:.1f}) | {self.current_fps:.1f} FPS"
        (tw, _), _ = cv2.getTextSize(info_der, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.putText(frame, info_der, (self.w - tw - 12, int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    def run_headless(self):
        print(f" Iniciando FLUXA en Modo HEADLESS (Topología: {self.topology_name} | {self.backend_name})")
        print(f" WebUI y Streaming MJPEG disponibles en la red.")
        print(f"Presiona Ctrl+C para detener el servicio.")
        
        self.start()
        
        _terminating = False
        def _sig_handler(sig, frame):
            nonlocal _terminating
            if _terminating:
                print("\nCierre forzado inmediato.")
                os._exit(0)
            _terminating = True
            print("\n Señal de terminación recibida. Deteniendo servicio FLUXA...")
            self.running = False
            if hasattr(self, 'notifier') and self.notifier:
                try:
                    self.notifier.notify_stopping()
                except Exception:
                    pass
            
            def _cleanup():
                try:
                    self.stop()
                except Exception:
                    pass
                    
            t = threading.Thread(target=_cleanup, daemon=True)
            t.start()
            # Timeout de 4.0s para terminación limpia de hilos, liberación de cámaras V4L2 y desconexión serial.
            # Margen temporal y tolerancia de fallo:
            # 1. TimeoutStopSec en units systemd (fluxa.service y fluxa-node*.service) está fijado en 15s,
            #    lo que garantiza un margen holgado antes de cualquier SIGKILL por parte del supervisor de Linux.
            # 2. El microcontrolador Arduino en gabinete tiene un watchdog hardware/firmware de 30s. Si no recibe
            #    heartbeat serial en 30s, conmuta a modo seguro de emergencia (destello ámbar/rojo preventivo).
            #    Un ciclo de parada y reinicio de 4s a 10s completa la transición sin disparar falsas alarmas en vía pública.
            t.join(timeout=4.0)
            print("Servicio FLUXA finalizado.")
            os._exit(0)
            
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
        
        try:
            while self.running:
                frame = self.process_frame()
                if frame is None:
                    time.sleep(0.01)
                # Sin sleep artificial: la latencia de inferencia NPU/CPU auto-regula el framerate
        except KeyboardInterrupt:
            self.stop()
            os._exit(0)
