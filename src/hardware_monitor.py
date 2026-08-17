import os
import time
import socket
import psutil
from datetime import timedelta

class HardwareMonitor:
    """
    Monitor de métricas de bajo nivel para plataformas Edge (Linux x86/ARM, Orange Pi 5 RK3588, Fedora/Ubuntu).
    Captura temperatura de CPU/SoC, uso de recursos, espacio en disco, I/O de red y tiempo de actividad.
    """
    def __init__(self):
        self.start_time = time.time()
        self.hostname = socket.gethostname()
        self._cached_ip = self._get_local_ip()
        self._last_ip_check = time.time()
        
        # Pre-calentar medición de CPU para evitar lecturas de 0.0% iniciales
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)
        
        try:
            self._last_net_io = psutil.net_io_counters()
        except Exception:
            self._last_net_io = None
        self._last_net_time = time.time()
        self.net_speed_kbps = {"rx": 0.0, "tx": 0.0}

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_temperature(self):
        """
        Lee la temperatura del SoC o CPU.
        Compatible con:
        1. psutil.sensors_temperatures() si está soportado.
        2. Linux sysfs /sys/class/thermal/ (Orange Pi 5 RK3588, Raspberry Pi, PCs Linux).
        """
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.current > 0:
                            return round(entry.current, 1)
        except Exception:
            pass

        thermal_paths = [
            "/sys/class/thermal/thermal_zone0/temp", # CPU Package / SoC
            "/sys/class/thermal/thermal_zone1/temp", # Big Core 0 (RK3588)
            "/sys/class/thermal/thermal_zone2/temp", # Big Core 1 (RK3588)
            "/sys/devices/virtual/thermal/thermal_zone0/temp"
        ]
        for path in thermal_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        raw = f.read().strip()
                        val = float(raw)
                        if val > 1000:
                            val = val / 1000.0
                        if 10.0 <= val <= 115.0:
                            return round(val, 1)
                except Exception:
                    pass

        return None

    def get_net_speed(self):
        """Calcula el ancho de banda de red en KB/s"""
        now = time.time()
        dt = now - self._last_net_time
        if dt >= 1.0 and self._last_net_io is not None:
            try:
                curr_io = psutil.net_io_counters()
                rx_bytes = curr_io.bytes_recv - self._last_net_io.bytes_recv
                tx_bytes = curr_io.bytes_sent - self._last_net_io.bytes_sent
                self.net_speed_kbps = {
                    "rx": round(max(0.0, (rx_bytes / 1024.0) / dt), 1),
                    "tx": round(max(0.0, (tx_bytes / 1024.0) / dt), 1)
                }
                self._last_net_io = curr_io
                self._last_net_time = now
            except Exception:
                pass
        return self.net_speed_kbps

    def get_metrics(self):
        """Obtiene el paquete completo de telemetría de hardware"""
        now = time.time()
        uptime_sec = int(now - self.start_time)
        uptime_str = str(timedelta(seconds=uptime_sec))

        # Re-verificar IP cada 60 segundos si estaba en localhost
        if self._cached_ip == "127.0.0.1" and (now - self._last_ip_check > 60):
            self._cached_ip = self._get_local_ip()
            self._last_ip_check = now

        # CPU y RAM
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
        mem = psutil.virtual_memory()
        
        # Almacenamiento (Raíz)
        try:
            disk = psutil.disk_usage('/')
            disk_info = {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent": disk.percent
            }
        except Exception:
            disk_info = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}

        temp_c = self.get_temperature()
        net_speed = self.get_net_speed()

        return {
            "hostname": self.hostname,
            "ip_address": self._cached_ip,
            "uptime_seconds": uptime_sec,
            "uptime_human": uptime_str,
            "cpu_percent": cpu_total,
            "cpu_cores": cpu_cores,
            "cpu_count": len(cpu_cores),
            "cpu_temp_c": temp_c,
            "ram_used_mb": round(mem.used / (1024**2), 1),
            "ram_total_mb": round(mem.total / (1024**2), 1),
            "ram_percent": mem.percent,
            "disk": disk_info,
            "net_speed_kbps": net_speed
        }
