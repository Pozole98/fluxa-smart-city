# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Servidor Web, Interfaces REST API, Transmisión MJPEG y Autenticación C5
Desarrollador Principal y Titular de Derechos: Moisés Emilio Martínez Arias
Todos los derechos reservados © 2026.
"""

import os
import csv
import json
import time
import glob
import logging
import threading
import secrets
from functools import wraps
from datetime import datetime
import cv2
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, render_template, Response, send_file, send_from_directory, session, redirect, url_for

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    Limiter = None
    get_remote_address = None
    LIMITER_AVAILABLE = False

from hardware_monitor import HardwareMonitor

# Silenciar logs excesivos del servidor WSGI interno
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get("FLUXA_SECRET_KEY", secrets.token_hex(32))

# Configuración de seguridad para cookies de sesión HTTPOnly y SameSite
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get("FLUXA_ENV", "dev").lower() == "production"
)

# Control de tasa de peticiones (Rate Limiting) para protección contra ataques de fuerza bruta
if LIMITER_AVAILABLE and get_remote_address:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],
        storage_uri="memory://"
    )
else:
    limiter = None

# Instancia global de monitor de hardware
hw_monitor = HardwareMonitor()
cached_hw_metrics = {}

# Directorios del sistema
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
instance_directory = os.path.join(base_dir, 'instance')
log_directory = os.path.join(base_dir, 'logs')
violations_directory = os.path.join(log_directory, 'violations')
videos_directory = os.path.join(base_dir, 'videos')
admin_creds_file = os.path.join(instance_directory, 'admin_credentials.json')

os.makedirs(instance_directory, exist_ok=True)
os.makedirs(violations_directory, exist_ok=True)
os.makedirs(videos_directory, exist_ok=True)

VALID_VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov', '.webm', '.mpg', '.mpeg', '.m4v')

# Estructura enriquecida del estado global de telemetría
estado_global = {
    "topologia": "4_way",
    "backend": "CPU",
    "status": "Iniciando...",
    "modo": "Normal",
    "emergencia_activa": False,
    "eje_emergencia": None,
    "fase_tiempo_transcurrido": 0,
    "fase_tiempo_asignado": 0,
    "fps": 0.0,
    "autos": {},
    "autos_acumulados": {},
    "total_acumulado": 0,
    "demanda_ponderada": {},
    "sostenibilidad": {
        "segundos_espera_ahorrados": 0.0,
        "minutos_espera_ahorrados": 0.0,
        "horas_espera_ahorradas": 0.0,
        "combustible_ahorrado_litros": 0.0,
        "co2_mitigado_kg": 0.0,
        "eficiencia_flujo_pct": 85.0,
        "tiempo_tradicional_seg": 0.0,
        "tiempo_fluxa_seg": 0.0
    },
    "v2x": {
        "fase_activa": "VERDE_NS",
        "tiempo_restante_seg": 0.0,
        "velocidad_recomendada_kmh": 45,
        "aviso_conductor": " Mantenga 40-50 km/h (Ola Verde Activa)",
        "spat_timestamp": datetime.now().isoformat()
    },
    "latencias_ms": {
        "inferencia": 0.0,
        "tracking": 0.0,
        "pipeline_total": 0.0
    },
    "arduino": {
        "connected": False,
        "port": "/dev/ttyACM0",
        "baudrate": 9600,
        "tx_count": 0,
        "last_command": None,
        "reconnects": 0
    },
    "semaforos": {
        "semaforo_a": "ROJO",
        "semaforo_b": "ROJO",
        "etiqueta_a": "Vía A",
        "etiqueta_b": "Vía B",
        "comando_arduino": None
    },
    "camara": {
        "connected": False,
        "resolution": "640x480",
        "tipo": "Auto-Detect",
        "source_raw": "0"
    },
    "hardware": {},
    "corridor": {
        "corridor_name": "Corredor Principal",
        "current_node_id": "CRUCE_01",
        "green_wave_active": False,
        "green_wave_origin": None,
        "green_wave_remaining_sec": 0.0,
        "nodes": []
    }
}

eventos_sistema = []
eventos_lock = threading.Lock()
estado_lock = threading.RLock()

control_callback = None
frame_getter_callback = None
hot_reload_callback_global = None
change_source_callback_global = None
db_manager_instance = None
corridor_manager_instance = None

def registrar_evento(tipo, mensaje):
    with eventos_lock:
        ahora = datetime.now().strftime("%H:%M:%S")
        eventos_sistema.append({
            "timestamp": ahora,
            "tipo": tipo,
            "mensaje": mensaje
        })
        if len(eventos_sistema) > 100:
            eventos_sistema.pop(0)

_login_failures = {}
_login_lock = threading.Lock()
_cached_auth_cfg = None
_cached_auth_time = 0.0

def load_auth_config(force_reload=False):
    """
    Carga la configuración de autenticación con hash seguro y caché en memoria.
    Si no existen credenciales configuradas, genera una contraseña aleatoria de 12 caracteres,
    la almacena de forma segura en instance/admin_credentials.json con hash pbkdf2/sha256 y la muestra una única vez.
    """
    global _cached_auth_cfg, _cached_auth_time
    now = time.time()
    if not force_reload and _cached_auth_cfg is not None and (now - _cached_auth_time < 10.0):
        return _cached_auth_cfg

    # 1. Prioridad: Archivo local protegido instance/admin_credentials.json
    if os.path.exists(admin_creds_file):
        try:
            with open(admin_creds_file, 'r') as f:
                creds = json.load(f)
                if creds.get("admin_pass_hash") or creds.get("admin_pass"):
                    _cached_auth_cfg = {
                        "enabled": creds.get("enabled", True),
                        "admin_user": creds.get("admin_user", "admin"),
                        "admin_pass_hash": creds.get("admin_pass_hash"),
                        "admin_pass": creds.get("admin_pass")
                    }
                    _cached_auth_time = now
                    return _cached_auth_cfg
        except Exception:
            pass

    # 2. Configuración en config.json
    cfg_path = os.path.join(base_dir, 'config.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r') as f:
                cfg = json.load(f)
                auth_cfg = cfg.get("auth", {})
                if auth_cfg.get("admin_pass_hash") or auth_cfg.get("admin_pass"):
                    _cached_auth_cfg = auth_cfg
                    _cached_auth_time = now
                    return _cached_auth_cfg
        except Exception:
            pass

    # 3. Generación automática y segura de credenciales en primer arranque
    raw_pass = secrets.token_urlsafe(12)
    pass_hash = generate_password_hash(raw_pass)
    auto_creds = {
        "enabled": True,
        "admin_user": "admin",
        "admin_pass_hash": pass_hash,
        "generated_at": datetime.now().isoformat()
    }
    try:
        with open(admin_creds_file, 'w') as f:
            json.dump(auto_creds, f, indent=4)
        os.chmod(admin_creds_file, 0o600)
    except Exception as e:
        print(f"Error guardando credenciales seguras: {e}")

    print("\n" + "=" * 72)
    print(" FLUXA SEGURIDAD: Credenciales de Administrador C5 Generadas")
    print(" Usuario:     admin")
    print(f" Contraseña:  {raw_pass}")
    print("ℹ️  Guarda esta contraseña de forma segura. No se volverá a mostrar en texto plano.")
    print(" Para cambiarla: python3 scripts/set_admin_password.py")
    print("=" * 72 + "\n")

    _cached_auth_cfg = auto_creds
    _cached_auth_time = now
    return _cached_auth_cfg

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_cfg = load_auth_config()
        if not auth_cfg.get("enabled", True):
            return f(*args, **kwargs)
        if not session.get('is_admin'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Acceso no autorizado. Inicie sesión como Administrador C5.", "authenticated": False}), 401
            return redirect(url_for('login_page', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# RUTAS DE NAVEGACIÓN Y VISTAS WEB
# ==========================================

@app.route('/logos/<path:filename>')
def serve_logo(filename):
    """Sirve los logos institucionales (TESCo, TecNM, SIC)"""
    logos_dir = os.path.join(base_dir, 'logos')
    return send_from_directory(logos_dir, filename)

@app.route('/presentaciones/<path:filename>')
def serve_presentaciones(filename):
    """Sirve las presentaciones oficiales para la defensa InnovaTecNM 2026"""
    pres_dir = os.path.join(base_dir, 'presentaciones')
    return send_from_directory(pres_dir, filename)

@app.route('/')
def public_index():
    """Portal Ciudadano Público - Información de tráfico en tiempo real sin controles sensibles"""
    return render_template('public.html')

@app.route('/login')
def login_page():
    """Portal de Autenticación para Operadores C5"""
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Centro de Mando C5 SCADA - Control Total y Monitoreo Avanzado (Protegido)"""
    return render_template('index.html', user=session.get('user', 'admin'))

@app.route('/c5')
@admin_required
def c5_scada_dashboard():
    """Consola C5 SCADA - Centro de Monitoreo Urbano y Operaciones Viales en Tiempo Real"""
    return render_template('c5_scada.html', user=session.get('user', 'admin'))

@app.route('/report/executive')
@admin_required
def report_executive():
    """Informe Ejecutivo Oficial de Movilidad y Auditoría Vial listo para imprimir o guardar como PDF"""
    target_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    summary = {}
    violations = []
    if db_manager_instance is not None:
        summary = db_manager_instance.get_peak_hour_summary(target_date)
        violations = db_manager_instance.get_recent_violations(limit=15)
        
    return render_template('report_executive.html', 
                           date=target_date, 
                           summary=summary, 
                           violations=violations,
                           telemetry=estado_global)

# ==========================================
# AUTENTICACIÓN Y CONTROL DE ACCESO (API)
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    # Rate Limiting manual por IP (Defensa en profundidad)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr) or '127.0.0.1'
    now_ts = time.time()
    with _login_lock:
        attempts = [t for t in _login_failures.get(client_ip, []) if now_ts - t < 60]
        _login_failures[client_ip] = attempts
        if len(attempts) >= 5:
            registrar_evento('CRITICAL', f"Bloqueo temporal por exceso de intentos de login desde IP: {client_ip}")
            return jsonify({
                "status": "error",
                "error": "Demasiados intentos fallidos. Por favor espere 1 minuto antes de reintentar."
            }), 429

    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    auth_cfg = load_auth_config()
    expected_user = auth_cfg.get("admin_user", "admin")
    expected_hash = auth_cfg.get("admin_pass_hash")
    expected_raw = auth_cfg.get("admin_pass")
    
    is_valid = False
    if username == expected_user:
        if expected_hash:
            try:
                is_valid = check_password_hash(expected_hash, password)
            except Exception:
                is_valid = False
        elif expected_raw:
            is_valid = (password == expected_raw)
            # Auto-migración a hash seguro
            if is_valid:
                try:
                    new_hash = generate_password_hash(password)
                    with open(admin_creds_file, 'w') as f:
                        json.dump({"enabled": True, "admin_user": username, "admin_pass_hash": new_hash}, f, indent=4)
                    os.chmod(admin_creds_file, 0o600)
                except Exception:
                    pass

    if is_valid:
        with _login_lock:
            _login_failures.pop(client_ip, None)
        session['is_admin'] = True
        session['user'] = username
        session['login_time'] = datetime.now().isoformat()
        registrar_evento('INFO', f"Operador '{username}' inició sesión en Centro de Mando C5")
        return jsonify({"status": "ok", "message": "Acceso concedido", "redirect": "/admin"})
    else:
        with _login_lock:
            _login_failures.setdefault(client_ip, []).append(now_ts)
        registrar_evento('WARN', f"Intento fallido de inicio de sesión para usuario: '{username}' desde {client_ip}")
        return jsonify({"status": "error", "error": "Credenciales inválidas. Verifique usuario y contraseña."}), 401

@app.route('/api/auth/logout', methods=['POST', 'GET'])
def api_logout():
    user = session.get('user', 'admin')
    session.clear()
    registrar_evento('INFO', f"Operador '{user}' cerró sesión")
    if request.is_json:
        return jsonify({"status": "ok", "message": "Sesión cerrada"})
    return redirect(url_for('public_index'))

@app.route('/api/auth/check', methods=['GET'])
def api_auth_check():
    return jsonify({
        "authenticated": bool(session.get('is_admin')),
        "user": session.get('user', None)
    })

# ==========================================
# STREAMING Y TELEMETRÍA PÚBLICA
# ==========================================

@app.route('/video_feed')
def video_feed():
    """Streaming de video MJPEG de baja latencia directo al navegador"""
    def generate():
        while True:
            try:
                if frame_getter_callback is not None:
                    frame_bytes = frame_getter_callback()
                    if frame_bytes is not None:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except (GeneratorExit, BrokenPipeError, ConnectionResetError):
                break
            except Exception:
                pass
            time.sleep(0.033)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retorna el paquete completo de telemetría de forma thread-safe"""
    global cached_hw_metrics
    try:
        cached_hw_metrics = hw_monitor.get_metrics()
    except Exception as e:
        cached_hw_metrics = {"error": str(e)}
        
    with estado_lock:
        estado_global["hardware"] = cached_hw_metrics
        snapshot = dict(estado_global)
    return jsonify(snapshot)

@app.route('/api/health', methods=['GET'])
def get_health():
    """
    Endpoint de Salud Integral (Health-Check) para supervisión C5, orquestadores y monitoreo SCADA.
    Evalúa la disponibilidad de la cámara, Arduino, FSM, DB y hardware.
    """
    global cached_hw_metrics
    try:
        cached_hw_metrics = hw_monitor.get_metrics()
    except Exception as e:
        cached_hw_metrics = {"error": str(e)}

    with estado_lock:
        cam_info = estado_global.get("camara", {})
        ard_info = estado_global.get("arduino", {})
        fsm_status = estado_global.get("status", "DESCONOCIDO")
        modo = estado_global.get("modo", "Normal")
        fps = float(estado_global.get("fps", 0.0))
        emergencia = bool(estado_global.get("emergencia_activa", False))
        f_trans = float(estado_global.get("fase_tiempo_transcurrido", 0.0))
        f_asig = float(estado_global.get("fase_tiempo_asignado", 0.0))
        topologia = estado_global.get("topologia", "desconocida")
        backend = estado_global.get("backend", "CPU")
        corr_info = estado_global.get("corridor", {})

    is_degraded = bool(cam_info.get("modo_degradado", False))
    cam_connected = bool(cam_info.get("connected", False))
    ard_connected = bool(ard_info.get("connected", False))
    is_virtual_ard = bool(ard_info.get("virtual_mode", False))

    db_connected = False
    if db_manager_instance is not None:
        try:
            db_connected = db_manager_instance.is_connected() if hasattr(db_manager_instance, 'is_connected') else True
        except Exception:
            db_connected = False

    if is_degraded or (not ard_connected and not is_virtual_ard):
        overall_status = "degraded"
    elif not cam_connected and not is_degraded and fps == 0:
        overall_status = "unhealthy"
    else:
        overall_status = "healthy"

    health_report = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "node": {
            "topologia": topologia,
            "backend": backend,
            "node_id": corr_info.get("node_id", "STANDALONE") if isinstance(corr_info, dict) else "STANDALONE"
        },
        "subsystems": {
            "camera": {
                "status": "degraded" if is_degraded else ("ok" if cam_connected else "disconnected"),
                "connected": cam_connected,
                "modo_degradado": is_degraded,
                "fps": fps,
                "tipo": cam_info.get("tipo", "Desconocido"),
                "source": cam_info.get("source_raw", "N/A"),
                "consecutive_failed_frames": cam_info.get("consecutive_failed_frames", 0)
            },
            "microcontroller": {
                "status": "ok" if (ard_connected or is_virtual_ard) else "disconnected",
                "connected": ard_connected,
                "virtual_mode": is_virtual_ard,
                "port": ard_info.get("port", "N/A"),
                "last_command": ard_info.get("last_command", "N/A"),
                "last_tx_ago_sec": ard_info.get("last_tx_ago", 0.0),
                "tx_count": ard_info.get("tx_count", 0),
                "reconnects": ard_info.get("reconnects", 0)
            },
            "database": {
                "status": "connected" if db_connected else "local_fallback",
                "connected": db_connected
            },
            "traffic_fsm": {
                "status": "active",
                "phase": fsm_status,
                "mode": modo,
                "emergency_active": emergencia,
                "elapsed_sec": f_trans,
                "assigned_sec": f_asig,
                "remaining_sec": max(0.0, f_asig - f_trans)
            },
            "hardware": {
                "soc_temperature_celsius": cached_hw_metrics.get("temp", 0.0),
                "cpu_usage_pct": cached_hw_metrics.get("cpu", 0.0),
                "ram_usage_pct": cached_hw_metrics.get("ram", 0.0)
            }
        }
    }

    http_code = 200 if overall_status in ("healthy", "degraded") else 503
    return jsonify(health_report), http_code

@app.route('/metrics', methods=['GET'])
def get_prometheus_metrics():
    """
    Exportador de Métricas en formato estándar de Prometheus (OpenMetrics).
    Permite integración con Grafana, Prometheus Agent y dashboards SCADA.
    """
    global cached_hw_metrics
    try:
        cached_hw_metrics = hw_monitor.get_metrics()
    except Exception:
        cached_hw_metrics = {}

    with estado_lock:
        fps = float(estado_global.get("fps", 0.0))
        total_veh = int(estado_global.get("total_acumulado", 0))
        autos_dict = estado_global.get("autos", {})
        curr_veh = sum(autos_dict.values()) if isinstance(autos_dict, dict) else 0
        f_trans = float(estado_global.get("fase_tiempo_transcurrido", 0.0))
        f_asig = float(estado_global.get("fase_tiempo_asignado", 0.0))
        cam_info = estado_global.get("camara", {})
        ard_info = estado_global.get("arduino", {})
        sost = estado_global.get("sostenibilidad", {})
        emergencia = 1 if estado_global.get("emergencia_activa", False) else 0

    degraded = 1 if cam_info.get("modo_degradado", False) else 0
    ard_conn = 1 if ard_info.get("connected", False) or ard_info.get("virtual_mode", False) else 0
    ard_tx = int(ard_info.get("tx_count", 0))
    temp = float(cached_hw_metrics.get("temp", 0.0)) if isinstance(cached_hw_metrics, dict) else 0.0
    cpu = float(cached_hw_metrics.get("cpu", 0.0)) if isinstance(cached_hw_metrics, dict) else 0.0
    ram = float(cached_hw_metrics.get("ram", 0.0)) if isinstance(cached_hw_metrics, dict) else 0.0
    fuel = float(sost.get("combustible_ahorrado_litros", 0.0)) if isinstance(sost, dict) else 0.0
    co2 = float(sost.get("co2_mitigado_kg", 0.0)) if isinstance(sost, dict) else 0.0

    lines = [
        "# HELP fluxa_fps Tasa actual de procesamiento de video en fotogramas por segundo",
        "# TYPE fluxa_fps gauge",
        f"fluxa_fps {fps:.1f}",
        "",
        "# HELP fluxa_vehicles_total Total acumulado de vehiculos detectados en el nodo",
        "# TYPE fluxa_vehicles_total counter",
        f"fluxa_vehicles_total {total_veh}",
        "",
        "# HELP fluxa_vehicles_current Vehiculos en escena actualmente en todas las zonas",
        "# TYPE fluxa_vehicles_current gauge",
        f"fluxa_vehicles_current {curr_veh}",
        "",
        "# HELP fluxa_phase_elapsed_seconds Tiempo transcurrido en la fase semaforica actual",
        "# TYPE fluxa_phase_elapsed_seconds gauge",
        f"fluxa_phase_elapsed_seconds {f_trans:.1f}",
        "",
        "# HELP fluxa_phase_assigned_seconds Tiempo asignado dinamicamente a la fase actual",
        "# TYPE fluxa_phase_assigned_seconds gauge",
        f"fluxa_phase_assigned_seconds {f_asig:.1f}",
        "",
        "# HELP fluxa_degraded_mode_active Estado binario de modo degradado por tiempos fijos fail-safe",
        "# TYPE fluxa_degraded_mode_active gauge",
        f"fluxa_degraded_mode_active {degraded}",
        "",
        "# HELP fluxa_emergency_active Estado binario de corredor de emergencia prioritario activo",
        "# TYPE fluxa_emergency_active gauge",
        f"fluxa_emergency_active {emergencia}",
        "",
        "# HELP fluxa_arduino_connected Estado de comunicacion con el microcontrolador semaforico",
        "# TYPE fluxa_arduino_connected gauge",
        f"fluxa_arduino_connected {ard_conn}",
        "",
        "# HELP fluxa_arduino_tx_total Total de comandos transmitidos al microcontrolador",
        "# TYPE fluxa_arduino_tx_total counter",
        f"fluxa_arduino_tx_total {ard_tx}",
        "",
        "# HELP fluxa_hardware_temp_celsius Temperatura del procesador central o SoC",
        "# TYPE fluxa_hardware_temp_celsius gauge",
        f"fluxa_hardware_temp_celsius {temp:.1f}",
        "",
        "# HELP fluxa_hardware_cpu_percent Porcentaje de carga del procesador",
        "# TYPE fluxa_hardware_cpu_percent gauge",
        f"fluxa_hardware_cpu_percent {cpu:.1f}",
        "",
        "# HELP fluxa_hardware_ram_percent Porcentaje de ocupacion de memoria RAM",
        "# TYPE fluxa_hardware_ram_percent gauge",
        f"fluxa_hardware_ram_percent {ram:.1f}",
        "",
        "# HELP fluxa_sustainability_fuel_saved_liters Combustible ahorrado en ralentis evitados",
        "# TYPE fluxa_sustainability_fuel_saved_liters counter",
        f"fluxa_sustainability_fuel_saved_liters {fuel:.3f}",
        "",
        "# HELP fluxa_sustainability_co2_mitigated_kg Emisiones de CO2 mitigadas en kilogramos",
        "# TYPE fluxa_sustainability_co2_mitigated_kg counter",
        f"fluxa_sustainability_co2_mitigated_kg {co2:.3f}",
        ""
    ]
    return Response("\n".join(lines), mimetype='text/plain; version=0.0.4; charset=utf-8')

@app.route('/api/v2x/spat', methods=['GET'])
def get_v2x_spat():
    """Retorna el mensaje broadcast V2X SPaT (Signal Phase and Timing)"""
    return jsonify(estado_global.get("v2x", {}))

@app.route('/api/kpis/sustainability', methods=['GET'])
def get_sustainability_kpis():
    """Retorna las métricas de sustentabilidad, combustible y CO2 mitigado"""
    return jsonify(estado_global.get("sostenibilidad", {}))

@app.route('/api/events', methods=['GET'])
def get_events():
    with eventos_lock:
        return jsonify(list(reversed(eventos_sistema)))

@app.route('/api/history', methods=['GET'])
def get_history():
    """Lee las últimas muestras del CSV de hoy para graficar tráfico en Chart.js"""
    try:
        log_files = glob.glob(os.path.join(log_directory, "traffic_log_*.csv"))
        if not log_files:
            return jsonify({"labels": [], "datasets": {}})
            
        latest_file = max(log_files, key=os.path.getctime)
        labels = []
        datasets = {}
        
        with open(latest_file, mode='r') as file:
            reader = list(csv.reader(file))
            if len(reader) > 1:
                headers = reader[0]
                carriles = headers[2:-1]
                for c in carriles:
                    datasets[c] = []
                    
                ultimos = reader[-60:]
                for row in ultimos:
                    if len(row) == len(headers) and row[0] != "Timestamp":
                        time_str = row[0].split(" ")[1]
                        labels.append(time_str)
                        for i, c in enumerate(carriles):
                            try:
                                datasets[c].append(int(row[2+i]))
                            except ValueError:
                                datasets[c].append(0)
                            
        return jsonify({"labels": labels, "datasets": datasets})
    except Exception as e:
        return jsonify({"labels": [], "datasets": {}})

@app.route('/api/reports/summary', methods=['GET'])
def get_reports_summary():
    """Retorna el reporte de Hora Pico y métricas consolidadas desde MariaDB"""
    if db_manager_instance is not None:
        target_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        summary = db_manager_instance.get_peak_hour_summary(target_date)
        return jsonify(summary)
    return jsonify({"error": "Base de datos no disponible", "peak_hour": "N/D", "hourly_distribution": []})

@app.route('/api/violations', methods=['GET'])
def get_violations():
    """Retorna el registro de infracciones viales en luz roja (Protegido o público)"""
    violations = []
    if db_manager_instance is not None:
        try:
            violations = db_manager_instance.get_recent_violations(limit=50)
        except Exception:
            violations = []
            
    if not violations:
        try:
            if os.path.exists(violations_directory):
                files = [f for f in os.listdir(violations_directory) if f.endswith('.jpg') or f.endswith('.png')]
                files.sort(key=lambda x: os.path.getmtime(os.path.join(violations_directory, x)), reverse=True)
                for idx, f in enumerate(files[:50], start=1):
                    full_p = os.path.join(violations_directory, f)
                    mtime = os.path.getmtime(full_p)
                    ts_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    track_id = "N/D"
                    if "_id" in f:
                        try:
                            track_id = int(f.rsplit("_id", 1)[1].split(".")[0])
                        except Exception:
                            pass
                    violations.append({
                        "id": idx,
                        "timestamp": ts_str,
                        "lane": "CARRIL",
                        "lane_name": "CARRIL",
                        "track_id": track_id,
                        "phase_state": "ROJO",
                        "snapshot_path": f
                    })
        except Exception:
            pass
            
    return jsonify(violations)

@app.route('/api/violations/snapshot/<path:filename>')
def get_violation_snapshot(filename):
    """Descarga o visualiza la foto de evidencia de una infracción"""
    clean_name = os.path.basename(filename)
    return send_from_directory(violations_directory, clean_name)

@app.route('/api/corridor/status', methods=['GET'])
def get_corridor_status():
    """Retorna el estado de sincronización del corredor vial y olas verdes activas"""
    if corridor_manager_instance is not None:
        return jsonify(corridor_manager_instance.get_status())
    return jsonify(estado_global.get("corridor", {}))

@app.route('/api/corridor/incoming_platoon', methods=['POST'])
def receive_incoming_platoon_api():
    """Endpoint REST para recibir notificación de pelotón de vehículos desde un nodo adyacente"""
    if not corridor_manager_instance:
        return jsonify({"error": "Gestor de corredor no inicializado"}), 400
    try:
        data = request.get_json(force=True)
        corridor_manager_instance.receive_incoming_platoon(data)
        registrar_evento('INFO', f"Pelotón entrante recibido desde {data.get('origin_node', 'NODO_EXTERNO')} (ETA: {data.get('eta_seconds')}s)")
        return jsonify({"status": "acknowledged", "green_wave_triggered": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/corridor/trigger_wave', methods=['POST'])
def trigger_corridor_wave_api():
    """Permite al operador SCADA C5 forzar o simular una ola verde a lo largo del corredor"""
    if not corridor_manager_instance:
        return jsonify({"error": "Gestor de corredor no inicializado"}), 400
    try:
        data = request.get_json(force=True) if request.is_json else {}
        vehicles = int(data.get("vehicle_count", 5))
        direction = str(data.get("direction", "SUR"))
        corridor_manager_instance.notify_departure_platoon(vehicle_count=vehicles, direction=direction)
        registrar_evento('EMERG', f" Ola Verde Manual iniciada en corredor hacia {direction} (Pelotón: {vehicles} veh)")
        return jsonify({"status": "wave_emitted", "vehicles": vehicles, "direction": direction})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/frame/snapshot')
def get_frame_snapshot():
    """Retorna un cuadro JPEG congelado del flujo de video activo para el Editor Gráfico en Canvas"""
    try:
        if frame_getter_callback is not None:
            frame_bytes = frame_getter_callback()
            if frame_bytes is not None:
                return Response(frame_bytes, mimetype='image/jpeg', headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})
    except Exception as e:
        pass
        
    # Generar cuadro sintético si no hay streaming activo
    placeholder = np.ones((480, 640, 3), dtype=np.uint8) * 20
    cv2.putText(placeholder, "FLUXA SNAPSHOT - NO SIGNAL", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
    ret, buf = cv2.imencode('.jpg', placeholder)
    return Response(buf.tobytes(), mimetype='image/jpeg')

@app.route('/api/models/list', methods=['GET'])
@admin_required
def list_available_models():
    """Lista los modelos YOLO disponibles para el backend activo"""
    backend = estado_global.get("backend", "CPU")
    config_path = os.path.join(base_dir, 'config.json')
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        current_model = cfg.get("ai_model", {}).get("model_file", "yolov8n.pt" if "CPU" in backend else "yolov8n.rknn")
    except Exception:
        current_model = "yolov8n.pt"

    found_models = []
    if "CPU" in backend:
        # Variantes YOLOv8 para CPU PyTorch
        candidates = [
            ("yolov8n.pt", "YOLOv8 Nano (Ultraligero - Máxima Velocidad, 3.2M params)"),
            ("yolov8s.pt", "YOLOv8 Small (Balanceado - 11.2M params)"),
            ("yolov8m.pt", "YOLOv8 Medium (Alta Precisión - 25.9M params)"),
            ("yolov8l.pt", "YOLOv8 Large (Red Pesada - 43.7M params)"),
            ("yolov8x.pt", "YOLOv8 XLarge (Máxima Precisión - 68.2M params)")
        ]
        for c, desc in candidates:
            p1 = os.path.join(base_dir, c)
            p2 = os.path.join(base_dir, 'models', c)
            found_models.append({"filename": c, "name": desc, "available": os.path.exists(p1) or os.path.exists(p2) or True})
    else:
        # RKNN - Escaneo dinámico y descripciones profesionales para Orange Pi 5
        known_descs = {
            "yolov8n.rknn": "YOLOv8 Nano RKNN (NPU INT8 Ultraligero - ~3.4ms)",
            "yolov8s.rknn": "YOLOv8 Small RKNN (NPU INT8 Balanceado - ~10-15ms)",
            "yolov8m.rknn": "YOLOv8 Medium RKNN (NPU INT8 Alta Capacidad - ~25-35ms)",
            "yolov8l.rknn": "YOLOv8 Large RKNN (NPU INT8 Alta Precisión)",
            "yolov8x.rknn": "YOLOv8 XLarge RKNN (NPU INT8 Nivel Servidor Edge)"
        }
        
        # Encontrar archivos .rknn en ./models y ./
        rknn_files = set(["yolov8n.rknn", "yolov8s.rknn", "yolov8m.rknn"])
        models_dir = os.path.join(base_dir, 'models')
        if os.path.exists(models_dir):
            for fn in os.listdir(models_dir):
                if fn.endswith('.rknn'):
                    rknn_files.add(fn)
        for fn in os.listdir(base_dir):
            if fn.endswith('.rknn'):
                rknn_files.add(fn)
                
        preferred_order = ["yolov8n.rknn", "yolov8s.rknn", "yolov8m.rknn", "yolov8l.rknn", "yolov8x.rknn"]
        all_rknn = sorted(list(rknn_files), key=lambda x: preferred_order.index(x) if x in preferred_order else 99)
        
        for c in all_rknn:
            p1 = os.path.join(base_dir, c)
            p2 = os.path.join(base_dir, 'models', c)
            desc = known_descs.get(c, f"YOLOv8 {c.replace('.rknn','').upper()} RKNN (NPU Rockchip RK3588)")
            found_models.append({
                "filename": c, 
                "name": desc, 
                "available": os.path.exists(p1) or os.path.exists(p2)
            })

    return jsonify({
        "backend": backend,
        "current_model": current_model,
        "models": found_models
    })

@app.route('/api/models/set', methods=['POST'])
@admin_required
def set_active_model():
    """Cambia el modelo YOLO activo en memoria y lo persiste en config.json"""
    data = request.json or {}
    model_name = data.get("model_file", "").strip()
    if not model_name:
        return jsonify({"error": "Nombre de modelo no especificado"}), 400
        
    config_path = os.path.join(base_dir, 'config.json')
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        if "ai_model" not in cfg:
            cfg["ai_model"] = {}
        cfg["ai_model"]["model_file"] = model_name
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
            
        if hot_reload_callback_global:
            hot_reload_callback_global()
            
        registrar_evento('INFO', f"Modelo YOLO cambiado en caliente a: {model_name}")
        return jsonify({"status": "ok", "message": f"Modelo YOLO cambiado a {model_name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/full', methods=['GET', 'POST'])
@admin_required
def manage_full_config():
    """Consulta o actualiza la configuración integral (Zonas Poligonales, Tiempos de Semáforo y Parámetros IA)"""
    config_path = os.path.join(base_dir, 'config.json')
    
    if request.method == 'GET':
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            topologia_activa = estado_global.get("topologia", "4_way")
            return jsonify({
                "topologia_activa": topologia_activa,
                "backend": estado_global.get("backend", "CPU"),
                "zones": cfg.get("zones", {}),
                "traffic_light": cfg.get("traffic_light", {}),
                "ai_model": cfg.get("ai_model", {}),
                "corridor": cfg.get("corridor", {})
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        data = request.json or {}
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                
            if "zones" in data and isinstance(data["zones"], dict):
                for topo, topo_zones in data["zones"].items():
                    if "zones" not in cfg:
                        cfg["zones"] = {}
                    cfg["zones"][topo] = topo_zones
                    
            if "traffic_light" in data and isinstance(data["traffic_light"], dict):
                for k, v in data["traffic_light"].items():
                    cfg["traffic_light"][k] = float(v)
                    
            if "ai_model" in data and isinstance(data["ai_model"], dict):
                for k, v in data["ai_model"].items():
                    if k in ["confidence_threshold", "iou_threshold"]:
                        cfg["ai_model"][k] = float(v)
                    elif k == "model_file":
                        cfg["ai_model"][k] = str(v)
                        
            if "corridor" in data and isinstance(data["corridor"], dict):
                if "corridor" not in cfg:
                    cfg["corridor"] = {}
                for k, v in data["corridor"].items():
                    if k == "avg_speed_kmh":
                        cfg["corridor"][k] = float(v)
                        if corridor_manager_instance:
                            corridor_manager_instance.avg_speed_kmh = max(20.0, float(v))
                            corridor_manager_instance.avg_speed_mps = (corridor_manager_instance.avg_speed_kmh * 1000.0) / 3600.0
                    elif k == "enabled":
                        cfg["corridor"][k] = bool(v)
                        if corridor_manager_instance:
                            corridor_manager_instance.enabled = bool(v)
                    else:
                        cfg["corridor"][k] = v
                        
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=4)
                
            if hot_reload_callback_global:
                hot_reload_callback_global()
                
            registrar_evento('INFO', "Configuración y ROIs actualizados en caliente desde el Calibrador Visual")
            return jsonify({"status": "ok", "message": "Configuración, polígonos y tiempos aplicados en caliente"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/config/zones', methods=['GET', 'POST'])
@admin_required
def manage_zones_config():
    """Permite consultar y guardar polígonos de carriles en caliente desde la WebUI"""
    config_path = os.path.join(base_dir, 'config.json')
    
    if request.method == 'GET':
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            topologia_activa = estado_global.get("topologia", "4_way")
            return jsonify({
                "topologia": topologia_activa,
                "zones": cfg.get("zones", {}).get(topologia_activa, {})
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        data = request.json or {}
        topologia = data.get("topologia", estado_global.get("topologia", "4_way"))
        nuevas_zonas = data.get("zones", {})
        
        if not nuevas_zonas:
            return jsonify({"error": "Zonas vacías"}), 400
            
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                
            if "zones" not in cfg:
                cfg["zones"] = {}
            cfg["zones"][topologia] = nuevas_zonas
            
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=4)
                
            if hot_reload_callback_global:
                hot_reload_callback_global()
                
            registrar_evento('INFO', f"Polígonos de {topologia} calibrados y guardados exitosamente")
            return jsonify({"status": "ok", "message": "Calibración guardada y aplicada en caliente"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/video_source/list', methods=['GET'])
@admin_required
def list_video_sources():
    """Lista los clips de video válidos disponibles en el servidor y la fuente actual activa"""
    video_files = []
    if os.path.exists(videos_directory):
        for fn in sorted(os.listdir(videos_directory)):
            if fn.startswith('.') or '.crdownload' in fn or '.part' in fn:
                continue
            if any(fn.lower().endswith(ext) for ext in VALID_VIDEO_EXTENSIONS):
                path = os.path.join(videos_directory, fn)
                try:
                    size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
                    video_files.append({
                        "filename": fn,
                        "path": path,
                        "size_mb": size_mb
                    })
                except Exception:
                    pass
            
    return jsonify({
        "current_source": estado_global.get("camara", {}).get("source_raw", "0"),
        "current_type": estado_global.get("camara", {}).get("tipo", "Cámara"),
        "available_videos": video_files
    })

@app.route('/api/video_source/set', methods=['POST'])
@admin_required
def set_video_source():
    """Permite alternar entre Cámara en Vivo y un Clip de Video de Demostración"""
    global change_source_callback_global
    if not change_source_callback_global:
        return jsonify({"error": "Controlador de video no enlazado"}), 500
        
    data = request.json or {}
    source_type = data.get("type", "camera")
    
    if source_type == "camera":
        cam_idx = int(data.get("index", 0))
        success, msg = change_source_callback_global(cam_idx)
        if success:
            registrar_evento('INFO', f"Entrada de video conmutada a CÁMARA EN VIVO ({cam_idx})")
            return jsonify({"status": "ok", "message": msg})
        else:
            return jsonify({"error": msg}), 400
            
    elif source_type == "video":
        filename = data.get("filename", "")
        if not filename:
            return jsonify({"error": "Nombre de archivo no especificado"}), 400
        video_path = os.path.join(videos_directory, filename)
        if not os.path.exists(video_path):
            return jsonify({"error": f"El archivo '{filename}' no existe en la carpeta videos/"}), 404
            
        success, msg = change_source_callback_global(video_path)
        if success:
            registrar_evento('INFO', f"Entrada de video conmutada a CLIP DEMO: {filename}")
            return jsonify({"status": "ok", "message": msg})
        else:
            return jsonify({"error": msg}), 400
    else:
        custom_path = str(data.get("path", "")).strip()
        if custom_path:
            # 1. Si es índice numérico de cámara
            if custom_path.isdigit():
                cam_idx = int(custom_path)
                success, msg = change_source_callback_global(cam_idx)
            # 2. Si es flujo de red seguro (RTSP / HTTP / HTTPS)
            elif custom_path.startswith(('rtsp://', 'http://', 'https://')):
                success, msg = change_source_callback_global(custom_path)
            # 3. Archivo local: Validación estricta de ruta (Defensa en profundidad contra Path Traversal)
            else:
                real_target = os.path.realpath(os.path.abspath(custom_path))
                real_videos_dir = os.path.realpath(os.path.abspath(videos_directory))
                if not (real_target == real_videos_dir or real_target.startswith(real_videos_dir + os.sep)) or not os.path.exists(real_target):
                    return jsonify({
                        "error": "Acceso denegado: Por seguridad, solo se permiten fuentes dentro del directorio videos/ o flujos de red (RTSP/HTTP)."
                    }), 403
                success, msg = change_source_callback_global(real_target)
                
            if success:
                registrar_evento('INFO', f"Entrada de video conmutada a: {custom_path}")
                return jsonify({"status": "ok", "message": msg})
            else:
                return jsonify({"error": msg}), 400
        return jsonify({"error": "Tipo de fuente inválido"}), 400

@app.route('/api/video_source/upload', methods=['POST'])
@admin_required
def upload_video():
    """Permite subir un archivo de video desde el navegador con validación previa de integridad"""
    global change_source_callback_global
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Archivo vacío"}), 400
        
    orig_name = file.filename
    lower_name = orig_name.lower()
    
    if not any(lower_name.endswith(ext) for ext in VALID_VIDEO_EXTENSIONS):
        return jsonify({"error": f"Formato no compatible. Por favor sube un archivo de video válido ({', '.join(VALID_VIDEO_EXTENSIONS)})."}), 400

    if '.crdownload' in lower_name or '.part' in lower_name or '.tmp' in lower_name:
        return jsonify({"error": "El archivo parece estar en descarga o incompleto. Espera a que termine de descargarse antes de subirlo."}), 400

    safe_filename = "".join(c for c in orig_name if c.isalnum() or c in "._- ")
    dest_path = os.path.join(videos_directory, safe_filename)
    
    try:
        file.save(dest_path)
    except Exception as e:
        return jsonify({"error": f"Falla guardando el archivo: {e}"}), 500

    # Validación con OpenCV para asegurar que el codec es reproducible
    try:
        test_cap = cv2.VideoCapture(dest_path)
        if not test_cap.isOpened():
            test_cap.release()
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return jsonify({"error": "El archivo de video no pudo ser decodificado por OpenCV. Verifica el codec del video."}), 400
            
        ret, test_frame = test_cap.read()
        test_cap.release()
        if not ret or test_frame is None:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return jsonify({"error": "El video está corrupto o no contiene fotogramas válidos."}), 400
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return jsonify({"error": f"Error verificando integridad del video: {e}"}), 400

    auto_play = request.form.get("autoplay", "true").lower() == "true"
    if auto_play and change_source_callback_global:
        success, msg = change_source_callback_global(dest_path)
        if not success:
            return jsonify({"error": f"Video subido pero no pudo ser reproducido: {msg}"}), 400
        registrar_evento('INFO', f"Nuevo video subido y activo: {safe_filename}")
        
    return jsonify({
        "status": "ok",
        "filename": safe_filename,
        "message": f"Clip '{safe_filename}' cargado y reproduciéndose exitosamente"
    })

@app.route('/api/logs/download', methods=['GET'])
@admin_required
def download_log():
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(log_directory, f"traffic_log_{date_str}.csv")
        if os.path.exists(filename):
            return send_file(filename, as_attachment=True, download_name=f"fluxa_traffic_{date_str}.csv")
        return jsonify({"error": "No hay registro de hoy disponible aún"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/control', methods=['POST'])
@admin_required
def control():
    """Control de fases, emergencias y corredores C5"""
    global control_callback
    if not control_callback:
        return jsonify({"error": "Controlador semafórico no enlazado"}), 500
        
    data = request.json or {}
    action = data.get("action", "")
    target = data.get("target", "")
    
    if action == "force_phase" or action in ["force_ns", "force_eo", "force_a", "force_b", "force_principal", "force_secundaria", "force_frente", "force_giro", "force_peatones"]:
        cmd = target if target else action.replace("force_", "").upper()
        control_callback(cmd)
        registrar_evento('EMERG', f"Control Remoto C5 activó prioridad: {cmd}")
        return jsonify({"message": f"Prioridad activada para {cmd}", "status": "ok"})
    elif action == "emergency_corridor":
        eje = target if target else "NS"
        control_callback(eje)
        registrar_evento('EMERG', f" CORREDOR DE EMERGENCIA C5 ACTIVADO PARA EJE {eje}")
        return jsonify({"message": f" Corredor de Emergencia despejado para {eje}", "status": "ok"})
    elif action == "pedestrian_call":
        control_callback("PEATONES")
        registrar_evento('INFO', "Demanda peatonal forzada vía API C5")
        return jsonify({"message": "Llamada peatonal registrada", "status": "ok"})
    elif action == "reset":
        control_callback("RESET")
        registrar_evento('INFO', "Modo Normal restaurado vía API C5")
        return jsonify({"message": "Ciclo semafórico normal restaurado", "status": "ok"})
    elif action == "set_mode":
        modo = data.get("mode", "Normal")
        control_callback(f"MODE:{modo}")
        registrar_evento('INFO', f"Modo de operación cambiado a: {modo}")
        return jsonify({"message": f"Modo configurado a {modo}", "status": "ok"})
    else:
        return jsonify({"error": f"Acción desconocida '{action}'"}), 400


change_arduino_port_callback_global = None

class TelemetryAPI:
    def __init__(self, host='0.0.0.0', port=5000, enabled=True):
        self.host = host
        self.port = port
        self.enabled = enabled
        self.thread = None

    def start(self, controller_callback=None, frame_getter=None, db_instance=None, hot_reload_callback=None, change_source_callback=None, corridor_instance=None, change_arduino_port_callback=None):
        global control_callback, frame_getter_callback, db_manager_instance, hot_reload_callback_global, change_source_callback_global, corridor_manager_instance, change_arduino_port_callback_global, server_port_global
        control_callback = controller_callback
        frame_getter_callback = frame_getter
        db_manager_instance = db_instance
        hot_reload_callback_global = hot_reload_callback
        change_source_callback_global = change_source_callback
        corridor_manager_instance = corridor_instance
        change_arduino_port_callback_global = change_arduino_port_callback
        server_port_global = self.port
        
        if not self.enabled:
            return
            
        print(f" Servidor Web de Comando y Streaming listo en http://{self.host}:{self.port}")
        self.thread = threading.Thread(target=self._run_flask, daemon=True)
        self.thread.start()
        registrar_evento('INFO', f"Servidor API y Telemetría iniciado en puerto {self.port}")

    def _run_flask(self):
        app.run(host=self.host, port=self.port, debug=False, use_reloader=False, threaded=True)

    def log_event(self, tipo, mensaje):
        registrar_evento(tipo, mensaje)

    def get_cached_hw_metrics(self):
        global cached_hw_metrics
        return cached_hw_metrics

    def update_state(self, topologia, backend, status_msg, autos_dict, autos_acumulados, fps, modo, 
                     arduino_info, camara_info, latencias, f_transcurrido=0, f_asignado=0,
                     emergencia_activa=False, eje_emergencia=None, demanda_ponderada=None,
                     sostenibilidad=None, v2x=None, ai_engine=None, corridor=None, semaforos=None):
        if not self.enabled:
            return
            
        with estado_lock:
            estado_global["topologia"] = topologia
            estado_global["backend"] = backend
            estado_global["status"] = status_msg
            estado_global["autos"] = autos_dict.copy()
            estado_global["autos_acumulados"] = autos_acumulados.copy()
            estado_global["total_acumulado"] = sum(autos_acumulados.values())
            if demanda_ponderada is not None:
                estado_global["demanda_ponderada"] = demanda_ponderada.copy()
            if sostenibilidad is not None:
                estado_global["sostenibilidad"] = sostenibilidad.copy()
            if v2x is not None:
                estado_global["v2x"] = v2x.copy()
            if ai_engine is not None:
                estado_global["ai_engine"] = ai_engine.copy()
            if corridor is not None:
                estado_global["corridor"] = corridor.copy()
            if semaforos is not None:
                estado_global["semaforos"] = semaforos.copy()
            estado_global["fps"] = round(fps, 1)
            estado_global["modo"] = modo
            estado_global["emergencia_activa"] = emergencia_activa
            estado_global["eje_emergencia"] = eje_emergencia
            estado_global["fase_tiempo_transcurrido"] = round(f_transcurrido, 1)
            estado_global["fase_tiempo_asignado"] = round(f_asignado, 1)
            estado_global["arduino"] = arduino_info
            estado_global["camara"] = camara_info
            estado_global["latencias_ms"] = latencias

server_port_global = 5000

@app.route('/api/config/arduino_ports', methods=['GET'])
@admin_required
def list_arduino_ports():
    import glob
    import serial.tools.list_ports
    from arduino_locker import inspect_port_lock

    my_node_port = server_port_global or 5000
    current_ard = estado_global.get("arduino", {})
    current_port_name = current_ard.get("port")
    is_virtual_active = current_ard.get("virtual_mode", False) or (current_port_name in ["Virtual (Simulado)", "VIRTUAL"])

    ports_detected = {}
    try:
        for p in serial.tools.list_ports.comports():
            ports_detected[p.device] = p.description or f"Dispositivo Serial ({p.device})"
    except Exception:
        pass

    for dev in sorted(glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')):
        if dev not in ports_detected:
            ports_detected[dev] = f"Microcontrolador Serial ({os.path.basename(dev)})"

    port_list = []
    # Opción Semáforo Virtual
    port_list.append({
        "port": "VIRTUAL",
        "desc": "Semáforos Virtuales (Gemelo Digital / Sin Hardware)",
        "status": "propio" if is_virtual_active else "disponible",
        "locked_by": f"Nodo {my_node_port} (Virtual)" if is_virtual_active else None,
        "is_current": is_virtual_active,
        "available": True
    })

    for dev, desc in ports_detected.items():
        info = inspect_port_lock(dev, current_node_port=my_node_port)
        is_cur = (current_port_name == dev and not is_virtual_active)
        available = (not info["is_locked"]) or info["is_mine"]
        port_list.append({
            "port": dev,
            "desc": desc,
            "status": info["status"],  # "disponible", "propio", "ocupado"
            "locked_by": info.get("owner"),
            "is_current": is_cur,
            "available": available
        })

    return jsonify({
        "ports": port_list,
        "status": "ok",
        "node_port": my_node_port,
        "current_port": current_port_name,
        "virtual_mode": is_virtual_active
    })

@app.route('/api/config/arduino_port', methods=['POST'])
@admin_required
def set_arduino_port_api():
    global change_arduino_port_callback_global
    if not change_arduino_port_callback_global:
        return jsonify({"error": "Controlador de Arduino no enlazado"}), 500
        
    data = request.json or {}
    port = data.get("port")
    if not port:
        return jsonify({"error": "Se requiere el parámetro 'port'"}), 400
        
    res = change_arduino_port_callback_global(port)
    if isinstance(res, dict) and res.get("status") == "error":
        return jsonify(res), 409
    
    msg = res.get("message", f"Puerto del Arduino cambiado a {port}") if isinstance(res, dict) else f"Puerto cambiado a {port}"
    registrar_evento('INFO', f"Asignación exclusiva serial: {msg}")
    return jsonify({"message": msg, "status": "ok"})
