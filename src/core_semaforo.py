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
    def __init__(self, topology_name="4_way", backend_name="CPU", port=None, video_source=None):
        self.topology_name = topology_name
        self.backend_name = backend_name
        print(f"⏳ Inicializando CoreSemaforoBase (Topología: {topology_name} | Motor: {backend_name})...")
        
        self.arduino = None
        self.cap = None
        self.config = self._load_config()
        
        # Fuente de video inicial
        if video_source is not None:
            self.fuente_actual = video_source
        else:
            self.fuente_actual = self.config.get("system", {}).get("camera_source", self.config.get("system", {}).get("camera_index", 0))
        
        # Telemetría de Arduino y Watchdog de Desconexión Prolongada (P2.4)
        self.arduino_port_actual = self.config.get("system", {}).get("serial_port", "/dev/ttyACM0")
        self.arduino_baud = self.config.get("system", {}).get("serial_baudrate", 9600)
        self.arduino_tx_count = 0
        self.arduino_reconnect_count = 0
        self.ultimo_comando = None
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

        # FPS y Latencias
        self.fps_frames = 0
        self.fps_start_time = time.time()
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
        self._video_switch_lock = threading.Lock()

        # Constantes de tiempo
        cfg_tl = self.config.get("traffic_light", {})
        self.TIEMPO_MINIMO_VERDE_BASE = cfg_tl.get("tiempo_minimo_verde", 5.0)
        self.TIEMPO_MAXIMO_VERDE = cfg_tl.get("tiempo_maximo_verde", 45.0)
        self.TIEMPO_AMARILLO = cfg_tl.get("tiempo_amarillo", 3.0)
        self.TIEMPO_ROJO_TODOS = cfg_tl.get("tiempo_rojo_todos", 2.0)
        self.TIEMPO_REPOSO = cfg_tl.get("tiempo_reposo", 20.0)
        
        self.CLASES_VEHICULOS = self.config.get("ai_model", {}).get("classes_to_detect", [0, 1, 2, 3, 5, 7])
        self.CONF_THRESH = self.config.get("ai_model", {}).get("confidence_threshold", 0.35)
        
        # Paleta de colores para ROIs y cajas
        self.COLORES_ZONAS = [
            (239, 68, 68),   # Rojo
            (59, 130, 246),  # Azul
            (16, 185, 129),  # Verde
            (245, 158, 11),  # Ámbar/Naranja
            (139, 92, 246),  # Púrpura
            (236, 72, 153)   # Rosa
        ]
        
        # Configuración unificada de la Máquina de Estados (FSM)
        self._configurar_topologia_fsm()

        # Inicializar Analytics Logger y Gestor MariaDB
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        self.logger = TrafficAnalyticsLogger(log_dir=log_dir, enabled=self.config.get("system", {}).get("log_analytics", True))
        self.ultimo_log_time = time.time()
        
        db_cfg = self.config.get("database", {})
        self.db = DatabaseManager(
            host=db_cfg.get("host", "localhost"),
            user=db_cfg.get("user", "root"),
            password=db_cfg.get("password", None),
            db_name=db_cfg.get("name", "fluxa_traffic"),
            port=db_cfg.get("port", 3306),
            enabled=db_cfg.get("enabled", True)
        )
        
        # Inicializar Servidor Web API
        api_cfg = self.config.get("api", {})
        api_port = port if port is not None else api_cfg.get("port", 5000)
        self.api = TelemetryAPI(host=api_cfg.get("host", "0.0.0.0"), port=api_port, enabled=api_cfg.get("enabled", True))
        self.api.start(
            controller_callback=self.forzar_emergencia,
            frame_getter=self.get_encoded_jpeg,
            db_instance=self.db,
            hot_reload_callback=self.reload_zones,
            change_source_callback=self.cambiar_fuente_video
        )

        # Inicialización del modelo (implementado en subclases)
        self._init_model()

    def _init_tracker(self):
        args = SimpleNamespace(
            track_high_thresh=self.config.get("tracker", {}).get("track_high_thresh", 0.4), 
            track_low_thresh=self.config.get("tracker", {}).get("track_low_thresh", 0.05), 
            new_track_thresh=self.config.get("tracker", {}).get("new_track_thresh", 0.5), 
            track_buffer=self.config.get("tracker", {}).get("track_buffer", 120), 
            match_thresh=self.config.get("tracker", {}).get("match_thresh", 0.8), 
            gmc_method='sparseOptFlow',
            fuse_score=False
        )
        self.tracker = BYTETracker(args)

    def _configurar_topologia_fsm(self):
        """Mapeo de zonas y características operativas según la topología activa (P1.2)"""
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
        Transición de Emergencia Segura con Intervalo de Despeje Vial Obligatorio (P1.1 y P1.3).
        
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

    def _procesar_logica_semaforo(self, autos, tiempo_minimo_actual):
        """
        Lógica unificada de la máquina de estados semafórica adaptativa (P1.2).
        Calcula tiempos dinámicos, gestiona intervalos de despeje y transiciones seguras.
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

        estado_str = self.estado_actual.name if hasattr(self.estado_actual, 'name') else str(self.estado_actual)

        # --- FASE 1: VERDE EJE 1 ---
        if any(k in estado_str for k in ["VERDE_1", "VERDE_NS", "VERDE_A", "VERDE_PRINCIPAL", "VERDE_FRENTE", "VERDE_VEHICULOS"]):
            self.enviar_comando(self.fsm_commands.get('VERDE_1', '1'))
            self.fase_tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, demanda_eje_1 * factor))
            
            hay_demanda_opuesta = (autos_eje_2 > 0 or demanda_eje_2 > 0) if not self.is_pedestrian else ((autos_eje_2 > 0 or demanda_eje_2 > 0) or getattr(self, 'llamada_peatonal_manual', False))
            
            if hay_demanda_opuesta and tiempo_transcurrido > tiempo_minimo_actual:
                if autos_eje_1 == 0 or tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_1")
                    if self.is_pedestrian:
                        self.llamada_peatonal_manual = False

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
            if self.is_pedestrian:
                tiempo_cruce = max(10.0, demanda_eje_2 * 3.5)
                self.fase_tiempo_asignado = min(25.0, tiempo_cruce)
                if tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self._cambiar_fase("AMARILLO_2")
            else:
                self.fase_tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, demanda_eje_2 * factor))
                if (autos_eje_1 > 0 or demanda_eje_1 > 0) and tiempo_transcurrido > tiempo_minimo_actual:
                    if autos_eje_2 == 0 or tiempo_transcurrido >= self.fase_tiempo_asignado:
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
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando config.json: {e}")
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
        self.CONF_THRESH = cfg_ai.get("confidence_threshold", 0.35)
        self.CLASES_VEHICULOS = cfg_ai.get("classes_to_detect", [0, 1, 2, 3, 5, 7])
        
        new_model = cfg_ai.get("model_file", "yolov8n.pt")
        if new_model != old_model:
            print(f"🔄 Recargando nuevo modelo YOLO en memoria: {new_model}...")
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
            print(f"🔄 Solicitud de cambio de fuente de video a: {nueva_fuente}...")
            
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
                    fallback_demo = os.path.join(os.path.dirname(__file__), '..', 'videos', 'demo_trafico_4vias.mp4')
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
                print(f"✅ {msg}")
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
        threading.Thread(target=self._init_arduino, daemon=True).start()
        
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

    def _construir_poligonos(self):
        self.poligonos = {}
        for nombre, puntos in self.zonas_raw.items():
            pts = []
            for px, py in puntos:
                pts.append([int(px * self.w), int(py * self.h)])
            self.poligonos[nombre] = np.array(pts, np.int32)

    def _init_arduino(self):
        ports_to_try = [
            self.arduino_port_actual,
            "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2",
            "/dev/ttyUSB0", "/dev/ttyUSB1"
        ]
        
        while self.running:
            is_connected = self.arduino is not None and getattr(self.arduino, 'is_open', False)
            if not is_connected:
                # Monitoreo de desconexión prolongada (>30s) (P2.4)
                tiempo_desconectado = time.time() - self.tiempo_desconexion_arduino
                if tiempo_desconectado > 30.0:
                    self.alerta_desconexion_prolongada = True
                    if not self._alerta_desconexion_notificada:
                        self._alerta_desconexion_notificada = True
                        msg = f"⚠️ CRÍTICO: Controlador físico (Arduino) desconectado por más de {int(tiempo_desconectado)}s. Semáforos en modo degradado."
                        self.api.log_event('CRITICAL', msg)
                        self.db.log_event_async('CRITICAL', msg)
                        logging.critical(msg)

                connected = False
                for port in ports_to_try:
                    try:
                        self.arduino = serial.Serial(port=port, baudrate=self.arduino_baud, timeout=0.1)
                        time.sleep(2)
                        self.arduino.reset_input_buffer()
                        self.arduino_port_actual = port
                        connected = True
                        break
                    except Exception:
                        pass
                
                if connected:
                    logging.info(f"✅ Enlace serial con Arduino UNO R4 activo en {self.arduino_port_actual}.")
                    self.api.log_event('INFO', f"Controlador físico (Arduino UNO R4) reconectado en {self.arduino_port_actual}")
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
        if self.cap:
            self.cap.stop()
        if self.arduino:
            try:
                self.arduino.close()
            except Exception:
                pass
        if self.db:
            self.db.close()
        self.api.log_event('WARN', "Sistema FLUXA detenido de forma segura")

    def enviar_comando(self, comando):
        if self.arduino and comando != self.ultimo_comando:
            try:
                self.arduino.write(comando.encode())
                self.ultimo_comando = comando
                self.arduino_tx_count += 1
                self.api.log_event('ARDUINO', f"Comando '{comando}' enviado a semáforos")
            except serial.SerialException:
                logging.warning("❌ Falla de comunicación Serial con Arduino R4. Iniciando watchdog de reconexión...")
                self.api.log_event('WARN', "Desconexión de Arduino detectada. Iniciando watchdog...")
                self.tiempo_desconexion_arduino = time.time()
                try:
                    self.arduino.close()
                except Exception:
                    pass
                self.arduino = None
            except Exception:
                pass

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
            self.modo_actual = f"🚨 CORREDOR EMERGENCIA ({accion})"
            self.api.log_event('EMERG', f"🚨 PRIORIDAD C5 ACTIVADA: Corredor de Emergencia para {accion}")
            self.db.log_event_async('EMERG', f"🚨 PRIORIDAD C5 ACTIVADA: Corredor de Emergencia para {accion}")

    def _check_modo_noche(self):
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

    def _verificar_infraccion_luz_roja(self, zona_nombre, track_id, frame, cx, cy):
        """Detecta si un vehículo avanza en una zona con semáforo en rojo y toma foto de evidencia"""
        estado_nombre = getattr(self, "estado_actual", None)
        estado_str = estado_nombre.name if estado_nombre else ""
        
        es_luz_roja = False
        if "ROJO_TODOS" in estado_str:
            es_luz_roja = True
        elif "VERDE_NS" in estado_str or "AMARILLO_NS" in estado_str:
            if zona_nombre in ['este', 'oeste', 'secundaria', 'zona_b', 'giro_izq', 'peatones_esperando']:
                es_luz_roja = True
        elif "VERDE_EO" in estado_str or "AMARILLO_EO" in estado_str:
            if zona_nombre in ['norte', 'sur', 'principal_izq', 'principal_der', 'zona_a']:
                es_luz_roja = True

        if es_luz_roja:
            clave_infraccion = f"{estado_str}_{zona_nombre}_{track_id}"
            if clave_infraccion not in self.infracciones_capturadas_ciclo:
                self.infracciones_capturadas_ciclo.add(clave_infraccion)
                
                snapshot_name = f"violation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_id{track_id}.jpg"
                snapshot_path = os.path.join(self.dir_infracciones, snapshot_name)
                
                evidence = frame.copy()
                cv2.rectangle(evidence, (0, 0), (self.w, 40), (0, 0, 200), -1)
                cv2.putText(evidence, f"INFRACCION: CRUCE EN LUZ ROJA | ZONA: {zona_nombre.upper()} | VEHICULO ID:{track_id}", 
                            (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.circle(evidence, (cx, cy), 15, (0, 0, 255), 3)
                
                try:
                    cv2.imwrite(snapshot_path, evidence)
                except Exception:
                    pass
                
                self.db.log_violation_async(zona_nombre, track_id, estado_str, snapshot_name)
                self.api.log_event('WARN', f"⚠️ Infracción: Vehículo ID:{track_id} cruzó en Rojo en zona {zona_nombre.upper()}")

    def _generar_frame_failsafe(self, estado_str):
        """Genera un cuadro de respaldo si la fuente de video se interrumpe temporalmente"""
        placeholder = np.ones((self.h, self.w, 3), dtype=np.uint8) * 18
        cv2.putText(placeholder, "⚠️ SENAL DE VIDEO EN RECONEXION", (int(self.w*0.18), int(self.h*0.45)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)
        cv2.putText(placeholder, f"FUENTE: {self.fuente_actual}", (int(self.w*0.22), int(self.h*0.55)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        self._dibujar_hud_universal(placeholder, estado_str, self.last_autos)
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
        
        # Manejo a prueba de fallos si la fuente se desconecta
        if not ret or frame is None:
            self.consecutive_failed_frames += 1
            if self.consecutive_failed_frames > 40:
                fallback_demo = os.path.join(os.path.dirname(__file__), '..', 'videos', 'demo_trafico_4vias.mp4')
                if os.path.exists(fallback_demo) and self.fuente_actual != fallback_demo:
                    print("⚠️ Fallo prolongado de video. Conmutando a clip de respaldo...")
                    self.cambiar_fuente_video(fallback_demo)
                self.consecutive_failed_frames = 0
                
            frame = self._generar_frame_failsafe(estado_str)
            try:
                ret_enc, jpeg_buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret_enc:
                    with self._jpeg_lock:
                        self._jpeg_frame_buffer = jpeg_buf.tobytes()
            except Exception:
                pass
            return frame

        self.consecutive_failed_frames = 0
        
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

        # Calcular FPS
        self.fps_frames += 1
        elapsed_fps = time.time() - self.fps_start_time
        if elapsed_fps >= 1.0:
            self.current_fps = self.fps_frames / elapsed_fps
            self.fps_frames = 0
            self.fps_start_time = time.time()

        # Inferencia
        t_infer_start = time.time()
        dets = self._predict(frame)
        t_infer_end = time.time()
        self.latencias["inferencia"] = round((t_infer_end - t_infer_start) * 1000, 1)

        overlay = frame.copy()

        # Tracking
        t_track_start = time.time()
        if dets is not None and len(dets) > 0:
            wrapper = DetectionsWrapper(dets)
            tracked = self.tracker.update(wrapper)
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

        # Renderizar ROIs
        for i, (nombre, pts) in enumerate(self.poligonos.items()):
            color = self.COLORES_ZONAS[i % len(self.COLORES_ZONAS)]
            cv2.fillPoly(overlay, [pts], color=color)
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
            
            cx = int(np.mean(pts[:, 0]))
            cy = int(np.mean(pts[:, 1]))
            count_zona = autos_estabilizados.get(nombre, 0)
            tag_text = f"{nombre.upper()}: {count_zona}"
            
            (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            cv2.rectangle(frame, (cx - tw//2 - 4, cy - th//2 - 4), (cx + tw//2 + 4, cy + th//2 + 4), (15, 23, 42), -1)
            cv2.rectangle(frame, (cx - tw//2 - 4, cy - th//2 - 4), (cx + tw//2 + 4, cy + th//2 + 4), color, 1)
            cv2.putText(frame, tag_text, (cx - tw//2, cy + th//2 - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        # HUD superior
        self._dibujar_hud_universal(frame, estado_str, autos_estabilizados)
        self._dibujar_interfaz_topologia(frame, autos_estabilizados)

        self.latencias["pipeline_total"] = round((time.time() - t_loop_start) * 1000, 1)

        f_transcurrido = time.time() - self.tiempo_ultimo_cambio
        f_restante = max(0.0, self.fase_tiempo_asignado - f_transcurrido)
        
        arduino_info = {
            "connected": self.arduino is not None and getattr(self.arduino, 'is_open', False),
            "port": self.arduino_port_actual,
            "baudrate": self.arduino_baud,
            "tx_count": self.arduino_tx_count,
            "last_command": self.ultimo_comando,
            "reconnects": self.arduino_reconnect_count,
            "alerta_desconexion_prolongada": self.alerta_desconexion_prolongada
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
            "source_raw": str(self.fuente_actual)
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
        v2x_advice = "🟢 Mantenga 40-50 km/h (Ola Verde Activa)" if "VERDE" in estado_str else ("🟡 Precaución: Reduzca a 25 km/h" if "AMARILLO" in estado_str else "🔴 Deténgase con seguridad")
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
            ai_engine=ai_engine_info
        )

        try:
            ret_enc, jpeg_buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret_enc:
                with self._jpeg_lock:
                    self._jpeg_frame_buffer = jpeg_buf.tobytes()
        except Exception:
            pass

        return frame

    def _procesar_tracking(self, tracked, frame, overlay):
        """Mapea detecciones rastreadas [x1, y1, x2, y2, track_id, conf, cls, idx] a zonas, calcula TSP e infracciones"""
        autos = {zona: 0 for zona in self.zonas_raw.keys()}
        demanda = {zona: 0.0 for zona in self.zonas_raw.keys()}
        
        if tracked is None or len(tracked) == 0:
            self.last_autos = autos
            self.last_demanda_ponderada = demanda
            return
            
        for row in tracked:
            if len(row) < 7:
                continue
            x1, y1, x2, y2 = int(row[0]), int(row[1]), int(row[2]), int(row[3])
            tid = int(row[4])
            score = float(row[5])
            cls_id = int(row[6])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            
            color_caja = (200, 200, 200)
            zona_encontrada = None
            
            for i, (nombre, pol) in enumerate(self.poligonos.items()):
                if cv2.pointPolygonTest(pol, (cx, cy), False) >= 0:
                    autos[nombre] += 1
                    zona_encontrada = nombre
                    color_caja = self.COLORES_ZONAS[i % len(self.COLORES_ZONAS)]
                    
                    peso = PESOS_PRIORIDAD_TSP.get(cls_id, 1.0)
                    demanda[nombre] += peso
                    
                    if tid not in self.tracked_ids_por_zona[nombre]:
                        self.tracked_ids_por_zona[nombre].add(tid)
                        self.autos_acumulados[nombre] += 1
                        
                    self._verificar_infraccion_luz_roja(nombre, tid, frame, cx, cy)
                    break
            
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
        texto_estado = f"{estado_str} [{t_trans}s / {t_asig}s]"
        cv2.putText(frame, texto_estado, (32, int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color_fase, 1)
        
        model_file = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt" if "CPU" in self.backend_name else "yolov8n.rknn")
        engine_tag = f"⚡ {self.backend_name}: {model_file}" if ("NPU" in self.backend_name or "RKNN" in self.backend_name) else f"🧠 {self.backend_name}: {model_file}"
        cv2.putText(frame, engine_tag, (int(self.w * 0.40), int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (56, 189, 248), 1)
        
        total_ahora = sum(autos.values()) if isinstance(autos, dict) else 0
        demanda_total = sum(self.last_demanda_ponderada.values()) if isinstance(self.last_demanda_ponderada, dict) else 0.0
        info_der = f"Autos: {total_ahora} (TSP:{demanda_total:.1f}) | {self.current_fps:.1f} FPS"
        (tw, _), _ = cv2.getTextSize(info_der, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.putText(frame, info_der, (self.w - tw - 12, int(hud_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    def run_headless(self):
        print(f"🚀 Iniciando FLUXA en Modo HEADLESS (Topología: {self.topology_name} | {self.backend_name})")
        print(f"📡 WebUI y Streaming MJPEG disponibles en la red.")
        print(f"Presiona Ctrl+C para detener el servicio.")
        
        self.start()
        
        def _sig_handler(sig, frame):
            print("\n🛑 Señal de terminación recibida. Deteniendo servicio FLUXA...")
            self.stop()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
        
        try:
            while self.running:
                frame = self.process_frame()
                if frame is None:
                    time.sleep(0.02)
                else:
                    time.sleep(0.005)
        except KeyboardInterrupt:
            self.stop()
