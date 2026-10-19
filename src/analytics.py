# -*- coding: utf-8 -*-
"""
FLUXA - Control Semafórico Inteligente y Telemetría Edge
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
División de Ingeniería en Sistemas Computacionales

Módulo de Registro Periódico de Telemetría y Aforo en CSV
Desarrollador Principal: Moisés Emilio Martínez Arias
"""

import csv
import os
import time
from datetime import datetime


class TrafficAnalyticsLogger:
    """
    Registra datos de aforo vehicular en archivos CSV diarios de forma desacoplada de la topología activa.
    """
    def __init__(self, log_dir="logs", enabled=True):
        self.enabled = enabled
        if not self.enabled:
            return
            
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

    def log_state(self, estado_nombre, autos):
        if not self.enabled or not autos:
            return
            
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        current_file = os.path.join(self.log_dir, f"traffic_log_{date_str}.csv")
        
        keys = list(autos.keys())
        values = list(autos.values())
        
        file_exists = os.path.isfile(current_file)
        if not file_exists:
            with open(current_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                headers = ["Timestamp", "Estado_Semaforo"] + keys + ["Total"]
                writer.writerow(headers)
            
        with open(current_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            total = sum(values)
            row = [timestamp, estado_nombre] + values + [total]
            writer.writerow(row)
