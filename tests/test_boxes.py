# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
import torch
import numpy as np
from types import SimpleNamespace
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.engine.results import Boxes

args = SimpleNamespace(
    track_high_thresh=0.5, 
    track_low_thresh=0.1, 
    new_track_thresh=0.6, 
    track_buffer=30, 
    match_thresh=0.8, 
    gmc_method='sparseOptFlow',
    fuse_score=False
)
tracker = BYTETracker(args)

det = torch.tensor([[10., 10., 20., 20., 0.9, 0.]])
boxes = Boxes(det, orig_shape=(640, 640))
img = np.zeros((640, 640, 3), dtype=np.uint8)

try:
    tracks = tracker.update(boxes, img)
    print("Success, tracks:", tracks)
except Exception as e:
    import traceback
    traceback.print_exc()
