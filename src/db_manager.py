import os
import time
import json
import queue
import threading
import collections
import logging
from datetime import datetime
import pymysql

class DatabaseManager:
    """
    Gestor asíncrono de persistencia en MariaDB para FLUXA con tolerancia a fallos.
    Utiliza una cola en segundo plano (Worker Thread) para garantizar que las escrituras
    en base de datos nunca bloqueen el ciclo de procesamiento de IA ni bajen los FPS.
    Si MariaDB no está disponible, mantiene un buffer local en memoria y en disco.
    """
    def __init__(self, host="localhost", user="root", password=None, db_name="fluxa_traffic", port=3306, enabled=True):
        self.host = os.environ.get("DATABASE_HOST", host)
        self.user = os.environ.get("DATABASE_USER", user)
        self.db_name = os.environ.get("DATABASE_NAME", db_name)
        self.port = int(os.environ.get("DATABASE_PORT", port))
        self.enabled = enabled
        
        # Buffer en memoria para tolerancia a fallos (Fail-Safe)
        self._local_violations = collections.deque(maxlen=200)
        self._local_events = collections.deque(maxlen=200)
        self._lock = threading.Lock()
        
        # Resolución segura de contraseña (P0.1)
        db_pass = os.environ.get("DATABASE_PASSWORD", password)
        if self.enabled and (db_pass is None or db_pass == ""):
            raise ValueError(
                "\n❌ Error de configuración crítico en DatabaseManager:\n"
                "   La contraseña de MariaDB no está definida.\n"
                "💡 Solución:\n"
                "   • Exporta la variable de entorno: export DATABASE_PASSWORD='<TU_CONTRASEÑA>'\n"
                "   • O especifícala en tu archivo config.json / .env / docker-compose.yml.\n"
            )
        self.password = db_pass or ""
        
        self.connected = False
        self.write_queue = queue.Queue(maxsize=1000)
        self.worker_thread = None
        self.running = False
        
        if self.enabled:
            self._init_db_schema()
            self.running = True
            self.worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
            self.worker_thread.start()

    def _get_connection(self, use_db=True):
        return pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.db_name if use_db else None,
            port=self.port,
            connect_timeout=3,
            cursorclass=pymysql.cursors.DictCursor
        )

    def _init_db_schema(self):
        """Crea la base de datos y las tablas relacionales si no existen"""
        try:
            conn = self._get_connection(use_db=False)
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.close()

            conn = self._get_connection(use_db=True)
            with conn.cursor() as cur:
                # Tabla de telemetría vial y de hardware periódica
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS traffic_telemetry (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        topology VARCHAR(50) NOT NULL,
                        active_phase VARCHAR(50) NOT NULL,
                        total_cars INT NOT NULL,
                        lane_counts_json TEXT NOT NULL,
                        weighted_demand FLOAT NOT NULL,
                        cpu_percent FLOAT,
                        cpu_temp_c FLOAT,
                        ram_percent FLOAT,
                        fps FLOAT,
                        INDEX idx_time (timestamp)
                    ) ENGINE=InnoDB;
                """)

                # Tabla de eventos del sistema (transiciones, alarmas, emergencias)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS system_events (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        event_type VARCHAR(20) NOT NULL,
                        message VARCHAR(255) NOT NULL,
                        INDEX idx_time (timestamp)
                    ) ENGINE=InnoDB;
                """)

                # Tabla de infracciones por paso en luz roja
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS red_light_violations (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        lane VARCHAR(50) NOT NULL,
                        track_id INT NOT NULL,
                        phase_state VARCHAR(50) NOT NULL,
                        snapshot_path VARCHAR(255),
                        INDEX idx_time (timestamp)
                    ) ENGINE=InnoDB;
                """)
            conn.commit()
            conn.close()
            self.connected = True
            print("🗄️ Base de datos MariaDB inicializada exitosamente (Esquema 'fluxa_traffic').")
        except Exception as e:
            self.connected = False
            print(f"⚠️ Advertencia MariaDB: No se pudo conectar al servidor: {e}. Operando con registro local.")

    def _queue_worker(self):
        """Hilo trabajador en segundo plano que procesa las inserciones en MariaDB"""
        while self.running:
            try:
                task = self.write_queue.get(timeout=2.0)
                if task is None:
                    break
                    
                task_type, data = task
                self._execute_insert(task_type, data)
                self.write_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.warning(f"⚠️ Error en worker MariaDB: {e}")

    def _execute_insert(self, task_type, data):
        try:
            conn = self._get_connection(use_db=True)
            with conn.cursor() as cur:
                if task_type == "TELEMETRY":
                    sql = """
                        INSERT INTO traffic_telemetry 
                        (timestamp, topology, active_phase, total_cars, lane_counts_json, weighted_demand, cpu_percent, cpu_temp_c, ram_percent, fps)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(sql, (
                        data["timestamp"], data["topology"], data["active_phase"], data["total_cars"],
                        json.dumps(data["lane_counts"]), data.get("weighted_demand", 0.0),
                        data.get("cpu_percent", 0.0), data.get("cpu_temp_c", 0.0),
                        data.get("ram_percent", 0.0), data.get("fps", 0.0)
                    ))
                elif task_type == "EVENT":
                    sql = "INSERT INTO system_events (timestamp, event_type, message) VALUES (%s, %s, %s)"
                    cur.execute(sql, (data["timestamp"], data["event_type"], data["message"]))
                elif task_type == "VIOLATION":
                    sql = """
                        INSERT INTO red_light_violations 
                        (timestamp, lane, track_id, phase_state, snapshot_path)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(sql, (
                        data["timestamp"], data["lane"], data["track_id"],
                        data["phase_state"], data.get("snapshot_path", "")
                    ))
            conn.commit()
            conn.close()
            self.connected = True
        except Exception:
            self.connected = False

    def log_telemetry_async(self, topology, active_phase, total_cars, lane_counts, weighted_demand=0.0, cpu_percent=0.0, cpu_temp_c=0.0, ram_percent=0.0, fps=0.0):
        if not self.enabled:
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "timestamp": now_str,
            "topology": topology,
            "active_phase": active_phase,
            "total_cars": total_cars,
            "lane_counts": lane_counts,
            "weighted_demand": weighted_demand,
            "cpu_percent": cpu_percent,
            "cpu_temp_c": cpu_temp_c,
            "ram_percent": ram_percent,
            "fps": fps
        }
        try:
            self.write_queue.put_nowait(("TELEMETRY", data))
        except queue.Full:
            pass

    def log_event_async(self, event_type, message):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            self._local_events.appendleft({"timestamp": now_str, "event_type": event_type, "message": message})
        if not self.enabled:
            return
        try:
            self.write_queue.put_nowait(("EVENT", {"timestamp": now_str, "event_type": event_type, "message": message}))
        except queue.Full:
            pass

    def log_violation_async(self, lane, track_id, phase_state, snapshot_path):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_snapshot = os.path.basename(snapshot_path) if snapshot_path else ""
        record = {
            "id": int(time.time() * 1000) % 10000000,
            "timestamp": now_str,
            "lane": lane,
            "lane_name": lane,
            "track_id": track_id,
            "phase_state": phase_state,
            "snapshot_path": clean_snapshot
        }
        with self._lock:
            self._local_violations.appendleft(record)

        if not self.enabled:
            return
        try:
            self.write_queue.put_nowait(("VIOLATION", {
                "timestamp": now_str,
                "lane": lane,
                "track_id": track_id,
                "phase_state": phase_state,
                "snapshot_path": clean_snapshot
            }))
        except queue.Full:
            pass

    def get_peak_hour_summary(self, target_date=None):
        """Calcula analítica de Hora Pico y volumen vehicular del día desde MariaDB con fallback local"""
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
            
        try:
            conn = self._get_connection(use_db=True)
            with conn.cursor() as cur:
                # Distribución por hora del día
                sql_hourly = """
                    SELECT HOUR(timestamp) as hora, AVG(total_cars) as avg_cars, MAX(total_cars) as max_cars, COUNT(*) as muestras
                    FROM traffic_telemetry
                    WHERE DATE(timestamp) = %s
                    GROUP BY HOUR(timestamp)
                    ORDER BY hora ASC;
                """
                cur.execute(sql_hourly, (target_date,))
                hourly_data = cur.fetchall()

                # Total de infracciones hoy
                cur.execute("SELECT COUNT(*) as total_violations FROM red_light_violations WHERE DATE(timestamp) = %s;", (target_date,))
                res_viol = cur.fetchone()
                total_violations = res_viol["total_violations"] if res_viol else 0

                # Promedios de hardware
                cur.execute("""
                    SELECT AVG(cpu_percent) as avg_cpu, AVG(cpu_temp_c) as avg_temp, AVG(ram_percent) as avg_ram, AVG(fps) as avg_fps
                    FROM traffic_telemetry
                    WHERE DATE(timestamp) = %s;
                """, (target_date,))
                hw_summary = cur.fetchone() or {}

            conn.close()

            # Determinar hora pico
            peak_hour = None
            peak_volume = 0
            for row in hourly_data:
                if row["avg_cars"] > peak_volume:
                    peak_volume = row["avg_cars"]
                    peak_hour = f"{row['hora']:02d}:00 - {row['hora']+1:02d}:00"

            return {
                "date": target_date,
                "peak_hour": peak_hour or "N/D (Insuficientes datos)",
                "peak_avg_volume": round(peak_volume, 1),
                "hourly_distribution": hourly_data,
                "total_violations_today": total_violations,
                "hardware_averages": {
                    "avg_cpu": round(hw_summary.get("avg_cpu") or 0.0, 1),
                    "avg_temp_c": round(hw_summary.get("avg_temp") or 0.0, 1),
                    "avg_ram": round(hw_summary.get("avg_ram") or 0.0, 1),
                    "avg_fps": round(hw_summary.get("avg_fps") or 0.0, 1)
                }
            }
        except Exception:
            # Fallback local
            with self._lock:
                local_count = sum(1 for v in self._local_violations if str(v.get("timestamp", "")).startswith(target_date))
            return {
                "date": target_date,
                "peak_hour": "N/D (Modo local)",
                "peak_avg_volume": 0.0,
                "hourly_distribution": [],
                "total_violations_today": local_count,
                "hardware_averages": {
                    "avg_cpu": 0.0, "avg_temp_c": 0.0, "avg_ram": 0.0, "avg_fps": 0.0
                }
            }

    def get_recent_violations(self, limit=50):
        """Retorna las infracciones más recientes registradas en MariaDB o en el buffer local de respaldo"""
        if self.enabled:
            try:
                conn = self._get_connection(use_db=True)
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, DATE_FORMAT(timestamp, '%%Y-%%m-%%d %%H:%%i:%%s') as timestamp, 
                               lane, lane as lane_name, track_id, phase_state, snapshot_path
                        FROM red_light_violations
                        ORDER BY id DESC
                        LIMIT %s;
                    """, (limit,))
                    rows = cur.fetchall()
                conn.close()
                if rows and len(rows) > 0:
                    return rows
            except Exception:
                pass

        # 1. Fallback a buffer local en RAM
        with self._lock:
            if self._local_violations and len(self._local_violations) > 0:
                return list(self._local_violations)[:limit]

        # 2. Fallback escaneando archivos en logs/violations/
        return self._scan_disk_violations(limit=limit)

    def _scan_disk_violations(self, limit=50):
        """Reconstruye infracciones a partir de las fotos guardadas en el disco"""
        violations_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'violations')
        if not os.path.exists(violations_dir):
            return []
            
        results = []
        try:
            files = [f for f in os.listdir(violations_dir) if f.endswith('.jpg') or f.endswith('.png')]
            # Ordenar por fecha de modificación descendente
            files.sort(key=lambda x: os.path.getmtime(os.path.join(violations_dir, x)), reverse=True)
            
            for idx, f in enumerate(files[:limit], start=1):
                full_path = os.path.join(violations_dir, f)
                mtime = os.path.getmtime(full_path)
                ts_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                # Extraer track_id si el nombre sigue el patrón violation_YYYYMMDD_HHMMSS_idX.jpg
                track_id = "N/D"
                if "_id" in f:
                    try:
                        part = f.rsplit("_id", 1)[1].split(".")[0]
                        track_id = int(part)
                    except Exception:
                        pass
                        
                results.append({
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
            
        return results

    def close(self):
        self.running = False
        if self.worker_thread:
            self.write_queue.put(None)
            self.worker_thread.join(timeout=2)
