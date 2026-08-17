#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import argparse
import numpy as np
import cv2

# Configuración de importación de RKNN
try:
    from rknnlite.api import RKNNLite as RKNN

    IS_LITE = True
    print("--> Cargado RKNNLite para Orange Pi 5.")
except ImportError:
    try:
        from rknn.api import RKNN

        IS_LITE = False
        print("--> RKNNLite no detectado. Cargado RKNN estándar para simulación.")
    except ImportError:
        print("[ERROR] No se pudo importar rknnlite o rknn. Instala la librería apropiada.")
        sys.exit(1)

# 80 Clases del dataset COCO (YOLOv8 estándar)
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
    'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush'
]

np.random.seed(42)
COLORS = np.random.randint(0, 255, size=(len(COCO_CLASSES), 3), dtype=np.uint8)


def letterbox(im, new_shape=(640, 640), color=(114, 114, 114)):
    shape = im.shape[:2]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
    dw = (new_shape[1] - new_unpad[0]) / 2
    dh = (new_shape[0] - new_unpad[1]) / 2
    if shape[::-1] != new_unpad:
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return im, r, (dw, dh)


def dfl_numpy(position):
    n, c, h, w = position.shape
    p_num = 4
    mc = c // p_num
    y = position.reshape(n, p_num, mc, h, w)
    
    max_y = np.max(y, axis=2, keepdims=True)
    exp_y = np.exp(y - max_y)
    y = exp_y / np.sum(exp_y, axis=2, keepdims=True)
    
    acc_metrix = np.arange(mc, dtype=np.float32).reshape(1, 1, mc, 1, 1)
    y = np.sum(y * acc_metrix, axis=2)
    return y

def box_process(position, img_size=(640, 640)):
    grid_h, grid_w = position.shape[2:4]
    col, row = np.meshgrid(np.arange(0, grid_w), np.arange(0, grid_h))
    col = col.reshape(1, 1, grid_h, grid_w)
    row = row.reshape(1, 1, grid_h, grid_w)
    grid = np.concatenate((col, row), axis=1)
    stride = np.array([img_size[1] // grid_h, img_size[0] // grid_w]).reshape(1, 2, 1, 1)

    position = dfl_numpy(position)
    box_xy = grid + 0.5 - position[:, 0:2, :, :]
    box_xy2 = grid + 0.5 + position[:, 2:4, :, :]
    xyxy = np.concatenate((box_xy * stride, box_xy2 * stride), axis=1)
    return xyxy

def postprocess_9tensors(outputs, conf_threshold):
    boxes, scores, classes_conf = [], [], []
    default_branch = 3
    pair_per_branch = len(outputs) // default_branch
    for i in range(default_branch):
        boxes.append(box_process(outputs[pair_per_branch * i]))
        classes_conf.append(outputs[pair_per_branch * i + 1])
        scores.append(np.ones_like(outputs[pair_per_branch * i + 1][:, :1, :, :], dtype=np.float32))

    def sp_flatten(_in):
        ch = _in.shape[1]
        _in = _in.transpose(0, 2, 3, 1)
        return _in.reshape(-1, ch)

    boxes = np.concatenate([sp_flatten(_v) for _v in boxes])
    classes_conf = np.concatenate([sp_flatten(_v) for _v in classes_conf])
    scores = np.concatenate([sp_flatten(_v) for _v in scores])

    class_max_score = np.max(classes_conf, axis=-1)
    classes = np.argmax(classes_conf, axis=-1)

    _class_pos = np.where(class_max_score * scores.reshape(-1) >= conf_threshold)
    final_scores = (class_max_score * scores.reshape(-1))[_class_pos]
    final_boxes = boxes[_class_pos]
    final_classes = classes[_class_pos]
    
    return final_boxes, final_classes, final_scores

def postprocess(outputs, r, padding, orig_shape, conf_threshold, nms_threshold):
    if outputs is None or len(outputs) == 0:
        print("[DEBUG] outputs es None o vacío.")
        return [], [], []
    
    print(f"[DEBUG] Número de tensores de salida: {len(outputs)}")
    for i, out in enumerate(outputs):
        print(f"[DEBUG] Forma del tensor {i}: {out.shape}")
        
    bboxes_list = []
    confs_list = []
    class_ids_list = []

    if len(outputs) == 9:
        b, c, s = postprocess_9tensors(outputs, conf_threshold)
        for i in range(len(b)):
            x1, y1, x2, y2 = b[i]
            w = x2 - x1
            h = y2 - y1
            bboxes_list.append([x1, y1, w, h])
            confs_list.append(s[i])
            class_ids_list.append(c[i])
    else:
        output = outputs[0]
        if len(output.shape) == 3:
            output = output[0]
            
        if output.shape[0] < output.shape[1]:
            output_t = output.T
        else:
            output_t = output
            
        print(f"[DEBUG] Forma de output_t después de procesar: {output_t.shape}")
            
        boxes = output_t[:, :4]
        scores = output_t[:, 4:]
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)
        
        mask = confidences > conf_threshold
        filtered_boxes = boxes[mask]
        filtered_confs = confidences[mask]
        filtered_class_ids = class_ids[mask]
        
        if len(filtered_boxes) == 0:
            return [], [], []
        cx, cy, w, h = filtered_boxes[:, 0], filtered_boxes[:, 1], filtered_boxes[:, 2], filtered_boxes[:, 3]
        x_min, y_min = cx - w / 2, cy - h / 2
        bboxes_list = np.column_stack((x_min, y_min, w, h)).tolist()
        confs_list = filtered_confs.tolist()
        class_ids_list = filtered_class_ids.tolist()

    indices = cv2.dnn.NMSBoxes(bboxes_list, confs_list, conf_threshold, nms_threshold)
    final_boxes, final_confs, final_class_ids = [], [], []
    orig_h, orig_w = orig_shape[:2]
    dw, dh = padding
    if len(indices) > 0:
        for idx in indices:
            if isinstance(idx, (list, np.ndarray)): idx = idx[0]
            bx, by, bw, bh = bboxes_list[idx]
            bx_orig, by_orig = (bx - dw) / r, (by - dh) / r
            bw_orig, bh_orig = bw / r, bh / r
            x1, y1 = int(max(0, bx_orig)), int(max(0, by_orig))
            x2, y2 = int(min(orig_w, bx_orig + bw_orig)), int(min(orig_h, by_orig + bh_orig))
            final_boxes.append((x1, y1, x2, y2))
            final_confs.append(confs_list[idx])
            final_class_ids.append(class_ids_list[idx])
    return final_boxes, final_confs, final_class_ids


def main():
    parser = argparse.ArgumentParser(description="Script para probar YOLOv8 RKNN en Orange Pi 5")
    parser.add_argument('--model', type=str, default='yolov8s.rknn', help='Ruta al modelo')
    parser.add_argument('--source', type=str, default='0', help='Imagen o índice de cámara')
    parser.add_argument('--headless', action='store_true', help='Modo sin GUI')
    parser.add_argument('--output', type=str, default='output.jpg', help='Salida')
    parser.add_argument('--conf', type=float, default=0.25, help='Confianza')
    parser.add_argument('--nms', type=float, default=0.45, help='NMS')
    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"[ERROR] Modelo no encontrado: {args.model}")
        sys.exit(1)

    is_headless = args.headless
    if not is_headless and not os.environ.get('DISPLAY'):
        is_headless = True

    rknn = RKNN()
    if rknn.load_rknn(args.model) != 0: sys.exit(1)
    if rknn.init_runtime() != 0: sys.exit(1)
    print("--> Runtime inicializado correctamente.")

    source_str = args.source
    is_image = os.path.exists(source_str) and source_str.lower().endswith(('.jpg', '.jpeg', '.png'))

    if is_image:
        frame = cv2.imread(source_str)
        orig_shape = frame.shape
        frame_resized, r, padding = letterbox(frame, new_shape=(640, 640))
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

        # CAMBIO CRÍTICO: Expansión a 4D (Batch size 1)
        input_data = np.expand_dims(frame_rgb, axis=0)

        t_start = time.time()
        outputs = rknn.inference(inputs=[input_data], data_format=['nhwc'])
        print(f"[INFO] Inferencia NPU: {(time.time() - t_start) * 1000:.2f} ms")

        boxes, confs, class_ids = postprocess(outputs, r, padding, orig_shape, args.conf, args.nms)
        for box, conf, cid in zip(boxes, confs, class_ids):
            x1, y1, x2, y2 = box
            color = [int(c) for c in COLORS[cid]]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{COCO_CLASSES[cid]}: {conf:.2f}"
            cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.imwrite(args.output, frame)
        print(f"--> Guardado en {args.output}")

    else:
        source = int(source_str) if source_str.isdigit() else source_str
        cap = cv2.VideoCapture(source)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            orig_shape = frame.shape
            frame_resized, r, padding = letterbox(frame, new_shape=(640, 640))
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

            # CAMBIO CRÍTICO: Expansión a 4D
            input_data = np.expand_dims(frame_rgb, axis=0)

            t_infer = time.time()
            outputs = rknn.inference(inputs=[input_data], data_format=['nhwc'])
            t_infer = time.time() - t_infer

            boxes, confs, class_ids = postprocess(outputs, r, padding, orig_shape, args.conf, args.nms)
            print(f"Inferencia: {t_infer * 1000:.1f}ms | Detecciones: {len(boxes)}")

            if not is_headless:
                for box, conf, cid in zip(boxes, confs, class_ids):
                    x1, y1, x2, y2 = box
                    color = [int(c) for c in COLORS[cid]]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{COCO_CLASSES[cid]}: {conf:.2f}"
                    cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.imshow("Fluxa NPU", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        cap.release()
    rknn.release()


if __name__ == "__main__":
    main()