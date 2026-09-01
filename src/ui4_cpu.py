# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
import os
import sys

# Redirección al controlador modular unificado de 4 vías (CPU)
sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    from ui4_way_cpu import App4V_CPU, tk
    ventana = tk.Tk()
    app = App4V_CPU(ventana)
    ventana.mainloop()
