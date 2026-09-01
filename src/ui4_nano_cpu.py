# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
import os
import sys
try:
    import tkinter as tk
    from tkinter import font, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    tk = None
    font = None
    messagebox = None
    TKINTER_AVAILABLE = False
import cv2
import serial
import time
from datetime import datetime
from enum import Enum
import numpy as np
import torch
import json
try:
    from PIL import Image, ImageTk
except ImportError:
    from PIL import Image
    ImageTk = None
import threading

from ultralytics import YOLO
from ultralytics.trackers.byte_tracker import BYTETracker

# Importar nuevos módulos de grado industrial
sys.path.append(os.path.dirname(__file__))
from videostream import VideoStream
from analytics import TrafficAnalyticsLogger
from api_server import TelemetryAPI

class EstadoSemaforo(Enum):
    VERDE_NS = 1
    AMARILLO_NS = 2
    ROJO_TODOS_NS_EO = 3
    VERDE_EO = 4
    AMARILLO_EO = 5
    ROJO_TODOS_EO_NS = 6
    EMERGENCIA = 7 # Estado temporal

class SemaforoController:
    def __init__(self):
        print("⏳ Inicializando controlador 4 vías (MODO CPU)...")
        self.arduino = None
        self.cap = None
        self.logger = None
        self.api = None
        self.config = self._load_config()
        
        # Forzar uso nativo de PyTorch (.pt) para evitar bugs de ONNX en CPU
        model_path = 'yolov8n.pt'
        posible = os.path.join(os.path.dirname(__file__), '..', 'models', 'yolov8n.pt')
        if os.path.exists(posible):
            model_path = posible

        print(f" Cargando modelo YOLO nativo en CPU desde: {model_path}")
        self.model = YOLO(model_path)
            
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
        
        self.estado_actual = EstadoSemaforo.VERDE_NS
        self.tiempo_ultimo_cambio = time.time()
        self.ultimo_comando = None
        self.running = False
        
        # Estado de Emergencia manual
        self.modo_actual = "Normal"
        self.emergencia_activa = False
        self.eje_emergencia = None # 'NS' o 'EO'
        
        self.frame_count = 0
        self.last_autos = {'N': 0, 'S': 0, 'E': 0, 'O': 0}
        self.autos_history = [] # Para filtro anti-flicker
        self.tiempo_sin_autos_inicio = time.time()
        self.fps_frames = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        self.w, self.h = 640, 480 

        # Constantes Originales
        cfg_tl = self.config.get("traffic_light", {})
        self.TIEMPO_MINIMO_VERDE_BASE = cfg_tl.get("tiempo_minimo_verde", 5.0)
        self.TIEMPO_MAXIMO_VERDE = cfg_tl.get("tiempo_maximo_verde", 45.0)
        self.TIEMPO_AMARILLO = cfg_tl.get("tiempo_amarillo", 3.0)
        self.TIEMPO_ROJO_TODOS = cfg_tl.get("tiempo_rojo_todos", 2.0)
        self.TIEMPO_REPOSO = cfg_tl.get("tiempo_reposo", 20.0)
        
        self.CLASES_VEHICULOS = self.config.get("ai_model", {}).get("classes_to_detect", [2, 3, 5, 7])
        self.CONF_THRESH = self.config.get("ai_model", {}).get("confidence_threshold", 0.35)
        
        self.COLORES = {
            "rojo": (0, 0, 255), "verde": (0, 255, 0), "amarillo": (0, 255, 255),
            "zona_n": (255, 100, 100), "zona_s": (100, 255, 100),
            "zona_e": (100, 100, 255), "zona_o": (255, 255, 100),
            "texto": (255, 255, 255)
        }
        
        # Telemetría y API
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        self.logger = TrafficAnalyticsLogger(log_dir=log_dir, enabled=self.config.get("system", {}).get("log_analytics", True))
        self.ultimo_log_time = time.time()
        
        api_cfg = self.config.get("api", {})
        self.api = TelemetryAPI(host=api_cfg.get("host", "0.0.0.0"), port=api_cfg.get("port", 5000), enabled=api_cfg.get("enabled", True))
        self.api.start(controller_callback=self._handle_api_command)

    def _handle_api_command(self, action):
        if action == "NS":
            self.emergencia_activa = True
            self.eje_emergencia = 'NS'
            self.modo_actual = "EMERGENCIA REMOTA (NS)"
        elif action == "EO":
            self.emergencia_activa = True
            self.eje_emergencia = 'EO'
            self.modo_actual = "EMERGENCIA REMOTA (EO)"
        elif action == "RESET":
            self.emergencia_activa = False
            self.modo_actual = "Normal"

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        if not os.path.exists(config_path):
            config_path = 'config.json'
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando config.json, usando defaults: {e}")
            return {}

    def start(self):
        self.running = True
        threading.Thread(target=self._init_arduino, daemon=True).start()
        
        cam_idx = self.config.get("system", {}).get("camera_index", 0)
        self.cap = VideoStream(src=cam_idx).start()
        
        time.sleep(1.0)
        ret, _ = self.cap.read()
        if not ret:
            messagebox.showwarning("Advertencia de Cámara", "No se pudo acceder a la cámara. Entrando en Modo Seguro.")
        
        self.estado_actual = EstadoSemaforo.VERDE_NS
        self.tiempo_ultimo_cambio = time.time()
        self.ultimo_comando = None

    def _init_arduino(self):
        port = self.config.get("system", {}).get("serial_port", "/dev/ttyACM0")
        baud = self.config.get("system", {}).get("serial_baudrate", 9600)
        try:
            self.arduino = serial.Serial(port=port, baudrate=baud, timeout=0.1)
            time.sleep(2)
            self.arduino.reset_input_buffer()
            print("Conexión con Arduino establecida.")
        except Exception as e:
            print(f"No se pudo conectar al Arduino (Modo Simulación CPU): {e}")
            self.arduino = None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.stop()
            self.cap = None
        if self.arduino:
            self.arduino.close()
            self.arduino = None

    def enviar_comando(self, comando):
        if self.arduino and comando != self.ultimo_comando:
            try:
                self.arduino.write(comando.encode())
                self.ultimo_comando = comando
            except Exception:
                pass
                
    def forzar_emergencia(self, eje):
        """Método llamado por UI al presionar N o E"""
        self.emergencia_activa = True
        self.eje_emergencia = eje
        self.modo_actual = f"EMERGENCIA ({eje})"

    def _check_modo_noche(self):
        night_cfg = self.config.get("night_mode", {})
        if not night_cfg.get("enabled", False):
            if not self.emergencia_activa: self.modo_actual = "Normal"
            return self.TIEMPO_MINIMO_VERDE_BASE
            
        ahora = datetime.now().hour
        inicio = night_cfg.get("start_hour", 23)
        fin = night_cfg.get("end_hour", 5)
        
        es_noche = False
        if inicio > fin: # cruza la medianoche (ej 23 a 5)
            es_noche = ahora >= inicio or ahora < fin
        else:
            es_noche = inicio <= ahora < fin
            
        if es_noche:
            if not self.emergencia_activa: self.modo_actual = "Noche (Valle)"
            return night_cfg.get("tiempo_verde_noche", 3.0)
        else:
            if not self.emergencia_activa: self.modo_actual = "Normal"
            return self.TIEMPO_MINIMO_VERDE_BASE

    def process_frame(self):
        if not self.running or not self.cap:
            return None

        ret, frame = self.cap.read()
        
        # --- MODO SEGURO ---
        if not ret or self.cap.failed:
            self.enviar_comando('5') 
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            cv2.putText(frame, "CAMARA DESCONECTADA", (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.putText(frame, "MODO SEGURO ACTIVO", (250, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
            self.api.update_state("MODO SEGURO (FALLA CAMARA)", {'N':0,'S':0,'E':0,'O':0}, 0, "Seguro")
            time.sleep(0.5)
            return frame

        self.h, self.w = frame.shape[:2]

        zn = self.config.get("zones", {}).get("4_way", {}).get("norte", [0.35, 0, 0.65, 0.4])
        zs = self.config.get("zones", {}).get("4_way", {}).get("sur", [0.35, 0.6, 0.65, 1.0])
        ze = self.config.get("zones", {}).get("4_way", {}).get("este", [0.65, 0.4, 1.0, 0.6])
        zo = self.config.get("zones", {}).get("4_way", {}).get("oeste", [0.0, 0.4, 0.35, 0.6])
        
        self.ZONA_N = (int(self.w * zn[0]), int(self.h * zn[1]), int(self.w * zn[2]), int(self.h * zn[3]))
        self.ZONA_S = (int(self.w * zs[0]), int(self.h * zs[1]), int(self.w * zs[2]), int(self.h * zs[3]))
        self.ZONA_E = (int(self.w * ze[0]), int(self.h * ze[1]), int(self.w * ze[2]), int(self.h * ze[3]))
        self.ZONA_O = (int(self.w * zo[0]), int(self.h * zo[1]), int(self.w * zo[3]), int(self.h * zo[3]))

        self.fps_frames += 1
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.current_fps = self.fps_frames / elapsed
            self.fps_frames = 0
            self.fps_start_time = time.time()

        autos_raw = self._detectar_vehiculos(frame)
        
        # Filtro Anti-Flicker (Max Pooling 5 frames)
        self.autos_history.append(autos_raw)
        if len(self.autos_history) > 5: self.autos_history.pop(0)
        autos = {k: max([h[k] for h in self.autos_history]) for k in autos_raw}

        self._actualizar_logica_semaforo(autos)
        self._dibujar_interfaz(frame, autos)

        # Update API con estado de hardware
        cam_ok = not self.cap.failed
        ard_ok = self.arduino is not None
        self.api.update_state(self.estado_actual.name, autos, round(self.current_fps, 1), self.modo_actual, ard_ok, cam_ok)

        if time.time() - self.ultimo_log_time >= 10.0:
            self.logger.log_state(self.estado_actual.name, autos)
            self.ultimo_log_time = time.time()

        return frame

    def _detectar_vehiculos(self, frame):
        self.frame_count += 1
        autos = {'N': 0, 'S': 0, 'E': 0, 'O': 0}
        tracks_to_draw = []
        
        results = self.model.predict(frame, conf=self.CONF_THRESH, classes=self.CLASES_VEHICULOS, verbose=False)
        
        if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
            tracks = self.tracker.update(results[0].boxes, frame)
            
            for track in tracks:
                x1, y1, x2, y2, track_id, conf, cls, *_ = track
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                
                if self.ZONA_N[0] < cx < self.ZONA_N[2] and self.ZONA_N[1] < cy < self.ZONA_N[3]: autos['N'] += 1
                elif self.ZONA_S[0] < cx < self.ZONA_S[2] and self.ZONA_S[1] < cy < self.ZONA_S[3]: autos['S'] += 1
                elif self.ZONA_E[0] < cx < self.ZONA_E[2] and self.ZONA_E[1] < cy < self.ZONA_E[3]: autos['E'] += 1
                elif self.ZONA_O[0] < cx < self.ZONA_O[2] and self.ZONA_O[1] < cy < self.ZONA_O[3]: autos['O'] += 1
                tracks_to_draw.append(track)

        if sum(autos.values()) == 0:
            if self.tiempo_sin_autos_inicio is None:
                self.tiempo_sin_autos_inicio = time.time()
        else:
            self.tiempo_sin_autos_inicio = None

        for track in tracks_to_draw:
            x1, y1, x2, y2, track_id, conf, cls, *_ = track
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            track_id = int(track_id)
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            
            color_caja = (0, 255, 255)
            if self.ZONA_N[0] < cx < self.ZONA_N[2] and self.ZONA_N[1] < cy < self.ZONA_N[3]: color_caja = self.COLORES["zona_n"]
            elif self.ZONA_S[0] < cx < self.ZONA_S[2] and self.ZONA_S[1] < cy < self.ZONA_S[3]: color_caja = self.COLORES["zona_s"]
            elif self.ZONA_E[0] < cx < self.ZONA_E[2] and self.ZONA_E[1] < cy < self.ZONA_E[3]: color_caja = self.COLORES["zona_e"]
            elif self.ZONA_O[0] < cx < self.ZONA_O[2] and self.ZONA_O[1] < cy < self.ZONA_O[3]: color_caja = self.COLORES["zona_o"]
                
            t = max(1, int(self.w / 400) + 1)
            l = max(10, int(min(x2-x1, y2-y1) * 0.2))
            
            cv2.line(frame, (x1, y1), (x1 + l, y1), color_caja, t)
            cv2.line(frame, (x1, y1), (x1, y1 + l), color_caja, t)
            cv2.line(frame, (x2, y1), (x2 - l, y1), color_caja, t)
            cv2.line(frame, (x2, y1), (x2, y1 + l), color_caja, t)
            cv2.line(frame, (x1, y2), (x1 + l, y2), color_caja, t)
            cv2.line(frame, (x1, y2), (x1, y2 - l), color_caja, t)
            cv2.line(frame, (x2, y2), (x2 - l, y2), color_caja, t)
            cv2.line(frame, (x2, y2), (x2, y2 - l), color_caja, t)
            cv2.circle(frame, (cx, cy), max(2, int(t*1.5)), color_caja, -1)
            font_s = max(0.4, self.w / 1500)
            text = f"ID:{track_id}"
            cv2.putText(frame, text, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, font_s, (0,0,0), t+1)
            cv2.putText(frame, text, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, font_s, color_caja, t)
                
        return autos

    def _actualizar_logica_semaforo(self, autos):
        # Determinar mínimo verde dinámico (Noche vs Normal)
        tiempo_minimo_actual = self._check_modo_noche()
        tiempo_transcurrido = time.time() - self.tiempo_ultimo_cambio
        autos_NS = max(autos['N'], autos['S'])
        autos_EO = max(autos['E'], autos['O'])
        factor = self.config.get("traffic_light", {}).get("factor_tiempo_por_auto", 3.0)

        # LÓGICA DE EMERGENCIA MANUAL
        if self.emergencia_activa:
            if self.eje_emergencia == 'NS':
                if self.estado_actual == EstadoSemaforo.VERDE_NS:
                    self.enviar_comando('1')
                    return # Mantener indefinidamente
                elif self.estado_actual in [EstadoSemaforo.VERDE_EO, EstadoSemaforo.AMARILLO_EO]:
                    self.estado_actual = EstadoSemaforo.AMARILLO_EO
                    if tiempo_transcurrido > 2.0: # Transición rápida
                        self.estado_actual = EstadoSemaforo.ROJO_TODOS_EO_NS
                        self.tiempo_ultimo_cambio = time.time()
                elif self.estado_actual == EstadoSemaforo.ROJO_TODOS_EO_NS:
                    if tiempo_transcurrido > 1.0:
                        self.estado_actual = EstadoSemaforo.VERDE_NS
                        self.tiempo_ultimo_cambio = time.time()
                else:
                    self.estado_actual = EstadoSemaforo.ROJO_TODOS_NS_EO
                    self.tiempo_ultimo_cambio = time.time() - self.TIEMPO_ROJO_TODOS # forzar cambio rápido
            
            elif self.eje_emergencia == 'EO':
                if self.estado_actual == EstadoSemaforo.VERDE_EO:
                    self.enviar_comando('3')
                    return
                elif self.estado_actual in [EstadoSemaforo.VERDE_NS, EstadoSemaforo.AMARILLO_NS]:
                    self.estado_actual = EstadoSemaforo.AMARILLO_NS
                    if tiempo_transcurrido > 2.0:
                        self.estado_actual = EstadoSemaforo.ROJO_TODOS_NS_EO
                        self.tiempo_ultimo_cambio = time.time()
                elif self.estado_actual == EstadoSemaforo.ROJO_TODOS_NS_EO:
                    if tiempo_transcurrido > 1.0:
                        self.estado_actual = EstadoSemaforo.VERDE_EO
                        self.tiempo_ultimo_cambio = time.time()
                else:
                    self.estado_actual = EstadoSemaforo.ROJO_TODOS_EO_NS
                    self.tiempo_ultimo_cambio = time.time() - self.TIEMPO_ROJO_TODOS
            return

        # LÓGICA NORMAL (Con horario)
        if self.tiempo_sin_autos_inicio is not None:
            if time.time() - self.tiempo_sin_autos_inicio > self.TIEMPO_REPOSO:
                if self.estado_actual not in [EstadoSemaforo.VERDE_NS, EstadoSemaforo.AMARILLO_EO, EstadoSemaforo.ROJO_TODOS_EO_NS]:
                    self.estado_actual = EstadoSemaforo.AMARILLO_EO
                    self.tiempo_ultimo_cambio = time.time()

        if self.estado_actual == EstadoSemaforo.VERDE_NS:
            self.enviar_comando('1')
            tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, autos_NS * factor))
            if autos_EO > 0 and tiempo_transcurrido > tiempo_minimo_actual:
                if autos_NS == 0 or tiempo_transcurrido >= tiempo_asignado:
                    self.estado_actual = EstadoSemaforo.AMARILLO_NS
                    self.tiempo_ultimo_cambio = time.time()
        
        elif self.estado_actual == EstadoSemaforo.AMARILLO_NS:
            self.enviar_comando('2')
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self.estado_actual = EstadoSemaforo.ROJO_TODOS_NS_EO
                self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo.ROJO_TODOS_NS_EO:
            self.enviar_comando('5')
            if tiempo_transcurrido > self.TIEMPO_ROJO_TODOS:
                self.estado_actual = EstadoSemaforo.VERDE_EO
                self.tiempo_ultimo_cambio = time.time()

        elif self.estado_actual == EstadoSemaforo.VERDE_EO:
            self.enviar_comando('3')
            tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, autos_EO * factor))
            if autos_NS > 0 and tiempo_transcurrido > tiempo_minimo_actual:
                if autos_EO == 0 or tiempo_transcurrido >= tiempo_asignado:
                    self.estado_actual = EstadoSemaforo.AMARILLO_EO
                    self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo.AMARILLO_EO:
            self.enviar_comando('4')
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self.estado_actual = EstadoSemaforo.ROJO_TODOS_EO_NS
                self.tiempo_ultimo_cambio = time.time()

        elif self.estado_actual == EstadoSemaforo.ROJO_TODOS_EO_NS:
            self.enviar_comando('5')
            if tiempo_transcurrido > self.TIEMPO_ROJO_TODOS:
                self.estado_actual = EstadoSemaforo.VERDE_NS
                self.tiempo_ultimo_cambio = time.time()

    def _dibujar_interfaz(self, frame, autos):
        cv2.rectangle(frame, (self.ZONA_N[0], self.ZONA_N[1]), (self.ZONA_N[2], self.ZONA_N[3]), self.COLORES["zona_n"], 2)
        cv2.rectangle(frame, (self.ZONA_S[0], self.ZONA_S[1]), (self.ZONA_S[2], self.ZONA_S[3]), self.COLORES["zona_s"], 2)
        cv2.rectangle(frame, (self.ZONA_E[0], self.ZONA_E[1]), (self.ZONA_E[2], self.ZONA_E[3]), self.COLORES["zona_e"], 2)
        cv2.rectangle(frame, (self.ZONA_O[0], self.ZONA_O[1]), (self.ZONA_O[2], self.ZONA_O[3]), self.COLORES["zona_o"], 2)
        
        font_scale = max(0.5, self.w / 1200)
        thickness = max(1, int(self.w / 400))
        
        # UI Top Bar
        cv2.rectangle(frame, (0, 0), (self.w, max(45, int(self.h * 0.08))), (20, 20, 20), -1)
        tiempo_transcurrido = time.time() - self.tiempo_ultimo_cambio
        texto_estado = "ESTADO: DESCONOCIDO"
        color_estado = (255, 255, 255)
        
        autos_NS = max(autos['N'], autos['S'])
        autos_EO = max(autos['E'], autos['O'])
        factor = self.config.get("traffic_light", {}).get("factor_tiempo_por_auto", 3.0)
        tiempo_min_verde_actual = self._check_modo_noche()

        if self.estado_actual == EstadoSemaforo.VERDE_NS:
            t_asig = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_min_verde_actual, autos_NS * factor))
            texto_estado = f"VERDE N-S [{int(tiempo_transcurrido)}s/{int(t_asig)}s]" if not self.emergencia_activa else "VERDE N-S [EMERGENCIA]"
            color_estado = self.COLORES["verde"]
        elif self.estado_actual == EstadoSemaforo.AMARILLO_NS:
            texto_estado = f"AMARILLO N-S [{int(tiempo_transcurrido)}s/{int(self.TIEMPO_AMARILLO)}s]"
            color_estado = self.COLORES["amarillo"]
        elif self.estado_actual in [EstadoSemaforo.ROJO_TODOS_NS_EO, EstadoSemaforo.ROJO_TODOS_EO_NS]:
            texto_estado = f"TODO ROJO [{int(tiempo_transcurrido)}s/{int(self.TIEMPO_ROJO_TODOS)}s]"
            color_estado = self.COLORES["rojo"]
        elif self.estado_actual == EstadoSemaforo.VERDE_EO:
            t_asig = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_min_verde_actual, autos_EO * factor))
            texto_estado = f"VERDE E-O [{int(tiempo_transcurrido)}s/{int(t_asig)}s]" if not self.emergencia_activa else "VERDE E-O [EMERGENCIA]"
            color_estado = self.COLORES["verde"]
        elif self.estado_actual == EstadoSemaforo.AMARILLO_EO:
            texto_estado = f"AMARILLO E-O [{int(tiempo_transcurrido)}s/{int(self.TIEMPO_AMARILLO)}s]"
            color_estado = self.COLORES["amarillo"]

        cv2.putText(frame, texto_estado, (int(self.w * 0.02), int(self.h * 0.05)), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.1, color_estado, thickness + 1)

        # Draw Mode (Normal/Noche/Emergencia)
        mode_color = (0, 0, 255) if self.emergencia_activa else ((255, 200, 0) if "Noche" in self.modo_actual else (200, 200, 200))
        cv2.putText(frame, f"MODO: {self.modo_actual}", (int(self.w * 0.65), int(self.h * 0.05)), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.9, mode_color, thickness)

        y_base = int(self.h * 0.8)
        cv2.putText(frame, f"Norte: {autos['N']}", (10, y_base), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.COLORES["zona_n"], thickness)
        cv2.putText(frame, f"Sur: {autos['S']}", (10, y_base + 25), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.COLORES["zona_s"], thickness)
        cv2.putText(frame, f"Este: {autos['E']}", (10, y_base + 50), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.COLORES["zona_e"], thickness)
        cv2.putText(frame, f"Oeste: {autos['O']}", (10, y_base + 75), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.COLORES["zona_o"], thickness)
        
        cv2.putText(frame, f"FPS: {self.current_fps:.1f}", (int(self.w*0.80), int(self.h * 0.95)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)

class App:
    def __init__(self, root):
        self.ventana = root
        self.ventana.title("FLUXA - Control Vial 4 Vías (Modo CPU + API)")
        self.ventana.geometry("1100x700")
        self.ventana.configure(bg="#0f172a")
        self.ventana.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.controller = SemaforoController()
        self.video_loop_id = None

        self.fuente_logo = font.Font(family="Segoe UI", size=18, weight="bold")
        self.fuente_titulo = font.Font(family="Segoe UI", size=26, weight="bold")
        self.VERDE_BRILLANTE = "#10b981"
        self.TEXTO_GRIS_BASE = "#94a3b8"

        self._crear_header()
        self._crear_pantalla_inicio()
        self._crear_pantalla_monitoreo()

        self.pantalla_inicio.pack(fill="both", expand=True)
        
        # Atajos de Teclado Globales para Emergencia
        self.ventana.bind('<KeyPress-n>', self.on_key_n)
        self.ventana.bind('<KeyPress-N>', self.on_key_n)
        self.ventana.bind('<KeyPress-e>', self.on_key_e)
        self.ventana.bind('<KeyPress-E>', self.on_key_e)
        self.ventana.bind('<KeyPress-r>', self.on_key_r) # Reset Normal
        self.ventana.bind('<KeyPress-R>', self.on_key_r)

    def on_key_n(self, event):
        if self.controller.running:
            print(" EMERGENCIA NORTE-SUR ACTIVADA")
            self.controller.forzar_emergencia('NS')
            
    def on_key_e(self, event):
        if self.controller.running:
            print(" EMERGENCIA ESTE-OESTE ACTIVADA")
            self.controller.forzar_emergencia('EO')
            
    def on_key_r(self, event):
        if self.controller.running:
            print(" VOLVIENDO A MODO NORMAL")
            self.controller.emergencia_activa = False

    def _crear_header(self):
        header = tk.Frame(self.ventana, bg="#020617", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        logo_contenedor = tk.Frame(header, bg="#020617")
        logo_contenedor.pack(side="left", padx=25, pady=15)
        lbl_logo = tk.Label(logo_contenedor, text="FLUXA SMART CITY (CPU)", fg=self.VERDE_BRILLANTE, bg="#020617", font=self.fuente_logo)
        lbl_logo.pack(side="left")

    def _crear_pantalla_inicio(self):
        self.pantalla_inicio = tk.Frame(self.ventana, bg="#0f172a")
        hero_contenedor = tk.Frame(self.pantalla_inicio, bg="#0f172a")
        hero_contenedor.pack(fill="x", pady=(50, 20))
        
        lbl_titulo = tk.Label(hero_contenedor, text="Centro de Control de Tráfico", fg="#ffffff", bg="#0f172a", font=self.fuente_titulo)
        lbl_titulo.pack(pady=(0, 15))
        btn_control = tk.Button(hero_contenedor, text="Ver Panel de Control", fg="#020617", bg=self.VERDE_BRILLANTE,
                                font=("Segoe UI", 12, "bold"), padx=30, pady=12, bd=0, cursor="hand2",
                                command=self.ir_al_panel_de_control)
        btn_control.pack()

    def _crear_pantalla_monitoreo(self):
        self.pantalla_monitoreo = tk.Frame(self.ventana, bg="#0f172a")
        
        controls_frame = tk.Frame(self.pantalla_monitoreo, bg="#0f172a")
        controls_frame.pack(fill="x", padx=40, pady=10)
        
        lbl_titulo_monitoreo = tk.Label(controls_frame, text=" MONITOREO EN VIVO", fg="#ffffff", bg="#0f172a", font=("Segoe UI", 16, "bold"))
        lbl_titulo_monitoreo.pack(side="left")
        
        lbl_hints = tk.Label(controls_frame, text="Presiona [N] Emergencia N-S | [E] Emergencia E-O | [R] Normalizar", fg="#ef4444", bg="#0f172a", font=("Segoe UI", 10, "bold"))
        lbl_hints.pack(side="right")

        contenedor_camaras = tk.Frame(self.pantalla_monitoreo, bg="#0f172a")
        contenedor_camaras.pack(fill="both", expand=True, padx=40, pady=5)
        contenedor_camaras.columnconfigure(0, weight=1)
        
        self.video_label = tk.Label(contenedor_camaras, bg="#020617")
        self.video_label.grid(row=0, column=0, sticky="nsew")

        btn_regresar = tk.Button(self.pantalla_monitoreo, text=" Cerrar ", fg="#ffffff", bg="#334155",
                                 font=("Segoe UI", 10, "bold"), padx=15, pady=6, bd=0, command=self.ir_al_inicio)
        btn_regresar.pack(pady=10)

    def ir_al_panel_de_control(self):
        self.pantalla_inicio.pack_forget()
        self.pantalla_monitoreo.pack(fill="both", expand=True)
        self.controller.start()
        self.update_video_feed()
        self.ventana.focus_set() # Para recibir teclas

    def ir_al_inicio(self):
        if self.video_loop_id:
            self.ventana.after_cancel(self.video_loop_id)
            self.video_loop_id = None
        self.controller.stop()
        self.pantalla_monitoreo.pack_forget()
        self.pantalla_inicio.pack(fill="both", expand=True)
        self.video_label.config(image='')

    def update_video_feed(self):
        frame = self.controller.process_frame()
        if frame is not None:
            h, w, _ = frame.shape
            max_h, max_w = 500, 880
            scale = min(max_w/w, max_h/h)
            nw, nh = int(w*scale), int(h*scale)
            frame = cv2.resize(frame, (nw, nh))

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        if self.controller.running:
            self.video_loop_id = self.ventana.after(15, self.update_video_feed)

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Cerrar sistema?"):
            self.controller.stop()
            self.ventana.destroy()

if __name__ == "__main__":
    ventana = tk.Tk()
    app = App(ventana)
    ventana.mainloop()
