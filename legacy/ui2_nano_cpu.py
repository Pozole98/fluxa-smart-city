# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
import os
import sys
import tkinter as tk
from tkinter import font, messagebox
import cv2
import serial
import time
from enum import Enum
import numpy as np
from PIL import Image, ImageTk
import threading
import json
from types import SimpleNamespace

from ultralytics import YOLO
from ultralytics.trackers.byte_tracker import BYTETracker

# Importar módulos industriales (Subir un nivel ya que estamos en /legacy)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from videostream import VideoStream
from analytics import TrafficAnalyticsLogger
from api_server import TelemetryAPI

class EstadoSemaforo2V(Enum):
    VERDE_A = 1
    AMARILLO_A = 2
    VERDE_B = 3
    AMARILLO_B = 4
    EMERGENCIA = 5

class SemaforoController2Vias:
    def __init__(self):
        print("⏳ Inicializando controlador 2 vías (MODO CPU)...")
        self.arduino = None
        self.cap = None
        self.config = self._load_config()
        
        # Buscar modelo (Priorizar .pt)
        model_path = 'yolov8n.pt'
        posible = os.path.join(os.path.dirname(__file__), '..', 'models', 'yolov8n.pt')
        if os.path.exists(posible):
            model_path = posible
            
        print(f" Cargando modelo YOLO nativo en CPU desde: {model_path}")
        self.model = YOLO(model_path)
            
        args = SimpleNamespace(
            track_high_thresh=self.config["tracker"]["track_high_thresh"], 
            track_low_thresh=self.config["tracker"]["track_low_thresh"], 
            new_track_thresh=self.config["tracker"]["new_track_thresh"], 
            track_buffer=self.config["tracker"]["track_buffer"], 
            match_thresh=self.config["tracker"]["match_thresh"], 
            gmc_method='sparseOptFlow',
            fuse_score=False
        )
        self.tracker = BYTETracker(args)
        
        self.estado_actual = EstadoSemaforo2V.VERDE_A
        self.tiempo_ultimo_cambio = time.time()
        self.ultimo_comando = None
        self.running = False
        
        self.modo_actual = "Normal"
        self.emergencia_activa = False
        self.eje_emergencia = None
        
        self.frame_count = 0
        self.last_autos = {'A': 0, 'B': 0}
        self.autos_history = []
        
        self.w, self.h = 640, 480 

        cfg_tl = self.config.get("traffic_light", {})
        self.TIEMPO_MINIMO_VERDE = cfg_tl.get("tiempo_minimo_verde", 5.0)
        self.TIEMPO_MAXIMO_VERDE = cfg_tl.get("tiempo_maximo_verde", 45.0)
        self.TIEMPO_AMARILLO = cfg_tl.get("tiempo_amarillo", 3.0)
        
        self.CLASES_VEHICULOS = self.config.get("ai_model", {}).get("classes_to_detect", [2,3,5,7])
        self.CONF_THRESH = self.config.get("ai_model", {}).get("confidence_threshold", 0.35)
        
        self.COLORES = {
            "zona_a": (255, 100, 100), "zona_b": (100, 255, 100)
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
            self.eje_emergencia = 'A'
            self.modo_actual = "EMERGENCIA (A)"
        elif action == "EO":
            self.emergencia_activa = True
            self.eje_emergencia = 'B'
            self.modo_actual = "EMERGENCIA (B)"
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
        except Exception:
            return {
                "system": {"camera_index": 0, "serial_port": "/dev/ttyACM0", "serial_baudrate": 9600, "log_analytics": False},
                "traffic_light": {"tiempo_minimo_verde": 5.0, "tiempo_maximo_verde": 45.0, "tiempo_amarillo": 3.0, "factor_tiempo_por_auto": 3.0},
                "ai_model": {"confidence_threshold": 0.35, "classes_to_detect": [2, 3, 5, 7]},
                "tracker": {"track_high_thresh": 0.4, "track_low_thresh": 0.05, "new_track_thresh": 0.5, "track_buffer": 120, "match_thresh": 0.8},
                "zones": {"2_way": {"zona_a": [0.0, 0.4, 0.45, 0.95], "zona_b": [0.5, 0.4, 1.0, 0.95]}}
            }

    def start(self):
        self.running = True
        threading.Thread(target=self._init_arduino, daemon=True).start()
        cam_idx = self.config["system"]["camera_index"]
        self.cap = VideoStream(src=cam_idx).start()
        time.sleep(1.0)
        self.estado_actual = EstadoSemaforo2V.VERDE_A
        self.tiempo_ultimo_cambio = time.time()

    def _init_arduino(self):
        port = self.config["system"]["serial_port"]
        baud = self.config["system"]["serial_baudrate"]
        try:
            self.arduino = serial.Serial(port=port, baudrate=baud, timeout=0.1)
            time.sleep(2)
            print("Arduino conectado.")
        except Exception:
            self.arduino = None

    def stop(self):
        self.running = False
        if self.cap: self.cap.stop()
        if self.arduino: self.arduino.close()

    def enviar_comando(self, comando):
        if self.arduino and comando != self.ultimo_comando:
            try:
                self.arduino.write(comando.encode())
                self.ultimo_comando = comando
            except Exception:
                pass

    def process_frame(self):
        if not self.running or not self.cap:
            return None

        ret, frame = self.cap.read()
        
        if not ret or self.cap.failed:
            self.enviar_comando('5') # Asumimos '5' es todo rojo o parpadeo
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            cv2.putText(frame, "MODO SEGURO - CAMARA PERDIDA", (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            time.sleep(0.5)
            return frame

        self.h, self.w = frame.shape[:2]

        za = self.config.get("zones", {}).get("2_way", {}).get("zona_a", [0.0, 0.4, 0.45, 0.95])
        zb = self.config.get("zones", {}).get("2_way", {}).get("zona_b", [0.5, 0.4, 1.0, 0.95])
        
        self.ZONA_A = (int(self.w * za[0]), int(self.h * za[1]), int(self.w * za[2]), int(self.h * za[3]))
        self.ZONA_B = (int(self.w * zb[0]), int(self.h * zb[1]), int(self.w * zb[2]), int(self.h * zb[3]))

        autos_raw = self._detectar_vehiculos(frame)
        self.autos_history.append(autos_raw)
        if len(self.autos_history) > 5: self.autos_history.pop(0)
        autos = {k: max([h[k] for h in self.autos_history]) for k in autos_raw}

        self._actualizar_logica(autos)
        self._dibujar_interfaz(frame, autos)

        # Update API (mapeando A->N y B->E para dashboard genérico)
        cam_ok = not self.cap.failed
        ard_ok = self.arduino is not None
        log_data = {'N': autos['A'], 'S': 0, 'E': autos['B'], 'O': 0}
        self.api.update_state(self.estado_actual.name, log_data, 0.0, self.modo_actual, ard_ok, cam_ok)

        if time.time() - self.ultimo_log_time >= 10.0:
            # Reusamos logger pero mapeando 'N'->'A' y 'S'->'B' para la estructura actual del logger
            log_data = {'N': autos['A'], 'S': autos['B'], 'E': 0, 'O': 0}
            self.logger.log_state(self.estado_actual.name, log_data)
            self.ultimo_log_time = time.time()

        return frame

    def _detectar_vehiculos(self, frame):
        autos = {'A': 0, 'B': 0}
        results = self.model.predict(frame, conf=self.CONF_THRESH, classes=self.CLASES_VEHICULOS, verbose=False)
        
        if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
            tracks = self.tracker.update(results[0].boxes, frame)
            for track in tracks:
                x1, y1, x2, y2, track_id, conf, cls, *_ = track
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                
                if self.ZONA_A[0] < cx < self.ZONA_A[2] and self.ZONA_A[1] < cy < self.ZONA_A[3]:
                    autos['A'] += 1
                elif self.ZONA_B[0] < cx < self.ZONA_B[2] and self.ZONA_B[1] < cy < self.ZONA_B[3]:
                    autos['B'] += 1
                    
        return autos

    def _actualizar_logica(self, autos):
        tiempo_transcurrido = time.time() - self.tiempo_ultimo_cambio
        factor = self.config.get("traffic_light", {}).get("factor_tiempo_por_auto", 3.0)

        if self.emergencia_activa:
            if self.eje_emergencia == 'A':
                if self.estado_actual == EstadoSemaforo2V.VERDE_A:
                    self.enviar_comando('1')
                else:
                    self.estado_actual = EstadoSemaforo2V.VERDE_A
                    self.tiempo_ultimo_cambio = time.time()
            elif self.eje_emergencia == 'B':
                if self.estado_actual == EstadoSemaforo2V.VERDE_B:
                    self.enviar_comando('3')
                else:
                    self.estado_actual = EstadoSemaforo2V.VERDE_B
                    self.tiempo_ultimo_cambio = time.time()
            return

        if self.estado_actual == EstadoSemaforo2V.VERDE_A:
            self.enviar_comando('1')
            tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(self.TIEMPO_MINIMO_VERDE, autos['A'] * factor))
            if autos['B'] > 0 and tiempo_transcurrido > self.TIEMPO_MINIMO_VERDE:
                if autos['A'] == 0 or tiempo_transcurrido >= tiempo_asignado:
                    self.estado_actual = EstadoSemaforo2V.AMARILLO_A
                    self.tiempo_ultimo_cambio = time.time()
        
        elif self.estado_actual == EstadoSemaforo2V.AMARILLO_A:
            self.enviar_comando('2')
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self.estado_actual = EstadoSemaforo2V.VERDE_B
                self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo2V.VERDE_B:
            self.enviar_comando('3')
            tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(self.TIEMPO_MINIMO_VERDE, autos['B'] * factor))
            if autos['A'] > 0 and tiempo_transcurrido > self.TIEMPO_MINIMO_VERDE:
                if autos['B'] == 0 or tiempo_transcurrido >= tiempo_asignado:
                    self.estado_actual = EstadoSemaforo2V.AMARILLO_B
                    self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo2V.AMARILLO_B:
            self.enviar_comando('4')
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self.estado_actual = EstadoSemaforo2V.VERDE_A
                self.tiempo_ultimo_cambio = time.time()

    def _dibujar_interfaz(self, frame, autos):
        cv2.rectangle(frame, (self.ZONA_A[0], self.ZONA_A[1]), (self.ZONA_A[2], self.ZONA_A[3]), self.COLORES["zona_a"], 2)
        cv2.rectangle(frame, (self.ZONA_B[0], self.ZONA_B[1]), (self.ZONA_B[2], self.ZONA_B[3]), self.COLORES["zona_b"], 2)
        
        font_scale = max(0.5, self.w / 1200)
        thickness = max(1, int(self.w / 400))
        
        # UI Top Bar
        cv2.rectangle(frame, (0, 0), (self.w, max(45, int(self.h * 0.08))), (20, 20, 20), -1)
        tiempo_transcurrido = time.time() - self.tiempo_ultimo_cambio
        texto_estado = "ESTADO: DESCONOCIDO"
        color_estado = (255, 255, 255)
        
        factor = self.config.get("traffic_light", {}).get("factor_tiempo_por_auto", 3.0)
        
        if self.estado_actual == EstadoSemaforo2V.VERDE_A:
            t_asig = min(self.TIEMPO_MAXIMO_VERDE, max(self.TIEMPO_MINIMO_VERDE, autos['A'] * factor))
            texto_estado = f"VERDE A [{int(tiempo_transcurrido)}s/{int(t_asig)}s]" if not self.emergencia_activa else "VERDE A [EMERGENCIA]"
            color_estado = (16, 185, 129)
        elif self.estado_actual == EstadoSemaforo2V.AMARILLO_A:
            texto_estado = f"AMARILLO A [{int(tiempo_transcurrido)}s/{int(self.TIEMPO_AMARILLO)}s]"
            color_estado = (255, 200, 0)
        elif self.estado_actual == EstadoSemaforo2V.VERDE_B:
            t_asig = min(self.TIEMPO_MAXIMO_VERDE, max(self.TIEMPO_MINIMO_VERDE, autos['B'] * factor))
            texto_estado = f"VERDE B [{int(tiempo_transcurrido)}s/{int(t_asig)}s]" if not self.emergencia_activa else "VERDE B [EMERGENCIA]"
            color_estado = (16, 185, 129)
        elif self.estado_actual == EstadoSemaforo2V.AMARILLO_B:
            texto_estado = f"AMARILLO B [{int(tiempo_transcurrido)}s/{int(self.TIEMPO_AMARILLO)}s]"
            color_estado = (255, 200, 0)

        cv2.putText(frame, texto_estado, (int(self.w * 0.02), int(self.h * 0.05)), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.1, color_estado, thickness + 1)

        # Draw Mode
        mode_color = (0, 0, 255) if self.emergencia_activa else (200, 200, 200)
        cv2.putText(frame, f"MODO: {self.modo_actual}", (int(self.w * 0.65), int(self.h * 0.05)), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.9, mode_color, thickness)

        y_base = int(self.h * 0.8)
        cv2.putText(frame, f"Zona A (Principal): {autos['A']}", (10, y_base), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.COLORES["zona_a"], thickness)
        cv2.putText(frame, f"Zona B (Secundaria): {autos['B']}", (10, y_base + 25), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.COLORES["zona_b"], thickness)

class EstadoSemaforo2V(Enum):
    VERDE_A = 1
    AMARILLO_A = 2
    VERDE_B = 3
    AMARILLO_B = 4

class App:
    def __init__(self, root):
        self.ventana = root
        self.ventana.title("FLUXA - Control Vial 2 Vías (Modo CPU + API)")
        self.ventana.geometry("1100x700")
        self.ventana.configure(bg="#0f172a")
        self.ventana.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.controller = SemaforoController2Vias()
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
            print("EMERGENCIA ZONA A ACTIVADA")
            self.controller.emergencia_activa = True
            self.controller.eje_emergencia = 'A'
            self.controller.modo_actual = "EMERGENCIA (A)"
            
    def on_key_e(self, event):
        if self.controller.running:
            print("EMERGENCIA ZONA B ACTIVADA")
            self.controller.emergencia_activa = True
            self.controller.eje_emergencia = 'B'
            self.controller.modo_actual = "EMERGENCIA (B)"
            
    def on_key_r(self, event):
        if self.controller.running:
            print("VOLVIENDO A MODO NORMAL")
            self.controller.emergencia_activa = False
            self.controller.modo_actual = "Normal"

    def _crear_header(self):
        header = tk.Frame(self.ventana, bg="#020617", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        logo_contenedor = tk.Frame(header, bg="#020617")
        logo_contenedor.pack(side="left", padx=25, pady=15)
        lbl_logo = tk.Label(logo_contenedor, text="FLUXA SMART CITY (CPU - 2 VIAS)", fg=self.VERDE_BRILLANTE, bg="#020617", font=self.fuente_logo)
        lbl_logo.pack(side="left")

    def _crear_pantalla_inicio(self):
        self.pantalla_inicio = tk.Frame(self.ventana, bg="#0f172a")
        hero_contenedor = tk.Frame(self.pantalla_inicio, bg="#0f172a")
        hero_contenedor.pack(fill="x", pady=(50, 20))
        
        lbl_titulo = tk.Label(hero_contenedor, text="Centro de Control de Trafico (2 Vias)", fg="#ffffff", bg="#0f172a", font=self.fuente_titulo)
        lbl_titulo.pack(pady=(0, 15))
        btn_control = tk.Button(hero_contenedor, text="Ver Panel de Control", fg="#020617", bg=self.VERDE_BRILLANTE,
                                font=("Segoe UI", 12, "bold"), padx=30, pady=12, bd=0, cursor="hand2",
                                command=self.ir_al_panel_de_control)
        btn_control.pack()

    def _crear_pantalla_monitoreo(self):
        self.pantalla_monitoreo = tk.Frame(self.ventana, bg="#0f172a")
        
        controls_frame = tk.Frame(self.pantalla_monitoreo, bg="#0f172a")
        controls_frame.pack(fill="x", padx=40, pady=10)
        
        lbl_titulo_monitoreo = tk.Label(controls_frame, text="MONITOREO EN VIVO", fg="#ffffff", bg="#0f172a", font=("Segoe UI", 16, "bold"))
        lbl_titulo_monitoreo.pack(side="left")
        
        lbl_hints = tk.Label(controls_frame, text="Presiona [N] Emergencia Zona A | [E] Emergencia Zona B | [R] Normalizar", fg="#ef4444", bg="#0f172a", font=("Segoe UI", 10, "bold"))
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
        if messagebox.askokcancel("Salir", "Cerrar sistema?"):
            self.controller.stop()
            self.ventana.destroy()

if __name__ == "__main__":
    ventana = tk.Tk()
    app = App(ventana)
    ventana.mainloop()
