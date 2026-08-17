import os
import cv2
import numpy as np

def generar_video_demostracion(output_path="videos/demo_trafico_4vias.mp4", duration_sec=25, fps=30):
    """
    Genera un clip de video sintetizado en MP4 de alta calidad simulando una intersección de 4 vías
    con flujo continuo de automóviles, autobuses de transporte público y motocicletas.
    Ideal para presentaciones escolares y demostraciones de detección de objetos e IA sin cámara real.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    w, h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    total_frames = duration_sec * fps
    print(f"🎬 Generando clip de video demostrativo de tráfico ({duration_sec}s a {fps} FPS)...")

    # Definir vehículos simulados: [x, y, vx, vy, tipo, color, w_box, h_box]
    # tipo: 0=auto, 1=bus, 2=moto
    np.random.seed(42)

    class VehiculoSimulado:
        def __init__(self, direccion):
            self.direccion = direccion # 'N_S', 'S_N', 'E_O', 'O_E'
            self.tipo = np.random.choice(['auto', 'bus', 'moto', 'camion'], p=[0.55, 0.20, 0.15, 0.10])
            
            if self.tipo == 'bus':
                self.ancho, self.alto = (42, 85) if direccion in ['N_S', 'S_N'] else (85, 42)
                self.color = (30, 180, 240) # Amarillo/Naranja
            elif self.tipo == 'camion':
                self.ancho, self.alto = (40, 80) if direccion in ['N_S', 'S_N'] else (80, 40)
                self.color = (60, 60, 200) # Azul oscuro
            elif self.tipo == 'moto':
                self.ancho, self.alto = (18, 30) if direccion in ['N_S', 'S_N'] else (30, 18)
                self.color = (180, 30, 180) # Magenta
            else: # auto
                self.ancho, self.alto = (32, 55) if direccion in ['N_S', 'S_N'] else (55, 32)
                self.color = (220, 220, 220) # Plata/Blanco

            speed = np.random.uniform(2.5, 4.5)
            if direccion == 'N_S':
                self.x = w * 0.42
                self.y = -100 - np.random.uniform(0, 300)
                self.vx, self.vy = 0, speed
            elif direccion == 'S_N':
                self.x = w * 0.55
                self.y = h + 100 + np.random.uniform(0, 300)
                self.vx, self.vy = 0, -speed
            elif direccion == 'O_E':
                self.x = -100 - np.random.uniform(0, 300)
                self.y = h * 0.55
                self.vx, self.vy = speed, 0
            elif direccion == 'E_O':
                self.x = w + 100 + np.random.uniform(0, 300)
                self.y = h * 0.42
                self.vx, self.vy = -speed, 0

        def update(self):
            self.x += self.vx
            self.y += self.vy

        def draw(self, frame):
            x1 = int(self.x - self.ancho / 2)
            y1 = int(self.y - self.alto / 2)
            x2 = int(self.x + self.ancho / 2)
            y2 = int(self.y + self.alto / 2)
            
            # Sombra
            cv2.rectangle(frame, (x1+3, y1+3), (x2+3, y2+3), (20, 20, 20), -1)
            # Cuerpo del vehículo
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 40, 40), 2)
            
            # Luces / Parabrisas
            if self.vy > 0: # Bajando
                cv2.rectangle(frame, (x1+4, y1+int(self.alto*0.2)), (x2-4, y1+int(self.alto*0.4)), (80, 80, 80), -1)
                cv2.circle(frame, (x1+6, y2-4), 4, (0, 255, 255), -1)
                cv2.circle(frame, (x2-6, y2-4), 4, (0, 255, 255), -1)
            elif self.vy < 0: # Subiendo
                cv2.rectangle(frame, (x1+4, y2-int(self.alto*0.4)), (x2-4, y2-int(self.alto*0.2)), (80, 80, 80), -1)
                cv2.circle(frame, (x1+6, y1+4), 4, (0, 255, 255), -1)
                cv2.circle(frame, (x2-6, y1+4), 4, (0, 255, 255), -1)
            elif self.vx > 0: # Derecha
                cv2.rectangle(frame, (x2-int(self.ancho*0.4), y1+4), (x2-int(self.ancho*0.2), y2-4), (80, 80, 80), -1)
                cv2.circle(frame, (x2-4, y1+6), 4, (0, 255, 255), -1)
                cv2.circle(frame, (x2-4, y2-6), 4, (0, 255, 255), -1)
            elif self.vx < 0: # Izquierda
                cv2.rectangle(frame, (x1+int(self.ancho*0.2), y1+4), (x1+int(self.ancho*0.4), y2-4), (80, 80, 80), -1)
                cv2.circle(frame, (x1+4, y1+6), 4, (0, 255, 255), -1)
                cv2.circle(frame, (x1+4, y2-6), 4, (0, 255, 255), -1)

    direcciones = ['N_S', 'S_N', 'E_O', 'O_E']
    vehiculos = []
    for _ in range(12):
        d = np.random.choice(direcciones)
        vehiculos.append(VehiculoSimulado(d))

    for f_idx in range(total_frames):
        frame = np.ones((h, w, 3), dtype=np.uint8) * 35 # Fondo asfalto

        # Dibujar Intersección / Pavimento
        cv2.rectangle(frame, (int(w*0.32), 0), (int(w*0.68), h), (45, 45, 50), -1)
        cv2.rectangle(frame, (0, int(h*0.35)), (w, int(h*0.65)), (45, 45, 50), -1)

        # Líneas de carril discontinuas
        for y in range(0, h, 30):
            if y < h*0.35 or y > h*0.65:
                cv2.line(frame, (int(w*0.5), y), (int(w*0.5), y+15), (200, 200, 200), 2)
        for x in range(0, w, 30):
            if x < w*0.32 or x > w*0.68:
                cv2.line(frame, (x, int(h*0.5)), (x+15, int(h*0.5)), (200, 200, 200), 2)

        # Líneas de alto (blancas gruesas)
        cv2.line(frame, (int(w*0.32), int(h*0.35)), (int(w*0.5), int(h*0.35)), (255, 255, 255), 4) # Norte
        cv2.line(frame, (int(w*0.5), int(h*0.65)), (int(w*0.68), int(h*0.65)), (255, 255, 255), 4) # Sur
        cv2.line(frame, (int(w*0.68), int(h*0.35)), (int(w*0.68), int(h*0.5)), (255, 255, 255), 4) # Este
        cv2.line(frame, (int(w*0.32), int(h*0.5)), (int(w*0.32), int(h*0.65)), (255, 255, 255), 4) # Oeste

        # Cruce peatonal (cebras)
        for cx in range(int(w*0.34), int(w*0.66), 14):
            cv2.line(frame, (cx, int(h*0.32)), (cx+8, int(h*0.32)), (220, 220, 220), 4)
            cv2.line(frame, (cx, int(h*0.68)), (cx+8, int(h*0.68)), (220, 220, 220), 4)

        # Actualizar y dibujar vehículos
        for v in vehiculos:
            v.update()
            v.draw(frame)
            
            # Reciclar vehículo si sale de pantalla
            if v.x < -150 or v.x > w + 150 or v.y < -150 or v.y > h + 150:
                d = np.random.choice(direcciones)
                v.__init__(d)

        # Marca de agua demo
        cv2.putText(frame, "FLUXA DEMO VIDEO | SIMULACION DE TRAFICO", (15, h - 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 150), 1)

        out.write(frame)

    out.release()
    print(f"✅ Video demostrativo generado exitosamente en: {output_path}")

if __name__ == "__main__":
    generar_video_demostracion()
