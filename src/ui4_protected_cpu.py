# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Controlador y GUI para 4 Vías con Giro Protegido (Motor CPU PyTorch)
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import time
from enum import Enum
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    tk = None
    filedialog = None
    TKINTER_AVAILABLE = False
try:
    from PIL import Image, ImageTk
except ImportError:
    from PIL import Image
    ImageTk = None
import cv2
from ultralytics import YOLO

from core_semaforo import CoreSemaforoBase

class EstadoSemaforoProtected(Enum):
    VERDE_FRENTE = 1
    AMARILLO_FRENTE = 2
    ROJO_TODOS_1 = 3
    VERDE_GIRO = 4
    AMARILLO_GIRO = 5
    ROJO_TODOS_2 = 6

class SemaforoController4VProtected_CPU(CoreSemaforoBase):
    def __init__(self, port=None, video_source=None):
        super().__init__(topology_name="4_way_protected", backend_name="CPU", port=port, video_source=video_source)
        self.estado_actual = EstadoSemaforoProtected.VERDE_FRENTE

    def _init_model(self):
        model_name = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt")
        if model_name.endswith('.rknn'):
            model_name = model_name.rsplit('.', 1)[0] + '.pt'
        model_path = model_name
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'models', model_name),
            os.path.join(os.path.dirname(__file__), '..', model_name),
            os.path.join(os.path.dirname(__file__), '..', 'yolov8n.pt'),
            model_name
        ]
        for p in possible_paths:
            if os.path.exists(p):
                model_path = p
                break
        print(f" Cargando modelo YOLO en CPU para Giro Protegido: {model_path}")
        self.model = YOLO(model_path)

    def _predict(self, frame):
        results = self.model.predict(source=frame, classes=self.CLASES_VEHICULOS, conf=self.CONF_THRESH, verbose=False)
        if len(results) > 0 and len(results[0].boxes) > 0:
            return results[0].boxes.data.cpu().numpy()
        return None

class App4VProtected_CPU:
    def __init__(self, root, video_source=None):
        self.ventana = root
        self.ventana.title("FLUXA - Giro Protegido (CPU)")
        self.ventana.geometry("1100x750")
        self.ventana.configure(bg="#0f172a")
        self.ventana.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.controller = SemaforoController4VProtected_CPU(video_source=video_source)
        self.video_loop_id = None
        self._crear_ui()
        
    def _crear_ui(self):
        header = tk.Frame(self.ventana, bg="#020617", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="FLUXA - GIRO PROTEGIDO Y SALTO DE FASE (CPU)", fg="#10b981", bg="#020617", font=("Segoe UI", 18, "bold")).pack(side="left", padx=25, pady=15)
        
        self.video_label = tk.Label(self.ventana, bg="#000")
        self.video_label.pack(fill="both", expand=True, padx=40, pady=15)
        
        btn_bar = tk.Frame(self.ventana, bg="#0f172a")
        btn_bar.pack(pady=10)
        
        tk.Button(btn_bar, text=" INICIAR OPERACIÓN ", bg="#10b981", font=("Segoe UI", 11, "bold"), command=self.iniciar).pack(side="left", padx=8)
        tk.Button(btn_bar, text="  CÁMARA EN VIVO ", bg="#3b82f6", fg="white", font=("Segoe UI", 11, "bold"), command=self.usar_camara).pack(side="left", padx=8)
        tk.Button(btn_bar, text="  CARGAR VIDEO DEMO ", bg="#f59e0b", fg="black", font=("Segoe UI", 11, "bold"), command=self.cargar_video).pack(side="left", padx=8)

    def iniciar(self):
        self.controller.start()
        self.update_video()

    def usar_camara(self):
        self.controller.cambiar_fuente_video(0)

    def cargar_video(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos de Video", "*.mp4 *.avi *.mkv *.mov")])
        if path:
            self.controller.cambiar_fuente_video(path)

    def update_video(self):
        frame = self.controller.process_frame()
        if frame is not None:
            h, w, _ = frame.shape
            scale = min(880/w, 500/h)
            frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
            img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            self.video_label.imgtk = img
            self.video_label.configure(image=img)
        if self.controller.running:
            self.video_loop_id = self.ventana.after(15, self.update_video)

    def on_closing(self):
        self.controller.stop()
        self.ventana.destroy()

if __name__ == "__main__":
    v = tk.Tk()
    app = App4VProtected_CPU(v)
    v.mainloop()
