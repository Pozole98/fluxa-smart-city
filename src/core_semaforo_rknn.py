import os
import sys
import numpy as np
import cv2

from core_semaforo import CoreSemaforoBase
from utils import letterbox, postprocess

import platform
IS_AARCH64 = platform.machine().startswith('aarch64') or platform.machine().startswith('arm64')

try:
    from rknnlite.api import RKNNLite
    RKNN_AVAILABLE = True
except ImportError:
    RKNN_AVAILABLE = False
    if IS_AARCH64:
        print("\n" + "="*70)
        print("❌ [ADVERTENCIA NPU] La librería 'rknnlite' no está instalada en este entorno.")
        print("💡 Para habilitar la NPU Rockchip RK3588 en Orange Pi 5, ejecuta:")
        py_ver = f"{sys.version_info.major}{sys.version_info.minor}"
        print(f"   pip install wheels/rknn_toolkit_lite2-2.3.2-cp{py_ver}-cp{py_ver}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl --break-system-packages")
        print("="*70 + "\n")

    # Clase de simulación solo para desarrollo en PC x86
    class RKNNLite:
        NPU_CORE_0_1_2 = 1
        def __init__(self, verbose=False): pass
        def load_rknn(self, path): return 0
        def init_runtime(self, core_mask): return 0
        def inference(self, inputs, data_format=None): return [np.zeros((1, 84, 8400), dtype=np.float32)]
        def release(self): pass

import threading

class CoreSemaforoRKNN(CoreSemaforoBase):
    """
    Clase base para aceleración en NPU (Rockchip RK3588 en Orange Pi 5) mediante RKNN-Toolkit2 Lite.
    """
    def __init__(self, topology_name="4_way", port=None, video_source=None):
        self._rknn_lock = threading.Lock()
        self.rknn = None
        super().__init__(topology_name=topology_name, backend_name="NPU (RKNN)", port=port, video_source=video_source)

    def _init_model(self):
        with self._rknn_lock:
            self.IOU_THRESH = self.config.get("ai_model", {}).get("iou_threshold", 0.45)
            
            model_name = self.config.get("ai_model", {}).get("model_file", "yolov8n.rknn")
            if not model_name.endswith('.rknn'):
                model_name = model_name.rsplit('.', 1)[0] + '.rknn'
                
            model_path = model_name
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'models', model_name),
                os.path.join(os.path.dirname(__file__), '..', model_name),
                os.path.join('models', model_name),
                os.path.join(os.getcwd(), 'models', model_name),
                model_name
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    model_path = os.path.abspath(p)
                    break

            print(f"📦 Cargando modelo RKNN en la NPU desde: {model_path}")
            
            new_rknn = RKNNLite(verbose=False)
            ret = new_rknn.load_rknn(model_path)
            if ret != 0:
                print(f"❌ Falla crítica al cargar el modelo RKNN {model_path} (ret={ret}).")
                return
                
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
                print(f"❌ Falla crítica inicializando el runtime de la NPU para {model_path} (ret={ret}).")
                return

            # Solo liberar el contexto anterior tras inicializar exitosamente el nuevo
            old_rknn = self.rknn
            self.rknn = new_rknn
            
            if old_rknn is not None:
                try:
                    old_rknn.release()
                except Exception:
                    pass
            print(f"✅ Modelo RKNN {os.path.basename(model_path)} cargado y activo en NPU.")

    def _predict(self, frame):
        with self._rknn_lock:
            if self.rknn is None:
                return None

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
                try:
                    outputs = self.rknn.inference(inputs=[input_data])
                except Exception as e:
                    logging.warning(f"Error en inferencia RKNN: {e}")
                    return None

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
                return np.array(dets, dtype=np.float32)
        return None

    def stop(self):
        super().stop()
        if hasattr(self, 'rknn') and self.rknn:
            self.rknn.release()
