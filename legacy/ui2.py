# ============================================================================
# FLUXA Smart City - Sistema de Control de Tráfico Adaptativo
# ============================================================================
# Desarrollador Principal y Propietario de Derechos: Moisés Emilio Martínez Arias
# Institución: Tecnológico de Estudios Superiores de Coacalco (TESCo) - TecNM
# Licencia: Propietaria / Comercial (Certamen InnovaTecNM 2026)
# ============================================================================
import os
import sys

# La lógica central ahora está unificada. Este script actúa como alias.
sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    import ui2_nano
    ui2_nano.tk.Tk().withdraw()
    ventana = ui2_nano.tk.Tk()
    app = ui2_nano.App(ventana)
    ventana.mainloop()
