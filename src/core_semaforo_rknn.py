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
import queue

class CoreSemaforoRKNN(CoreSemaforoBase):
    """
    Clase base para aceleración en NPU (Rockchip RK3588 en Orange Pi 5) mediante RKNN-Toolkit2 Lite.
    Incluye aceleración Pipelined Asíncrona Multi-Core específica para YOLOv8 Medium.
    """
    def __init__(self, topology_name="4_way", port=None, video_source=None):
        self._rknn_lock = threading.Lock()
        self.rknn = None
        self.rknn_pool = []
        self._is_pipelined_m = False
        self._pipeline_workers = []
        self._task_queue = None
        self._latest_dets_m = None
        self._dets_lock_m = threading.Lock()
        self._pipeline_running = False
        super().__init__(topology_name=topology_name, backend_name="NPU (RKNN)", port=port, video_source=video_source)

    def _stop_pipeline_workers(self):
        self._pipeline_running = False
        if self._task_queue is not None:
            for _ in range(len(self._pipeline_workers) + 2):
                try:
                    self._task_queue.put_nowait(None)
                except Exception:
                    pass
        self._pipeline_workers = []

    def _start_pipeline_workers(self, pool_items):
        self._task_queue = queue.Queue(maxsize=3)
        self._pipeline_running = True
        self._pipeline_workers = []
        
        for idx, (r_inst, mask) in enumerate(pool_items):
            t = threading.Thread(target=self._worker_loop_m, args=(r_inst, idx), daemon=True)
            t.start()
            self._pipeline_workers.append(t)

    def _worker_loop_m(self, r_inst, worker_idx):
        while self._pipeline_running and self.running:
            try:
                task = self._task_queue.get(timeout=0.2)
            except queue.Empty:
                continue
                
            if task is None:
                break
                
            frame_resized, r, padding, orig_shape = task
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            input_data = np.expand_dims(frame_rgb, axis=0)
            
            try:
                outputs = r_inst.inference(inputs=[input_data], data_format=['nhwc'])
            except Exception:
                try:
                    outputs = r_inst.inference(inputs=[input_data])
                except Exception:
                    outputs = None
                    
            if outputs:
                boxes, confs, classes = postprocess(
                    outputs=outputs,
                    r=r,
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
                        dets.append([b[0], b[1], b[2], b[3], s, c])
                    with self._dets_lock_m:
                        if len(dets) > 0:
                            self._latest_dets_m = np.array(dets, dtype=np.float32)
                        else:
                            self._latest_dets_m = np.empty((0, 6), dtype=np.float32)
                else:
                    with self._dets_lock_m:
                        self._latest_dets_m = np.empty((0, 6), dtype=np.float32)
            self._task_queue.task_done()

    def _init_model(self):
        with self._rknn_lock:
            self._stop_pipeline_workers()
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
            
            # --- Modo Pipelined Exclusivo para YOLOv8 Medium ---
            if "yolov8m" in model_name:
                print(f"⚡ [NPU MULTI-CORE] Inicializando Pool Asíncrono de 3 Núcleos para {os.path.basename(model_path)}...")
                core_masks = [
                    getattr(RKNNLite, 'NPU_CORE_0', 1),
                    getattr(RKNNLite, 'NPU_CORE_1', 2),
                    getattr(RKNNLite, 'NPU_CORE_2', 4)
                ]
                new_pool = []
                for i, c_mask in enumerate(core_masks):
                    r_inst = RKNNLite(verbose=False)
                    if r_inst.load_rknn(model_path) == 0:
                        try:
                            if r_inst.init_runtime(core_mask=c_mask) == 0:
                                new_pool.append((r_inst, c_mask))
                                print(f"  • Worker NPU Núcleo {i} listo.")
                        except Exception:
                            pass
                            
                if len(new_pool) >= 2:
                    old_rknn = self.rknn
                    old_pool = self.rknn_pool
                    self.rknn_pool = [item[0] for item in new_pool]
                    self.rknn = self.rknn_pool[0]
                    self._is_pipelined_m = True
                    
                    self._start_pipeline_workers(new_pool)
                    
                    if old_pool:
                        for op in old_pool:
                            try: op.release()
                            except Exception: pass
                    elif old_rknn:
                        try: old_rknn.release()
                        except Exception: pass
                        
                    print(f"🚀 [PIPELINE ACTIVO] {len(new_pool)} Núcleos NPU operando en paralelo para YOLOv8 Medium.")
                    return

            # --- Modo Estándar para YOLOv8 Nano y Small ---
            self._is_pipelined_m = False
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

            old_rknn = self.rknn
            old_pool = self.rknn_pool
            self.rknn = new_rknn
            self.rknn_pool = []
            
            if old_pool:
                for op in old_pool:
                    try: op.release()
                    except Exception: pass
            elif old_rknn is not None:
                try: old_rknn.release()
                except Exception: pass
            print(f"✅ Modelo RKNN {os.path.basename(model_path)} cargado y activo en NPU.")

    def _predict(self, frame):
        # 1. Ruta Pipelined Asíncrona para YOLOv8 Medium
        if self._is_pipelined_m and self._pipeline_running:
            frame_resized, r, padding = letterbox(frame, new_shape=(640, 640))
            task = (frame_resized, r, padding, frame.shape)
            try:
                self._task_queue.put_nowait(task)
            except queue.Full:
                pass
                
            with self._dets_lock_m:
                if self._latest_dets_m is not None and len(self._latest_dets_m) > 0:
                    return self._latest_dets_m.copy()
            return None

        # 2. Ruta Estándar Secuencial e Intacta para YOLOv8 Nano y Small
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
        self._stop_pipeline_workers()
        super().stop()
        if hasattr(self, 'rknn_pool') and self.rknn_pool:
            for r in self.rknn_pool:
                try: r.release()
                except Exception: pass
        elif hasattr(self, 'rknn') and self.rknn:
            try: self.rknn.release()
            except Exception: pass
