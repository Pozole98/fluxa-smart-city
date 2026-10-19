#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador Pro de Presentación DEFENSA TÉCNICA Y PLAN DE NEGOCIOS (7 Minutos)
InnovaTecNM 2026 • Región 5 • FLUXA Smart Mobility (Folio 70785-17)
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
bom_chart = b64_img(OPT_DIR, 'bom_cost_pie_chart.png')
rev_chart = b64_img(OPT_DIR, 'revenue_ramp_chart.png')
failsafe_img = b64_img(OPT_DIR, 'fail_safe_matrix.png')
indautor_img = b64_img(OPT_DIR, 'indautor_facade.jpg', 'image/jpeg')
b2g_funnel = b64_img(OPT_DIR, 'b2g_adoption_funnel.png')
report_pdf = b64_img(OPT_DIR, 'official_report_pdf.jpg', 'image/jpeg')
delay_chart = b64_img(OPT_DIR, 'delay_reduction_corridor.png')

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
.event-stamp .event-title { font-weight: 700; color: #f1f5f9; }
.event-stamp .tag-folio { color: var(--accent-mint); font-weight: 800; font-family: 'JetBrains Mono', monospace; }
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
.slide-subtitle { font-size: 0.95rem; color: var(--text-muted); margin-top: 0.2rem; }
.slide-body { flex: 1; display: flex; align-items: center; margin-top: 0.6rem; }
.split-hero {
  display: grid;
  grid-template-columns: 1.18fr 1fr;
  gap: 2.2rem;
  width: 100%;
  align-items: center;
}
.text-col { display: flex; flex-direction: column; gap: 0.9rem; }
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
  padding: 1.1rem 1.35rem;
  backdrop-filter: blur(12px);
  box-shadow: 0 6px 22px rgba(0, 0, 0, 0.45);
}
.card-pro.highlight { border-color: var(--border-glow); background: rgba(16, 185, 129, 0.12); }
.card-pro.danger { border-color: rgba(239, 68, 68, 0.45); background: rgba(239, 68, 68, 0.08); }
.card-headline {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.45rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.card-text { font-size: 0.88rem; line-height: 1.5; color: var(--text-sub); }
.feature-list { list-style: none; display: flex; flex-direction: column; gap: 0.6rem; }
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  font-size: 0.86rem;
  color: var(--text-sub);
  line-height: 1.45;
}
.feature-bullet { color: var(--accent-mint); font-weight: 800; font-size: 1.1rem; line-height: 1; }
.stat-strip { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.85rem; }
.stat-card-pro {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 0.75rem 1rem;
}
.stat-card-pro.highlight { border-color: rgba(34, 197, 94, 0.45); background: rgba(16, 185, 129, 0.15); }
.stat-big { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 800; color: var(--accent-mint); line-height: 1.1; }
.stat-desc { font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.25rem; }
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
.progress-track { position: absolute; top: 0; left: 0; height: 3px; background: rgba(255, 255, 255, 0.1); width: 100%; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent-green), var(--accent-mint)); width: 0%; transition: width 0.25s ease; }
.nav-controls { display: flex; align-items: center; gap: 0.6rem; }
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
.btn-ctrl:hover { background: rgba(16, 185, 129, 0.25); border-color: var(--accent-mint); }
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
        {"".join(slides_list)}
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
                <span style="font-size: 0.7rem; color: var(--text-muted);" id="timer-max">/ 07:00</span>
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
        const notesData = {json.dumps(notes_dict)};
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

            document.getElementById('slide-num').innerText = `${{currentSlide + 1}} / ${{totalSlides}}`;
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
            document.getElementById('notes-slide-title').innerText = `Slide ${{currentSlide + 1}}: Guion (${{noteObj.speaker || 'Equipo'}})`;
            document.getElementById('notes-time-cue').innerText = `⏱️ Ventana: ${{noteObj.cue}}`;
            document.getElementById('notes-content').innerHTML = noteObj.text;
        }}

        function toggleNotes() {{ document.getElementById('notes-drawer').classList.toggle('open'); }}

        function formatTime(sec) {{
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
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

        document.getElementById('timer-max').innerText = `/ ${{formatTime(totalDuration)}}`;
        showSlide(0);
        updateTimerUI();
    </script>
</body>
</html>
"""

slides_defense = [
    # Slide 1: Ficha Técnica
    f"""
    <div class="slide active" data-speaker="Expositor 1 (Técnico)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">DEFENSA OFICIAL EN SALA • 7 MINUTOS</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Bloque 1: Memoria Técnica (3:30 min) | Bloque 2: Plan de Negocios (3:30 min)</span>
        </div>
        <h1 class="slide-title">FLUXA: Memoria Técnica y Plan de Negocios</h1>
        <p class="slide-subtitle">Sistema de Semáforos Inteligentes Edge AI, Telemetría SCADA y Red Vial Autónoma</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro highlight">
                        <div class="card-headline"><span class="icon">📋</span> Ficha Técnica de Registro Oficial</div>
                        <div style="font-size: 0.84rem; line-height: 1.6; color: #cbd5e1;">
                            • <strong>Folio Oficial:</strong> 70785-17<br>
                            • <strong>Categoría:</strong> Industria Eléctrica y Electrónica<br>
                            • <strong>Área de Aplicación:</strong> Digitalización y Automatización<br>
                            • <strong>Áreas Específicas:</strong> Infraestructura y Ciudades Inteligentes, Industria 4.0<br>
                            • <strong>Naturaleza Técnica:</strong> Ciencias Computacionales y Electrónica<br>
                            • <strong>Institución:</strong> Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
                        </div>
                    </div>
                    <div class="card-pro">
                        <div class="card-headline"><span class="icon">👥</span> Equipo Multidisciplinario y Asesoría</div>
                        <div style="font-size: 0.8rem; line-height: 1.45; color: #cbd5e1;">
                            • <strong>Moisés Emilio Martínez Arias</strong> (Líder / Dev Principal - ISC 3°)<br>
                            • <strong>Diego Huichapeño</strong> (ISC 5°) • <strong>Ethan Flores</strong> (ISC 5°)<br>
                            • <strong>Citlalli Rojas</strong> (TICs 8°) • <strong>Jerazan Becerra</strong> (ISC 3°)<br>
                            • <strong>Asesor Técnico:</strong> Mtro. Roberto Carlos Muñoz Celaya
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{fluxa_logo}" alt="Logotipo Oficial FLUXA" style="padding: 1.5rem; background: #060b08;">
                    <div class="media-caption">
                        <span>Marca y Desarrollo Registrado: <strong>FLUXA Smart Mobility</strong></span>
                        <span class="badge-tag">TESCo • TecNM</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 2: Diagnóstico
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag red">DIAGNÓSTICO DE INGENIERÍA</span>
            <span style="font-size: 0.8rem; color: #fca5a5;">Obsolescencia Tecnológica en la Red Vial Nacional</span>
        </div>
        <h1 class="slide-title">El Cuello de Botella de los Controladores Actuales</h1>
        <p class="slide-subtitle">Fallas críticas de temporizadores fijos, sensores invasivos y arquitecturas de nube</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro danger">
                        <ul class="feature-list">
                            <li class="feature-item">
                                <span class="feature-bullet" style="color: #f87171;">✕</span>
                                <div><strong>Temporizadores Fijos Rígidos:</strong> Incapaces de adaptarse a la demanda real, provocando colas kilométricas y emisiones masivas en ralentí.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet" style="color: #f87171;">✕</span>
                                <div><strong>Espiras Inductivas Invasivas:</strong> Sensores magnéticos bajo el asfalto que se fracturan con el reencarpetamiento y baches en menos de 1 año.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet" style="color: #f87171;">✕</span>
                                <div><strong>Dependencia de Nube Inviable:</strong> Latencias superiores a 500 ms y costos exorbitantes en dólares por streaming de video.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight">
                        <div style="font-size: 0.88rem; color: #a7f3d0; line-height: 1.5;">
                            🎯 <strong>Objetivo Técnico de FLUXA:</strong> Llevar la toma de decisiones al borde (*Edge AI*), con latencia menor a 12 ms, sin tocar el asfalto y manteniendo compatibilidad total con la infraestructura eléctrica existente.
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{traffic_img}" alt="Congestión en intersección">
                    <div class="media-caption">
                        <span>Evidencia de campo: <strong>Saturación vial por semáforos de tiempo fijo</strong></span>
                        <span class="badge-tag red">Diagnóstico</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 3: Hardware Edge & Retrofit
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">HARDWARE EMBEBIDO & RETROFIT</span>
            <span style="font-size: 0.8rem; color: var(--accent-mint);">Arquitectura Edge Appliance Industrial</span>
        </div>
        <h1 class="slide-title">Arquitectura Edge Appliance & Retrofit Overlay</h1>
        <p class="slide-subtitle">Modernización sobre gabinetes normados sin requerir obra civil destructiva</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">Componentes del Edge Box (Gabinete NEMA IP66):</div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>SBC Principal:</strong> Orange Pi 5 (SoC Rockchip RK3588, 8 Cores CPU + Tri-Core NPU 6 TOPS).</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>Sensor Óptico:</strong> Cámara vial gran angular HD con carcasa antivandalismo IP66.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>Etapa de Potencia:</strong> Relevadores de Estado Sólido (SSR) con aislamiento optoacoplado para 120VAC / 24VDC.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>Controlador Esclavo:</strong> Arduino UNO R4 Minima con Watchdog de hardware.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight">
                        <div style="font-size: 0.86rem; color: #6ee7b7; line-height: 1.5;">
                            ⚡ <strong>Instalación Retrofit (&lt; 4 horas):</strong> Se conecta a gabinetes NEMA TS2 o Tipo 170/2070 existentes. Aprovecha cabezales, postes y acometidas eléctricas sin romper calles.
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{opi5_img}" alt="Orange Pi 5 Hardware">
                    <div class="media-caption">
                        <span>Unidad de Procesamiento: <strong>SoC Rockchip RK3588 (6 TOPS NPU)</strong></span>
                        <span class="badge-tag">Edge Box</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 4: Pipeline Inferencia NPU
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">INTELIGENCIA ARTIFICIAL EN EL BORDE</span>
            <span style="font-size: 0.8rem; color: var(--accent-mint);">Optimización Cuantizada INT8 con RKNN-Toolkit2</span>
        </div>
        <h1 class="slide-title">Pipeline de Inferencia Neuronal en NPU & Tracking</h1>
        <p class="slide-subtitle">Procesamiento visual determinista a 30 FPS continuos con latencia menor a 12 ms</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro highlight">
                        <div class="card-headline">Etapas del Pipeline de Visión:</div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">1</span>
                                <div><strong>Inferencia Cuantizada INT8:</strong> YOLOv8 adaptado a formato binario RKNN. Ejecución en NPU dedicada (&lt;12ms), liberando el 70% de la CPU.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">2</span>
                                <div><strong>BYTETracker con Filtro de Kalman:</strong> Asigna IDs únicos a cada vehículo y mantiene el seguimiento aun con oclusiones visuales temporales.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">3</span>
                                <div><strong>Zonificación y Demanda Ponderada (TSP):</strong> Polígonos ROIs direccionales. Prioriza transporte público (factor 1.5x) y ajusta verdes entre 5 y 45 segundos.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">&lt; 12 ms</div>
                            <div class="stat-desc">Latencia de Inferencia por Frame</div>
                        </div>
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">30 FPS</div>
                            <div class="stat-desc">Tasa Continua de Video Vial</div>
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{yolo_img}" alt="Detección y seguimiento vehicular YOLOv8">
                    <div class="media-caption">
                        <span>Detección y tracking en vivo: <strong>IDs únicos y estimación de velocidad</strong></span>
                        <span class="badge-tag">YOLOv8 INT8</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 5: Tri-Core & Ola Verde
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag blue">ORQUESTACIÓN MULTI-CRUCE & OLA VERDE</span>
            <span style="font-size: 0.8rem; color: #67e8f9;">Arquitectura Simétrica Tri-Core</span>
        </div>
        <h1 class="slide-title">Orquestación Tri-Core y Sincronización Vial</h1>
        <p class="slide-subtitle">1 sola Orange Pi 5 gestiona 3 intersecciones completas con Ola Verde Dinámica</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">Despliegue Tri-Core en 1 solo SoC:</div>
                        <div style="font-size: 0.82rem; line-height: 1.5; color: #cbd5e1;">
                            • <strong>Cruce Norte (Av. Central):</strong> Puerto 5000 • Core NPU 0<br>
                            • <strong>Cruce Centro (Av. Hidalgo):</strong> Puerto 5001 • Core NPU 1<br>
                            • <strong>Cruce Sur (Av. del Parque):</strong> Puerto 5002 • Core NPU 2
                        </div>
                    </div>
                    <div class="card-pro highlight">
                        <div class="card-headline">Módulo corridor_sync.py (Ola Verde Adaptativa):</div>
                        <p class="card-text" style="font-size: 0.82rem;">
                            Detecta la salida de pelotones vehiculares en el cruce aguas arriba y calcula su tiempo estimado de arribo a 45 km/h. Conmuta a verde anticipadamente en el semáforo receptor, eliminando las paradas continuas y reduciendo hasta un 40% las demoras de corredor.
                        </p>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{delay_chart}" alt="Reducción de demora en corredor vial">
                    <div class="media-caption">
                        <span>Demoras en Corredor: <strong>FLUXA Ola Verde vs Control Tradicional</strong></span>
                        <span class="badge-tag blue">-40% Demora</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 6: Fail-Safe & NOMs
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag amber">SEGURIDAD VIAL & NORMATIVIDAD</span>
            <span style="font-size: 0.8rem; color: #fde047;">Tolerancia a Fallos y Conmutación en Caliente</span>
        </div>
        <h1 class="slide-title">Matriz Fail-Safe Industrial y Cumplimiento NOM</h1>
        <p class="slide-subtitle">3 niveles de resiliencia operativa y estricto apego a normas oficiales mexicanas</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">3 Niveles de Protección Redundante:</div>
                        <ul class="feature-list" style="font-size: 0.82rem;">
                            <li class="feature-item">
                                <span class="feature-bullet" style="color: var(--accent-mint);">N1</span>
                                <div><strong>Pérdida de Video:</strong> Conmutación automática instantánea a ciclo de tiempo fijo predeterminado.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet" style="color: var(--accent-amber);">N2</span>
                                <div><strong>Fallo de NPU:</strong> Conmutación en caliente (*hot-swap*) a CPU PyTorch sin apagar los semáforos.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet" style="color: var(--accent-red);">N3</span>
                                <div><strong>Congelamiento de SBC:</strong> Watchdog de hardware en microcontrolador (Arduino R4) activa destello preventivo ámbar a los 3 segundos.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight">
                        <div style="font-size: 0.82rem; color: #cbd5e1; line-height: 1.5;">
                            📜 <strong>NOM-034-SCT2-2011:</strong> Fases mínimas de ámbar (3s) y todo-rojo (1.5s). Cero verdes conflictivos simultáneos.<br>
                            ⚡ <strong>NOM-001-SEDE-2012:</strong> Aislamiento galvánico y protecciones contra transitorios.
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{failsafe_img}" alt="Matriz de Tolerancia a Fallos Industrial">
                    <div class="media-caption">
                        <span>Matriz Fail-Safe Industrial: <strong>Conmutación en 3 niveles de seguridad</strong></span>
                        <span class="badge-tag amber">NOM-034 / NOM-001</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 7: Mercado B2G (Transición a Expositor 2)
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag blue">VALIDACIÓN DE MERCADO Y CLIENTE</span>
            <span style="font-size: 0.8rem; color: #67e8f9;">Bloque 2: Viabilidad Comercial y Financiera</span>
        </div>
        <h1 class="slide-title">Segmentación de Mercado B2G / B2B y Validación</h1>
        <p class="slide-subtitle">Validación técnica en campo con autoridades viales del Estado de México</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">Segmentos de Clientes Clave:</div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">🏛️</span>
                                <div><strong>Tomador de Decisión (B2G):</strong> Direcciones de Seguridad Ciudadana y Tránsito Municipal, Secretarías de Movilidad Estatales (SEMOV).</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">👮</span>
                                <div><strong>Usuario Operativo:</strong> Operadores de Centros de Comando C5/C4 e ingenieros de semaforización.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">🚑</span>
                                <div><strong>Beneficiarios:</strong> Servicios de emergencia con prioridad de paso, transporte público y ciudadanía en general.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight">
                        <div class="card-headline" style="font-size: 0.95rem;">Entrevistas en Coacalco, Ecatepec y Tultitlán:</div>
                        <p class="card-text" style="font-size: 0.82rem;">
                            Los municipios buscan modernizar pero están atados por la burocracia de licitaciones costosas. FLUXA supera esta barrera mediante <strong>pilotos demostrativos de 30 días</strong> y <strong>esquemas de arrendamiento de bajo costo inicial</strong>.
                        </p>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{b2g_funnel}" alt="Embudo de Adopción y Venta B2G">
                    <div class="media-caption">
                        <span>Embudo Comercial B2G: <strong>Piloto ➔ Dictamen ROI ➔ Adjudicación ➔ Despliegue</strong></span>
                        <span class="badge-tag blue">Estrategia B2G</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 8: BOM de Costos
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag blue">MODELO ECONÓMICO UNITARIO</span>
            <span style="font-size: 0.8rem; color: #67e8f9;">Estructura de Fabricación Industrial</span>
        </div>
        <h1 class="slide-title">Estructura de Costo Directo (BOM) y Margen</h1>
        <p class="slide-subtitle">Desglose de costos directos de fabricación (COGS) por intersección de 4 accesos</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">Desglose BOM Unitario ($10,750 MXN):</div>
                        <div style="font-size: 0.82rem; line-height: 1.5; color: #cbd5e1;">
                            • <strong>Orange Pi 5 (RK3588 + eMMC industrial):</strong> $3,200 MXN (29.8%)<br>
                            • <strong>Ensamble, Calibración y Pruebas:</strong> $2,200 MXN (20.5%)<br>
                            • <strong>Gabinete NEMA IP66 + Fuente MeanWell:</strong> $2,100 MXN (19.5%)<br>
                            • <strong>Cámara Vial Gran Angular HD Intemperie:</strong> $1,800 MXN (16.7%)<br>
                            • <strong>Relevadores SSR + Arduino R4 Watchdog:</strong> $1,450 MXN (13.5%)
                        </div>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">$28,500</div>
                            <div class="stat-desc">Precio Venta CapEx (Cruce 4 vías)</div>
                        </div>
                        <div class="stat-card-pro highlight">
                            <div class="stat-big" style="color: #6ee7b7;">62.3%</div>
                            <div class="stat-desc">Margen Bruto de Utilidad</div>
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{bom_chart}" alt="Estructura de Costo Unitario BOM">
                    <div class="media-caption">
                        <span>BOM Desglosado: <strong>Costo $10,750 MXN | Venta $28,500 MXN</strong></span>
                        <span class="badge-tag blue">Margen 62.3%</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 9: Proyecciones Financieras Año 1
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag blue">PROYECCIONES FINANCIERAS</span>
            <span style="font-size: 0.8rem; color: #67e8f9;">Escalabilidad Comercial y Flujo Recurrente</span>
        </div>
        <h1 class="slide-title">Proyección de Ingresos y Utilidad (Año 1)</h1>
        <p class="slide-subtitle">Rampa de ventas proyectada para 50 intersecciones en el Valle de México</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">3 Vertientes de Ingresos:</div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>Venta Hardware (CapEx):</strong> 50 unidades x $28,500 = <strong>$1,425,000 MXN</strong>.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>Licencia SCADA C5 (OpEx):</strong> 50 cruces x $8,400 = <strong>$420,000 MXN</strong>.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>Póliza SLA 24/7:</strong> 50 cruces x $6,000 = <strong>$300,000 MXN</strong>.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="stat-strip">
                        <div class="stat-card-pro highlight">
                            <div class="stat-big">$2.145 MDP</div>
                            <div class="stat-desc">Ingreso Total Proyectado Año 1</div>
                        </div>
                        <div class="stat-card-pro highlight">
                            <div class="stat-big" style="color: #6ee7b7;">$890,000</div>
                            <div class="stat-desc">Utilidad Neta Estimada (41.5%)</div>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">
                        Inversión inicial requerida: <strong>$180,000 MXN</strong> (10 kits piloto, trámites IMPI/INDAUTOR y herramental).
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{rev_chart}" alt="Proyección de Escalabilidad e Ingresos">
                    <div class="media-caption">
                        <span>Escalabilidad Año 1: <strong>Rampa de $162k a $2.14 MDP acumulados</strong></span>
                        <span class="badge-tag blue">50 Nodos</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 10: Retorno de Inversión Social
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag amber">RETORNO SOCIAL & AMBIENTAL</span>
            <span style="font-size: 0.8rem; color: #fde047;">Impacto en Ciudadanía y Descarbonización Urbana</span>
        </div>
        <h1 class="slide-title">Retorno de Inversión Social (Social Payback)</h1>
        <p class="slide-subtitle">Modelo econométrico auditado con fuentes oficiales verificables</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro highlight">
                        <div class="card-headline" style="color: #6ee7b7;">Beneficio Social Auditado por Cruce / Año:</div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">⛽</span>
                                <div><strong>15,968 Litros de Gasolina Ahorrados:</strong> Basado en 0.70 L/h de ralentí (DOE / CONUEE) y aforo de 15,000 veh/día (SEDATU).</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">💵</span>
                                <div><strong>$391,234 MXN de Ahorro Directo:</strong> Beneficio neto en el bolsillo de las familias conductoras ($24.50/L CRE).</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">🌱</span>
                                <div><strong>36.8 Toneladas de CO₂ Mitigadas:</strong> Factor oficial INECC de 2.31 kg CO₂e por litro no quemado.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro" style="text-align: center; border-color: var(--accent-mint); background: rgba(16, 185, 129, 0.15);">
                        <div style="font-size: 1.1rem; font-weight: 800; color: #fff;">
                            Payback Social: <span style="color: #6ee7b7;">Menos de 90 Días</span>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">
                            En 10 cruces: $3.91 MDP ahorrados y 368 Ton CO₂ mitigadas al año.
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{report_pdf}" alt="Informe Oficial de Auditoría Vial">
                    <div class="media-caption">
                        <span>Reporte Ejecutivo Automatizado: <strong>Métricas de ahorro y CO₂ para Cabildo</strong></span>
                        <span class="badge-tag amber">Auditoría Vial</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 11: Propiedad Intelectual & Ejes Transversales
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">PROPIEDAD INTELECTUAL & ÉTICA</span>
            <span style="font-size: 0.8rem; color: var(--accent-mint);">Protección Legal y Responsabilidad Social</span>
        </div>
        <h1 class="slide-title">Propiedad Intelectual y Ejes Transversales</h1>
        <p class="slide-subtitle">Blindaje jurídico integral ante INDAUTOR e IMPI y apego a lineamientos TecNM</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline"><span class="icon">⚖️</span> Estrategia de Propiedad Intelectual:</div>
                        <ul class="feature-list" style="font-size: 0.82rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>INDAUTOR:</strong> Registro de Software para la máquina de estados FSM, algoritmos TSP y consola SCADA como "Programa de Computación".</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>IMPI (Modelo de Utilidad):</strong> Disposición física del nodo, gabinete antivandalismo y habitáculo óptico.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">•</span>
                                <div><strong>IMPI (Marca):</strong> Registro de la denominación "FLUXA" en Clase 9 (aparatos científicos y de procesamiento).</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight">
                        <div class="card-headline"><span class="icon">🌟</span> Ejes Transversales del TecNM:</div>
                        <div style="font-size: 0.8rem; color: #cbd5e1; line-height: 1.45;">
                            • <strong>Inclusión:</strong> Módulo de demanda peatonal asistida.<br>
                            • <strong>Impacto Social:</strong> Despeje de emergencias C5 en 2 segundos.<br>
                            • <strong>Sustentabilidad:</strong> Descarbonización de corredores urbanos.<br>
                            • <strong>Tecnologías Emergentes:</strong> Edge AI, NPU INT8 y Digital Twins.
                        </div>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{indautor_img}" alt="Sede INDAUTOR">
                    <div class="media-caption">
                        <span>Protección Intelectual: <strong>Trámites ante INDAUTOR e IMPI en curso</strong></span>
                        <span class="badge-tag">INDAUTOR / IMPI</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 12: Hoja de Ruta y Conclusiones
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr}
        <div class="slide-meta-row">
            <span class="badge-tag">CONCLUSIONES & HOJA DE RUTA</span>
            <span style="font-size: 0.8rem; color: var(--accent-mint);">Soberanía e Innovación Mexicana</span>
        </div>
        <h1 class="slide-title">Hoja de Ruta y Conclusiones</h1>
        <p class="slide-subtitle">Trascendencia tecnológica, escalamiento y soberanía para México</p>
        
        <div class="slide-body">
            <div class="split-hero">
                <div class="text-col">
                    <div class="card-pro">
                        <div class="card-headline">Cronograma de Escalamiento:</div>
                        <ul class="feature-list" style="font-size: 0.84rem;">
                            <li class="feature-item">
                                <span class="feature-bullet">📍</span>
                                <div><strong>Fase 1 (Meses 1-4):</strong> 10 cruces piloto demostrativos en Coacalco y Ecatepec con auditoría de tráfico gratuita para el municipio.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">🚀</span>
                                <div><strong>Fase 2 (Meses 5-12):</strong> Venta y despliegue de 40 unidades en corredores metropolitanos e integración formal con C5.</div>
                            </li>
                            <li class="feature-item">
                                <span class="feature-bullet">🇲🇽</span>
                                <div><strong>Fase 3:</strong> Escalamiento nacional mediante convenios interinstitucionales a través de la red del TecNM.</div>
                            </li>
                        </ul>
                    </div>
                    <div class="card-pro highlight" style="text-align: center; padding: 1.1rem; background: rgba(16, 185, 129, 0.2); border-color: var(--accent-mint);">
                        <div style="font-size: 1.15rem; font-weight: 800; color: #fff; margin-bottom: 0.3rem;">
                            FLUXA: Orgullo Tecnológico Mexicano del TESCo • TecNM
                        </div>
                        <p class="card-text" style="font-size: 0.88rem;">
                            Agradecemos su atención y quedamos a su entera disposición para la sesión de preguntas y respuestas, y la demostración física de nuestro prototipo en el stand.
                        </p>
                    </div>
                </div>
                <div class="media-frame">
                    <img src="{scada_img}" alt="Plataforma FLUXA SCADA">
                    <div class="media-caption">
                        <span>Demostración en Stand: <strong>Prototipo Físico + SCADA en Tiempo Real</strong></span>
                        <span class="badge-tag">Stand #1</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
]

notes_defense = {
    0: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "0:00 - 0:25 (25s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[0:00]</span> Buenos días, honorable jurado calificador y miembros del comité evaluador de la Etapa Regional del InnovaTecNM 2026. Representamos con orgullo al Tecnológico de Estudios Superiores de Coacalco.<br><span class=\"notes-cue\">[0:12]</span> Defendemos el proyecto <strong>FLUXA Smart Mobility</strong>, folio <strong>70785-17</strong> en la categoría de Industria Eléctrica y Electrónica. Esta defensa se divide en dos bloques: los primeros 3:30 minutos dedicados a la arquitectura de ingeniería a mi cargo, y los siguientes 3:30 minutos a la viabilidad financiera y de mercado a cargo de mi compañera/compañero.</p>"
    },
    1: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "0:25 - 1:05 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[0:25]</span> Comenzamos con el diagnóstico. El 90% de la red semafórica nacional opera bajo temporizadores de tiempo fijo diseñados hace cuatro décadas. Son ciegos al tráfico: asignan tiempos iguales a avenidas colapsadas y a vías desiertas.<br><span class=\"notes-cue\">[0:45]</span> Las espiras inductivas bajo el asfalto se rompen con el primer bache, y las soluciones que envían video a la nube sufren de latencias inaceptables y altos costos en dólares.<br><span class=\"notes-cue\">[0:58]</span> La solución técnica de FLUXA es el <strong>Edge Computing</strong>: ver, razonar y conmutar directamente en la intersección en milisegundos con total autonomía.</p>"
    },
    2: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "1:05 - 1:45 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[1:05]</span> Para materializar esto desarrollamos el <strong>FLUXA Edge Appliance</strong> bajo arquitectura <strong>Retrofit Overlay</strong>. En lugar de reemplazar el poste o cableado, colocamos un gabinete NEMA IP66 que se acopla en <strong>menos de 4 horas</strong> a la infraestructura existente.<br><span class=\"notes-cue\">[1:25]</span> El corazón del sistema es una Orange Pi 5 dotada del SoC Rockchip RK3588 con NPU de 6 TOPS. El control de las luces se realiza mediante relevadores de estado sólido con aislamiento optoacoplado y un microcontrolador esclavo Arduino UNO R4 Minima que gobierna la potencia con grado industrial.</p>"
    },
    3: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "1:45 - 2:25 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[1:45]</span> En la capa de visión, cuantizamos modelos YOLOv8 a formato binario asimétrico INT8 mediante RKNN-Toolkit2. Esto nos permite ejecutar inferencia completa en <strong>menos de 12 milisegundos</strong> a 30 cuadros por segundo continuos.<br><span class=\"notes-cue\">[2:05]</span> Asociamos el algoritmo BYTETracker con Filtro de Kalman para rastrear vehículos individuales aun con oclusiones visuales. Los centroides se cruzan contra polígonos de aforo para calcular la Demanda Ponderada (TSP), otorgando prioridad matemática al transporte público.</p>"
    },
    4: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "2:25 - 3:00 (35s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[2:25]</span> Un diferenciador de ingeniería único de FLUXA es su capacidad <strong>Tri-Core</strong>: una sola placa Orange Pi 5 es capaz de orquestar <strong>3 intersecciones completas simultáneamente</strong>, asignando un núcleo NPU a cada cruce en puertos independientes.<br><span class=\"notes-cue\">[2:45]</span> Además, desarrollamos el módulo <strong>corridor_sync.py</strong>, que calcula la velocidad promedio y el tiempo de arribo de pelotones vehiculares para coordinar <strong>Olas Verdes Dinámicas</strong> entre cruces consecutivos, reduciendo hasta un 40% las demoras de corredor.</p>"
    },
    5: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "3:00 - 3:30 (30s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[3:00]</span> La seguridad vial es innegociable. FLUXA implementa una matriz de tolerancia a fallos de 3 niveles: si falla la cámara, conmuta a tiempo fijo; si falla la NPU, conmuta en caliente a la CPU PyTorch; y si se congela el sistema operativo, el watchdog del microcontrolador entra en destello preventivo en 3 segundos.<br><span class=\"notes-cue\">[3:18]</span> Cumplimos con la <strong>NOM-034-SCT2-2011</strong> en tiempos de despeje y con la <strong>NOM-001-SEDE-2012</strong> en seguridad eléctrica. 100% aprobado en PyTest con madurez <strong>TRL 6/7</strong>.<br><span class=\"notes-cue\">[3:28]</span> Cedo la palabra a mi compañera/compañero para exponer la viabilidad de mercado y negocios.</p>"
    },
    6: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "3:30 - 4:10 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[3:30]</span> Muchas gracias. Pasando a la viabilidad comercial, FLUXA opera en el mercado <strong>B2G y B2B de movilidad inteligente</strong>. Nuestros compradores directos son las Direcciones de Tránsito Municipal y Secretarías de Movilidad, y los usuarios operativos son los operadores de centros de comando C5.<br><span class=\"notes-cue\">[3:50]</span> Durante el desarrollo realizamos entrevistas en campo con técnicos de semaforización de <strong>Coacalco, Ecatepec y Tultitlán</strong>. Confirmamos que su mayor obstáculo es la barrera presupuestal de las marcas extranjeras. Para mitigar la burocracia de licitaciones, estructuramos pilotos demostrativos de 30 días y contratos por arrendamiento.</p>"
    },
    7: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "4:10 - 4:50 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[4:10]</span> Analicemos los costos unitarios. El Costo Directo de Fabricación (BOM) de un nodo FLUXA de 4 vías es de <strong>$10,750 MXN</strong>, que incluye la Orange Pi 5, relevadores SSR, cámara HD para intemperie, gabinete NEMA MeanWell y mano de obra.<br><span class=\"notes-cue\">[4:30]</span> Fijamos un precio de venta de <strong>$28,500 MXN</strong> por intersección. Esto nos otorga un <strong>margen bruto del 62.3%</strong>, dejando una utilidad de $17,750 pesos por equipo, y ofreciendo al municipio un ahorro del <strong>95%</strong> frente a los más de medio millón de pesos que cuesta una solución importada.</p>"
    },
    8: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "4:50 - 5:30 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[4:50]</span> Nuestro modelo de ingresos es híbrido para garantizar recurrencia: venta de hardware más una licencia anual de software SCADA C5 de $8,400 pesos por cruce, y una póliza de servicio SLA 24/7 de $6,000 pesos.<br><span class=\"notes-cue\">[5:10]</span> Para el Año 1 proyectamos instalar 50 intersecciones en corredores prioritarios del Valle de México. Esto generará <strong>$2.14 millones de pesos en ingresos totales</strong> y una <strong>utilidad neta de $890,000 MXN</strong>, lo que representa un margen neto del <strong>41.5%</strong>, requiriendo una inversión inicial de solo $180,000 MXN.</p>"
    },
    9: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "5:30 - 6:10 (40s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[5:30]</span> Sin embargo, el argumento más contundente para un gobierno es el <strong>Retorno de Inversión Social</strong>. Utilizando fórmulas estandarizadas del Departamento de Energía de EE.UU., CONUEE, SEDATU e INECC, un ahorro de apenas 15 segundos de ralentí en un cruce con 15,000 autos al día produce:<br><span class=\"notes-cue\">[5:50]</span> Un ahorro anual de <strong>15,968 litros de gasolina</strong>, equivalente a <strong>$391,234 pesos ahorrados directamente por la ciudadanía</strong> y 36.8 toneladas de CO₂ evitadas por cruce. En un corredor de 10 cruces, son casi 4 millones de pesos anuales de beneficio social. El retorno de inversión social se logra en <strong>menos de 90 días</strong>.</p>"
    },
    10: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "6:10 - 6:40 (30s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[6:10]</span> En materia de Propiedad Intelectual, protegemos el código fuente integral y la consola SCADA ante el <strong>INDAUTOR</strong> como Programa de Computación. Paralelamente, tramitamos ante el <strong>IMPI</strong> el Modelo de Utilidad para el habitáculo físico antivandalismo y el registro marcario de FLUXA en Clase 9.<br><span class=\"notes-cue\">[6:25]</span> Cumplimos con los cuatro ejes transversales del TecNM: Inclusión mediante botonera peatonal asistida, Impacto Social con prioridad a ambulancias C5, Sustentabilidad ambiental con descarbonización y Adopción de Tecnologías Emergentes.</p>"
    },
    11: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "6:40 - 7:00 (20s)",
        "text": "<p class=\"notes-body\"><span class=\"notes-cue\">[6:40]</span> Nuestra hoja de ruta contempla iniciar pilotos en Coacalco, expandirnos a corredores metropolitanos y escalar nacionalmente mediante convenios del TecNM.<br><span class=\"notes-cue\">[6:52]</span> Concluimos con orgullo: FLUXA es soberanía tecnológica mexicana para transformar nuestras ciudades. Quedamos a su entera disposición para sus preguntas y para recibirlos en nuestro stand. <strong>Muchas gracias.</strong></p>"
    }
}

defense_html = wrap_html("DEFENSA OFICIAL (7 Min)", 420, slides_defense, notes_defense, "Expositor 1 (Técnico)")
def_out_path = os.path.join(OUTPUT_DIR, 'defensa_tecnica_negocios_7min.html')

with open(def_out_path, 'w', encoding='utf-8') as f:
    f.write(defense_html)

print("defensa_tecnica_negocios_7min.html generado.")

# Render to PDF
pdf_target = os.path.join(OUTPUT_DIR, 'FLUXA_Defensa_Tecnica_Negocios_7Min_InnovaTecNM_2026.pdf')
cmd = [
    'chromium', '--headless=new', '--no-sandbox', '--disable-gpu',
    '--run-all-compositor-stages-before-draw', '--virtual-time-budget=6000',
    f'--print-to-pdf={pdf_target}',
    '--print-to-pdf-no-header', def_out_path
]
subprocess.run(cmd, check=True)

# Copy aliases
subprocess.run(['cp', pdf_target, os.path.join(OUTPUT_DIR, 'defensa_tecnica_negocios_7min.pdf')], check=True)
subprocess.run(['cp', pdf_target, os.path.join(USER_PDF_DIR, 'FLUXA_Defensa_Tecnica_Negocios_7Min_InnovaTecNM_2026.pdf')], check=True)
subprocess.run(['cp', pdf_target, os.path.join(USER_PDF_DIR, 'defensa_tecnica_negocios_7min.pdf')], check=True)

print("Defense PDF compiled and deployed successfully!")
