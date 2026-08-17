import os
import sys

# La lógica central ahora está unificada. Este script actúa como alias.
sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    import ui2_nano_cpu
    ui2_nano_cpu.tk.Tk().withdraw()
    ventana = ui2_nano_cpu.tk.Tk()
    app = ui2_nano_cpu.App(ventana)
    ventana.mainloop()
