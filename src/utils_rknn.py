import cv2
import numpy as np

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

def postprocess_multi_tensors(outputs, conf_threshold):
    boxes, scores, classes_conf = [], [], []
    default_branch = 3
    pair_per_branch = len(outputs) // default_branch
    for i in range(default_branch):
        boxes.append(box_process(outputs[pair_per_branch * i]))
        classes_conf.append(outputs[pair_per_branch * i + 1])
        if pair_per_branch == 3:
            scores.append(outputs[pair_per_branch * i + 2])
        else:
            scores.append(np.ones_like(outputs[pair_per_branch * i + 1][:, :1, :, :], dtype=np.float32))

    def sp_flatten(_in):
        ch = _in.shape[1]
        _in = _in.transpose(0, 2, 3, 1)
        return _in.reshape(-1, ch)

    boxes = np.concatenate([sp_flatten(_v) for _v in boxes])
    classes_conf = np.concatenate([sp_flatten(_v) for _v in classes_conf])
    scores = np.concatenate([sp_flatten(_v) for _v in scores])

    # Aplicar sigmoid si son logits (valores fuera del rango [0, 1])
    if np.min(classes_conf) < 0.0 or np.max(classes_conf) > 1.0:
        classes_conf = 1.0 / (1.0 + np.exp(-np.clip(classes_conf, -20.0, 20.0)))
        
    if scores.size > 0 and (np.min(scores) < 0.0 or np.max(scores) > 1.0):
        scores = 1.0 / (1.0 + np.exp(-np.clip(scores, -20.0, 20.0)))

    class_max_score = np.max(classes_conf, axis=-1)
    classes = np.argmax(classes_conf, axis=-1)

    total_conf = class_max_score * scores.reshape(-1)
    _class_pos = np.where(total_conf >= conf_threshold)
    final_scores = total_conf[_class_pos]
    final_boxes = boxes[_class_pos]
    final_classes = classes[_class_pos]
    
    return final_boxes, final_classes, final_scores

def nms_fast(boxes, scores, iou_threshold):
    """NMS vectorial en NumPy a prueba de fallos para cualquier formato de caja"""
    if len(boxes) == 0:
        return []
    boxes = np.array(boxes, dtype=np.float32)
    scores = np.array(scores, dtype=np.float32)
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]
    return keep

def postprocess(outputs, r, padding, orig_shape, conf_threshold, nms_threshold):
    if outputs is None or len(outputs) == 0:
        return [], [], []
    
    bboxes_list = []
    confs_list = []
    class_ids_list = []

    if len(outputs) == 9:
        b, c, s = postprocess_multi_tensors(outputs, conf_threshold)
        for i in range(len(b)):
            x1, y1, x2, y2 = b[i]
            w = x2 - x1
            h = y2 - y1
            bboxes_list.append([x1, y1, w, h])
            confs_list.append(float(s[i]))
            class_ids_list.append(int(c[i]))
    else:
        output = outputs[0]
        if len(output.shape) == 3:
            output = output[0]
            
        if output.shape[0] < output.shape[1]:
            output_t = output.T
        else:
            output_t = output
            
        boxes = output_t[:, :4]
        scores = output_t[:, 4:]
        
        if np.min(scores) < 0.0 or np.max(scores) > 1.0:
            scores = 1.0 / (1.0 + np.exp(-np.clip(scores, -20.0, 20.0)))
            
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

    try:
        indices = cv2.dnn.NMSBoxes(bboxes_list, confs_list, conf_threshold, nms_threshold)
        if indices is None or len(indices) == 0:
            indices = nms_fast(bboxes_list, confs_list, nms_threshold)
    except Exception:
        indices = nms_fast(bboxes_list, confs_list, nms_threshold)

    final_boxes, final_confs, final_class_ids = [], [], []
    orig_h, orig_w = orig_shape[:2]
    dw, dh = padding
    if len(indices) > 0:
        for idx in indices:
            if isinstance(idx, (list, np.ndarray, tuple)): idx = idx[0]
            idx = int(idx)
            bx, by, bw, bh = bboxes_list[idx]
            bx_orig, by_orig = (bx - dw) / r, (by - dh) / r
            bw_orig, bh_orig = bw / r, bh / r
            x1, y1 = int(max(0, bx_orig)), int(max(0, by_orig))
            x2, y2 = int(min(orig_w, bx_orig + bw_orig)), int(min(orig_h, by_orig + bh_orig))
            final_boxes.append((x1, y1, x2, y2))
            final_confs.append(float(confs_list[idx]))
            final_class_ids.append(int(class_ids_list[idx]))
            
    return final_boxes, final_confs, final_class_ids
