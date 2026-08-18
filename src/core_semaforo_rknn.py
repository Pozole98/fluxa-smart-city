import os
import sys
import numpy as np
import cv2

from core_semaforo import CoreSemaforoBase
from utils import letterbox, postprocess

try:
    from rknnlite.api import RKNNLite
except ImportError:
    # Para permitir pruebas de sintaxis y desarrollo en PC x86 (sin RKNNLite instalado)
    class RKNNLite:
        NPU_CORE_0_1_2 = 1
        def __init__(self, verbose=False): pass
        def load_rknn(self, path): return 0
        def init_runtime(self, core_mask): return 0
        def inference(self, inputs): return [np.zeros((1, 84, 8400), dtype=np.float32)]
        def release(self): pass

class CoreSemaforoRKNN(CoreSemaforoBase):
    """
    Clase base para aceleración en NPU (Rockchip RK3588 en Orange Pi 5) mediante RKNN-Toolkit2 Lite.
    """
    def __init__(self, topology_name="4_way", port=None, video_source=None):
        super().__init__(topology_name=topology_name, backend_name="NPU (RKNN)", port=port, video_source=video_source)

    def _init_model(self):
        self.IOU_THRESH = self.config.get("ai_model", {}).get("iou_threshold", 0.45)
        
        model_name = self.config.get("ai_model", {}).get("model_file", "yolov8n.rknn")
        if not model_name.endswith('.rknn'):
            model_name = model_name.rsplit('.', 1)[0] + '.rknn'
            
        model_path = model_name
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'models', model_name),
            os.path.join('models', model_name),
            os.path.join(os.path.dirname(__file__), '..', model_name),
            model_name
        ]
        for p in possible_paths:
            if os.path.exists(p):
                model_path = p
                break

        print(f"📦 Cargando modelo RKNN en la NPU desde: {model_path}")
        self.rknn = RKNNLite(verbose=False)
        ret = self.rknn.load_rknn(model_path)
        if ret != 0:
            print("❌ Falla crítica al cargar el modelo RKNN.")
            sys.exit(1)
            
        ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0_1_2)
        if ret != 0:
            print("❌ Falla crítica inicializando el runtime de la NPU.")
            sys.exit(1)

    def _predict(self, frame):
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        orig_shape = img_rgb.shape
        img_resized, ratio, padding = letterbox(img_rgb, new_shape=(640, 640))
        img_input = np.expand_dims(img_resized, axis=0)

        outputs = self.rknn.inference(inputs=[img_input])

        boxes, confs, classes = postprocess(
            outputs=outputs, 
            r=ratio, 
            padding=padding, 
            orig_shape=orig_shape, 
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
                return np.array(dets)
        return None

    def stop(self):
        super().stop()
        if hasattr(self, 'rknn') and self.rknn:
            self.rknn.release()
