#!/usr/bin/env python3
"""
FLUXA - Extractor de Cuadros de Calibración para Cuantización INT8 RKNN (P3.1).
Extrae fotogramas representativos espaciados uniformemente desde videos de tráfico,
los normaliza a 640x640 y genera el archivo dataset.txt requerido por RKNN-Toolkit2.
"""

import os
import sys
import argparse
import cv2
import glob

def extraer_cuadros(video_path, num_frames=60, output_dir=None, dataset_txt_path=None):
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'calibration_images')
    if dataset_txt_path is None:
        dataset_txt_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset.txt')
        
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(dataset_txt_path), exist_ok=True)
    
    if not os.path.exists(video_path):
        print(f"❌ Error: El video especificado no existe: {video_path}")
        return False
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: No se pudo abrir el archivo de video: {video_path}")
        return False
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duracion_seg = total_frames / fps if fps > 0 else 0
    
    print("=" * 65)
    print("🎞️  EXTRACTOR DE CALIBRACIÓN RKNN INT8 - FLUXA SMART CITY")
    print("=" * 65)
    print(f"📹 Video origen:        {video_path}")
    print(f"⏱️  Duración:           {duracion_seg:.1f}s ({total_frames} cuadros totales)")
    print(f"🎯 Cuadros a extraer:   {num_frames}")
    print(f"📁 Directorio destino:  {output_dir}")
    print(f"📄 Archivo de dataset:  {dataset_txt_path}")
    print("=" * 65)
    
    if total_frames <= 0:
        step = 30
    else:
        step = max(1, total_frames // num_frames)
        
    saved_images = []
    frame_idx = 0
    extracted_count = 0
    
    while cap.isOpened() and extracted_count < num_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % step == 0:
            # Redimensionar a resolución nativa del modelo YOLO (640x640)
            img_resized = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_AREA)
            img_name = f"calib_{extracted_count:04d}.jpg"
            img_path = os.path.join(output_dir, img_name)
            
            cv2.imwrite(img_path, img_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            saved_images.append(img_path)
            extracted_count += 1
            print(f"  ✓ [{extracted_count:02d}/{num_frames}] Guardado: {img_name} (Cuadro original: #{frame_idx})")
            
        frame_idx += 1
        
    cap.release()
    
    # Escribir dataset.txt para el toolkit de RKNN
    with open(dataset_txt_path, 'w') as f:
        for p in saved_images:
            # Escribir ruta relativa limpia
            rel_path = os.path.relpath(p, os.path.dirname(dataset_txt_path))
            f.write(f"{rel_path}\n")
            
    print("-" * 65)
    print(f"✅ Extracción completada exitosamente: {extracted_count} imágenes listas.")
    print(f"📝 Archivo de calibración generado: {dataset_txt_path}")
    print("💡 Ahora puedes ejecutar rknn.build(do_quantization=True, dataset='data/dataset.txt')")
    print("=" * 65)
    return True

if __name__ == "__main__":
    default_video = os.path.join(os.path.dirname(__file__), '..', 'videos', 'demo.mp4')
    if not os.path.exists(default_video):
        all_videos = glob.glob(os.path.join(os.path.dirname(__file__), '..', 'videos', '*.mp4'))
        if all_videos:
            default_video = all_videos[0]
            
    parser = argparse.ArgumentParser(description="Extractor de Cuadros de Calibración RKNN INT8")
    parser.add_argument("--video", type=str, default=default_video, help="Ruta al video de tráfico representativo")
    parser.add_argument("--num-frames", type=int, default=60, help="Cantidad de cuadros a extraer (recomendado: 50-100)")
    parser.add_argument("--out-dir", type=str, default=None, help="Directorio donde guardar los JPGs 640x640")
    parser.add_argument("--dataset-txt", type=str, default=None, help="Ruta del archivo dataset.txt de salida")
    
    args = parser.parse_args()
    extraer_cuadros(args.video, args.num_frames, args.out_dir, args.dataset_txt)
