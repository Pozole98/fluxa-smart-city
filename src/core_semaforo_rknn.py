# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Controlador de Inferencia Acelerada en NPU (Rockchip RK3588) con Fallback en CPU
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import os
import sys
import numpy as np
import cv2
import logging
import threading
import platform

from core_semaforo import CoreSemaforoBase
from utils import letterbox, postprocess

IS_AARCH64 = platform.machine().startswith('aarch64') or platform.machine().startswith('arm64')

try:
    from rknnlite.api import RKNNLite
    RKNN_AVAILABLE = True
except ImportError:
    RKNN_AVAILABLE = False
    if IS_AARCH64:
        logging.info("Librería rknnlite no detectada en el entorno aarch64 actual.")

    class RKNNLite:
        NPU_CORE_0_1_2 = 1
        def __init__(self, verbose=False): pass
        def load_rknn(self, path): return -1
        def init_runtime(self, core_mask=1): return -1
        def inference(self, inputs, data_format=None): return None
        def release(self): pass

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class CoreSemaforoRKNN(CoreSemaforoBase):
    """
    Controlador de inferencia acelerada sobre la NPU de la Orange Pi 5 (Rockchip RK3588)
    con arquitectura de respaldo automático en CPU (PyTorch) para alta disponibilidad.
    """

    def __init__(self, topology_name="4_way", port=None, video_source=None):
        self._rknn_lock = threading.RLock()
        self.rknn = None
        self.cpu_model = None
        self.is_cpu_fallback = False
        self.npu_error_count = 0
        self._frame_count = 0
        self._cached_dets_m = None
        super().__init__(topology_name=topology_name, backend_name="NPU (RKNN)", port=port, video_source=video_source)

    def _init_cpu_fallback(self, reason="Falla en NPU"):
        """Inicializa el motor de respaldo PyTorch en CPU de forma transparente"""
        logging.warning(f"Activando motor de respaldo YOLOv8 en CPU: {reason}")
        self.is_cpu_fallback = True
        self.backend_name = "CPU (Fallback)"
        
        if not ULTRALYTICS_AVAILABLE:
            logging.error("Ultralytics no se encuentra disponible para el motor de respaldo en CPU.")
            return False

        try:
            model_name = self.config.get("ai_model", {}).get("model_file", "yolov8n.pt")
            if model_name.endswith('.rknn'):
                model_name = model_name.rsplit('.', 1)[0] + '.pt'

            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'models', model_name),
                os.path.join(os.path.dirname(__file__), '..', model_name),
                os.path.join(os.path.dirname(__file__), '..', 'yolov8n.pt'),
                'yolov8n.pt',
                model_name
            ]
            cpu_model_path = 'yolov8n.pt'
            for p in possible_paths:
                if os.path.exists(p):
                    cpu_model_path = p
                    break

            logging.info(f"Cargando modelo PyTorch de respaldo: {cpu_model_path}")
            self.cpu_model = YOLO(cpu_model_path)
            if hasattr(self, 'api') and self.api:
                self.api.log_event('WARN', f"NPU no disponible. Operando en modo de respaldo CPU ({os.path.basename(cpu_model_path)})")
            return True
        except Exception as e:
            logging.error(f"Error al inicializar motor de respaldo en CPU: {e}")
            return False

    def _init_model(self):
        """Carga y configura el modelo de red neuronal en los 3 núcleos de la NPU"""
        with self._rknn_lock:
            self.IOU_THRESH = self.config.get("ai_model", {}).get("iou_threshold", 0.45)
            self._cached_dets_m = None
            self._frame_count = 0
            self.npu_error_count = 0
            self.is_cpu_fallback = False

            if not RKNN_AVAILABLE:
                self._init_cpu_fallback("Librería rknnlite no disponible")
                return

            model_name = self.config.get("ai_model", {}).get("model_file", "yolov8n.rknn")
            if not model_name.endswith('.rknn'):
                model_name = model_name.rsplit('.', 1)[0] + '.rknn'
                
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'models', model_name),
                os.path.join(os.path.dirname(__file__), '..', model_name),
                os.path.join('models', model_name),
                os.path.join(os.getcwd(), 'models', model_name),
                model_name
            ]
            model_path = None
            for p in possible_paths:
                if os.path.exists(p):
                    model_path = os.path.abspath(p)
                    break

            if not model_path:
                self._init_cpu_fallback(f"Archivo de modelo RKNN '{model_name}' no encontrado")
                return

            logging.info(f"Cargando modelo RKNN en la NPU desde: {model_path}")
            
            try:
                new_rknn = RKNNLite(verbose=False)
                ret = new_rknn.load_rknn(model_path)
                if ret != 0:
                    self._init_cpu_fallback(f"Error cargando archivo RKNN (código {ret})")
                    return
                    
                # Activar los 3 núcleos del acelerador NPU (Core 0 + Core 1 + Core 2 = 6 TOPS)
                core_mask = getattr(RKNNLite, 'NPU_CORE_0_1_2', 1)
                try:
                    ret = new_rknn.init_runtime(core_mask=core_mask)
                except Exception:
                    ret = -1

                if ret != 0:
                    try:
                        ret = new_rknn.init_runtime()
                    except Exception:
                        ret = -1

                if ret != 0:
                    self._init_cpu_fallback(f"Falla al inicializar runtime de NPU (código {ret})")
                    return

                old_rknn = self.rknn
                self.rknn = new_rknn
                self.backend_name = "NPU (RKNN)"
                
                if old_rknn is not None:
                    try:
                        old_rknn.release()
                    except Exception:
                        pass
                logging.info(f"Modelo RKNN {os.path.basename(model_path)} cargado y activo en los 3 núcleos de la NPU.")
            except Exception as e:
                self._init_cpu_fallback(f"Excepción al inicializar NPU: {e}")

    def _predict(self, frame):
        """Ejecuta inferencia con la NPU o con el motor de respaldo en CPU"""
        if self.is_cpu_fallback:
            if self.cpu_model is not None:
                try:
                    results = self.cpu_model.predict(source=frame, classes=self.CLASES_VEHICULOS, conf=self.CONF_THRESH, verbose=False)
                    if len(results) > 0 and len(results[0].boxes) > 0:
                        return results[0].boxes.data.cpu().numpy()
                except Exception as e:
                    logging.warning(f"Error en inferencia CPU fallback: {e}")
            return None

        # Cadencia temporal optimizada para YOLOv8 Medium en hardware embebido
        model_name = self.config.get("ai_model", {}).get("model_file", "")
        if "yolov8m" in model_name:
            self._frame_count += 1
            if self._frame_count % 2 != 0 and self._cached_dets_m is not None:
                return self._cached_dets_m.copy()

        with self._rknn_lock:
            if self.rknn is None:
                return None

            try:
                frame_resized, r, padding = letterbox(frame, new_shape=(640, 640))
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                input_data = np.expand_dims(frame_rgb, axis=0)

                try:
                    outputs = self.rknn.inference(inputs=[input_data], data_format=['nhwc'])
                except TypeError:
                    try:
                        outputs = self.rknn.inference(inputs=[input_data], data_format='nhwc')
                    except Exception:
                        outputs = self.rknn.inference(inputs=[input_data])
                except Exception:
                    outputs = self.rknn.inference(inputs=[input_data])

                if outputs is None:
                    raise RuntimeError("Salida nula de la NPU")

                self.npu_error_count = 0

                boxes, confs, classes = postprocess(
                    outputs=outputs, 
                    r=r, 
                    padding=padding, 
                    orig_shape=frame.shape, 
                    conf_threshold=self.CONF_THRESH, 
                    nms_threshold=self.IOU_THRESH
                )

                if len(boxes) > 0:
                    dets = []
                    for b, s, c in zip(boxes, confs, classes):
                        if self.CLASES_VEHICULOS and c not in self.CLASES_VEHICULOS:
                            continue
                        x1, y1, x2, y2 = b
                        dets.append([x1, y1, x2, y2, s, c])
                    if len(dets) > 0:
                        arr = np.array(dets, dtype=np.float32)
                        self._cached_dets_m = arr
                        return arr
                        
                self._cached_dets_m = None
                return None

            except Exception as e:
                self.npu_error_count += 1
                logging.warning(f"Error en inferencia RKNN ({self.npu_error_count}/3): {e}")
                if self.npu_error_count >= 3:
                    self._init_cpu_fallback(f"Falla repetida de inferencia en NPU ({e})")
                return None

    def stop(self):
        """Libera de forma ordenada los recursos de la NPU y el controlador base"""
        try:
            super().stop()
        except Exception:
            pass
            
        acquired = False
        try:
            acquired = self._rknn_lock.acquire(timeout=1.0)
            if hasattr(self, 'rknn') and self.rknn is not None:
                try:
                    self.rknn.release()
                except Exception:
                    pass
                self.rknn = None
            self.cpu_model = None
        except Exception:
            pass
        finally:
            if acquired:
                try:
                    self._rknn_lock.release()
                except Exception:
                    pass
