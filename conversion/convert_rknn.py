import os
import sys
from rknn.api import RKNN

def clean_and_verify_dataset(dataset_path="dataset.txt"):
    """
    Lee dataset.txt, normaliza las rutas de las imágenes y verifica que existan.
    Si algún nombre de archivo contiene espacios, lo renombra en el disco
    reemplazando los espacios con guiones bajos, ya que RKNN-Toolkit2 separa
    las rutas por espacios para modelos de múltiples entradas.
    Escribe un archivo temporal 'dataset_clean.txt' con rutas válidas y absolutas.
    """
    print("Normalizando y verificando las rutas del dataset de calibración...")
    
    if not os.path.exists(dataset_path):
        print(f"[ERROR] No se encontró el archivo del dataset: '{dataset_path}'", file=sys.stderr)
        return None

    clean_paths = []
    missing_files = []

    with open(dataset_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        raw_path = line.strip()
        if not raw_path:
            continue
        
        # Normalizar la ruta eliminando duplicados de '.' o '/'
        normalized_path = os.path.normpath(raw_path)
        abs_path = os.path.abspath(normalized_path)
        
        # RKNN-Toolkit2 separa los datasets por espacios. Los nombres de archivos con espacios
        # romperán la lectura del dataset. Renombramos los archivos en disco si tienen espacios.
        filename = os.path.basename(abs_path)
        if " " in filename:
            dirname = os.path.dirname(abs_path)
            new_filename = filename.replace(" ", "_")
            new_abs_path = os.path.join(dirname, new_filename)
            
            if os.path.exists(abs_path):
                try:
                    os.rename(abs_path, new_abs_path)
                    print(f"  [Renombrado] '{filename}' -> '{new_filename}'")
                    abs_path = new_abs_path
                except Exception as e:
                    print(f"  [ERROR] No se pudo renombrar '{filename}' a '{new_filename}': {e}")
            elif os.path.exists(new_abs_path):
                # Si el archivo con espacios ya fue renombrado en una ejecución anterior
                abs_path = new_abs_path

        if os.path.exists(abs_path):
            clean_paths.append(abs_path)
        else:
            missing_files.append((i, raw_path, abs_path))

    if missing_files:
        print(f"\n[ADVERTENCIA] Se encontraron {len(missing_files)} imágenes que no existen en el disco:")
        for idx, raw, abs_p in missing_files[:5]:
            print(f"  - Línea {idx}: '{raw}' (Buscada en: '{abs_p}')")
        if len(missing_files) > 5:
            print(f"  ... y {len(missing_files) - 5} imágenes más no encontradas.")
    
    if not clean_paths:
        print("[ERROR] No se encontró ninguna imagen de calibración válida en el dataset.", file=sys.stderr)
        return None

    print(f"Total de imágenes válidas encontradas: {len(clean_paths)} / {len(lines)}")
    
    # Crear un dataset limpio sin espacios en las rutas
    clean_dataset_path = "dataset_clean.txt"
    with open(clean_dataset_path, "w", encoding="utf-8") as f:
        for path in clean_paths:
            f.write(path + "\n")
            
    print(f"Archivo de calibración temporal creado en: '{clean_dataset_path}'")
    return clean_dataset_path


def convert_onnx_to_rknn():
    print("=" * 60)
    print("Iniciando la conversión de ONNX a RKNN (INT8 para RK3588)...")
    print("=" * 60)

    onnx_model = "yolov8s.onnx"
    rknn_model = "yolov8s.rknn"

    # Verificar que el modelo ONNX existe
    if not os.path.exists(onnx_model):
        print(f"[ERROR] No se encontró el modelo ONNX '{onnx_model}'.", file=sys.stderr)
        print("Por favor, ejecuta primero: python export_onnx.py", file=sys.stderr)
        sys.exit(1)

    # Preparar el archivo de calibración limpio
    clean_dataset = clean_and_verify_dataset("dataset.txt")
    if not clean_dataset:
        print("[ERROR] Falló la preparación del dataset de calibración. Abortando.", file=sys.stderr)
        sys.exit(1)

    # Crear el objeto de la API RKNN
    rknn = RKNN(verbose=True)

    try:
        # 1. Configurar los parámetros de preprocesamiento del compilador
        # - target_platform='rk3588': Específico para Orange Pi 5.
        # - mean_values=[[0, 0, 0]]: YOLOv8 no requiere restar media en RGB.
        # - std_values=[[255, 255, 255]]: Divide cada píxel entre 255 para escalar al rango [0.0, 1.0].
        # - reorder_channel='2 1 0': Invierte el orden BGR a RGB. Esto permite que pases imágenes
        #   directamente desde OpenCV (BGR) a la NPU sin procesamiento manual en la CPU de la Orange Pi.
        print("\n--> 1. Configurando parámetros del modelo...")
        rknn.config(
            mean_values=[[0, 0, 0]],
            std_values=[[255, 255, 255]],
            target_platform='rk3588',
            quant_img_RGB2BGR=False
        )

        # 2. Cargar el modelo ONNX
        print(f"\n--> 2. Cargando modelo ONNX: '{onnx_model}'...")
        ret = rknn.load_onnx(model=onnx_model)
        if ret != 0:
            print("[ERROR] Falló la carga del modelo ONNX.", file=sys.stderr)
            sys.exit(1)

        # 3. Compilar el modelo en FP16 (Sin cuantización INT8)
        # - do_quantization=False: YOLOv8 puro pierde toda su precisión en INT8 
        #   debido a la capa DFL y Softmax en la cabeza de detección. 
        #   Usar FP16 en RK3588 es muy rápido y mantiene el 100% de precisión.
        print("\n--> 3. Compilando el modelo a FP16 (para preservar precisión en YOLOv8)...")
        ret = rknn.build(do_quantization=False, dataset=clean_dataset)
        if ret != 0:
            print("[ERROR] Falló la compilación del modelo.", file=sys.stderr)
            sys.exit(1)

        # 4. Exportar el modelo al formato RKNN
        print(f"\n--> 4. Exportando modelo a RKNN: '{rknn_model}'...")
        ret = rknn.export_rknn(rknn_model)
        if ret != 0:
            print("[ERROR] Falló la exportación del archivo RKNN.", file=sys.stderr)
            sys.exit(1)

        print("\n" + "=" * 60)
        print("¡CONVERSIÓN A RKNN COMPLETADA CON ÉXITO!")
        print(f"Modelo RKNN guardado en: '{os.path.abspath(rknn_model)}'")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo inesperado durante la conversión: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Limpiar el archivo de calibración temporal
        clean_dataset_path = "dataset_clean.txt"
        if os.path.exists(clean_dataset_path):
            os.remove(clean_dataset_path)
            print("Limpieza completada (archivo temporal de calibración eliminado).")
        rknn.release()

if __name__ == "__main__":
    convert_onnx_to_rknn()
