# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Módulo de Gestión y Bloqueo Exclusivo de Controladores Físicos (Hardware Device Locker)
Garantiza que cada nodo de la Orange Pi 5 / Linux secuestre de forma exclusiva un solo Arduino
evitando colisiones o envío simultáneo de instrucciones por múltiples procesos.
"""

import os
import fcntl
import json
import time
import logging
from typing import Dict, Any, Optional, List

LOCK_DIR = "/tmp"

def _normalize_dev_name(device_path: str) -> str:
    """Convierte /dev/ttyACM0 en ttyACM0 para nombres de archivos seguros."""
    clean = os.path.basename(device_path.strip())
    return clean or "arduino_unknown"

def get_lock_file_path(device_path: str) -> str:
    """Devuelve la ruta absoluta del archivo de cerrojo en /tmp/."""
    dev_name = _normalize_dev_name(device_path)
    return os.path.join(LOCK_DIR, f"fluxa_serial_{dev_name}.lock")

def is_pid_alive(pid: int) -> bool:
    """Comprueba si un proceso sigue activo en el sistema operativo."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def inspect_port_lock(device_path: str, current_node_port: Optional[int] = None) -> Dict[str, Any]:
    """
    Inspecciona si un puerto serie está libre o secuestrado por algún nodo.
    Retorna información detallada sin modificar el estado del cerrojo.
    """
    if not device_path or device_path.upper() in ["VIRTUAL", "NONE", "NULL", "DESACTIVADO"]:
        return {
            "device": "VIRTUAL",
            "is_locked": False,
            "is_mine": False,
            "status": "disponible",
            "owner": "Modo Virtual (Sin Bloqueo)",
            "pid": None,
            "node_port": None
        }

    lock_file = get_lock_file_path(device_path)
    if not os.path.exists(lock_file):
        return {
            "device": device_path,
            "is_locked": False,
            "is_mine": False,
            "status": "disponible",
            "owner": None,
            "pid": None,
            "node_port": None
        }

    # Intentar adquirir cerrojo en modo no bloqueante para probar si está tomado
    try:
        fd = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o666)
    except Exception as e:
        return {
            "device": device_path,
            "is_locked": True,
            "is_mine": False,
            "status": "ocupado",
            "owner": f"No accesible ({e})",
            "pid": None,
            "node_port": None
        }

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Si se pudo bloquear, significa que NO había ningún proceso activo manteniéndolo
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        return {
            "device": device_path,
            "is_locked": False,
            "is_mine": False,
            "status": "disponible",
            "owner": None,
            "pid": None,
            "node_port": None
        }
    except (BlockingIOError, OSError):
        # El archivo está tomado por otro descriptor de archivo activo
        owner_info = {}
        try:
            with open(lock_file, "r") as f:
                owner_info = json.load(f)
        except Exception:
            pass
        finally:
            os.close(fd)

        owner_pid = owner_info.get("pid")
        owner_port = owner_info.get("node_port")
        my_pid = os.getpid()

        if current_node_port is not None:
            is_mine = (owner_port == current_node_port)
        else:
            is_mine = (owner_pid == my_pid)

        status = "propio" if is_mine else "ocupado"
        owner_name = owner_info.get("owner", f"PID {owner_pid}")

        return {
            "device": device_path,
            "is_locked": True,
            "is_mine": is_mine,
            "status": status,
            "owner": owner_name,
            "pid": owner_pid,
            "node_port": owner_port
        }


class ArduinoDeviceLock:
    """
    Controlador de exclusividad para asegurar que un nodo "secuestre"
    un único Arduino físico en Linux mediante descriptores de archivo fcntl.flock.
    """

    def __init__(self, node_port: Optional[int] = None):
        self.node_port = node_port
        self.current_device: Optional[str] = None
        self._lock_fd: Optional[int] = None
        self._lock_path: Optional[str] = None

    def acquire(self, device_path: str) -> bool:
        """
        Intenta secuestrar exclusivamente el puerto serial indicado.
        Retorna True si fue adquirido exitosamente, False si está ocupado por otro nodo.
        """
        if not device_path or device_path.upper() in ["VIRTUAL", "NONE", "NULL", "DESACTIVADO"]:
            self.release()
            self.current_device = "VIRTUAL"
            return True

        if self.current_device == device_path and self._lock_fd is not None:
            # Ya lo tenemos secuestrado en esta instancia
            return True

        new_lock_path = get_lock_file_path(device_path)
        try:
            new_fd = os.open(new_lock_path, os.O_RDWR | os.O_CREAT, 0o666)
            fcntl.flock(new_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as e:
            logging.warning(f"No se pudo secuestrar el puerto {device_path}: Ocupado por otro nodo. Error: {e}")
            return False
        except Exception as e:
            logging.error(f"Error inesperado al intentar bloquear {device_path}: {e}")
            return False

        # Si adquirió con éxito el nuevo puerto, ahora sí liberamos el anterior de forma atómica
        old_fd = self._lock_fd
        old_path = self._lock_path
        old_device = self.current_device

        if old_fd is not None:
            try:
                fcntl.flock(old_fd, fcntl.LOCK_UN)
                os.close(old_fd)
            except Exception:
                pass

        if old_path and os.path.exists(old_path) and old_path != new_lock_path:
            try:
                os.remove(old_path)
            except Exception:
                pass

        # Registrar el nuevo cerrojo
        self._lock_fd = new_fd
        self._lock_path = new_lock_path
        self.current_device = device_path

        metadata = {
            "node_port": self.node_port,
            "pid": os.getpid(),
            "device": device_path,
            "owner": f"Nodo {self.node_port or 'Default'} (PID {os.getpid()})",
            "acquired_at": time.time(),
            "acquired_str": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            os.ftruncate(new_fd, 0)
            os.lseek(new_fd, 0, os.SEEK_SET)
            os.write(new_fd, json.dumps(metadata, indent=2).encode('utf-8'))
            os.fsync(new_fd)
        except Exception as e:
            logging.warning(f"No se pudo escribir metadata en cerrojo {new_lock_path}: {e}")

        logging.info(f"🔒 Puerto serial '{device_path}' secuestrado con éxito por Nodo {self.node_port} (PID {os.getpid()}).")
        return True

    def release(self):
        """Libera el cerrojo sobre el dispositivo actual."""
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except Exception as e:
                logging.debug(f"Error liberando flock: {e}")
            self._lock_fd = None

        if self._lock_path and os.path.exists(self._lock_path):
            try:
                # Si el archivo está vacío o somos los dueños, removerlo
                os.remove(self._lock_path)
            except Exception:
                pass
            self._lock_path = None

        if self.current_device:
            logging.info(f"🔓 Cerrojo sobre puerto serial '{self.current_device}' liberado.")
            self.current_device = None

    def __del__(self):
        self.release()
