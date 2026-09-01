# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
import os
import sys
from ultralytics import YOLO

def export_to_onnx():
    print("=" * 60)
    print("Iniciando la exportación de YOLOv8s a ONNX (opset 12)...")
    print("=" * 60)
    
    # Nombre del archivo del modelo PyTorch
    pt_model_path = "yolov8s.pt"
    
    # Comprobar si el archivo local existe, si no, se descargará automáticamente
    if not os.path.exists(pt_model_path):
        print(f"El archivo '{pt_model_path}' no se encontró localmente.")
        print("Ultralytics lo descargará de manera automática desde el repositorio oficial...")
    
    try:
        # Cargar el modelo
        model = YOLO(pt_model_path)
        
        # Exportar a formato ONNX
        # Parámetros críticos:
        # - format="onnx": Especifica el formato de salida.
        # - opset=12: Opset estable y recomendado para rknn-toolkit2.
        # - dynamic=False: Genera una entrada estática de 640x640, obligatoria para NPU.
        # - imgsz=640: Tamaño de entrada del modelo (640x640 píxeles).
        # - simplify=True: Fusión y simplificación de operaciones para un modelo ONNX optimizado.
        print("\nExportando modelo...")
        onnx_path = model.export(
            format="onnx",
            opset=12,
            dynamic=False,
            imgsz=640,
            simplify=True
        )
        
        print("\n" + "=" * 60)
        print("EXPORTACIÓN COMPLETADA CON ÉXITO!")
        print(f"Modelo ONNX guardado en: {onnx_path}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo durante la exportación a ONNX: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    export_to_onnx()
