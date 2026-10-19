#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador Maestro de Presentaciones InnovaTecNM 2026 - FLUXA Smart Mobility
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
"""

import os
import base64
import json

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
    notes_json = json.dumps(notes_dict)
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
            --bg-card: rgba(14, 25, 18, 0.88);
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
            padding: 1.8rem 3.2rem 4.5rem 3.2rem;
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
            padding-bottom: 0.7rem;
            margin-bottom: 0.9rem;
        }}
        .logos-group {{
            display: flex;
            align-items: center;
            gap: 1.4rem;
        }}
        .inst-logo {{
            height: 38px;
            object-fit: contain;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
        }}
        .event-meta {{
            text-align: right;
            font-size: 0.78rem;
            color: var(--text-muted);
            line-height: 1.4;
        }}
        .event-meta strong {{
            color: var(--accent-mint);
            font-weight: 700;
        }}
        .slide-title-area {{
            margin-bottom: 0.8rem;
        }}
        .slide-badge {{
            display: inline-block;
            font-size: 0.7rem;
            text-transform: uppercase;
            font-weight: 800;
            letter-spacing: 1px;
            padding: 0.2rem 0.65rem;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-mint);
            border: 1px solid rgba(16, 185, 129, 0.35);
            margin-bottom: 0.35rem;
        }}
        .slide-title {{
            font-size: 1.95rem;
            font-weight: 800;
            line-height: 1.2;
            background: linear-gradient(135deg, #ffffff 40%, var(--accent-mint) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .slide-subtitle {{
            font-size: 0.92rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }}
        .slide-body {{
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 1rem;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.2rem;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.1rem;
        }}
        .grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.9rem;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 1.1rem 1.3rem;
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
            font-size: 1rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }}
        .card-title span.icon {{ font-size: 1.15rem; }}
        .card p {{
            font-size: 0.85rem;
            line-height: 1.45;
            color: #cbd5e1;
        }}
        .stat-box {{
            display: flex;
            flex-direction: column;
            padding: 0.8rem 1rem;
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.45);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .stat-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.85rem;
            font-weight: 800;
            color: var(--accent-mint);
        }}
        .stat-label {{
            font-size: 0.74rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.25rem;
            line-height: 1.3;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
        }}
        .data-table th {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-mint);
            padding: 0.55rem 0.8rem;
            text-align: left;
            border-bottom: 2px solid var(--border-card);
            font-weight: 700;
        }}
        .data-table td {{
            padding: 0.55rem 0.8rem;
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
            font-size: 0.7rem;
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
            width: 100%; height: 50px;
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
            font-size: 1rem;
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
            margin-right: 0.4rem;
        }}

        @page {{
            size: 16in 9in;
            margin: 0;
        }}
        @media print {{
            body {{
                overflow: visible !important;
                height: auto !important;
                width: 16in !important;
                background: #050a07 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            #presentation {{
                display: block !important;
                height: auto !important;
                width: 16in !important;
            }}
            .slide {{
                display: flex !important;
                position: relative !important;
                width: 16in !important;
                height: 9in !important;
                max-width: 16in !important;
                max-height: 9in !important;
                box-sizing: border-box !important;
                page-break-after: always !important;
                page-break-inside: avoid !important;
                padding: 2.2rem 3.5rem !important;
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

            slides.forEach((s, i) => {{
                s.classList.toggle('active', i === currentSlide);
            }});

            document.getElementById('slide-num').innerText = `${{currentSlide + 1}} / ${{totalSlides}}`;
            const pct = ((currentSlide + 1) / totalSlides) * 100;
            document.getElementById('progress-fill').style.width = pct + '%';

            const activeSlide = slides[currentSlide];
            const customSpeaker = activeSlide.getAttribute('data-speaker');
            if (customSpeaker) {{
                document.getElementById('speaker-display').innerText = customSpeaker;
            }}

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

        document.getElementById('timer-max').innerText = `/ ${{formatTime(totalDuration)}}`;
        showSlide(0);
        updateTimerUI();
    </script>
</body>
</html>
"""

print("Writing presentations...")

# ==============================================================================
# 1. PITCH (3 MINUTOS)
# ==============================================================================
hdr_pitch = make_header("INDUSTRIA ELÉCTRICA Y ELECTRÓNICA")

slides_pitch = [
    # Slide 1: Portada
    f"""
    <div class="slide active" data-speaker="Expositor 1 (Pitch)">
        {hdr_pitch}
        <div class="slide-title-area">
            <span class="slide-badge">PITCH DE ALTO IMPACTO • 3 MINUTOS</span>
            <h1 class="slide-title">FLUXA: Inteligencia Artificial en el Borde para Movilidad Urbana</h1>
            <p class="slide-subtitle">Modernización vial mediante arquitectura Retrofit Overlay y visión computacional</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card highlight" style="display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 1.25rem; font-weight: 800; color: #6ee7b7; margin-bottom: 0.8rem; line-height: 1.4;">
                        "¿Cuántas horas de nuestras vidas hemos perdido frente a un semáforo en rojo viendo un carril completamente vacío?"
                    </div>
                    <p style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6;">
                        El 90% de los semáforos en México operan como en 1980: con temporizadores ciegos que colapsan nuestras ciudades. Hoy les presentamos <strong>FLUXA</strong>, la solución mexicana que dota de visión, inteligencia y autonomía a cualquier cruce vial en menos de 4 horas y con un 95% de ahorro.
                    </p>
                </div>
                <div class="card" style="display: flex; flex-direction: column; justify-content: center; gap: 0.9rem;">
                    <div class="stat-box">
                        <div class="stat-value">95%</div>
                        <div class="stat-label">Ahorro en CapEx frente a marcas importadas tradicionales</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">&lt; 12 ms</div>
                        <div class="stat-label">Latencia en NPU dedicada (Zero dependencias de la nube)</div>
                    </div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); text-align: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.5rem;">
                        Tecnológico de Estudios Superiores de Coacalco • TecNM
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 2: El Problema
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr_pitch}
        <div class="slide-title-area">
            <span class="slide-badge pill-red">EL PROBLEMA NACIONAL</span>
            <h1 class="slide-title">La Crisis Urbana: Tiempos Muertos y Brecha Presupuestal</h1>
            <p class="slide-subtitle">La congestión asfixia la productividad de millones de familias mexicanas</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card danger">
                    <div class="card-title"><span class="icon">⏱️</span> Pérdida de Vida</div>
                    <div class="stat-value" style="color: #fca5a5; font-size: 1.8rem; margin: 0.4rem 0;">3,500 M</div>
                    <p>De horas-hombre desperdiciadas anualmente en tráfico en México. El Valle de México es la segunda zona más congestionada de América Latina.</p>
                </div>
                <div class="card danger">
                    <div class="card-title"><span class="icon">💸</span> Impacto Económico</div>
                    <div class="stat-value" style="color: #fca5a5; font-size: 1.8rem; margin: 0.4rem 0;">$94,000 MDP</div>
                    <p>Costo económico anual de la congestión vial (IMCO). Millones de litros de gasolina quemados en ralentí frente a luces rojas desiertas.</p>
                </div>
                <div class="card danger">
                    <div class="card-title"><span class="icon">🚧</span> Barrera Presupuestal</div>
                    <div class="stat-value" style="color: #fca5a5; font-size: 1.8rem; margin: 0.4rem 0;">$500,000+</div>
                    <p>Costo por cruce con marcas extranjeras (Siemens, Econolite). Exigen romper asfalto para espiras inductivas y cobros en dólares a la nube.</p>
                </div>
            </div>
            <div class="card" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); text-align: center;">
                <div style="font-size: 0.92rem; color: #fecaca;">
                    <strong>La Paradoja Municipal:</strong> Las alcaldías reconocen la crisis pero no modernizan sus semáforos porque no pueden costearlos.
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 3: Solución
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr_pitch}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">NUESTRA SOLUCIÓN</span>
            <h1 class="slide-title">FLUXA: Capa Inteligente Retrofit sin Obra Civil</h1>
            <p class="slide-subtitle">Transformamos la infraestructura existente en intersecciones autónomas de alta precisión</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🔌</span> Retrofit Plug & Play</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">&lt; 4 Horas</div>
                    <p>Se instala dentro del gabinete semafórico actual aprovechando mástiles, cabezales y cableado. Cero afectación a la obra civil.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🧠</span> Inferencia Edge Local</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">6 TOPS NPU</div>
                    <p>Orange Pi 5 con SoC Rockchip RK3588. Ejecuta YOLOv8 cuantizado a INT8 en 12 ms, sin dependencia de internet ni rentas de nube.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🚦</span> Algoritmo TSP y C5</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">Tiempo Real</div>
                    <p>Aforo vehicular adaptativo por carriles, prioridad a transporte masivo y despeje inmediato de corredores para ambulancias del C5.</p>
                </div>
            </div>
            <div class="card" style="display: flex; justify-content: space-around; align-items: center; padding: 0.8rem 1.4rem;">
                <span class="pill pill-green">Cámara HD Gran Angular</span>
                <span style="color: var(--accent-mint); font-weight: 700;">➔</span>
                <span class="pill pill-green">NPU RK3588 (YOLOv8 INT8)</span>
                <span style="color: var(--accent-mint); font-weight: 700;">➔</span>
                <span class="pill pill-green">FSM + Watchdog Arduino R4</span>
                <span style="color: var(--accent-mint); font-weight: 700;">➔</span>
                <span class="pill pill-green">Telemetría Web SCADA C5</span>
            </div>
        </div>
    </div>
    """,

    # Slide 4: Modelo de Negocio
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr_pitch}
        <div class="slide-title-area">
            <span class="slide-badge pill-blue">MODELO DE NEGOCIO B2G</span>
            <h1 class="slide-title">Viabilidad Financiera: 95% de Ahorro y Alta Rentabilidad</h1>
            <p class="slide-subtitle">Modelo híbrido de Hardware Edge Appliance + Suscripción SCADA C5 + Póliza SLA</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title"><span class="icon">📊</span> Comparativa de CapEx por Intersección</div>
                    <div style="margin: 0.8rem 0; display: flex; flex-direction: column; gap: 0.6rem;">
                        <div style="font-size: 0.78rem; display: flex; justify-content: space-between;">
                            <span>Siemens (Importado):</span> <strong style="color: #f87171;">$650,000 MXN</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.1); height: 10px; border-radius: 5px; overflow: hidden;">
                            <div style="width: 100%; height: 100%; background: #ef4444;"></div>
                        </div>

                        <div style="font-size: 0.78rem; display: flex; justify-content: space-between;">
                            <span>Econolite (Tradicional):</span> <strong style="color: #f87171;">$520,000 MXN</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.1); height: 10px; border-radius: 5px; overflow: hidden;">
                            <div style="width: 80%; height: 100%; background: #f87171;"></div>
                        </div>

                        <div style="font-size: 0.78rem; display: flex; justify-content: space-between;">
                            <span>FLUXA Smart Mobility:</span> <strong style="color: #34d399;">$28,500 MXN (-95%)</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.1); height: 12px; border-radius: 5px; overflow: hidden;">
                            <div style="width: 6%; height: 100%; background: #10b981;"></div>
                        </div>
                    </div>
                    <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.6rem;">
                        <strong>Costo de Fabricación (BOM):</strong> $10,750 MXN | <strong>Margen Bruto:</strong> 62.3%
                    </p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">💰</span> Proyección Año 1 (50 Cruces)</div>
                    <div class="grid-2" style="gap: 0.8rem; margin: 0.6rem 0;">
                        <div class="stat-box">
                            <div class="stat-value" style="font-size: 1.6rem;">$2.14 MDP</div>
                            <div class="stat-label">Ingresos Proyectados Año 1</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value" style="font-size: 1.6rem; color: #6ee7b7;">$890,000</div>
                            <div class="stat-label">Utilidad Neta (41.5%)</div>
                        </div>
                    </div>
                    <div style="font-size: 0.82rem; color: #cbd5e1; line-height: 1.5;">
                        • <strong>Hardware:</strong> $28,500 MXN / cruce<br>
                        • <strong>Licencia SCADA C5:</strong> $8,400 MXN / cruce / año<br>
                        • <strong>Póliza SLA 24/7:</strong> $6,000 MXN / cruce / año
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 5: Impacto Social
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr_pitch}
        <div class="slide-title-area">
            <span class="slide-badge pill-amber">RETORNO SOCIAL Y AMBIENTAL</span>
            <h1 class="slide-title">Impacto Comprobado: Payback Social en Menos de 90 Días</h1>
            <p class="slide-subtitle">Metodología auditada con factores oficiales de SEDATU, DOE, CONUEE e INECC</p>
        </div>
        <div class="slide-body">
            <div class="grid-4">
                <div class="card">
                    <div class="stat-box">
                        <div class="stat-value">15,968 L</div>
                        <div class="stat-label">Gasolina ahorrada al año por cruce</div>
                    </div>
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">Por reducción de 15 segundos de ralentí en 15,000 vehículos/día.</p>
                </div>
                <div class="card">
                    <div class="stat-box">
                        <div class="stat-value">$391,234</div>
                        <div class="stat-label">Ahorro ciudadano anual en MXN / cruce</div>
                    </div>
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">En un corredor de 10 cruces: <strong>$3.91 MDP</strong> de beneficio económico anual para la comunidad.</p>
                </div>
                <div class="card">
                    <div class="stat-box">
                        <div class="stat-value">36.8 Ton</div>
                        <div class="stat-label">CO₂ mitigado al año por cruce</div>
                    </div>
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">Equivalente al secuestro de carbono de más de 1,600 árboles urbanos.</p>
                </div>
                <div class="card highlight">
                    <div class="stat-box">
                        <div class="stat-value" style="color: #6ee7b7;">&lt; 90 Días</div>
                        <div class="stat-label">Retorno de Inversión Social</div>
                    </div>
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">El beneficio social devuelto a la población supera la inversión inicial en el primer trimestre.</p>
                </div>
            </div>
            <div class="card" style="text-align: center; font-size: 0.88rem; color: #a7f3d0;">
                🌱 <strong>Sustentabilidad y Soberanía:</strong> Reducción directa de emisiones tóxicas locales alineada al Plan México 2024-2030.
            </div>
        </div>
    </div>
    """,

    # Slide 6: Cierre y Tracción
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {hdr_pitch}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">TRACCIÓN Y TRASCENDENCIA</span>
            <h1 class="slide-title">Madurez Tecnológica y Soberanía Nacional</h1>
            <p class="slide-subtitle">Desarrollado con rigor técnico en el Tecnológico de Estudios Superiores de Coacalco</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card">
                    <div class="card-title"><span class="icon">🚀</span> Madurez TRL 6 / 7</div>
                    <p>Probado y validado en banco experimental de potencia con relevadores y video en vivo en cruces de Coacalco, Ecatepec y Tultitlán. 100% aprobado en suite PyTest.</p>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">⚖️</span> Propiedad Intelectual</div>
                    <p>Trámites ante <strong>INDAUTOR</strong> (Registro de Software integral) y ante el <strong>IMPI</strong> (Modelo de Utilidad para el nodo físico y Registro de Marca "FLUXA" en Clase 9).</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">👥</span> El Equipo</div>
                    <p style="font-size: 0.82rem; line-height: 1.4;">
                        <strong>Líder & Dev:</strong> Moisés Emilio Martínez Arias<br>
                        <strong>Equipo:</strong> Diego Huichapeño, Ethan Flores, Citlalli Rojas, Jerazan Becerra<br>
                        <strong>Asesor:</strong> Mtro. Roberto Carlos Muñoz Celaya
                    </p>
                </div>
            </div>
            <div class="card highlight" style="text-align: center; padding: 1.2rem; background: rgba(16, 185, 129, 0.2); border-color: var(--accent-mint);">
                <div style="font-size: 1.25rem; font-weight: 800; color: #ffffff; margin-bottom: 0.3rem;">
                    FLUXA: Ciudades Inteligentes, Autónomas y Sostenibles
                </div>
                <p style="font-size: 0.92rem; color: #cbd5e1;">
                    En el TecNM demostramos que con innovación propia resolvemos los desafíos más apremiantes del país. ¡Muchas gracias!
                </p>
            </div>
        </div>
    </div>
    """
]

notes_pitch = {
    0: {
        "speaker": "Expositor 1",
        "cue": "0:00 - 0:25 (25s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:00]</span> Buenos días, honorable jurado calificador y autoridades del TecNM. Les hago una pregunta muy directa: <strong>¿cuántas horas de sus vidas han perdido frente a un semáforo en rojo viendo un carril completamente vacío?</strong><br>
        <span class="notes-cue">[0:12]</span> En México, esto nos cuesta más de 3.5 mil millones de horas al año. Para resolver esto creamos <strong>FLUXA</strong>: una plataforma industrial de semaforización inteligente basada en Inteligencia Artificial en el Borde, desarrollada con orgullo en el TESCo para transformar semáforos ciegos en cruces autónomos sin obra civil.
        </p>
        """
    },
    1: {
        "speaker": "Expositor 1",
        "cue": "0:25 - 0:55 (30s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:25]</span> El 90% de los semáforos de nuestras ciudades siguen operando con temporizadores de los años 80. Esto genera pérdidas económicas por más de <strong>94 mil millones de pesos anuales</strong>, además de miles de toneladas de CO₂ por vehículos en ralentí.<br>
        <span class="notes-cue">[0:40]</span> ¿Por qué los municipios no los cambian? Porque marcas extranjeras como Siemens o Econolite cobran <strong>entre 350 mil y 750 mil pesos por una sola intersección</strong>, exigen romper el asfalto para poner sensores que se rompen con los baches y cobran licencias en dólares con servidores en la nube. Es un costo prohibitivo para nuestras alcaldías.
        </p>
        """
    },
    2: {
        "speaker": "Expositor 1",
        "cue": "0:55 - 1:30 (35s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:55]</span> <strong>Aquí es donde entra la disrupción de FLUXA:</strong> operamos bajo una arquitectura <strong>Retrofit Overlay</strong>. Nos conectamos directamente al gabinete, cabezales y cableado existentes en <strong>menos de 4 horas</strong>, sin romper pavimento.<br>
        <span class="notes-cue">[1:12]</span> En lugar de costosos servidores en la nube, colocamos una computadora de borde con la NPU Rockchip RK3588 de 6 TOPS. Ejecutamos redes neuronales YOLOv8 cuantizadas a INT8 con una latencia de <strong>menos de 12 milisegundos</strong>. El sistema ve los autos en tiempo real, calcula la demanda ponderada y ajusta las luces de forma 100% autónoma.
        </p>
        """
    },
    3: {
        "speaker": "Expositor 1",
        "cue": "1:30 - 2:05 (35s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[1:30]</span> Nuestro modelo de negocio B2G es accesible y altamente rentable. Vendemos el kit industrial completo a <strong>$28,500 MXN</strong> por cruce de 4 vías: un <strong>ahorro del 95%</strong> frente a la competencia extranjera.<br>
        <span class="notes-cue">[1:45]</span> Con un costo directo de fabricación de $10,750 MXN, logramos un margen bruto del 62.3%. Sumamos ingresos recurrentes por la licencia de monitoreo SCADA C5 y pólizas de mantenimiento.<br>
        <span class="notes-cue">[1:55]</span> En nuestro primer año, con solo 50 cruces en el Valle de México, proyectamos <strong>$2.14 millones de pesos de facturación</strong> y una utilidad neta de $890 mil pesos (41.5% de margen neto).
        </p>
        """
    },
    4: {
        "speaker": "Expositor 1",
        "cue": "2:05 - 2:35 (30s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[2:05]</span> Pero lo más valioso no es lo que ahorra el municipio, sino lo que devuelve a la sociedad. Validado bajo metodologías oficiales del Departamento de Energía, CONUEE e INECC, cada cruce FLUXA ahorra <strong>15,968 litros de gasolina al año</strong>.<br>
        <span class="notes-cue">[2:20]</span> Esto representa <strong>$391 mil pesos de ahorro directo en el bolsillo de los ciudadanos</strong> y evita 36.8 toneladas de CO₂ al año por cruce. En un corredor de 10 cruces son casi 4 millones de pesos de beneficio social. El retorno de inversión social se logra en <strong>menos de 90 días</strong>.
        </p>
        """
    },
    5: {
        "speaker": "Expositor 1",
        "cue": "2:35 - 3:00 (25s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[2:35]</span> FLUXA cuenta con un nivel de madurez <strong>TRL 6/7</strong>, validado con tráfico real en Coacalco, Ecatepec y Tultitlán, con protección de propiedad intelectual en trámite ante INDAUTOR e IMPI.<br>
        <span class="notes-cue">[2:48]</span> Con FLUXA, demostramos que en el Tecnológico Nacional de México creamos tecnología de clase mundial con impacto social tangible: más tiempo con nuestras familias, menos emisiones y ciudades vivas y eficientes. <strong>Muchas gracias.</strong>
        </p>
        """
    }
}

pitch_html = get_base_html(
    title="PITCH (3 Min)",
    total_seconds=180,
    slides_html="".join(slides_pitch),
    notes_dict=notes_pitch,
    speaker_tag="Expositor 1 (Pitch)"
)

with open(os.path.join(OUTPUT_DIR, 'pitch_3min.html'), 'w', encoding='utf-8') as f:
    f.write(pitch_html)

print(" -> pitch_3min.html generado.")

# ==============================================================================
# 2. DEFENSA TÉCNICA Y PLAN DE NEGOCIOS (7 MINUTOS)
# ==============================================================================
hdr_def = make_header("INDUSTRIA ELÉCTRICA Y ELECTRÓNICA")

slides_defense = [
    # Slide 1: Portada
    f"""
    <div class="slide active" data-speaker="Expositor 1 (Técnico)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge">DEFENSA OFICIAL • 7 MINUTOS (SALA DE EVALUACIÓN)</span>
            <h1 class="slide-title">FLUXA: Memoria Técnica y Plan de Negocios</h1>
            <p class="slide-subtitle">Sistema de Semáforos Inteligentes Edge AI, Telemetría SCADA y Red Vial Autónoma</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card highlight">
                    <div class="card-title"><span class="icon">📋</span> Ficha Técnica de Registro</div>
                    <div style="font-size: 0.85rem; line-height: 1.6; color: #cbd5e1;">
                        • <strong>Folio Oficial:</strong> 70785-17<br>
                        • <strong>Categoría:</strong> Industria Eléctrica y Electrónica<br>
                        • <strong>Área de Aplicación:</strong> Digitalización y Automatización<br>
                        • <strong>Áreas Específicas:</strong> Infraestructura y Ciudades Inteligentes, Industria 4.0<br>
                        • <strong>Naturaleza Técnica:</strong> Ciencias Computacionales y Electrónica<br>
                        • <strong>Institución:</strong> Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
                    </div>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">👥</span> Equipo Multidisciplinario y Asesoría</div>
                    <div style="font-size: 0.82rem; line-height: 1.5; color: #cbd5e1;">
                        • <strong>Moisés Emilio Martínez Arias</strong> (Líder & Dev Principal - ISC 3°)<br>
                        • <strong>Diego Alejandro Huichapeño González</strong> (Ing. en Sistemas Comp. 5°)<br>
                        • <strong>Ethan Rafael Flores Medina</strong> (Ing. en Sistemas Comp. 5°)<br>
                        • <strong>Citlalli Rojas Rico</strong> (Ing. en TICs 8°)<br>
                        • <strong>Jerazan Becerra Mendoza</strong> (Ing. en Sistemas Comp. 3°)<br>
                        • <strong>Asesor Técnico:</strong> Mtro. Roberto Carlos Muñoz Celaya
                    </div>
                </div>
            </div>
            <div class="card" style="display: flex; justify-content: space-around; align-items: center; padding: 0.6rem 1rem;">
                <span style="font-size: 0.8rem; color: #6ee7b7;"><strong>Bloque 1 (3:30 min):</strong> Memoria Técnica y Arquitectura Hardware</span>
                <span style="color: var(--text-muted);">|</span>
                <span style="font-size: 0.8rem; color: #38bdf8;"><strong>Bloque 2 (3:30 min):</strong> Plan de Negocios, Finanzas y Propiedad Intelectual</span>
            </div>
        </div>
    </div>
    """,

    # Slide 2: Problema y Reto de Ingeniería
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-red">INGENIERÍA Y DIAGNÓSTICO</span>
            <h1 class="slide-title">Obsolescencia en la Red Semafórica Actual</h1>
            <p class="slide-subtitle">Limitaciones críticas de los controladores tradicionales frente a la dinámica urbana</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card danger">
                    <div class="card-title"><span class="icon">⏱️</span> Temporizadores Fijos</div>
                    <p>Los ciclos rígidos no responden a variaciones en tiempo real. Mantienen verdes en carriles vacíos mientras la vía perpendicular se congestiona, disparando tiempos de espera y emisiones en ralentí.</p>
                </div>
                <div class="card danger">
                    <div class="card-title"><span class="icon">🚧</span> Sensores Invasivos Frágiles</div>
                    <p>Las espiras inductivas bajo el asfalto se fracturan con baches y reencarpetamiento municipal. Su reposición exige cerrar calles y genera costos de mantenimiento recurrentes inasumibles.</p>
                </div>
                <div class="card danger">
                    <div class="card-title"><span class="icon">☁️</span> Dependencia de Nube Crítica</div>
                    <p>Plataformas que dependen de servidores externos sufren por latencias elevadas (&gt;500ms), desconexiones de red y facturación mensual en dólares por ancho de banda de video.</p>
                </div>
            </div>
            <div class="card highlight">
                <div style="font-size: 0.9rem; color: #a7f3d0;">
                    🎯 <strong>Requerimiento de Ingeniería de FLUXA:</strong> Desarrollar un sistema embebido industrial autónomo en el borde (Edge), no invasivo, con inferencia &lt;12ms y conmutación segura de potencia para gabinetes normados.
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 3: Arquitectura Hardware & Retrofit
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">HARDWARE EMBEBIDO & RETROFIT</span>
            <h1 class="slide-title">Arquitectura Edge Appliance & Retrofit Overlay</h1>
            <p class="slide-subtitle">Modernización sobre gabinetes existentes sin requerir obra civil invasiva</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title"><span class="icon">📦</span> Componentes del Edge Box (Gabinete NEMA IP66)</div>
                    <div style="font-size: 0.82rem; line-height: 1.5; color: #cbd5e1;">
                        • <strong>SBC de Cómputo Principal:</strong> Orange Pi 5 (SoC Rockchip RK3588, 8 Cores CPU + Tri-Core NPU 6 TOPS).<br>
                        • <strong>Sistema de Visión:</strong> Cámara vial gran angular HD con carcasa antivandalismo.<br>
                        • <strong>Control de Potencia:</strong> Relevadores de Estado Sólido (SSR) con aislamiento optoacoplado para 120VAC / 24VDC.<br>
                        • <strong>Microcontrolador Esclavo & Watchdog:</strong> Arduino UNO R4 Minima.<br>
                        • <strong>Protección Eléctrica:</strong> Fuente industrial MeanWell y supresor de picos transitorios.
                    </div>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🔌</span> Capa de Integración Retrofit Overlay</div>
                    <div class="stat-box" style="margin-bottom: 0.6rem;">
                        <div class="stat-value">&lt; 4 Horas</div>
                        <div class="stat-label">Tiempo total de instalación por intersección</div>
                    </div>
                    <p style="font-size: 0.82rem; color: #cbd5e1;">
                        Se acopla a los gabinetes normativos (NEMA TS2, Tipo 170/2070 o relés electromecánicos) aprovechando los cabezales y cableado existentes. No requiere perforar calles ni tender cableado subterráneo nuevo.
                    </p>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 4: Pipeline Inferencia NPU
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">INTELIGENCIA ARTIFICIAL EN EL BORDE</span>
            <h1 class="slide-title">Pipeline de Inferencia NPU INT8 & Tracking</h1>
            <p class="slide-subtitle">Procesamiento neuronal ultrarrápido a 30 FPS sin saturación térmica</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card highlight">
                    <div class="card-title"><span class="icon">⚡</span> Inferencia en NPU RKNN</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">&lt; 12 ms</div>
                    <p>YOLOv8 cuantizado a formato binario asimétrico INT8 mediante RKNN-Toolkit2. 30 FPS continuos en la NPU liberando el 70% de la CPU para tareas de red y SCADA.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🎯</span> BYTETracker & Filtro Espacial</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">IDs Únicos</div>
                    <p>Filtro de Kalman para mantener el rastreo continuo aun con oclusiones temporales. Mapeo de centroides contra polígonos de aforo para conteo direccional preciso.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">📐</span> Demanda Ponderada (TSP)</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">Adaptativo</div>
                    <p>Pondera el aforo asignando factores multiplicadores a transporte público (1.5x) y vehículos pesados, adaptando el verde dinámicamente entre 5 y 45 segundos.</p>
                </div>
            </div>
            <div class="card" style="padding: 0.8rem 1.2rem; font-size: 0.85rem; color: #a7f3d0; text-align: center;">
                🔬 <strong>Inferencia determinista:</strong> Al operar al 100% en el borde, garantizamos tiempos de respuesta en tiempo real independientemente del estado de la red celular o fibra óptica.
            </div>
        </div>
    </div>
    """,

    # Slide 5: Tri-Core & Corredor
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-blue">MULTI-CRUCE & OLA VERDE</span>
            <h1 class="slide-title">Orquestación Tri-Core y Sincronización Vial</h1>
            <p class="slide-subtitle">1 sola Orange Pi 5 gestiona 3 intersecciones independientes con Ola Verde Dinámica</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title"><span class="icon">🖥️</span> Despliegue Multi-Instancia Tri-Core</div>
                    <p style="font-size: 0.82rem; margin-bottom: 0.6rem;">
                        Aprovechando la arquitectura simétrica de 3 núcleos de la NPU del RK3588, FLUXA ejecuta 3 nodos semafóricos independientes en un solo procesador físico:
                    </p>
                    <div style="font-size: 0.8rem; line-height: 1.5; color: #cbd5e1;">
                        • <strong>Cruce 1 (Norte):</strong> Puerto 5000 • Core NPU 0 (Inferencia INT8)<br>
                        • <strong>Cruce 2 (Centro):</strong> Puerto 5001 • Core NPU 1 (Inferencia INT8)<br>
                        • <strong>Cruce 3 (Sur):</strong> Puerto 5002 • Core NPU 2 (Inferencia INT8)
                    </div>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🌊</span> Sincronización en Malla (corridor_sync.py)</div>
                    <p style="font-size: 0.82rem; margin-bottom: 0.6rem;">
                        Algoritmo descentralizado de detección de pelotones vehiculares (*Platoon Arrival Time*):
                    </p>
                    <div style="font-size: 0.8rem; line-height: 1.5; color: #cbd5e1;">
                        • Detecta pelotones salientes en el Cruce A y calcula su arribo al Cruce B a 45 km/h.<br>
                        • Anticipa la fase verde en el semáforo receptor para permitir flujo ininterrumpido.<br>
                        • Elimina el efecto de "freno y arranque" continuo, reduciendo drásticamente las emisiones.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 6: Fail-Safe & Normas
    f"""
    <div class="slide" data-speaker="Expositor 1 (Técnico)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-amber">SEGURIDAD VIAL & NORMATIVIDAD</span>
            <h1 class="slide-title">Matriz Fail-Safe Industrial y Cumplimiento NOM</h1>
            <p class="slide-subtitle">Arquitectura tolerante a fallos de 3 niveles y estricto apego normativo</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card">
                    <div class="card-title"><span class="icon">🛡️</span> Fail-Safe Nivel 1</div>
                    <span class="pill pill-green" style="margin-bottom: 0.4rem;">Pérdida de Video</span>
                    <p>Si la cámara se desconecta o falla ópticamente, el software conmuta de inmediato a un ciclo de tiempo fijo preestablecido.</p>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">🔄</span> Fail-Safe Nivel 2</div>
                    <span class="pill pill-amber" style="margin-bottom: 0.4rem;">Fallo de NPU</span>
                    <p>Conmutación en caliente (*hot-swap*) a CPU PyTorch sin detener el servicio ni reiniciar el ciclo semafórico.</p>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">⚡</span> Fail-Safe Nivel 3</div>
                    <span class="pill pill-red" style="margin-bottom: 0.4rem;">Watchdog Hardware</span>
                    <p>Si el sistema operativo o SBC se congelan por &gt;3s, el Arduino R4 activa destello ámbar preventivo por hardware.</p>
                </div>
            </div>
            <div class="grid-2">
                <div class="card" style="padding: 0.8rem 1.2rem;">
                    <div style="font-size: 0.82rem; color: #cbd5e1;">
                        📜 <strong>NOM-034-SCT2-2011:</strong> Fases mínimas de ámbar (3s) y todo-rojo canónico (1.5s). Cero conflicto de verdes simultáneos.
                    </div>
                </div>
                <div class="card" style="padding: 0.8rem 1.2rem;">
                    <div style="font-size: 0.82rem; color: #cbd5e1;">
                        ⚡ <strong>NOM-001-SEDE-2012:</strong> Aislamiento galvánico por optoacopladores y supresión de transitorios eléctricos.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 7: Mercado B2G (Transición a Expositor 2)
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-blue">VALIDACIÓN DE MERCADO Y CLIENTE</span>
            <h1 class="slide-title">Segmentación de Mercado B2G / B2B y Validación</h1>
            <p class="slide-subtitle">Validación técnica en campo con autoridades viales del Estado de México</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🏛️</span> Comprador y Decisor</div>
                    <p>Direcciones de Seguridad Ciudadana y Tránsito Municipal, Secretarías de Movilidad (SEMOV) y administradores de Centros de Comando C5/C4.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">👮</span> Usuario Operativo</div>
                    <p>Operadores de salas de monitoreo C5 e ingenieros de semaforización municipal que controlan fases y corredores de emergencia en la plataforma SCADA.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🚑</span> Beneficiario Final</div>
                    <p>Servicios de emergencia (ambulancias y bomberos con prioridad de paso), transporte público concesionado y más de 35 millones de ciudadanos.</p>
                </div>
            </div>
            <div class="card">
                <div class="card-title"><span class="icon">📝</span> Validación y Entrevistas en Campo</div>
                <p style="font-size: 0.82rem; line-height: 1.5;">
                    Realizamos sesiones técnicas con personal de mantenimiento semafórico y supervisión de tránsito en <strong>Coacalco, Ecatepec y Tultitlán</strong>. Hallazgo crítico: los municipios enfrentan techos presupuestales que les impiden adquirir tecnología importada, y buscan soluciones nacionales de bajo costo con soporte local.
                </p>
            </div>
        </div>
    </div>
    """,

    # Slide 8: Estructura de Costos BOM
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-blue">MODELO ECONÓMICO</span>
            <h1 class="slide-title">Estructura de Costo Unitario Directo (BOM)</h1>
            <p class="slide-subtitle">Desglose de fabricación y margen bruto de utilidad de grado industrial</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Componente Industrial</th>
                                <th>Costo MXN</th>
                                <th>% BOM</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Orange Pi 5 (RK3588 + eMMC/NVMe)</td>
                                <td>$3,200</td>
                                <td>29.8%</td>
                            </tr>
                            <tr>
                                <td>Ensamble, Calibración Óptica y Pruebas</td>
                                <td>$2,200</td>
                                <td>20.5%</td>
                            </tr>
                            <tr>
                                <td>Gabinete NEMA IP66 + Fuente MeanWell</td>
                                <td>$2,100</td>
                                <td>19.5%</td>
                            </tr>
                            <tr>
                                <td>Cámara Vial Gran Angular HD Intemperie</td>
                                <td>$1,800</td>
                                <td>16.7%</td>
                            </tr>
                            <tr>
                                <td>Relevadores SSR + Arduino R4 Watchdog</td>
                                <td>$1,450</td>
                                <td>13.5%</td>
                            </tr>
                            <tr class="highlight-row">
                                <td><strong>Costo Total de Fabricación (COGS)</strong></td>
                                <td><strong>$10,750</strong></td>
                                <td><strong>100%</strong></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="card highlight" style="display: flex; flex-direction: column; justify-content: center; gap: 0.8rem;">
                    <div class="stat-box">
                        <div class="stat-value">$28,500 MXN</div>
                        <div class="stat-label">Precio de Venta al Público (CapEx por Cruce 4 Vías)</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" style="color: #6ee7b7;">62.3%</div>
                        <div class="stat-label">Margen Bruto de Utilidad por Unidad Vendida</div>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); text-align: center;">
                        Ganancia bruta de $17,750 MXN por cada cruce semafórico instalado.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 9: Proyecciones Financieras Año 1
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-blue">PROYECCIONES Y ESCALABILIDAD</span>
            <h1 class="slide-title">Modelo de Ingresos y Proyección Financiera (Año 1)</h1>
            <p class="slide-subtitle">Rampa de escalabilidad comercial y diversificación de flujos de efectivo</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card">
                    <div class="card-title"><span class="icon">💼</span> 1. Venta Hardware (CapEx)</div>
                    <div class="stat-value" style="font-size: 1.6rem; margin: 0.3rem 0;">$28,500 MXN</div>
                    <p>Gabinete industrial IP66 preconfigurado con cámara y arnés de conexión rápida Plug & Play.</p>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">🖥️</span> 2. Licencia SCADA C5 (OpEx)</div>
                    <div class="stat-value" style="font-size: 1.6rem; margin: 0.3rem 0;">$8,400 / año</div>
                    <p>Suscripción anual por nodo ($700 MXN/mes) para enlace a centro de mando C5, base MariaDB y reportes ejecutivos.</p>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">🔧</span> 3. Póliza SLA 24/7 (SaaS)</div>
                    <div class="stat-value" style="font-size: 1.6rem; margin: 0.3rem 0;">$6,000 / año</div>
                    <p>Mantenimiento preventivo, calibración de polígonos de visión y reentrenamiento semestral de IA.</p>
                </div>
            </div>
            <div class="card highlight">
                <div class="grid-3" style="align-items: center;">
                    <div class="stat-box">
                        <div class="stat-value">50 Cruces</div>
                        <div class="stat-label">Meta Año 1 (Valle de México)</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">$2.145 MDP</div>
                        <div class="stat-label">Ingreso Total Proyectado</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" style="color: #6ee7b7;">$890,000</div>
                        <div class="stat-label">Utilidad Neta Estimada (41.5%)</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 10: Retorno Social y Sustentabilidad
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-amber">IMPACTO SOCIAL & SUSTENTABILIDAD</span>
            <h1 class="slide-title">Retorno de Inversión Social (Social Payback)</h1>
            <p class="slide-subtitle">Modelo econométrico validado con factores oficiales verificables</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title"><span class="icon">📐</span> Factores y Supuestos Metodológicos</div>
                    <table class="data-table">
                        <tbody>
                            <tr>
                                <td>Aforo promedio por cruce</td>
                                <td><strong>15,000 veh/día</strong> (SEDATU / SICT)</td>
                            </tr>
                            <tr>
                                <td>Reducción de demora vehicular</td>
                                <td><strong>15.0 s / vehículo</strong> (FHWA ASCT)</td>
                            </tr>
                            <tr>
                                <td>Consumo de combustible en ralentí</td>
                                <td><strong>0.70 L / hora</strong> (DOE / CONUEE)</td>
                            </tr>
                            <tr>
                                <td>Factor de emisión de gases</td>
                                <td><strong>2.31 kg CO₂ / Litro</strong> (INECC / EPA)</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🌱</span> Resultados Auditados por Cruce / Año</div>
                    <div style="font-size: 0.88rem; line-height: 1.6; color: #f1f5f9;">
                        • <strong>Combustible Ahorrado:</strong> 15,968 Litros / año<br>
                        • <strong>Beneficio Directo al Ciudadano:</strong> $391,234 MXN / año<br>
                        • <strong>Mitigación Ambiental:</strong> 36.8 Toneladas de CO₂ / año<br>
                        • <strong>En Corredor de 10 Cruces:</strong> $3.91 MDP y 368 Ton CO₂ / año
                    </div>
                    <div class="stat-box" style="margin-top: 0.6rem;">
                        <div class="stat-value" style="font-size: 1.5rem; color: #6ee7b7;">Payback Social &lt; 90 Días</div>
                        <div class="stat-label">Amortización comunitaria en el primer trimestre</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 11: Propiedad Intelectual & Ejes Transversales
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">PROPIEDAD INTELECTUAL & ÉTICA</span>
            <h1 class="slide-title">Propiedad Intelectual y Ejes Transversales</h1>
            <p class="slide-subtitle">Estrategia jurídica de protección y responsabilidad ética social</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title"><span class="icon">⚖️</span> Protección Jurídica Integral</div>
                    <div style="font-size: 0.82rem; line-height: 1.6; color: #cbd5e1;">
                        • <strong>INDAUTOR:</strong> Registro de Software integral de la máquina de estados adaptativa (FSM), algoritmos TSP y consola SCADA como "Programa de Computación".<br>
                        • <strong>IMPI - Modelo de Utilidad:</strong> Protección de la disposición física del gabinete antivandalismo, habitáculo óptico y sistema maestro-esclavo.<br>
                        • <strong>IMPI - Marca Registrada:</strong> Denominación "FLUXA" registrada en Clase 9 de la Clasificación de Niza para licitaciones públicas.
                    </div>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🌟</span> Cumplimiento de Ejes Transversales</div>
                    <div style="font-size: 0.82rem; line-height: 1.6; color: #cbd5e1;">
                        • <strong>Inclusión y Equidad:</strong> Módulo de demanda peatonal asistida para personas con movilidad reducida y adultos mayores.<br>
                        • <strong>Impacto Social:</strong> Despeje prioritario de unidades de rescate (C5) para salvar vidas en emergencias viales críticas.<br>
                        • <strong>Sustentabilidad:</strong> Descarbonización de corredores urbanos.<br>
                        • <strong>Tecnologías Emergentes:</strong> Edge AI, Digital Twins y protocolos V2X.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 12: Hoja de Ruta y Cierre
    f"""
    <div class="slide" data-speaker="Expositor 2 (Negocios)">
        {hdr_def}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">CONCLUSIONES Y DEFENSA</span>
            <h1 class="slide-title">Hoja de Ruta y Conclusiones</h1>
            <p class="slide-subtitle">Trascendencia tecnológica, escalamiento y soberanía para México</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card">
                    <div class="card-title"><span class="icon">📍</span> Fase 1: Piloto (Meses 1-4)</div>
                    <p>Despliegue demostrativo de 10 cruces en Coacalco y Ecatepec con acceso gratuito temporal a telemetría para auditoría de tráfico.</p>
                </div>
                <div class="card">
                    <div class="card-title"><span class="icon">🚀</span> Fase 2: Consolidación (Meses 5-12)</div>
                    <p>Venta de 40 unidades en corredores metropolitanos prioritarios e integración formal con plataformas C5 estatales.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🇲🇽</span> Fase 3: Escalamiento Nacional</div>
                    <p>Transferencia tecnológica mediante convenios interinstitucionales a través de la red de tecnológicos del TecNM.</p>
                </div>
            </div>
            <div class="card highlight" style="text-align: center; padding: 1.1rem; background: rgba(16, 185, 129, 0.2); border-color: var(--accent-mint);">
                <div style="font-size: 1.2rem; font-weight: 800; color: #ffffff; margin-bottom: 0.3rem;">
                    FLUXA: Orgullo Tecnológico Mexicano del TESCo • TecNM
                </div>
                <p style="font-size: 0.88rem; color: #cbd5e1;">
                    Agradecemos su atención y quedamos a su entera disposición para la sesión de preguntas y respuestas, y la demostración física de nuestro prototipo en el stand.
                </p>
            </div>
        </div>
    </div>
    """
]

notes_defense = {
    0: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "0:00 - 0:25 (25s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:00]</span> Buenos días, honorable jurado calificador y miembros del comité evaluador de la Etapa Regional del InnovaTecNM 2026. Es un honor presentarnos ante ustedes en representación del Tecnológico de Estudios Superiores de Coacalco.<br>
        <span class="notes-cue">[0:12]</span> Defendemos el proyecto <strong>FLUXA Smart Mobility</strong>, registrado bajo el folio <strong>70785-17</strong> en la categoría de Industria Eléctrica y Electrónica. Esta presentación está dividida rigurosamente en dos bloques: los primeros 3 minutos y medio dedicados a la ingeniería y memoria técnica a mi cargo, y los siguientes 3 minutos y medio a la viabilidad económica, financiera y de mercado a cargo de mi compañera/compañero.
        </p>
        """
    },
    1: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "0:25 - 1:05 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:25]</span> Comenzamos con el diagnóstico de ingeniería. Más del 90% de la red semafórica nacional opera bajo temporizadores de tiempo fijo diseñados hace cuatro décadas. Estos controladores son ciegos a la realidad del tráfico: asignan tiempos iguales a carriles congestionados y a carriles desiertos.<br>
        <span class="notes-cue">[0:45]</span> Las soluciones tradicionales intentaron usar espiras inductivas bajo el asfalto, pero en México estas se rompen con el primer bache o reencarpetamiento. Por otro lado, las soluciones modernas que envían video a la nube sufren de latencias inaceptables y exigen pagar costosas rentas de servidores.<br>
        <span class="notes-cue">[0:58]</span> La solución técnica exigía procesamiento en el borde: una arquitectura que vea, razone y actúe directamente en la intersección en milisegundos y con total autonomía.
        </p>
        """
    },
    2: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "1:05 - 1:45 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[1:05]</span> Para materializar esto desarrollamos el <strong>FLUXA Edge Appliance</strong> bajo una arquitectura <strong>Retrofit Overlay</strong>. En lugar de demoler la infraestructura existente, colocamos un gabinete NEMA IP66 que se acopla en <strong>menos de 4 horas</strong> a los mástiles, cabezales y cableados actuales.<br>
        <span class="notes-cue">[1:25]</span> El corazón del sistema es una computadora Orange Pi 5 dotada del SoC Rockchip RK3588, con 8 núcleos de CPU y una NPU de 6 TOPS. El control de las luces se realiza mediante relevadores de estado sólido con aislamiento optoacoplado y un microcontrolador esclavo Arduino UNO R4 Minima que gobierna la conmutación física de potencia con grado industrial.
        </p>
        """
    },
    3: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "1:45 - 2:25 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[1:45]</span> En la capa algorítmica, cuantizamos modelos de redes neuronales YOLOv8 a formato binario asimétrico INT8 utilizando RKNN-Toolkit2. Esto nos permite ejecutar inferencia completa en <strong>menos de 12 milisegundos</strong> a 30 cuadros por segundo continuos, consumiendo apenas una fracción de energía térmica.<br>
        <span class="notes-cue">[2:05]</span> Asociamos el algoritmo BYTETracker con Filtro de Kalman para rastrear vehículos individuales aun con oclusiones visuales. Los centroides se cruzan contra polígonos de aforo dinámicos (ROIs) para calcular la Demanda Ponderada (TSP), otorgando prioridad matemática al transporte público masivo.
        </p>
        """
    },
    4: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "2:25 - 3:00 (35s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[2:25]</span> Un diferenciador tecnológico clave de FLUXA es su capacidad <strong>Tri-Core</strong>: una sola placa Orange Pi 5 es capaz de orquestar <strong>3 intersecciones completas simultáneamente</strong>, asignando un núcleo NPU a cada cruce en puertos de red independientes.<br>
        <span class="notes-cue">[2:45]</span> Además, desarrollamos el módulo <strong>corridor_sync.py</strong>, que calcula la velocidad promedio y el tiempo de arribo de pelotones vehiculares para coordinar <strong>Olas Verdes Dinámicas</strong> entre cruces consecutivos, eliminando el desgaste de frenado continuo.
        </p>
        """
    },
    5: {
        "speaker": "Expositor 1 (Memoria Técnica)",
        "cue": "3:00 - 3:30 (30s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[3:00]</span> La seguridad vial es innegociable. FLUXA implementa una matriz de tolerancia a fallos de tres niveles: si falla la cámara, conmuta a tiempo fijo; si falla la NPU, conmuta en caliente a la CPU PyTorch; y si se congela el sistema operativo, el watchdog del microcontrolador entra en destello preventivo en 3 segundos.<br>
        <span class="notes-cue">[3:18]</span> Cumplimos rigurosamente con la <strong>NOM-034-SCT2-2011</strong> en tiempos de despeje y con la <strong>NOM-001-SEDE-2012</strong> en seguridad eléctrica. 100% de pruebas aprobadas en PyTest con madurez <strong>TRL 6/7</strong>.<br>
        <span class="notes-cue">[3:28]</span> Cedo la palabra a mi compañera/compañero para exponer la viabilidad de mercado y negocios.
        </p>
        """
    },
    6: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "3:30 - 4:10 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[3:30]</span> Muchas gracias. Pasando a la viabilidad comercial, FLUXA opera en el mercado <strong>B2G y B2B de movilidad inteligente</strong>. Nuestros compradores directos son las Direcciones de Tránsito Municipal y Secretarías de Movilidad, mientras que los usuarios operativos son los operadores de centros de comando C5.<br>
        <span class="notes-cue">[3:50]</span> Durante la preparación para esta etapa regional, realizamos entrevistas en campo con técnicos de semaforización de <strong>Coacalco, Ecatepec y Tultitlán</strong>. Confirmamos que su mayor obstáculo no es la falta de voluntad, sino la barrera presupuestal que imponen las marcas extranjeras. Para mitigar la burocracia de licitaciones, estructuramos esquemas de pilotos demostrativos de 30 días y contratos por arrendamiento.
        </p>
        """
    },
    7: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "4:10 - 4:50 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[4:10]</span> Analicemos la estructura de costos unitarios. El Costo Directo de Fabricación (BOM) de un nodo FLUXA de 4 vías es de <strong>$10,750 MXN</strong>, que incluye la Orange Pi 5, relevadores SSR, cámara HD para intemperie, gabinete NEMA MeanWell y mano de obra.<br>
        <span class="notes-cue">[4:30]</span> Fijamos un precio de venta de <strong>$28,500 MXN</strong> por intersección. Esto nos otorga un <strong>margen bruto del 62.3%</strong>, dejando una utilidad bruta de $17,750 pesos por equipo, y ofreciendo al municipio un ahorro del <strong>95%</strong> frente a los más de medio millón de pesos que cuesta una solución importada.
        </p>
        """
    },
    8: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "4:50 - 5:30 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[4:50]</span> Nuestro modelo de ingresos es híbrido para garantizar recurrencia. Además de la venta del hardware, cobramos una licencia anual de software SCADA C5 de $8,400 pesos por cruce, y una póliza de servicio SLA 24/7 de $6,000 pesos.<br>
        <span class="notes-cue">[5:10]</span> Para el Año 1 proyectamos la instalación de 50 intersecciones en corredores prioritarios del Valle de México. Esto generará <strong>$2.14 millones de pesos en ingresos totales</strong> y una <strong>utilidad neta de $890,000 MXN</strong>, lo que representa un margen neto altamente saludable del <strong>41.5%</strong>, requiriendo una inversión inicial de solo $180,000 MXN.
        </p>
        """
    },
    9: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "5:30 - 6:10 (40s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[5:30]</span> Sin embargo, el argumento de venta más poderoso para un gobierno es el <strong>Retorno de Inversión Social</strong>. Utilizando fórmulas estandarizadas del Departamento de Energía de EE.UU., CONUEE, SEDATU e INECC, un ahorro de apenas 15 segundos de ralentí en un cruce con 15,000 autos al día produce:<br>
        <span class="notes-cue">[5:50]</span> Un ahorro anual de <strong>15,968 litros de gasolina</strong>, equivalente a <strong>$391,234 pesos ahorrados directamente por la ciudadanía</strong> y 36.8 toneladas de CO₂ evitadas por cruce. En un corredor de 10 cruces, son casi 4 millones de pesos anuales de beneficio social. El retorno de inversión social se logra en <strong>menos de 90 días</strong>.
        </p>
        """
    },
    10: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "6:10 - 6:40 (30s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[6:10]</span> En materia de Propiedad Intelectual, protegemos el código fuente integral y la consola SCADA ante el <strong>INDAUTOR</strong> como Programa de Computación. Paralelamente, tramitamos ante el <strong>IMPI</strong> la figura de Modelo de Utilidad para el habitáculo físico antivandalismo y el registro de marca FLUXA en Clase 9.<br>
        <span class="notes-cue">[6:25]</span> Cumplimos con los cuatro ejes transversales del TecNM: Inclusión mediante botonera peatonal asistida, Impacto Social con prioridad a ambulancias C5, Sustentabilidad ambiental con descarbonización y Adopción de Tecnologías Emergentes de vanguardia.
        </p>
        """
    },
    11: {
        "speaker": "Expositor 2 (Plan de Negocios)",
        "cue": "6:40 - 7:00 (20s)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[6:40]</span> Nuestra hoja de ruta contempla iniciar pilotos en Coacalco, expandirnos a corredores metropolitanos y escalar nacionalmente mediante convenios del TecNM.<br>
        <span class="notes-cue">[6:52]</span> Concluimos con orgullo: FLUXA es soberanía tecnológica mexicana para transformar nuestras ciudades. Quedamos a su entera disposición para sus preguntas y para recibirlos en nuestro stand. <strong>Muchas gracias.</strong>
        </p>
        """
    }
}

defense_html = get_base_html(
    title="DEFENSA TÉCNICA Y DE NEGOCIOS (7 Min)",
    total_seconds=420,
    slides_html="".join(slides_defense),
    notes_dict=notes_defense,
    speaker_tag="Expositor 1 (Técnico)"
)

with open(os.path.join(OUTPUT_DIR, 'defensa_tecnica_negocios_7min.html'), 'w', encoding='utf-8') as f:
    f.write(defense_html)

print(" -> defensa_tecnica_negocios_7min.html generado.")

# ==============================================================================
# 3. HUB / INDEX DE PRESENTACIONES
# ==============================================================================
hub_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Centro de Presentaciones Oficiales — FLUXA Smart Mobility</title>
    <style>
        body {{
            background: #050a07;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 2rem;
            margin: 0;
        }}
        .hub-card {{
            background: rgba(14, 25, 18, 0.95);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 16px;
            max-width: 800px;
            width: 100%;
            padding: 2.5rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 1.2rem;
            margin-bottom: 1.8rem;
        }}
        .logos {{ display: flex; gap: 1rem; align-items: center; }}
        .logos img {{ height: 42px; object-fit: contain; }}
        h1 {{
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 50%, #34d399 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.4rem;
        }}
        .meta {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 1.8rem; }}
        .pres-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; margin-bottom: 1.8rem; }}
        .pres-card {{
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(34, 197, 94, 0.2);
            border-radius: 12px;
            padding: 1.4rem;
            text-decoration: none;
            color: inherit;
            transition: all 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .pres-card:hover {{
            border-color: #34d399;
            transform: translateY(-2px);
            background: rgba(16, 185, 129, 0.12);
        }}
        .badge {{
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 800;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            margin-bottom: 0.8rem;
            width: fit-content;
        }}
        .badge-pitch {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }}
        .badge-def {{ background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); }}
        .pres-title {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 0.4rem; }}
        .pres-desc {{ font-size: 0.82rem; color: #94a3b8; line-height: 1.5; }}
        .btn-launch {{
            margin-top: 1rem;
            background: #10b981;
            color: #050a07;
            padding: 0.45rem 1rem;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.82rem;
            text-align: center;
        }}
        .shortcuts {{
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 0.8rem 1rem;
            font-size: 0.78rem;
            color: #cbd5e1;
        }}
        .shortcuts strong {{ color: #34d399; }}
    </style>
</head>
<body>
    <div class="hub-card">
        <div class="header">
            <div class="logos">
                <img src="{tecnm_img}" alt="TecNM">
                <img src="{tesco_img}" alt="TESCo">
                <img src="{sic_img}" alt="SIC">
            </div>
            <div style="text-align: right; font-size: 0.78rem; color: #94a3b8;">
                <strong>InnovaTecNM 2026</strong> • Región 5<br>
                Folio: <strong>70785-17</strong>
            </div>
        </div>

        <h1>FLUXA: Centro de Presentaciones Oficiales</h1>
        <div class="meta">
            Presentaciones web interactivas listas para proyector, con temporizador de cuenta regresiva, notas del orador integradas y soporte para exportar a PDF (Ctrl + P).
        </div>

        <div class="pres-grid">
            <a href="pitch_3min.html" class="pres-card">
                <div>
                    <span class="badge badge-pitch">PITCH • 3 MINUTOS</span>
                    <div class="pres-title">Presentación de Pitch de Alto Impacto</div>
                    <div class="pres-desc">
                        6 Diapositivas diseñadas para 1 expositor. Enfocadas en el problema, la solución disruptiva Retrofit, el modelo B2G, ROI social en &lt;90 días y visión.
                    </div>
                </div>
                <div class="btn-launch">Abrir Presentación Pitch ▶</div>
            </a>

            <a href="defensa_tecnica_negocios_7min.html" class="pres-card">
                <div>
                    <span class="badge badge-def">DEFENSA OFICIAL • 7 MINUTOS</span>
                    <div class="pres-title">Memoria Técnica y Plan de Negocios</div>
                    <div class="pres-desc">
                        12 Diapositivas para 2 expositores. Cubre arquitectura NPU RK3588, Tri-Core, Ola Verde, matriz fail-safe, NOM-034/001, BOM de costos y finanzas.
                    </div>
                </div>
                <div class="btn-launch">Abrir Defensa Técnica ▶</div>
            </a>
        </div>

        <div class="shortcuts">
            ⌨️ <strong>Controles de Teclado durante la presentación:</strong><br>
            • <strong>Flecha Derecha / Espacio:</strong> Siguiente diapositiva | <strong>Flecha Izquierda:</strong> Anterior<br>
            • <strong>T:</strong> Iniciar / Pausar Cronómetro | <strong>R:</strong> Reiniciar tiempo<br>
            • <strong>N:</strong> Mostrar / Ocultar Guion y Notas del Orador | <strong>F:</strong> Pantalla Completa | <strong>Ctrl + P:</strong> Guardar como PDF
        </div>
    </div>
</body>
</html>
"""

with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(hub_html)

print(" -> index.html (Hub) generado.")
print("Todas las presentaciones han sido compiladas exitosamente.")
