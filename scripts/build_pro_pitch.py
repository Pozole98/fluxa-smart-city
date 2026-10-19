#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador Pro de Presentación PITCH (3 Minutos) - InnovaTecNM 2026
FLUXA Smart Mobility (Folio 70785-17)
"""

import os
import base64
import json
import subprocess

BASE_DIR = '/home/fluxa/fluxa-smart-city'
LOGOS_DIR = os.path.join(BASE_DIR, 'logos')
OPT_DIR = os.path.join(BASE_DIR, 'presentaciones/assets_opt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'presentaciones')
USER_PDF_DIR = '/home/fluxa/presentaciones_pdf'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(USER_PDF_DIR, exist_ok=True)

def b64_img(folder, filename, mime="image/png"):
    p = os.path.join(folder, filename)
    if os.path.exists(p):
        with open(p, 'rb') as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

tesco_b64 = b64_img(LOGOS_DIR, 'tesco.png')
tecnm_b64 = b64_img(LOGOS_DIR, 'tecnm.png')
sic_b64 = b64_img(LOGOS_DIR, 'sic.png')

fluxa_logo = b64_img(OPT_DIR, 'fluxa_official_logo.png')
traffic_img = b64_img(OPT_DIR, 'traffic_congestion_mexico.jpg', 'image/jpeg')
opi5_img = b64_img(OPT_DIR, 'orange_pi_5_hardware.png')
yolo_img = b64_img(OPT_DIR, 'yolo_detection_boxes.jpg', 'image/jpeg')
scada_img = b64_img(OPT_DIR, 'scada_dashboard_full.jpg', 'image/jpeg')
capex_chart = b64_img(OPT_DIR, 'capex_benchmark_chart.png')
trl_chart = b64_img(OPT_DIR, 'trl_maturity_chart.png')

hdr = f"""
<div class="slide-header">
    <div class="brand-cluster">
        <img src="{tecnm_b64}" alt="TecNM" class="logo-inst logo-tecnm">
        <img src="{tesco_b64}" alt="TESCo" class="logo-inst logo-tesco">
        <img src="{sic_b64}" alt="SIC" class="logo-inst logo-sic">
        <div class="brand-divider"></div>
        <img src="{fluxa_logo}" alt="FLUXA" class="logo-fluxa">
    </div>
    <div class="event-stamp">
        <div class="event-title">InnovaTecNM 2026 • Etapa Regional</div>
        <div class="event-sub">Región 5 • Folio: <span class="tag-folio">70785-17</span> | INDUSTRIA ELÉCTRICA Y ELECTRÓNICA</div>
    </div>
</div>
"""

PRO_CSS = """
:root {
  --bg-deep: #050a07;
  --bg-card: rgba(13, 23, 17, 0.94);
  --border-card: rgba(34, 197, 94, 0.3);
  --border-glow: rgba(52, 211, 153, 0.6);
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --text-sub: #cbd5e1;
  --accent-green: #10b981;
  --accent-mint: #34d399;
  --accent-cyan: #06b6d4;
  --accent-amber: #f59e0b;
  --accent-red: #ef4444;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: var(--bg-deep);
  color: var(--text-main);
  overflow: hidden;
  height: 100vh;
  width: 100vw;
  user-select: none;
}
#presentation {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}
.slide {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  padding: 1.8rem 3.4rem 4.6rem 3.4rem;
  display: none;
  flex-direction: column;
  background: radial-gradient(circle at 50% 8%, rgba(16, 185, 129, 0.1) 0%, rgba(5, 10, 7, 0.98) 75%);
  overflow: hidden;
}
.slide.active {
  display: flex;
  animation: slideFade 0.28s ease-out forwards;
}
@keyframes slideFade {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
.slide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding-bottom: 0.75rem;
  margin-bottom: 0.85rem;
}
.brand-cluster {
  display: flex;
  align-items: center;
  gap: 1.1rem;
}
.logo-inst {
  height: 38px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
}
.brand-divider {
  width: 1px;
  height: 32px;
  background: rgba(255, 255, 255, 0.2);
  margin: 0 0.2rem;
}
.logo-fluxa {
  height: 40px;
  object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(16, 185, 129, 0.35));
}
.event-stamp {
  text-align: right;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.4;
}
.event-stamp .event-title {
  font-weight: 700;
  color: #f1f5f9;
}
.event-stamp .tag-folio {
  color: var(--accent-mint);
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
}
.slide-meta-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 0.3rem;
}
.badge-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 0.8px;
  padding: 0.22rem 0.65rem;
  border-radius: 9999px;
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-mint);
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.badge-tag.red { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border-color: rgba(239, 68, 68, 0.4); }
.badge-tag.blue { background: rgba(6, 182, 212, 0.15); color: #67e8f9; border-color: rgba(6, 182, 212, 0.4); }
.badge-tag.amber { background: rgba(245, 158, 11, 0.15); color: #fde047; border-color: rgba(245, 158, 11, 0.4); }
.slide-title {
  font-size: 2.15rem;
  font-weight: 800;
  line-height: 1.18;
  background: linear-gradient(135deg, #ffffff 45%, var(--accent-mint) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.5px;
}
.slide-subtitle {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin-top: 0.2rem;
}
.slide-body {
  flex: 1;
  display: flex;
  align-items: center;
  margin-top: 0.6rem;
}
.split-hero {
  display: grid;
  grid-template-columns: 1.18fr 1fr;
  gap: 2.2rem;
  width: 100%;
  align-items: center;
}
.text-col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.media-frame {
  position: relative;
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid var(--border-glow);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 12px 35px rgba(0, 0, 0, 0.65), 0 0 25px rgba(16, 185, 129, 0.15);
  display: flex;
  flex-direction: column;
}
.media-frame img {
  width: 100%;
  height: auto;
  max-height: 380px;
  object-fit: contain;
  background: #060b08;
  display: block;
}
.media-caption {
  background: rgba(8, 15, 10, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.5rem 0.9rem;
  font-size: 0.76rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.media-caption strong { color: var(--accent-mint); }
.card-pro {
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 14px;
  padding: 1.15rem 1.4rem;
  backdrop-filter: blur(12px);
  box-shadow: 0 6px 22px rgba(0, 0, 0, 0.45);
}
.card-pro.highlight {
  border-color: var(--border-glow);
  background: rgba(16, 185, 129, 0.12);
}
.card-pro.danger {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.08);
}
.card-headline {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.card-text {
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--text-sub);
}
.feature-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  font-size: 0.88rem;
  color: var(--text-sub);
  line-height: 1.45;
}
.feature-bullet {
  color: var(--accent-mint);
  font-weight: 800;
  font-size: 1.1rem;
  line-height: 1;
}
.stat-strip {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.9rem;
}
.stat-card-pro {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 0.75rem 1rem;
}
.stat-card-pro.highlight {
  border-color: rgba(34, 197, 94, 0.45);
  background: rgba(16, 185, 129, 0.15);
}
.stat-big {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.85rem;
  font-weight: 800;
  color: var(--accent-mint);
  line-height: 1.1;
}
.stat-desc {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 0.25rem;
}
.bottom-bar {
  position: absolute;
  bottom: 0; left: 0;
  width: 100%; height: 50px;
  background: rgba(5, 10, 7, 0.98);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  z-index: 100;
}
.progress-track {
  position: absolute;
  top: 0; left: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  width: 100%;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-green), var(--accent-mint));
  width: 0%;
  transition: width 0.25s ease;
}
.nav-controls {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.btn-ctrl {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s;
}
.btn-ctrl:hover {
  background: rgba(16, 185, 129, 0.25);
  border-color: var(--accent-mint);
}
.timer-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--accent-mint);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0.7rem;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.timer-warning { color: var(--accent-amber) !important; border-color: var(--accent-amber) !important; }
.timer-expired { color: var(--accent-red) !important; border-color: var(--accent-red) !important; animation: pulse 1s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.slide-counter { font-size: 0.82rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
.speaker-pill {
  font-size: 0.75rem;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.35);
  padding: 0.2rem 0.65rem;
  border-radius: 9999px;
  font-weight: 700;
}
#notes-drawer {
  position: fixed;
  bottom: 50px; left: 0;
  width: 100%;
  max-height: 240px;
  background: rgba(8, 16, 11, 0.98);
  border-top: 2px solid var(--accent-mint);
  padding: 1.2rem 3rem;
  overflow-y: auto;
  box-shadow: 0 -10px 30px rgba(0,0,0,0.85);
  z-index: 99;
  display: none;
}
#notes-drawer.open { display: block; }
.notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--accent-mint);
  font-weight: 800;
  letter-spacing: 1px;
}
.notes-body { font-size: 1rem; line-height: 1.6; color: #f1f5f9; }
.notes-cue { font-weight: 800; color: #38bdf8; margin-right: 0.4rem; }

@page { size: 16in 9in; margin: 0; }
@media print {
  body {
    overflow: visible !important;
    height: auto !important;
    width: 16in !important;
    background: #050a07 !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  #presentation { display: block !important; height: auto !important; width: 16in !important; }
  .slide {
    display: flex !important;
    position: relative !important;
    width: 16in !important;
    height: 9in !important;
    max-width: 16in !important;
    max-height: 9in !important;
    box-sizing: border-box !important;
    page-break-after: always !important;
    page-break-inside: avoid !important;
    padding: 2rem 3.4rem !important;
  }
  .bottom-bar, #notes-drawer { display: none !important; }
}
"""


def wrap_html(title, total_seconds, slides_list, notes_dict, speaker_tag="Expositor 1"):
    slides_rendered = "".join(slides_list)
    notes_json = json.dumps(notes_dict)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — FLUXA Smart Mobility (InnovaTecNM 2026)</title>
    <style>{PRO_CSS}</style>
</head>
<body>
    <div id="presentation">
        {slides_rendered}
    </div>

    <div id="notes-drawer">
        <div class="notes-header">
            <span id="notes-slide-title">Guion de Exposición</span>
            <span id="notes-time-cue" style="color: #38bdf8; font-family: 'JetBrains Mono';">Tiempo sugerido</span>
        </div>
        <div class="notes-body" id="notes-content">Cargando guion...</div>
    </div>

    <div class="bottom-bar">
        <div class="progress-track"><div class="progress-bar-fill" id="progress-fill"></div></div>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div class="slide-counter" id="slide-num">1 / {len(slides_list)}</div>
            <div class="speaker-pill" id="speaker-display">{speaker_tag}</div>
        </div>

        <div class="nav-controls">
            <div class="timer-display" id="timer-box">
                <span id="timer-text">00:00</span>
                <span style="font-size: 0.7rem; color: var(--text-muted);" id="timer-max">/ 03:00</span>
            </div>
            <button class="btn-ctrl" onclick="toggleTimer()" id="btn-timer">▶ Play</button>
            <button class="btn-ctrl" onclick="resetTimer()">↺ Reset</button>
            <button class="btn-ctrl" onclick="toggleNotes()">📝 Guion</button>
            <button class="btn-ctrl" onclick="prevSlide()">◀</button>
            <button class="btn-ctrl" onclick="nextSlide()">▶</button>
            <button class="btn-ctrl" onclick="toggleFullscreen()">⛶</button>
        </div>
    </div>

    <script>
        const totalDuration = {total_seconds};
        const notesData = {notes_json};
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        const totalSlides = slides.length;
        let timerSeconds = 0;
        let timerInterval = null;
        let isRunning = false;

        function showSlide(index) {{
            if (index < 0) index = 0;
            if (index >= totalSlides) index = totalSlides - 1;
            currentSlide = index;

            slides.forEach((s, i) => s.classList.toggle('active', i === currentSlide));

            document.getElementById('slide-num').innerText = ;
            const pct = ((currentSlide + 1) / totalSlides) * 100;
            document.getElementById('progress-fill').style.width = pct + '%';

            const activeSlide = slides[currentSlide];
            const customSpeaker = activeSlide.getAttribute('data-speaker');
            if (customSpeaker) document.getElementById('speaker-display').innerText = customSpeaker;

            updateNotes();
        }}

        function nextSlide() {{ showSlide(currentSlide + 1); }}
        function prevSlide() {{ showSlide(currentSlide - 1); }}

        function updateNotes() {{
            const noteObj = notesData[currentSlide] || {{ text: 'Sin notas.', cue: '0:00', speaker: '' }};
            document.getElementById('notes-slide-title').innerText = ;
            document.getElementById('notes-time-cue').innerText = ;
            document.getElementById('notes-content').innerHTML = noteObj.text;
        }}

        function toggleNotes() {{ document.getElementById('notes-drawer').classList.toggle('open'); }}

        function formatTime(sec) {{
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return ;
        }}

        function updateTimerUI() {{
            const tBox = document.getElementById('timer-box');
            document.getElementById('timer-text').innerText = formatTime(timerSeconds);
            const ratio = timerSeconds / totalDuration;
            if (timerSeconds >= totalDuration) tBox.className = 'timer-display timer-expired';
            else if (ratio >= 0.8) tBox.className = 'timer-display timer-warning';
            else tBox.className = 'timer-display';
        }}

        function toggleTimer() {{
            if (isRunning) {{
                clearInterval(timerInterval);
                isRunning = false;
                document.getElementById('btn-timer').innerText = '▶ Play';
            }} else {{
                isRunning = true;
                document.getElementById('btn-timer').innerText = '⏸ Pausa';
                timerInterval = setInterval(() => {{ timerSeconds++; updateTimerUI(); }}, 1000);
            }}
        }}

        function resetTimer() {{
            clearInterval(timerInterval);
            isRunning = false;
            timerSeconds = 0;
            updateTimerUI();
            document.getElementById('btn-timer').innerText = '▶ Play';
        }}

        function toggleFullscreen() {{
            if (!document.fullscreenElement) document.documentElement.requestFullscreen();
            else if (document.exitFullscreen) document.exitFullscreen();
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') nextSlide();
            else if (e.key === 'ArrowLeft' || e.key === 'PageUp') prevSlide();
            else if (e.key === 'n' || e.key === 'N') toggleNotes();
            else if (e.key === 't' || e.key === 'T') toggleTimer();
            else if (e.key === 'r' || e.key === 'R') resetTimer();
            else if (e.key === 'f' || e.key === 'F') toggleFullscreen();
        }});

        document.getElementById('timer-max').innerText = ;
        showSlide(0);
        updateTimerUI();
    </script>
</body>
</html>"""

slides_pitch = [
    # Slide 1: Portada
    f"""
    <div class="slide active" data-speaker="Expositor 1 (Pitch)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">PITCH DE ALTO IMPACTO • 3 MINUTOS</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Ciencias Computacionales • Digitalización y Automatización</span>
        </div>
        <h1 class="slide-title">FLUXA: Inteligencia Artificial en el Borde para Movilidad Urbana</h1>
        <p class="slide-subtitle">Modernización de cruces semafóricos mediante arquitectura Retrofit Overlay y visión computacional</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro highlight">
                        <div class="card-headline" style="color: #6ee7b7; font-size: 1.15rem;">
                            "¿Cuántas horas de tu vida has perdido frente a un semáforo en rojo viendo un carril completamente vacío?"
                        </div>
                        <p class="card-text">
                            En México, 9 de cada 10 semáforos operan como hace 40 años: ciegos a la realidad del tráfico. Desarrollamos <strong>FLUXA</strong> para dotar de visión por computadora, toma de decisiones autónoma y sincronización vial en tiempo real a cualquier intersección existente en <strong>menos de 4 horas</strong>.
                        </p>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">95%</div>
                            <div class="stat-desc">Ahorro en costo frente a marcas extranjeras</div>
                        </div>
                        <div class="stat-card-pro">
                            <div class="stat-big">&lt; 12 ms</div>
                            <div class="stat-desc">Latencia NPU Edge (Cero pagos de nube)</div>
                        </div>
                    </div>
                    <div style="font-size: 0.82rem; color: var(--text-muted);">
                        <strong>Autores:</strong> Moisés Martínez (Líder), Diego Huichapeño, Ethan Flores, Citlalli Rojas, Jerazan Becerra • <strong>Asesor:</strong> Mtro. Roberto Carlos Muñoz
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{opi5_img}" alt="Orange Pi 5 RK3588 Edge Appliance">
                    <div class="media-caption">
                        <span>Hardware Edge: <strong>Orange Pi 5 (RK3588 NPU 6 TOPS)</strong></span>
                        <span class="badge-tag">TRL 6 / 7</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 2: Problema
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag red">EL PROBLEMA NACIONAL</span>
            <span style="font-size: 0.8rem; color: #fca5a5;">Crisis de Movilidad y Barrera Presupuestal en Municipios</span>
        </div>
        <h1 class="slide-title">La Trampa de los Semáforos Ciegos y el Alto Costo</h1>
        <p class="slide-subtitle">La congestión vehicular destruye la productividad familiar y asfixia los presupuestos públicos</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro danger">
                        <div class="card-headline" style="color: #fca5a5;">
                            La Realidad Cotidiana de Millones de Familias
                        </div>
                        <p class="card-text">
                            El Valle de México es la <strong>2da zona más congestionada de América Latina</strong>. Miles de automovilistas y usuarios de transporte público pasan más de 100 horas al año atrapados en colas viales provocadas por semáforos de tiempo fijo desfasados.
                        </p>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro" style="border-color: rgba(239, 68, 68, 0.4);">
                            <div class="stat-big" style="color: #fca5a5;">3,500 M</div>
                            <div class="stat-desc">Horas-hombre perdidas al año en México</div>
                        </div>
                        <div class="stat-card-pro" style="border-color: rgba(239, 68, 68, 0.4);">
                            <div class="stat-big" style="color: #fca5a5;">$94,000 MDP</div>
                            <div class="stat-desc">Costo económico anual (IMCO / ITDP)</div>
                        </div>
                    </div>
                    <div class="card-pro">
                        <div class="card-headline" style="font-size: 0.92rem;">
                            ¿Por qué los municipios no modernizan?
                        </div>
                        <p class="card-text" style="font-size: 0.82rem;">
                            Marcas extranjeras (Siemens, Econolite) exigen <strong>entre $350,000 y $750,000 MXN por cruce</strong>, obra civil destructiva para espiras en asfalto y cobros en dólares por servidores en la nube.
                        </p>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{traffic_img}" alt="Tráfico severo en México">
                    <div class="media-caption">
                        <span>Congestión urbana en horas pico (Ralentí y emisiones)</span>
                        <span class="badge-tag red">Crisis Urbana</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 3: Solución
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">PROPUESTA DE VALOR DISRUPTIVA</span>
            <span style="font-size: 0.8rem; color: var(--accent-mint);">Ingeniería Edge AI Mexicana</span>
        </div>
        <h1 class="slide-title">FLUXA: Capa Inteligente Retrofit sin Obra Civil</h1>
        <p class="slide-subtitle">Transformamos intersecciones convencionales en nodos viales autónomos de alta precisión</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro highlight">
                        <ul class="feature-list">
                            <li class="feature-item">
                                <span class="feature-bullet">✓</span>
                                <div><strong>Retrofit Plug & Play (&lt; 4 horas):</strong> Se instala en el gabinete actual aprovechando cabezales, postes y cableado. Cero afectación al pavimento.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">✓</span>
                                <div><strong>Inferencia 100% en el Borde:</strong> NPU Rockchip RK3588 con 6 TOPS procesando YOLOv8 INT8 a menos de 12 ms. Cero dependencia de internet ni rentas de nube.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">✓</span>
                                <div><strong>Algoritmo Adaptativo TSP:</strong> Detecta flujo vehicular en tiempo real, prioriza transporte público masivo y activa corredores de emergencia C5 en &lt;2 segundos.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">&lt; 4 Horas</div>
                            <div class="stat-desc">Despliegue rápido por intersección</div>
                        </div>
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">6 TOPS</div>
                            <div class="stat-desc">Poder de cálculo neuronal local</div>
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{yolo_img}" alt="Detección vehicular con YOLOv8 en NPU">
                    <div class="media-caption">
                        <span>Visión Artificial: <strong>YOLOv8 INT8 + BYTETracker en tiempo real</strong></span>
                        <span class="badge-tag">Edge AI</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 4: Modelo de Negocio B2G
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag blue">MODELO DE NEGOCIO B2G</span>
            <span style="font-size: 0.8rem; color: #67e8f9;">Esquema Comercial Híbrido y Escalable</span>
        </div>
        <h1 class="slide-title">95% de Ahorro y Alta Rentabilidad Comercial</h1>
        <p class="slide-subtitle">Venta de hardware appliance de bajo costo con ingresos recurrentes por software SCADA C5</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">
                            <span style="color: var(--accent-mint);">3 Fuentes de Ingresos Complementarias:</span>
                        </div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">1</span>
                                <div><strong>Venta de Edge Appliance (CapEx):</strong> $28,500 MXN / cruce (Costo fabricación BOM: $10,750 | <strong>Margen Bruto: 62.3%</strong>).</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">2</span>
                                <div><strong>Licencia SCADA C5 (OpEx / Anual):</strong> $8,400 MXN / cruce / año ($700 MXN mensuales por nodo conectado).</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">3</span>
                                <div><strong>Póliza SLA 24/7 y Calibración:</strong> $6,000 MXN / cruce / año para soporte y reentrenamiento semestral de IA.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">$2.14 MDP</div>
                            <div class="stat-desc">Ingresos Proyectados Año 1 (50 cruces)</div>
                        </div>
                        <div class="stat-card-pro highlight">
                            <div class="stat-big" style="color: #6ee7b7;">$890,000</div>
                            <div class="stat-desc">Utilidad Neta Año 1 (41.5% Margen)</div>
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{capex_chart}" alt="Comparativa de CapEx por Intersección">
                    <div class="media-caption">
                        <span>Benchmarking de Costo CapEx: <strong>FLUXA $28.5k vs Siemens $650k</strong></span>
                        <span class="badge-tag blue">-95% Costo</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 5: Retorno Social y Ambiental
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag amber">RETORNO SOCIAL & AMBIENTAL</span>
            <span style="font-size: 0.8rem; color: #fde047;">Validado con Metodologías Oficiales del Gobierno</span>
        </div>
        <h1 class="slide-title">Payback Social en Menos de 90 Días</h1>
        <p class="slide-subtitle">El beneficio devuelto a los ciudadanos supera la inversión total en el primer trimestre</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro highlight">
                        <div class="card-headline" style="color: #6ee7b7;">
                            Cálculo Verificable (SEDATU / DOE / CONUEE / INECC):
                        </div>
                        <p class="card-text">
                            En un cruce de 15,000 autos/día, reduciendo apenas <strong>15 segundos de ralentí</strong> (0.70 L/h), se obtienen resultados tangibles inmediatos:
                        </p>
                        <ul class="feature-list" style="margin-top: 0.6rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">⛽</span>
                                <div><strong>15,968 Litros de gasolina ahorrados</strong> al año por cruce.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">💵</span>
                                <div><strong>$391,234 MXN de ahorro directo</strong> al bolsillo ciudadano por intersección.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">🌱</span>
                                <div><strong>36.8 Toneladas de CO₂ evitadas</strong> anualmente por cruce.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro" style="background: rgba(16, 185, 129, 0.18); border-color: var(--accent-mint); text-align: center;">
                        <div style="font-size: 0.95rem; font-weight: 800; color: #fff;">
                            En un corredor piloto de 10 cruces: <span style="color: #6ee7b7;">$3.91 MDP</span> en ahorro social y <span style="color: #6ee7b7;">368.8 Ton de CO₂</span> al año.
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{scada_img}" alt="Consola SCADA FLUXA en vivo">
                    <div class="media-caption">
                        <span>Telemetría SCADA C5: <strong>Aforo en vivo, Ola Verde y KPIs de CO₂</strong></span>
                        <span class="badge-tag amber">Payback &lt;90d</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 6: Cierre y Tracción
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">TRACCIÓN, EQUIPO & SOBERANÍA</span>
            <span style="font-size: 0.8rem; color: var(--accent-mint);">Orgullo Tecnológico TecNM • TESCo</span>
        </div>
        <h1 class="slide-title">Madurez Tecnológica y Soberanía Nacional</h1>
        <p class="slide-subtitle">Solución lista para despliegue piloto metropolitano alineada al Plan México 2024-2030</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <ul class="feature-list">
                            <li class="feature-item">
                                <span class="feature-bullet">🚀</span>
                                <div><strong>Madurez TRL 6/7:</strong> Probado en banco experimental de potencia con relevadores y video en vivo en Coacalco, Ecatepec y Tultitlán.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">⚖️</span>
                                <div><strong>Propiedad Intelectual:</strong> Registro de Software ante INDAUTOR + Modelo de Utilidad y Marca Clase 9 ante IMPI.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">🤝</span>
                                <div><strong>Alianzas Viales:</strong> Vinculación técnica con talleres de semaforización y áreas de movilidad del Estado de México.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight" style="text-align: center; padding: 1.1rem; border-color: var(--accent-mint); background: rgba(16, 185, 129, 0.2);">
                        <div style="font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: 0.3rem;">
                            FLUXA: Ciudades Inteligentes, Autónomas y Humanas
                        </div>
                        <p class="card-text" style="font-size: 0.9rem;">
                            Demostramos que con ingeniería mexicana del TecNM transformamos la movilidad nacional. ¡Muchas gracias!
                        </p>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{trl_chart}" alt="Nivel de Madurez Tecnológica TRL 6/7">
                    <div class="media-caption">
                        <span>Madurez Tecnológica: <strong>TRL 6 / TRL 7 con 100% PyTest</strong></span>
                        <span class="badge-tag">TecNM 2026</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
]

notes_pitch = {
    0: {
        "speaker": "Expositor 1",
        "cue": "0:00 - 0:25 (25s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[0:00]</span> Buenos días, honorable jurado calificador. Les hago una pregunta muy honesta: <strong>¿cuántas horas de sus vidas han perdido frente a un semáforo en rojo viendo un carril completamente vacío?</strong><br><span class=\"notes-cue\">[0:12]</span> En México, esto nos cuesta 3.5 mil millones de horas al año. Para resolver esto creamos <strong>FLUXA</strong>: una plataforma industrial de semaforización inteligente basada en Inteligencia Artificial en el Borde, desarrollada en el TESCo para transformar semáforos ciegos en cruces autónomos sin obra civil.</p>"
    },
    1: {
        "speaker": "Expositor 1",
        "cue": "0:25 - 0:55 (30s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[0:25]</span> El 90% de los semáforos del país siguen usando temporizadores rígidos de los años 80, provocando pérdidas por más de <strong>94 mil millones de pesos anuales</strong> y toneladas de gases contaminantes en ralentí.<br><span class=\"notes-cue\">[0:40]</span> ¿Por qué los municipios no los cambian? Porque marcas extranjeras como Siemens o Econolite cobran <strong>entre 350 mil y 750 mil pesos por una sola intersección</strong>, exigen romper el asfalto para poner sensores que se dañan con los baches y cobran rentas en dólares con servidores en la nube. Nuestras ciudades no pueden pagar eso.</p>"
    },
    2: {
        "speaker": "Expositor 1",
        "cue": "0:55 - 1:30 (35s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[0:55]</span> <strong>Aquí es donde entra la innovación de FLUXA:</strong> operamos bajo una arquitectura <strong>Retrofit Overlay</strong>. Nos conectamos directamente al gabinete, cabezales y cableado existentes en <strong>menos de 4 horas</strong>, sin romper pavimento.<br><span class=\"notes-cue\">[1:12]</span> Colocamos una computadora de borde con la NPU Rockchip RK3588 de 6 TOPS. Ejecutamos YOLOv8 cuantizado a INT8 con una latencia de <strong>menos de 12 milisegundos</strong>. El sistema ve los autos en tiempo real, calcula la demanda ponderada y ajusta las luces de forma 100% autónoma, dando paso a ambulancias del C5 en menos de 2 segundos.</p>"
    },
    3: {
        "speaker": "Expositor 1",
        "cue": "1:30 - 2:05 (35s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[1:30]</span> Nuestro modelo de negocio B2G es disruptivo y altamente rentable. Vendemos el kit industrial completo a <strong>$28,500 MXN</strong> por cruce: un <strong>ahorro del 95%</strong> frente a la competencia extranjera.<br><span class=\"notes-cue\">[1:45]</span> Con un costo directo de fabricación de $10,750 MXN, logramos un margen bruto del 62.3%. Sumamos ingresos recurrentes por la licencia de software SCADA C5 y pólizas de mantenimiento.<br><span class=\"notes-cue\">[1:55]</span> En nuestro primer año, con 50 cruces en el Valle de México, proyectamos <strong>$2.14 millones de pesos de facturación</strong> y una utilidad neta de $890 mil pesos (41.5% de margen neto).</p>"
    },
    4: {
        "speaker": "Expositor 1",
        "cue": "2:05 - 2:35 (30s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[2:05]</span> Pero lo más valioso no es lo que ahorra el municipio, sino lo que devuelve a la sociedad. Validado bajo metodologías del Departamento de Energía de EE.UU., CONUEE e INECC, cada cruce FLUXA ahorra <strong>15,968 litros de gasolina al año</strong>.<br><span class=\"notes-cue\">[2:20]</span> Esto representa <strong>$391 mil pesos de ahorro directo en el bolsillo de los ciudadanos</strong> y evita 36.8 toneladas de CO₂ al año por cruce. En un corredor de 10 cruces son casi 4 millones de pesos al año. El retorno de inversión social se logra en <strong>menos de 90 días</strong>.</p>"
    },
    5: {
        "speaker": "Expositor 1",
        "cue": "2:35 - 3:00 (25s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[2:35]</span> FLUXA cuenta con un nivel de madurez <strong>TRL 6/7</strong>, validado con tráfico real en Coacalco, Ecatepec y Tultitlán, con protección de propiedad intelectual en trámite ante INDAUTOR e IMPI.<br><span class=\"notes-cue\">[2:48]</span> Con FLUXA, demostramos que en el Tecnológico Nacional de México creamos tecnología de clase mundial con impacto social tangible: más tiempo con nuestras familias, menos emisiones y ciudades vivas y eficientes. <strong>Muchas gracias.</strong></p>"
    }
}

pitch_html = wrap_html("PITCH OFICIAL (3 Min)", 180, slides_pitch, notes_pitch, "Expositor 1 (Pitch)")
pitch_out_path = os.path.join(OUTPUT_DIR, 'pitch_3min.html')

with open(pitch_out_path, 'w', encoding='utf-8') as f:
    f.write(pitch_html)

print("pitch_3min.html generado.")

# Render to PDF
pdf_target = os.path.join(OUTPUT_DIR, 'FLUXA_Pitch_3Min_InnovaTecNM_2026.pdf')
cmd = [
    'chromium', '--headless=new', '--no-sandbox', '--disable-gpu',
    '--run-all-compositor-stages-before-draw', '--virtual-time-budget=6000',
    f'--print-to-pdf={pdf_target}',
    '--print-to-pdf-no-header', pitch_out_path
]
subprocess.run(cmd, check=True)

# Copy aliases
subprocess.run(['cp', pdf_target, os.path.join(OUTPUT_DIR, 'pitch_3min.pdf')], check=True)
subprocess.run(['cp', pdf_target, os.path.join(USER_PDF_DIR, 'FLUXA_Pitch_3Min_InnovaTecNM_2026.pdf')], check=True)
subprocess.run(['cp', pdf_target, os.path.join(USER_PDF_DIR, 'pitch_3min.pdf')], check=True)

print("Pitch PDF compiled and deployed successfully!")
