#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador Pro de Presentaciones Oficiales InnovaTecNM 2026 - FLUXA Smart Mobility
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
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
bom_chart = b64_img(OPT_DIR, 'bom_cost_pie_chart.png')
rev_chart = b64_img(OPT_DIR, 'revenue_ramp_chart.png')
failsafe_img = b64_img(OPT_DIR, 'fail_safe_matrix.png')
pytest_img = b64_img(OPT_DIR, 'pytest_suite_approved.png')
trl_chart = b64_img(OPT_DIR, 'trl_maturity_chart.png')
indautor_img = b64_img(OPT_DIR, 'indautor_facade.jpg', 'image/jpeg')
sct_diag = b64_img(OPT_DIR, 'sct_intersection_diagram.png')
b2g_funnel = b64_img(OPT_DIR, 'b2g_adoption_funnel.png')
report_pdf = b64_img(OPT_DIR, 'official_report_pdf.jpg', 'image/jpeg')
delay_chart = b64_img(OPT_DIR, 'delay_reduction_corridor.png')

PRO_CSS = """
:root {
  --bg-deep: #050a07;
  --bg-card: rgba(13, 23, 17, 0.92);
  --border-card: rgba(34, 197, 94, 0.28);
  --border-glow: rgba(52, 211, 153, 0.55);
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

/* Header */
.slide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding-bottom: 0.75rem;
  margin-bottom: 1rem;
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
  height: 38px;
  object-fit: contain;
  filter: drop-shadow(0 2px 6px rgba(16, 185, 129, 0.3));
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

/* Titles */
.slide-meta-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 0.35rem;
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

.badge-tag.red {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border-color: rgba(239, 68, 68, 0.4);
}

.badge-tag.blue {
  background: rgba(6, 182, 212, 0.15);
  color: #67e8f9;
  border-color: rgba(6, 182, 212, 0.4);
}

.badge-tag.amber {
  background: rgba(245, 158, 11, 0.15);
  color: #fde047;
  border-color: rgba(245, 158, 11, 0.4);
}

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

/* Body Content */
.slide-body {
  flex: 1;
  display: flex;
  align-items: center;
  margin-top: 0.6rem;
}

.split-hero {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 2rem;
  width: 100%;
  align-items: center;
}

.split-hero-reverse {
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 2rem;
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
  background: rgba(0, 0, 0, 0.6);
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
  object-fit: cover;
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

.media-caption strong {
  color: var(--accent-mint);
}

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

/* Bottom Bar */
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

.timer-warning {
  color: var(--accent-amber) !important;
  border-color: var(--accent-amber) !important;
}

.timer-expired {
  color: var(--accent-red) !important;
  border-color: var(--accent-red) !important;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.slide-counter {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

.speaker-pill {
  font-size: 0.75rem;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.35);
  padding: 0.2rem 0.65rem;
  border-radius: 9999px;
  font-weight: 700;
}

/* Notes Drawer */
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
.notes-body {
  font-size: 1rem;
  line-height: 1.6;
  color: #f1f5f9;
}
.notes-cue {
  font-weight: 800;
  color: #38bdf8;
  margin-right: 0.4rem;
}

/* Print Rules: 16in x 9in exactly */
@page {
  size: 16in 9in;
  margin: 0;
}

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
  #presentation {
    display: block !important;
    height: auto !important;
    width: 16in !important;
  }
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
    padding: 2rem 3.4rem 2rem 3.4rem !important;
  }
  .bottom-bar, #notes-drawer { display: none !important; }
}
"""

def generate_pro_html(title, total_seconds, slides_list, notes_dict, speaker_tag="Expositor 1"):
    slides_rendered = "".join(slides_list)
    notes_json = json.dumps(notes_dict)
    
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — FLUXA Smart Mobility</title>
    <style>{PRO_CSS}</style>
</head>
<body>
    <div id="presentation">
        {slides_rendered}
    </div>

    <!-- Notes Drawer -->
    <div id="notes-drawer">
        <div class="notes-header">
            <span id="notes-slide-title">Guion de Exposición</span>
            <span id="notes-time-cue" style="color: #38bdf8; font-family: 'JetBrains Mono';">Tiempo sugerido</span>
        </div>
        <div class="notes-body" id="notes-content">Cargando guion...</div>
    </div>

    <!-- Bottom Controls -->
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

        function toggleNotes() {{
            document.getElementById('notes-drawer').classList.toggle('open');
        }}

        function formatTime(sec) {{
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
        }}

        function updateTimerUI() {{
            const tBox = document.getElementById('timer-box');
            document.getElementById('timer-text').innerText = formatTime(timerSeconds);
            const ratio = timerSeconds / totalDuration;
            if (timerSeconds >= totalDuration) {{
                tBox.className = 'timer-display timer-expired';
            }} else if (ratio >= 0.8) {{
                tBox.className = 'timer-display timer-warning';
            }} else {{
                tBox.className = 'timer-display';
            }}
        }}

        function toggleTimer() {{
            if (isRunning) {{
                clearInterval(timerInterval);
                isRunning = false;
                document.getElementById('btn-timer').innerText = '▶ Play';
            }} else {{
                isRunning = true;
                document.getElementById('btn-timer').innerText = '⏸ Pausa';
                timerInterval = setInterval(() => {{
                    timerSeconds++;
                    updateTimerUI();
                }}, 1000);
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

print("Generator function ready.")
