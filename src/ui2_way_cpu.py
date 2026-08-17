import os
import time
from enum import Enum
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import cv2
from ultralytics import YOLO

from core_semaforo import CoreSemaforoBase

class EstadoSemaforo2V(Enum):
    VERDE_A = 1
    AMARILLO_A = 2
    ROJO_TODOS_1 = 3
    VERDE_B = 4
    AMARILLO_B = 5
    ROJO_TODOS_2 = 6

class SemaforoController2V_CPU(CoreSemaforoBase):
    def __init__(self, port=None, video_source=None):
        super().__init__(topology_name="2_way", backend_name="CPU", port=port, video_source=video_source)
        self.estado_actual = EstadoSemaforo2V.VERDE_A

    def _init_model(self):
        model_name = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt")
        model_path = model_name
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'models', model_name),
            os.path.join(os.path.dirname(__file__), '..', model_name),
            model_name
        ]
        for p in possible_paths:
            if os.path.exists(p):
                model_path = p
                break
        print(f"📦 Cargando modelo YOLO en CPU para 2 Vías: {model_path}")
        self.model = YOLO(model_path)

    def _predict(self, frame):
        results = self.model.predict(source=frame, classes=self.CLASES_VEHICULOS, conf=self.CONF_THRESH, verbose=False)
        if len(results) > 0 and len(results[0].boxes) > 0:
            return results[0].boxes.data.cpu().numpy()
        return None

    def _procesar_logica_semaforo(self, autos, tiempo_minimo_actual):
        tiempo_transcurrido = time.time() - self.tiempo_ultimo_cambio
        autos_a = autos.get('zona_a', 0)
        autos_b = autos.get('zona_b', 0)
        
        demanda_a = max(autos_a, self.last_demanda_ponderada.get('zona_a', 0.0))
        demanda_b = max(autos_b, self.last_demanda_ponderada.get('zona_b', 0.0))
        
        factor = self.config.get("traffic_light", {}).get("factor_tiempo_por_auto", 3.0)

        if self.emergencia_activa:
            if self.eje_emergencia in ['A', 'ZONA_A', 'NS']:
                if self.estado_actual != EstadoSemaforo2V.VERDE_A:
                    self.estado_actual = EstadoSemaforo2V.VERDE_A
                    self.enviar_comando('1')
            elif self.eje_emergencia in ['B', 'ZONA_B', 'EO']:
                if self.estado_actual != EstadoSemaforo2V.VERDE_B:
                    self.estado_actual = EstadoSemaforo2V.VERDE_B
                    self.enviar_comando('3')
            return

        if self.estado_actual == EstadoSemaforo2V.VERDE_A:
            self.enviar_comando('1')
            self.fase_tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, demanda_a * factor))
            if autos_b > 0 and tiempo_transcurrido > tiempo_minimo_actual:
                if autos_a == 0 or tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self.estado_actual = EstadoSemaforo2V.AMARILLO_A
                    self.tiempo_ultimo_cambio = time.time()
                    
        elif self.estado_actual == EstadoSemaforo2V.AMARILLO_A:
            self.enviar_comando('2')
            self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self.estado_actual = EstadoSemaforo2V.ROJO_TODOS_1
                self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo2V.ROJO_TODOS_1:
            self.enviar_comando('5')
            self.fase_tiempo_asignado = self.TIEMPO_ROJO_TODOS
            if tiempo_transcurrido > self.TIEMPO_ROJO_TODOS:
                self.estado_actual = EstadoSemaforo2V.VERDE_B
                self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo2V.VERDE_B:
            self.enviar_comando('3')
            self.fase_tiempo_asignado = min(self.TIEMPO_MAXIMO_VERDE, max(tiempo_minimo_actual, demanda_b * factor))
            if autos_a > 0 and tiempo_transcurrido > tiempo_minimo_actual:
                if autos_b == 0 or tiempo_transcurrido >= self.fase_tiempo_asignado:
                    self.estado_actual = EstadoSemaforo2V.AMARILLO_B
                    self.tiempo_ultimo_cambio = time.time()
                    
        elif self.estado_actual == EstadoSemaforo2V.AMARILLO_B:
            self.enviar_comando('4')
            self.fase_tiempo_asignado = self.TIEMPO_AMARILLO
            if tiempo_transcurrido > self.TIEMPO_AMARILLO:
                self.estado_actual = EstadoSemaforo2V.ROJO_TODOS_2
                self.tiempo_ultimo_cambio = time.time()
                
        elif self.estado_actual == EstadoSemaforo2V.ROJO_TODOS_2:
            self.enviar_comando('5')
            self.fase_tiempo_asignado = self.TIEMPO_ROJO_TODOS
            if tiempo_transcurrido > self.TIEMPO_ROJO_TODOS:
                self.estado_actual = EstadoSemaforo2V.VERDE_A
                self.tiempo_ultimo_cambio = time.time()

    def _dibujar_interfaz_topologia(self, frame, autos):
        pass

class App2V_CPU:
    def __init__(self, root, video_source=None):
        self.ventana = root
        self.ventana.title("FLUXA - Avenida 2 Vías (CPU)")
        self.ventana.geometry("1100x750")
        self.ventana.configure(bg="#0f172a")
        self.ventana.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.controller = SemaforoController2V_CPU(video_source=video_source)
        self.video_loop_id = None
        self._crear_ui()
        
    def _crear_ui(self):
        header = tk.Frame(self.ventana, bg="#020617", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="FLUXA - CONTROL 2 VÍAS / AVENIDA (CPU)", fg="#10b981", bg="#020617", font=("Segoe UI", 18, "bold")).pack(side="left", padx=25, pady=15)
        
        self.video_label = tk.Label(self.ventana, bg="#000")
        self.video_label.pack(fill="both", expand=True, padx=40, pady=15)
        
        btn_bar = tk.Frame(self.ventana, bg="#0f172a")
        btn_bar.pack(pady=10)
        
        tk.Button(btn_bar, text=" INICIAR OPERACIÓN ", bg="#10b981", font=("Segoe UI", 11, "bold"), command=self.iniciar).pack(side="left", padx=8)
        tk.Button(btn_bar, text=" 📹 CÁMARA EN VIVO ", bg="#3b82f6", fg="white", font=("Segoe UI", 11, "bold"), command=self.usar_camara).pack(side="left", padx=8)
        tk.Button(btn_bar, text=" 🎬 CARGAR VIDEO DEMO ", bg="#f59e0b", fg="black", font=("Segoe UI", 11, "bold"), command=self.cargar_video).pack(side="left", padx=8)

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
    app = App2V_CPU(v)
    v.mainloop()
