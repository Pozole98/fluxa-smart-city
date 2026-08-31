# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Controlador y GUI para Intersección de 4 Vías (Motor NPU RKNN)
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

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

from core_semaforo_rknn import CoreSemaforoRKNN

class EstadoSemaforo4V(Enum):
    VERDE_NS = 1
    AMARILLO_NS = 2
    ROJO_TODOS_1 = 3
    VERDE_EO = 4
    AMARILLO_EO = 5
    ROJO_TODOS_2 = 6

class SemaforoController4V_RKNN(CoreSemaforoRKNN):
    def __init__(self, port=None, video_source=None, npu_core_id=None):
        super().__init__(topology_name="4_way", port=port, video_source=video_source, npu_core_id=npu_core_id)
        self.estado_actual = EstadoSemaforo4V.VERDE_NS

    def _dibujar_interfaz_topologia(self, frame, autos):
        pass

class App4V_RKNN:
    def __init__(self, root, video_source=None):
        self.ventana = root
        self.ventana.title("FLUXA - Intersección 4 Vías (RKNN NPU)")
        self.ventana.geometry("1100x750")
        self.ventana.configure(bg="#0f172a")
        self.ventana.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.controller = SemaforoController4V_RKNN(video_source=video_source)
        self.video_loop_id = None
        self._crear_ui()
        
    def _crear_ui(self):
        header = tk.Frame(self.ventana, bg="#020617", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="FLUXA RKNN - INTERSECCIÓN 4 VÍAS (ORANGE PI 5)", fg="#f59e0b", bg="#020617", font=("Segoe UI", 18, "bold")).pack(side="left", padx=25, pady=15)
        
        self.video_label = tk.Label(self.ventana, bg="#000")
        self.video_label.pack(fill="both", expand=True, padx=40, pady=15)
        
        btn_bar = tk.Frame(self.ventana, bg="#0f172a")
        btn_bar.pack(pady=10)
        
        tk.Button(btn_bar, text=" INICIAR OPERACIÓN ", bg="#f59e0b", fg="black", font=("Segoe UI", 11, "bold"), command=self.iniciar).pack(side="left", padx=8)
        tk.Button(btn_bar, text=" 📹 CÁMARA EN VIVO ", bg="#3b82f6", fg="white", font=("Segoe UI", 11, "bold"), command=self.usar_camara).pack(side="left", padx=8)
        tk.Button(btn_bar, text=" 🎬 CARGAR VIDEO DEMO ", bg="#10b981", fg="black", font=("Segoe UI", 11, "bold"), command=self.cargar_video).pack(side="left", padx=8)

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
    app = App4V_RKNN(v)
    v.mainloop()
