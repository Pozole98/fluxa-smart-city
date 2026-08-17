import os
import sys

# Redirección al controlador modular unificado de 4 vías (RKNN NPU)
sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    from ui4_way import App4V_RKNN, tk
    ventana = tk.Tk()
    app = App4V_RKNN(ventana)
    ventana.mainloop()
