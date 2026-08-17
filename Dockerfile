# ==============================================================================
#  🐳 FLUXA Smart Mobility • Dockerfile Multi-Arquitectura (x86_64 y ARM64)
# ==============================================================================

FROM python:3.11-slim

# Evitar prompts interactivos durante apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependencias de sistema (OpenGL, Glib, librerías V4L2 y utilidades)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    v4l-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo
COPY . .

# Exponer el puerto del Centro de Mando Web y Streaming MJPEG
EXPOSE 5000

# Punto de entrada predeterminado
ENTRYPOINT ["python3", "main.py"]
CMD ["--topology", "4_way", "--backend", "cpu", "--headless", "--video", "videos/13868586_1280_720_24fps.mp4", "--port", "5000"]
