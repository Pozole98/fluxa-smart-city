import csv
import os
import time
from datetime import datetime

class TrafficAnalyticsLogger:
    """
    Registra datos de tráfico de forma dinámica sin importar la topología.
    """
    def __init__(self, log_dir="logs", enabled=True):
        self.enabled = enabled
        if not self.enabled:
            return
            
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.filename = os.path.join(self.log_dir, f"traffic_log_{date_str}.csv")
        self.headers_written = os.path.isfile(self.filename)

    def log_state(self, estado_nombre, autos):
        if not self.enabled or not autos:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keys = list(autos.keys())
        values = list(autos.values())
        
        if not self.headers_written:
            with open(self.filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                headers = ["Timestamp", "Estado_Semaforo"] + keys + ["Total"]
                writer.writerow(headers)
            self.headers_written = True
            
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            total = sum(values)
            row = [timestamp, estado_nombre] + values + [total]
            writer.writerow(row)
