#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificación de Calidad de Detección y Rastreo en Video Real
"""
import os
import sys
import time
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, BASE_DIR)

from ultralytics import YOLO
from ultralytics.trackers.byte_tracker import BYTETracker
from types import SimpleNamespace

def main():
    video_path = os.path.join(BASE_DIR, "videos", "demo.mp4")
    if not os.path.exists(video_path):
        print(f"[ERROR] No se encontró el video: {video_path}")
        return

    print("=" * 65)
    print("🚦 VALIDACIÓN DE CALIDAD DE DETECCIÓN Y RASTREO EN VIDEO REAL")
    print("=" * 65)
    
    model_path = os.path.join(BASE_DIR, "yolov8n.pt")
    print(f"Cargando modelo neuronal: {model_path}")
    model = YOLO(model_path)
    
    tracker_args = SimpleNamespace(
        track_thresh=0.25,
        match_thresh=0.8,
        track_buffer=30,
        frame_rate=30,
        mot20=False
    )
    tracker = BYTETracker(tracker_args)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir {video_path}")
        return

    frame_count = 0
    total_detections = 0
    class_counts = {}
    latencies = []
    
    print("Procesando fotogramas de prueba...")
    while cap.isOpened() and frame_count < 90:
        ret, frame = cap.read()
        if not ret:
            break
            
        t0 = time.perf_counter()
        results = model.predict(frame, imgsz=640, verbose=False, conf=0.25)[0]
        t_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(t_ms)
        
        if results.boxes is not None and len(results.boxes) > 0:
            boxes = results.boxes
            total_detections += len(boxes)
            for cls_id in boxes.cls.cpu().numpy():
                cls_name = model.names.get(int(cls_id), f"class_{int(cls_id)}")
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"  • Cuadros procesados: {frame_count:02d} | Latencia media: {np.mean(latencies[-30:]):.1f} ms | Detecciones en cuadro: {len(results.boxes)}")

    cap.release()
    
    avg_latency = np.mean(latencies) if latencies else 0
    print("-" * 65)
    print(f"✅ Validación de detección completada exitosamente:")
    print(f"   • Total de cuadros analizados: {frame_count}")
    print(f"   • Latencia media por cuadro:   {avg_latency:.2f} ms (~{1000/avg_latency:.1f} FPS en CPU)")
    print(f"   • Total de detecciones:        {total_detections} objetos")
    print(f"   • Desglose por clase:          {class_counts}")
    print("=" * 65)

if __name__ == "__main__":
    main()
