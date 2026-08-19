#!/usr/bin/env python3
"""
FLUXA SCADA - Servidor de Demostración y Previsualización UI
Permite previsualizar el diseño de todas las vistas sin requerir hardware físico ni OpenCV.
"""

import os
import sys
import time
import json
import random
import io
import threading
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, jsonify, request, Response, session, redirect, url_for, send_from_directory

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
logos_dir = os.path.join(base_dir, 'logos')
logs_dir = os.path.join(base_dir, 'logs')
violations_dir = os.path.join(logs_dir, 'violations')

os.makedirs(violations_dir, exist_ok=True)
os.makedirs(logos_dir, exist_ok=True)

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = "fluxa_preview_secret_key"

# Estado simulado
state = {
    "topologia": "4_way",
    "backend": "NPU RK3588 (Simulado)",
    "status": "VERDE_NS",
    "modo": "Normal (IA Edge)",
    "emergencia_activa": False,
    "fase_tiempo_transcurrido": 0.0,
    "fase_tiempo_asignado": 15.0,
    "fps": 30.0,
    "total_acumulado": 1420,
    "autos": {
        "norte": 6,
        "sur": 8,
        "este": 3,
        "oeste": 2
    },
    "autos_acumulados": {
        "norte": 480,
        "sur": 510,
        "este": 220,
        "oeste": 210
    },
    "demanda_ponderada": {
        "norte": 7.2,
        "sur": 9.1,
        "este": 3.4,
        "oeste": 2.2
    },
    "latencias_ms": {
        "inferencia": 14.2,
        "tracking": 3.1,
        "pipeline_total": 19.5
    },
    "sostenibilidad": {
        "segundos_espera_ahorrados": 3120.0,
        "minutos_espera_ahorrados": 52.0,
        "combustible_ahorrado_litros": 8.45,
        "co2_mitigado_kg": 19.52,
        "eficiencia_flujo_pct": 89.4,
        "tiempo_tradicional_seg": 2840.0,
        "tiempo_fluxa_seg": 1120.0
    },
    "v2x": {
        "aviso_conductor": "Ola Verde Activa",
        "velocidad_recomendada_kmh": 45,
        "tiempo_restante_seg": 12.0
    },
    "ai_engine": {
        "is_npu": True,
        "model_file": "yolov8s.rknn",
        "model_type": "RKNN (NPU)"
    },
    "camara": {
        "tipo": "Video Demo 4 Vías",
        "connected": True,
        "resolution": "640x360"
    },
    "arduino": {
        "connected": True,
        "port": "/dev/ttyACM0 (Virtual)",
        "tx_count": 842,
        "alerta_desconexion_prolongada": False
    },
    "hardware": {
        "hostname": "orangepi5-c5",
        "ip_address": "192.168.100.20",
        "uptime_human": "04h 22m 15s",
        "cpu_percent": 24.5,
        "cpu_count": 8,
        "cpu_temp_c": 48.5,
        "ram_percent": 38.2,
        "ram_used_mb": 3120,
        "ram_total_mb": 8192,
        "disk": {
            "percent": 28.4,
            "free_gb": 42.6
        },
        "npu": {
            "supported": True,
            "cores_load": [45, 42, 38],
            "freq_mhz": 1000
        }
    }
}

events_log = [
    {"timestamp": datetime.now().strftime("%H:%M:%S"), "tipo": "INFO", "mensaje": "FLUXA SCADA inicializado con éxito."},
    {"timestamp": datetime.now().strftime("%H:%M:%S"), "tipo": "PHASE", "mensaje": "Fase cambiada a VERDE_NS (15.0s asignados)."},
    {"timestamp": datetime.now().strftime("%H:%M:%S"), "tipo": "INFO", "mensaje": "Controlador semafórico sincronizado con NPU."}
]

# Thread de simulación de semáforo
def simulation_loop():
    phases = [
        ("VERDE_NS", 14.0),
        ("AMARILLO_NS", 3.0),
        ("VERDE_EO", 12.0),
        ("AMARILLO_EO", 3.0)
    ]
    p_idx = 0
    start_time = time.time()

    while True:
        current_phase, duration = phases[p_idx]
        elapsed = time.time() - start_time

        if elapsed >= duration:
            p_idx = (p_idx + 1) % len(phases)
            current_phase, duration = phases[p_idx]
            start_time = time.time()
            elapsed = 0.0
            
            # Registrar evento
            events_log.insert(0, {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "tipo": "PHASE",
                "mensaje": f"Fase cambiada a {current_phase} ({duration}s asignados)."
            })
            if len(events_log) > 50:
                events_log.pop()

        state["status"] = current_phase
        state["fase_tiempo_transcurrido"] = round(elapsed, 1)
        state["fase_tiempo_asignado"] = duration

        # V2X
        rem = max(0.0, duration - elapsed)
        state["v2x"]["tiempo_restante_seg"] = round(rem, 1)
        if "VERDE" in current_phase:
            state["v2x"]["aviso_conductor"] = "Ola Verde Activa • Mantenga 40-50 km/h"
            state["v2x"]["velocidad_recomendada_kmh"] = 45
        elif "AMARILLO" in current_phase:
            state["v2x"]["aviso_conductor"] = "Luz Ámbar • Reduzca Velocidad"
            state["v2x"]["velocidad_recomendada_kmh"] = 20
        else:
            state["v2x"]["aviso_conductor"] = "Luz Roja • Deténgase"
            state["v2x"]["velocidad_recomendada_kmh"] = 0

        # Simular variación de autos
        if random.random() < 0.15:
            state["autos"]["norte"] = max(1, min(15, state["autos"]["norte"] + random.randint(-1, 1)))
            state["autos"]["sur"] = max(1, min(15, state["autos"]["sur"] + random.randint(-1, 1)))
            state["autos"]["este"] = max(0, min(10, state["autos"]["este"] + random.randint(-1, 1)))
            state["autos"]["oeste"] = max(0, min(10, state["autos"]["oeste"] + random.randint(-1, 1)))
            state["total_acumulado"] += 1
            state["sostenibilidad"]["combustible_ahorrado_litros"] += 0.01
            state["sostenibilidad"]["co2_mitigado_kg"] += 0.02
            state["sostenibilidad"]["minutos_espera_ahorrados"] += 0.05

        time.sleep(0.5)

sim_thread = threading.Thread(target=simulation_loop, daemon=True)
sim_thread.start()

# Generador de fotogramas sintéticos con PIL
def generate_synthetic_frame():
    w, h = 640, 360
    while True:
        img = Image.new('RGB', (w, h), color=(20, 26, 22))
        draw = ImageDraw.Draw(img)

        # Calles en cruz
        draw.rectangle([(int(w*0.35), 0), (int(w*0.65), h)], fill=(36, 44, 40))
        draw.rectangle([(0, int(h*0.35)), (w, int(h*0.65))], fill=(36, 44, 40))

        # Líneas de carril
        draw.line([(int(w*0.5), 0), (int(w*0.5), h)], fill=(80, 100, 90), width=1)
        draw.line([(0, int(h*0.5)), (w, int(h*0.5))], fill=(80, 100, 90), width=1)

        # Semáforos visuales
        current_st = state["status"]
        color_ns = (0, 200, 0) if "VERDE_NS" in current_st else ((255, 180, 0) if "AMARILLO_NS" in current_st else (220, 0, 0))
        color_eo = (0, 200, 0) if "VERDE_EO" in current_st else ((255, 180, 0) if "AMARILLO_EO" in current_st else (220, 0, 0))

        draw.ellipse([(int(w*0.5)-7, int(h*0.28)-7), (int(w*0.5)+7, int(h*0.28)+7)], fill=color_ns)
        draw.ellipse([(int(w*0.5)-7, int(h*0.72)-7), (int(w*0.5)+7, int(h*0.72)+7)], fill=color_ns)
        draw.ellipse([(int(w*0.28)-7, int(h*0.5)-7), (int(w*0.28)+7, int(h*0.5)+7)], fill=color_eo)
        draw.ellipse([(int(w*0.72)-7, int(h*0.5)-7), (int(w*0.72)+7, int(h*0.5)+7)], fill=color_eo)

        # Vehículos simulados
        t = time.time()
        y_pos1 = int((t * 50) % (h * 0.32))
        draw.rectangle([(int(w*0.4), y_pos1), (int(w*0.46), y_pos1+30)], outline=(112, 186, 40), width=2)
        draw.text((int(w*0.4), max(0, y_pos1-12)), "CAR #101", fill=(112, 186, 40))

        x_pos2 = int((t * 45) % (w * 0.32))
        draw.rectangle([(x_pos2, int(h*0.42)), (x_pos2+35, int(h*0.48))], outline=(59, 130, 246), width=2)
        draw.text((x_pos2, int(h*0.42)-12), "CAR #104", fill=(59, 130, 246))

        # HUD superior
        draw.rectangle([(0, 0), (w, 22)], fill=(7, 13, 9))
        draw.text((10, 5), f"FLUXA SCADA • TESCo / TecNM | NPU RK3588 | FASE: {current_st}", fill=(240, 245, 242))

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)
        frame_bytes = buf.getvalue()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05)

# ==========================================
# RUTAS WEB
# ==========================================

@app.route('/logos/<path:filename>')
def serve_logo(filename):
    return send_from_directory(logos_dir, filename)

@app.route('/')
def public_index():
    return render_template('public.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('index.html', user='admin')

@app.route('/report/executive')
def report_executive():
    target_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    summary = {
        "total_vehicles": 1420,
        "peak_hour": "14:00 - 15:00",
        "peak_hour_vehicles": 240,
        "avg_weighted_demand": 8.4
    }
    violations = [
        {"timestamp": f"{target_date} 10:14:22", "track_id": 142, "lane_name": "este", "snapshot_path": "demo_viol1.jpg"},
        {"timestamp": f"{target_date} 12:45:08", "track_id": 208, "lane_name": "sur", "snapshot_path": "demo_viol2.jpg"}
    ]
    return render_template('report_executive.html', date=target_date, summary=summary, violations=violations, telemetry=state)

# ==========================================
# RUTAS API
# ==========================================

@app.route('/video_feed')
def video_feed():
    return Response(generate_synthetic_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    return jsonify(state)

@app.route('/api/events')
def api_events():
    return jsonify(events_log)

@app.route('/api/history')
def api_history():
    now = int(time.time())
    labels = [datetime.fromtimestamp(now - (10 - i) * 60).strftime("%H:%M") for i in range(10)]
    return jsonify({
        "labels": labels,
        "datasets": {
            "norte": [random.randint(4, 12) for _ in range(10)],
            "sur": [random.randint(5, 14) for _ in range(10)],
            "este": [random.randint(2, 8) for _ in range(10)],
            "oeste": [random.randint(1, 6) for _ in range(10)]
        }
    })

@app.route('/api/reports/summary')
def api_reports_summary():
    return jsonify({
        "peak_hour": "14:00 - 15:00",
        "peak_hour_vehicles": 240,
        "hourly_distribution": [
            {"hour": h, "avg_cars": random.randint(40, 240)} for h in range(6, 22)
        ]
    })

@app.route('/api/violations')
def api_violations():
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify([
        {"timestamp": f"{today} 08:32:11", "lane_name": "norte", "track_id": 104, "phase_state": "ROJO_NS", "snapshot_path": ""},
        {"timestamp": f"{today} 11:15:40", "lane_name": "este", "track_id": 218, "phase_state": "ROJO_EO", "snapshot_path": ""}
    ])

@app.route('/api/models/list')
def api_models_list():
    return jsonify({
        "current_model": "yolov8s.rknn",
        "models": [
            {"filename": "yolov8n.pt", "name": "YOLOv8 Nano (PyTorch CPU)"},
            {"filename": "yolov8s.pt", "name": "YOLOv8 Small (PyTorch CPU)"},
            {"filename": "yolov8m.pt", "name": "YOLOv8 Medium (PyTorch CPU)"},
            {"filename": "yolov8n.rknn", "name": "YOLOv8 Nano RKNN (NPU RK3588)"},
            {"filename": "yolov8s.rknn", "name": "YOLOv8 Small RKNN (NPU RK3588)"},
            {"filename": "yolov8m.rknn", "name": "YOLOv8 Medium RKNN (NPU RK3588)"}
        ]
    })

@app.route('/api/video_source/list')
def api_video_source_list():
    videos_dir = os.path.join(base_dir, 'videos')
    available = []
    if os.path.exists(videos_dir):
        for fn in os.listdir(videos_dir):
            if fn.endswith(('.mp4', '.avi', '.mkv', '.mov')) and not fn.startswith('.'):
                path = os.path.join(videos_dir, fn)
                try:
                    size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
                    available.append({"filename": fn, "size_mb": size_mb})
                except Exception:
                    pass
    return jsonify({
        "current_source": "demo.mp4",
        "available_videos": available
    })

@app.route('/api/config/full', methods=['GET', 'POST'])
def api_config_full():
    cfg_file = os.path.join(base_dir, 'config.json')
    if request.method == 'POST':
        return jsonify({"status": "ok", "message": "Configuración y ROIs actualizados con éxito."})
    try:
        with open(cfg_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            return jsonify(cfg)
    except Exception:
        return jsonify({})

@app.route('/api/frame/snapshot')
def api_frame_snapshot():
    w, h = 640, 360
    img = Image.new('RGB', (w, h), color=(20, 26, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(int(w*0.35), 0), (int(w*0.65), h)], fill=(36, 44, 40))
    draw.rectangle([(0, int(h*0.35)), (w, int(h*0.65))], fill=(36, 44, 40))
    draw.text((int(w*0.15), int(h*0.48)), "CUADRO DE CALIBRACION - TESCo / TecNM", fill=(112, 186, 40))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return Response(buf.getvalue(), mimetype='image/jpeg')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    user = data.get('username')
    pw = data.get('password')
    if user == 'admin':
        session['is_admin'] = True
        session['user'] = 'admin'
        return jsonify({"status": "ok", "redirect": "/admin"})
    return jsonify({"error": "Credenciales no válidas. Use 'admin'."}), 401

@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/control', methods=['POST'])
def api_control():
    data = request.get_json() or {}
    act = data.get('action')
    events_log.insert(0, {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "tipo": "WARN" if act == "emergency_corridor" else "INFO",
        "mensaje": f"Comando C5 ejecutado: {act}"
    })
    return jsonify({"status": "ok", "action": act})

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print("\n" + "=" * 70)
    print("🚦 FLUXA SCADA • Servidor de Previsualización UI Institucional Activo")
    print(f"🌐 Portal Ciudadano:    http://localhost:{port}/")
    print(f"🔐 Acceso Operadores:   http://localhost:{port}/login")
    print(f"📊 Tablero SCADA C5:    http://localhost:{port}/admin")
    print(f"📄 Reporte Ejecutivo:   http://localhost:{port}/report/executive")
    print("=" * 70 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
