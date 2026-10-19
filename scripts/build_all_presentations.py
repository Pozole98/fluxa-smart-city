#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador Automatizado de Presentaciones Oficiales - InnovaTecNM 2026
Proyecto: FLUXA Smart Mobility (Folio 70785-17)
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
"""

import os
import base64

BASE_DIR = '/home/fluxa/fluxa-smart-city'
LOGOS_DIR = os.path.join(BASE_DIR, 'logos')
OUTPUT_DIR = os.path.join(BASE_DIR, 'presentaciones')
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

def get_base64(name):
    p = os.path.join(LOGOS_DIR, name)
    if os.path.exists(p):
        with open(p, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

tesco_img = get_base64('tesco.png')
tecnm_img = get_base64('tecnm.png')
sic_img = get_base64('sic.png')

def make_header(tag="INDUSTRIA ELÉCTRICA Y ELECTRÓNICA"):
    return f"""
    <div class="header-bar">
        <div class="logos-group">
            <img src="{tecnm_img}" alt="TecNM" class="inst-logo">
            <img src="{tesco_img}" alt="TESCo" class="inst-logo">
            <img src="{sic_img}" alt="SIC" class="inst-logo">
        </div>
        <div class="event-meta">
            <div><strong>InnovaTecNM 2026</strong> • Región 5 (Etapa Regional)</div>
            <div>Folio: <strong>70785-17</strong> | {tag}</div>
        </div>
    </div>
    """

def get_base_html(title, total_seconds, slides_html, notes_dict, speaker_tag="Expositor 1"):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — FLUXA Smart Mobility (InnovaTecNM 2026)</title>
    <style>
        :root {{
            --bg-deep: #060b08;
            --bg-surface: #0c1510;
            --bg-card: rgba(14, 25, 18, 0.85);
            --border-card: rgba(34, 197, 94, 0.25);
            --border-highlight: rgba(52, 211, 153, 0.6);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-green: #10b981;
            --accent-mint: #34d399;
            --accent-emerald: #059669;
            --accent-cyan: #06b6d4;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-deep);
            color: var(--text-main);
            overflow: hidden;
            height: 100vh;
            width: 100vw;
            user-select: none;
        }}
        #presentation {{
            position: relative;
            width: 100vw;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .slide {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            padding: 2rem 3.5rem 4.5rem 3.5rem;
            display: none;
            flex-direction: column;
            background: radial-gradient(circle at 50% 10%, rgba(16, 185, 129, 0.08) 0%, rgba(6, 11, 8, 0.98) 75%);
            overflow: hidden;
        }}
        .slide.active {{
            display: flex;
            animation: slideIn 0.25s ease-out forwards;
        }}
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .header-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 0.8rem;
            margin-bottom: 1.2rem;
        }}
        .logos-group {{
            display: flex;
            align-items: center;
            gap: 1.4rem;
        }}
        .inst-logo {{
            height: 42px;
            object-fit: contain;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
        }}
        .event-meta {{
            text-align: right;
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
        }}
        .event-meta strong {{
            color: var(--accent-mint);
            font-weight: 700;
        }}
        .slide-title-area {{
            margin-bottom: 1rem;
        }}
        .slide-badge {{
            display: inline-block;
            font-size: 0.72rem;
            text-transform: uppercase;
            font-weight: 800;
            letter-spacing: 1px;
            padding: 0.25rem 0.7rem;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-mint);
            border: 1px solid rgba(16, 185, 129, 0.35);
            margin-bottom: 0.4rem;
        }}
        .slide-title {{
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.2;
            background: linear-gradient(135deg, #ffffff 40%, var(--accent-mint) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .slide-subtitle {{
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}
        .slide-body {{
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 1.2rem;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.4rem;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.2rem;
        }}
        .grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 1.2rem 1.4rem;
            backdrop-filter: blur(12px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        }}
        .card.highlight {{
            border-color: var(--border-highlight);
            background: rgba(16, 185, 129, 0.12);
        }}
        .card.danger {{
            border-color: rgba(239, 68, 68, 0.4);
            background: rgba(239, 68, 68, 0.08);
        }}
        .card-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.6rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .card-title span.icon {{
            font-size: 1.2rem;
        }}
        .card p {{
            font-size: 0.88rem;
            line-height: 1.5;
            color: #cbd5e1;
        }}
        .stat-box {{
            display: flex;
            flex-direction: column;
            padding: 0.9rem 1.1rem;
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.45);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .stat-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2.1rem;
            font-weight: 800;
            color: var(--accent-mint);
        }}
        .stat-label {{
            font-size: 0.76rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.3rem;
            line-height: 1.3;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        .data-table th {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-mint);
            padding: 0.65rem 0.9rem;
            text-align: left;
            border-bottom: 2px solid var(--border-card);
            font-weight: 700;
        }}
        .data-table td {{
            padding: 0.65rem 0.9rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            color: var(--text-main);
        }}
        .data-table tr.highlight-row {{
            background: rgba(16, 185, 129, 0.14);
            font-weight: 700;
        }}
        .data-table tr.highlight-row td {{
            color: #a7f3d0;
        }}
        .pill {{
            display: inline-block;
            font-size: 0.72rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .pill-green {{ background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); }}
        .pill-blue {{ background: rgba(6, 182, 212, 0.2); color: #67e8f9; border: 1px solid rgba(6, 182, 212, 0.4); }}
        .pill-amber {{ background: rgba(245, 158, 11, 0.2); color: #fde047; border: 1px solid rgba(245, 158, 11, 0.4); }}
        .pill-red {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}

        /* Bottom Control Bar */
        .bottom-bar {{
            position: absolute;
            bottom: 0; left: 0;
            width: 100%; height: 52px;
            background: rgba(5, 10, 7, 0.98);
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            z-index: 100;
        }}
        .progress-track {{
            position: absolute;
            top: 0; left: 0;
            height: 3px;
            background: rgba(255, 255, 255, 0.1);
            width: 100%;
        }}
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent-emerald), var(--accent-mint));
            width: 0%;
            transition: width 0.3s ease;
        }}
        .nav-controls {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .btn-ctrl {{
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
        }}
        .btn-ctrl:hover {{
            background: rgba(16, 185, 129, 0.25);
            border-color: var(--accent-mint);
        }}
        .timer-display {{
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
        }}
        .timer-warning {{
            color: var(--accent-amber) !important;
            border-color: var(--accent-amber) !important;
        }}
        .timer-expired {{
            color: var(--accent-red) !important;
            border-color: var(--accent-red) !important;
            animation: pulse 1s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.35; }}
        }}
        .slide-counter {{
            font-size: 0.82rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}
        .speaker-badge {{
            font-size: 0.75rem;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-weight: 700;
        }}

        /* Speaker Notes Drawer */
        #notes-drawer {{
            position: fixed;
            bottom: 52px; left: 0;
            width: 100%;
            max-height: 240px;
            background: rgba(8, 16, 11, 0.98);
            border-top: 2px solid var(--accent-mint);
            padding: 1.2rem 3rem;
            overflow-y: auto;
            box-shadow: 0 -10px 30px rgba(0,0,0,0.85);
            z-index: 99;
            display: none;
        }}
        #notes-drawer.open {{ display: block; }}
        .notes-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.6rem;
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--accent-mint);
            font-weight: 800;
            letter-spacing: 1px;
        }}
        .notes-body {{
            font-size: 1.05rem;
            line-height: 1.6;
            color: #f1f5f9;
        }}
        .notes-body mark {{
            background: rgba(245, 158, 11, 0.35);
            color: #fef08a;
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
        }}
        .notes-cue {{
            font-weight: 800;
            color: #38bdf8;
            margin-right: 0.5rem;
        }}

        @media print {{
            body {{
                overflow: visible !important;
                height: auto !important;
                background: #050a07 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            #presentation {{ display: block !important; height: auto !important; }}
            .slide {{
                display: flex !important;
                position: relative !important;
                width: 100vw !important;
                height: 100vh !important;
                page-break-after: always !important;
                page-break-inside: avoid !important;
            }}
            .bottom-bar, #notes-drawer {{ display: none !important; }}
        }}
    </style>
</head>
<body>
    <div id="presentation">
        {slides_html}
    </div>

    <!-- Notes Drawer -->
    <div id="notes-drawer">
        <div class="notes-header">
            <span id="notes-slide-title">Notas del Orador</span>
            <span id="notes-time-cue" style="color: #38bdf8; font-family: 'JetBrains Mono';">Tiempo sugerido</span>
        </div>
        <div class="notes-body" id="notes-content">
            Cargando guion...
        </div>
    </div>

    <!-- Bottom Navigation Bar -->
    <div class="bottom-bar">
        <div class="progress-track">
            <div class="progress-bar-fill" id="progress-fill"></div>
        </div>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div class="slide-counter" id="slide-num">1 / 6</div>
            <div class="speaker-badge" id="speaker-display">{speaker_tag}</div>
        </div>

        <div class="nav-controls">
            <div class="timer-display" id="timer-box">
                <span id="timer-text">00:00</span>
                <span style="font-size: 0.7rem; color: var(--text-muted);" id="timer-max">/ 03:00</span>
            </div>
            <button class="btn-ctrl" onclick="toggleTimer()" id="btn-timer" title="Iniciar/Pausar cronómetro (T)">▶ Play</button>
            <button class="btn-ctrl" onclick="resetTimer()" title="Reiniciar tiempo (R)">↺ Reset</button>
            <button class="btn-ctrl" onclick="toggleNotes()" title="Ver guion / notas del orador (N)">📝 Guion</button>
            <button class="btn-ctrl" onclick="prevSlide()" title="Diapositiva anterior (Flecha Izq)">◀</button>
            <button class="btn-ctrl" onclick="nextSlide()" title="Siguiente diapositiva (Flecha Der / Espacio)">▶</button>
            <button class="btn-ctrl" onclick="toggleFullscreen()" title="Pantalla completa (F)">⛶</button>
        </div>
    </div>

    <script>
        const totalDuration = {total_seconds};
        const notesData = {notes_dict};
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

            slides.forEach((s, i) => {{
                s.classList.toggle('active', i === currentSlide);
            }});

            document.getElementById('slide-num').innerText = `${{currentSlide + 1}} / ${{totalSlides}}`;
            const pct = ((currentSlide + 1) / totalSlides) * 100;
            document.getElementById('progress-fill').style.width = pct + '%';

            // Update speaker badge if slide has custom speaker attribute
            const activeSlide = slides[currentSlide];
            const customSpeaker = activeSlide.getAttribute('data-speaker');
            if (customSpeaker) {{
                document.getElementById('speaker-display').innerText = customSpeaker;
            }}

            // Update notes
            updateNotes();
        }}

        function nextSlide() {{ showSlide(currentSlide + 1); }}
        function prevSlide() {{ showSlide(currentSlide - 1); }}

        function updateNotes() {{
            const noteObj = notesData[currentSlide] || {{ text: 'Sin notas.', cue: '0:00', speaker: '' }};
            document.getElementById('notes-slide-title').innerText = `Slide ${{currentSlide + 1}}: Notas de Apoyo (${{noteObj.speaker || 'Equipo'}})`;
            document.getElementById('notes-time-cue').innerText = `⏱️ Ventana sugerida: ${{noteObj.cue}}`;
            document.getElementById('notes-content').innerHTML = noteObj.text;
        }}

        function toggleNotes() {{
            const drawer = document.getElementById('notes-drawer');
            drawer.classList.toggle('open');
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
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen();
            }} else if (document.exitFullscreen) {{
                document.exitFullscreen();
            }}
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {{
                nextSlide();
            }} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
                prevSlide();
            }} else if (e.key === 'n' || e.key === 'N') {{
                toggleNotes();
            }} else if (e.key === 't' || e.key === 'T') {{
                toggleTimer();
            }} else if (e.key === 'r' || e.key === 'R') {{
                resetTimer();
            }} else if (e.key === 'f' || e.key === 'F') {{
                toggleFullscreen();
            }}
        }});

        // Init
        document.getElementById('timer-max').innerText = `/ ${{formatTime(totalDuration)}}`;
        showSlide(0);
        updateTimerUI();
    </script>
</body>
</html>
"""

print("Helper base HTML function ready.")
