# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Módulo de Ingestión de Video en Hilo Asíncrono para Cámaras USB, MIPI CSI y Archivos
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import cv2
import threading
import time
import os

VALID_VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov', '.webm', '.mpg', '.mpeg', '.m4v')


class VideoStream:
    """
    Gestor multihilo de ingestión de video continuo con control de cuadros y reconexión automática.
    Soporta flujos RTSP, dispositivos de captura V4L2 (/dev/video*), cámaras MIPI CSI y archivos locales.
    """
    def __init__(self, src=0, width=640, height=480):
        self.src = src
        self.width = width
        self.height = height
        self.is_file = self._check_if_file(self.src)
        self.target_fps = 30.0
        
        self.stream = None
        self.grabbed = False
        self.frame = None
        self.failed = False
        self.stopped = False
        self.lock = threading.RLock()
        self.thread = None

        self.stream = self._conectar_fuente()
        if self.stream is not None:
            self._configurar_stream()
            self.grabbed, self.frame = self.stream.read()
            self.failed = not self.grabbed
        else:
            self.failed = True

    def _check_if_file(self, src):
        if isinstance(src, str):
            lower = src.lower()
            if any(lower.endswith(ext) for ext in VALID_VIDEO_EXTENSIONS) and os.path.isfile(src):
                return True
        return False

    def _configurar_stream(self):
        if self.stream is not None:
            if not self.is_file:
                try:
                    self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                except Exception:
                    pass
            else:
                fps = self.stream.get(cv2.CAP_PROP_FPS)
                if fps and 5.0 <= fps <= 120.0:
                    self.target_fps = fps
                else:
                    self.target_fps = 30.0

    def _conectar_fuente(self):
        # 1. Si es archivo de video local válido
        if self.is_file:
            try:
                if os.path.exists(self.src) and os.path.getsize(self.src) > 1024:
                    cap = cv2.VideoCapture(self.src)
                    if cap.isOpened():
                        ret, test_f = cap.read()
                        if ret and test_f is not None:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            print(f"🎬 Archivo de video verificado y cargado: {self.src}")
                            return cap
                        cap.release()
            except Exception as e:
                print(f"⚠️ Error abriendo archivo de video {self.src}: {e}")

        # 2. Si es URL RTSP o HTTP
        if isinstance(self.src, str) and (self.src.startswith("rtsp://") or self.src.startswith("http://")):
            try:
                cap = cv2.VideoCapture(self.src)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        print(f"📡 Flujo de red conectado: {self.src}")
                        return cap
                    cap.release()
            except Exception:
                pass

        # 3. Cámaras de hardware
        print("🔍 Buscando cámaras disponibles (A prueba de balas)...")
        # 3.1. MIPI CSI Pipeline (Orange Pi 5)
        try:
            mipi_pipe = "v4l2src device=/dev/video11 ! video/x-raw, width=640, height=480, format=NV12 ! videoconvert ! appsink"
            cap = cv2.VideoCapture(mipi_pipe, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print("🎥 Cámara MIPI CSI detectada exitosamente.")
                    return cap
                cap.release()
        except Exception:
            pass
            
        # 3.2. Dispositivo específico si src es entero
        if isinstance(self.src, int) or (isinstance(self.src, str) and self.src.isdigit()):
            dev_idx = int(self.src)
            try:
                cap = cv2.VideoCapture(dev_idx)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        print(f"🎥 Cámara seleccionada ({dev_idx}) conectada.")
                        return cap
                    cap.release()
            except Exception:
                pass

        # 3.3. Dispositivos USB en cascada (0, 1, 2)
        for dev in [0, 1, 2]:
            try:
                cap = cv2.VideoCapture(dev)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        print(f"🎥 Cámara USB ({dev}) detectada.")
                        return cap
                    cap.release()
            except Exception:
                pass
                
        # 3.4. Último recurso: video demo en carpeta videos/
        videos_dir = os.path.join(os.path.dirname(__file__), '..', 'videos')
        fallback_demo = os.path.join(videos_dir, 'demo.mp4')
        if not os.path.exists(fallback_demo) and os.path.exists(videos_dir):
            for fn in os.listdir(videos_dir):
                if fn.endswith(('.mp4', '.avi', '.mkv', '.mov')) and not fn.startswith('.'):
                    fallback_demo = os.path.join(videos_dir, fn)
                    break
        if os.path.exists(fallback_demo):
            try:
                cap = cv2.VideoCapture(fallback_demo)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.is_file = True
                        print(f"🎬 Activando clip de video predeterminado: {os.path.basename(fallback_demo)}")
                        return cap
                    cap.release()
            except Exception:
                pass

        print("❌ No se detectó ninguna fuente de video funcional.")
        return None

    def start(self):
        self.stopped = False
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        return self

    def update(self):
        """
        Bucle de captura ejecutado exclusivamente en su hilo dedicado.
        Este hilo es el único que realiza llamadas a self.stream.read() y self.stream.release()
        para evitar condiciones de carrera y fallos de double-free en libavcodec.
        """
        frame_interval = 1.0 / max(10.0, self.target_fps) if self.is_file else 0.005
        
        try:
            while not self.stopped:
                loop_start = time.time()
                
                if self.stream is None or not self.stream.isOpened():
                    with self.lock:
                        self.failed = True
                    time.sleep(1.0)
                    if self.stopped:
                        break
                    self.stream = self._conectar_fuente()
                    if self.stream:
                        self._configurar_stream()
                    continue

                try:
                    grabbed, frame = self.stream.read()
                except Exception:
                    grabbed, frame = False, None
                
                # Loop automático para archivos de video al llegar al final
                if not grabbed and self.is_file and self.stream is not None and not self.stopped:
                    try:
                        self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        grabbed, frame = self.stream.read()
                    except Exception:
                        grabbed, frame = False, None

                with self.lock:
                    if not grabbed or frame is None:
                        self.failed = True
                        if self.stream is not None:
                            try:
                                self.stream.release()
                            except Exception:
                                pass
                            self.stream = None
                    else:
                        self.grabbed = True
                        self.frame = frame
                        self.failed = False
                
                # Control de velocidad de reproducción para archivos de video
                if self.is_file:
                    elapsed = time.time() - loop_start
                    sleep_time = max(0.002, frame_interval - elapsed)
                    time.sleep(sleep_time)
                else:
                    time.sleep(0.005)
                    
        finally:
            # Limpieza segura exclusiva dentro del hilo de captura
            with self.lock:
                if self.stream is not None:
                    try:
                        self.stream.release()
                    except Exception:
                        pass
                    self.stream = None
                self.grabbed = False
                self.failed = True

    def read(self):
        with self.lock:
            if self.failed or not self.grabbed or self.frame is None:
                return False, None
            return True, self.frame.copy()

    def stop(self):
        """Detiene el hilo de forma síncrona esperando a que termine limpiamente sin bloquearse"""
        self.stopped = True
        if self.thread is not None and self.thread.is_alive() and threading.current_thread() != self.thread:
            try:
                self.thread.join(timeout=0.5)
            except Exception:
                pass
        acquired = False
        try:
            acquired = self.lock.acquire(timeout=0.5)
            self.grabbed = False
            self.failed = True
            if self.stream is not None:
                try:
                    self.stream.release()
                except Exception:
                    pass
                self.stream = None
        except Exception:
            pass
        finally:
            if acquired:
                try:
                    self.lock.release()
                except Exception:
                    pass
