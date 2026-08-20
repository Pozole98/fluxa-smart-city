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

# Silenciar logs excesivos de Flask/Werkzeug
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get("FLUXA_SECRET_KEY", secrets.token_hex(32))

# Endurecimiento de cookies de sesión (P0.4)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get("FLUXA_ENV", "dev").lower() == "production"
)

# Rate Limiter (P0.3)
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
        "aviso_conductor": "🟢 Mantenga 40-50 km/h (Ola Verde Activa)",
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
    "camara": {
        "connected": False,
        "resolution": "640x480",
        "tipo": "Auto-Detect",
        "source_raw": "0"
    },
    "hardware": {}
}

eventos_sistema = []
eventos_lock = threading.Lock()

control_callback = None
frame_getter_callback = None
hot_reload_callback_global = None
change_source_callback_global = None
db_manager_instance = None

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

def load_auth_config():
    """
    Carga la configuración de autenticación con hash seguro.
    Si no existen credenciales configuradas, genera una contraseña aleatoria de 12 caracteres,
    la almacena de forma segura en instance/admin_credentials.json con hash pbkdf2/sha256 y la muestra una única vez.
    """
    # 1. Prioridad: Archivo local protegido instance/admin_credentials.json
    if os.path.exists(admin_creds_file):
        try:
            with open(admin_creds_file, 'r') as f:
                creds = json.load(f)
                if creds.get("admin_pass_hash") or creds.get("admin_pass"):
                    return {
                        "enabled": creds.get("enabled", True),
                        "admin_user": creds.get("admin_user", "admin"),
                        "admin_pass_hash": creds.get("admin_pass_hash"),
                        "admin_pass": creds.get("admin_pass")
                    }
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
                    return auth_cfg
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
        print(f"⚠️ Error guardando credenciales seguras: {e}")

    print("\n" + "=" * 72)
    print("⚠️  FLUXA SEGURIDAD: Credenciales de Administrador C5 Generadas")
    print("👤 Usuario:     admin")
    print(f"🔑 Contraseña:  {raw_pass}")
    print("ℹ️  Guarda esta contraseña de forma segura. No se volverá a mostrar en texto plano.")
    print("💡 Para cambiarla: python3 scripts/set_admin_password.py")
    print("=" * 72 + "\n")

    return auto_creds

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
            except Exception:
                pass
            time.sleep(0.033)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retorna el paquete completo de telemetría"""
    global cached_hw_metrics
    try:
        cached_hw_metrics = hw_monitor.get_metrics()
        estado_global["hardware"] = cached_hw_metrics
    except Exception as e:
        estado_global["hardware"] = {"error": str(e)}
        
    return jsonify(estado_global)

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
                "ai_model": cfg.get("ai_model", {})
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
        registrar_evento('EMERG', f"🚨 CORREDOR DE EMERGENCIA C5 ACTIVADO PARA EJE {eje}")
        return jsonify({"message": f"🚨 Corredor de Emergencia despejado para {eje}", "status": "ok"})
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


class TelemetryAPI:
    def __init__(self, host='0.0.0.0', port=5000, enabled=True):
        self.host = host
        self.port = port
        self.enabled = enabled
        self.thread = None

    def start(self, controller_callback=None, frame_getter=None, db_instance=None, hot_reload_callback=None, change_source_callback=None):
        global control_callback, frame_getter_callback, db_manager_instance, hot_reload_callback_global, change_source_callback_global
        control_callback = controller_callback
        frame_getter_callback = frame_getter
        db_manager_instance = db_instance
        hot_reload_callback_global = hot_reload_callback
        change_source_callback_global = change_source_callback
        
        if not self.enabled:
            return
            
        print(f"🌐 Servidor Web de Comando y Streaming listo en http://{self.host}:{self.port}")
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
                     sostenibilidad=None, v2x=None, ai_engine=None):
        if not self.enabled:
            return
            
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
        estado_global["fps"] = round(fps, 1)
        estado_global["modo"] = modo
        estado_global["emergencia_activa"] = emergencia_activa
        estado_global["eje_emergencia"] = eje_emergencia
        estado_global["fase_tiempo_transcurrido"] = round(f_transcurrido, 1)
        estado_global["fase_tiempo_asignado"] = round(f_asignado, 1)
        estado_global["arduino"] = arduino_info
        estado_global["camara"] = camara_info
        estado_global["latencias_ms"] = latencias
