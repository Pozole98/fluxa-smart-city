#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import base64
import json

BASE_DIR = '/home/fluxa/fluxa-smart-city'
LOGOS_DIR = os.path.join(BASE_DIR, 'logos')
OUTPUT_DIR = os.path.join(BASE_DIR, 'presentaciones')

def get_base64(name):
    p = os.path.join(LOGOS_DIR, name)
    if os.path.exists(p):
        with open(p, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

tesco_img = get_base64('tesco.png')
tecnm_img = get_base64('tecnm.png')
sic_img = get_base64('sic.png')

header_html = f"""
<div class="header-bar">
    <div class="logos-group">
        <img src="{tecnm_img}" alt="TecNM" class="inst-logo">
        <img src="{tesco_img}" alt="TESCo" class="inst-logo">
        <img src="{sic_img}" alt="SIC" class="inst-logo">
    </div>
    <div class="event-meta">
        <div><strong>InnovaTecNM 2026</strong> • Región 5 (Etapa Regional)</div>
        <div>Folio: <strong>70785-17</strong> | INDUSTRIA ELÉCTRICA Y ELECTRÓNICA</div>
    </div>
</div>
"""

slides = [
    # Slide 1: Portada
    f"""
    <div class="slide active" data-speaker="Expositor 1 (Pitch)">
        {header_html}
        <div class="slide-title-area">
            <span class="slide-badge">PITCH DE ALTO IMPACTO (3 MINUTOS)</span>
            <h1 class="slide-title">FLUXA: Inteligencia Artificial en el Borde para Movilidad Urbana</h1>
            <p class="slide-subtitle">Modernización vial inteligente mediante arquitectura Retrofit Overlay y visión artificial</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card highlight" style="display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #6ee7b7; margin-bottom: 0.6rem;">
                        ¿Cuántas horas de tu vida has perdido frente a un semáforo en rojo viendo un carril totalmente vacío?
                    </div>
                    <p style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6;">
                        El 90% de los semáforos en México siguen operando como en 1980: con temporizadores ciegos que colapsan nuestras ciudades. Hoy les presentamos <strong>FLUXA</strong>, la plataforma que dota de visión, inteligencia y autonomía a cualquier intersección existente en menos de 4 horas.
                    </p>
                </div>
                <div class="card" style="display: flex; flex-direction: column; justify-content: center; gap: 0.8rem;">
                    <div class="stat-box">
                        <div class="stat-value">95%</div>
                        <div class="stat-label">Ahorro en costo frente a marcas extranjeras tradicionales</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">&lt; 12 ms</div>
                        <div class="stat-label">Latencia de inferencia local en NPU (Cero dependencia de la nube)</div>
                    </div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); text-align: center;">
                        Tecnológico de Estudios Superiores de Coacalco • TecNM
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 2: Problema
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {header_html}
        <div class="slide-title-area">
            <span class="slide-badge pill-red">EL PROBLEMA NACIONAL</span>
            <h1 class="slide-title">La Crisis Urbana: Tiempos Muertos y Barrera Presupuestal</h1>
            <p class="slide-subtitle">El congestionamiento asfixia la economía ciudadana y las arcas municipales</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card danger">
                    <div class="card-title"><span class="icon">⏱️</span> Pérdida de Productividad</div>
                    <div class="stat-value" style="color: #fca5a5; font-size: 1.8rem; margin: 0.4rem 0;">3,500 M</div>
                    <p>De horas-hombre desperdiciadas al año en el tráfico en México. El Valle de México es la segunda zona más congestionada de Latinoamérica.</p>
                </div>
                <div class="card danger">
                    <div class="card-title"><span class="icon">💸</span> Impacto Económico y Salud</div>
                    <div class="stat-value" style="color: #fca5a5; font-size: 1.8rem; margin: 0.4rem 0;">$94,000 MDP</div>
                    <p>Costo anual de la congestión vial (IMCO). Miles de toneladas de CO₂ emitidas por motores en ralentí frente a luces rojas absurdas.</p>
                </div>
                <div class="card danger">
                    <div class="card-title"><span class="icon">🚧</span> Barrera Presupuestal</div>
                    <div class="stat-value" style="color: #fca5a5; font-size: 1.8rem; margin: 0.4rem 0;">$500,000+</div>
                    <p>Costo en pesos por cruce de marcas extranjeras (Siemens, Econolite). Exigen obra civil destructiva y pagos mensuales en dólares a la nube.</p>
                </div>
            </div>
            <div class="card" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3);">
                <div style="font-size: 0.9rem; color: #fecaca;">
                    <strong>Consecuencia directa:</strong> Los municipios no modernizan sus semáforos porque no pueden pagarlos. Las ambulancias se quedan atrapadas y los ciudadanos pierden horas de vida en el tráfico.
                </div>
            </div>
        </div>
    </div>
    """,

    # Slide 3: Solución
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {header_html}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">NUESTRA PROPUESTA DE VALOR</span>
            <h1 class="slide-title">FLUXA: Retrofit Inteligente sin Obra Civil</h1>
            <p class="slide-subtitle">Una capa de inteligencia artificial que aprovecha la infraestructura ya instalada</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🔌</span> Retrofit Plug & Play</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">&lt; 4 Horas</div>
                    <p>Se conecta directamente a los gabinetes, cabezales y cableado existentes. No requiere romper pavimento ni interrumpir el tránsito.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🧠</span> Inferencia Edge Local</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">6 TOPS INT8</div>
                    <p>Procesamiento 100% en el borde sobre la NPU Rockchip RK3588 (Orange Pi 5). Cero pagos de servidores en la nube y latencia menor a 12 ms.</p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">🚦</span> Algoritmo Adaptativo TSP</div>
                    <div class="stat-value" style="font-size: 1.8rem; margin: 0.3rem 0;">Tiempo Real</div>
                    <p>Visión artificial con YOLOv8 que detecta vehículos, afora carriles, prioriza transporte público y abre corredores de emergencia para el C5.</p>
                </div>
            </div>
            <div class="card" style="display: flex; justify-content: space-around; align-items: center; padding: 0.8rem 1.4rem;">
                <div style="text-align: center;"><span class="pill pill-green">Cámara HD Gran Angular</span></div>
                <div style="color: var(--accent-mint); font-weight: 700;">➔</div>
                <div style="text-align: center;"><span class="pill pill-green">NPU Edge RK3588 (INT8)</span></div>
                <div style="color: var(--accent-mint); font-weight: 700;">➔</div>
                <div style="text-align: center;"><span class="pill pill-green">FSM + Watchdog Arduino</span></div>
                <div style="color: var(--accent-mint); font-weight: 700;">➔</div>
                <div style="text-align: center;"><span class="pill pill-green">Telemetría Web SCADA C5</span></div>
            </div>
        </div>
    </div>
    """,

    # Slide 4: Modelo de Negocio
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {header_html}
        <div class="slide-title-area">
            <span class="slide-badge pill-blue">MODELO DE NEGOCIO B2G</span>
            <h1 class="slide-title">Viabilidad Financiera: 95% de Ahorro y Alta Rentabilidad</h1>
            <p class="slide-subtitle">Modelo híbrido de hardware appliance + suscripción de software y soporte</p>
        </div>
        <div class="slide-body">
            <div class="grid-2">
                <div class="card">
                    <div class="card-title"><span class="icon">📊</span> Comparativa de Costo por Cruce (CapEx)</div>
                    <div style="margin: 0.8rem 0; display: flex; flex-direction: column; gap: 0.5rem;">
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
                            <div style="width: 5%; height: 100%; background: #10b981;"></div>
                        </div>
                    </div>
                    <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.6rem;">
                        <strong>Costo de Fabricación Unitario (BOM):</strong> $10,750 MXN | <strong>Margen Bruto:</strong> 62.3%
                    </p>
                </div>
                <div class="card highlight">
                    <div class="card-title"><span class="icon">💰</span> Proyección Año 1 (50 Cruces)</div>
                    <div class="grid-2" style="gap: 0.8rem; margin: 0.6rem 0;">
                        <div class="stat-box">
                            <div class="stat-value" style="font-size: 1.6rem;">$2.14 MDP</div>
                            <div class="stat-label">Ingresos Totales Año 1</div>
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
        {header_html}
        <div class="slide-title-area">
            <span class="slide-badge pill-amber">RETORNO SOCIAL Y AMBIENTAL</span>
            <h1 class="slide-title">Impacto Comprobado: Payback Social en Menos de 90 Días</h1>
            <p class="slide-subtitle">Metodología auditada con factores oficiales del DOE, CONUEE, SEDATU e INECC</p>
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
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">En un corredor de 10 cruces: <strong>$3.91 MDP</strong> de beneficio económico directo a la comunidad.</p>
                </div>
                <div class="card">
                    <div class="stat-box">
                        <div class="stat-value">36.8 Ton</div>
                        <div class="stat-label">CO₂ mitigado al año por cruce</div>
                    </div>
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">Equivalente a plantar más de 1,600 árboles urbanos maduros anualmente.</p>
                </div>
                <div class="card highlight">
                    <div class="stat-box">
                        <div class="stat-value" style="color: #6ee7b7;">&lt; 90 Días</div>
                        <div class="stat-label">Retorno de Inversión Social</div>
                    </div>
                    <p style="font-size: 0.78rem; margin-top: 0.5rem;">El sistema se amortiza ante los ojos de la ciudadanía en su primer trimestre de operación.</p>
                </div>
            </div>
            <div class="card" style="text-align: center; font-size: 0.88rem; color: #a7f3d0;">
                🌱 <strong>Alineación con los Ejes Estratégicos del TecNM:</strong> Sustentabilidad Ambiental, Impacto Social palpable y Adopción de Tecnologías Emergentes.
            </div>
        </div>
    </div>
    """,

    # Slide 6: Cierre & Equipo
    f"""
    <div class="slide" data-speaker="Expositor 1 (Pitch)">
        {header_html}
        <div class="slide-title-area">
            <span class="slide-badge pill-green">TRACCIÓN Y TRASCENDENCIA</span>
            <h1 class="slide-title">Madurez Tecnológica y Soberanía Nacional</h1>
            <p class="slide-subtitle">Desarrollado con orgullo en el Tecnológico de Estudios Superiores de Coacalco</p>
        </div>
        <div class="slide-body">
            <div class="grid-3">
                <div class="card">
                    <div class="card-title"><span class="icon">🚀</span> Madurez TRL 6 / 7</div>
                    <p>Probado y validado en banco experimental de potencia con relevadores y video en vivo en cruces de Coacalco, Ecatepec y Tultitlán. 100% de tests unitarios aprobados en PyTest.</p>
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
                    FLUXA: Movilidad Inteligente, Autónoma y Soberana para México
                </div>
                <p style="font-size: 0.92rem; color: #cbd5e1;">
                    No solo mejoramos el tráfico: demostramos que la tecnología mexicana puede resolver los grandes retos de nuestras ciudades. ¡Muchas gracias!
                </p>
            </div>
        </div>
    </div>
    """
]

notes_pitch = {
    0: {
        "speaker": "Expositor 1",
        "cue": "0:00 - 0:25 (25 seg)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:00]</span> Buenos días, miembros del jurado calificador y autoridades del TecNM. Les hago una pregunta honesta: <strong>¿cuántas horas de sus vidas han perdido esperando en un semáforo en rojo viendo un carril completamente vacío?</strong><br>
        <span class="notes-cue">[0:12]</span> En México, esto nos cuesta más de 3.5 mil millones de horas al año. Para resolver esto creamos <strong>FLUXA</strong>: una plataforma industrial de semaforización inteligente basada en Inteligencia Artificial en el Borde, desarrollada con orgullo en el TESCo para transformar semáforos ciegos en cruces autónomos sin obra civil.
        </p>
        """
    },
    1: {
        "speaker": "Expositor 1",
        "cue": "0:25 - 0:55 (30 seg)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:25]</span> El 90% de los semáforos del país siguen usando temporizadores fijos. Esto genera un costo de <strong>94 mil millones de pesos anuales</strong> por demoras y quema inútil de combustible en ralentí.<br>
        <span class="notes-cue">[0:40]</span> ¿Por qué los municipios no los cambian? Porque marcas extranjeras como Siemens o Econolite cobran <strong>entre 350 mil y 750 mil pesos por una sola intersección</strong>, exigen romper el asfalto para poner sensores que se destruyen con los baches y cobran licencias en dólares con servidores en la nube. Es un lujo que nuestras ciudades no pueden pagar.
        </p>
        """
    },
    2: {
        "speaker": "Expositor 1",
        "cue": "0:55 - 1:30 (35 seg)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[0:55]</span> <strong>Aquí es donde entra la innovación de FLUXA:</strong> operamos bajo una arquitectura <strong>Retrofit Overlay</strong>. Nos conectamos directamente al gabinete, cabezales y cableado existentes en <strong>menos de 4 horas</strong>, sin romper pavimento.<br>
        <span class="notes-cue">[1:12]</span> En lugar de costosos servidores en la nube, colocamos una computadora de borde con la NPU Rockchip RK3588 de 6 TOPS. Ejecutamos redes neuronales YOLOv8 cuantizadas a INT8 con una latencia de <strong>menos de 12 milisegundos</strong>. El sistema ve los autos en tiempo real, calcula la demanda ponderada y ajusta las luces de forma 100% autónoma.
        </p>
        """
    },
    3: {
        "speaker": "Expositor 1",
        "cue": "1:30 - 2:05 (35 seg)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[1:30]</span> Nuestro modelo de negocio B2G es disruptivo y altamente rentable. Vendemos el kit industrial completo a <strong>$28,500 MXN</strong> por cruce de 4 vías: un <strong>ahorro del 95%</strong> frente a la competencia extranjera.<br>
        <span class="notes-cue">[1:45]</span> Con un costo directo de fabricación de $10,750 MXN, logramos un margen bruto del 62.3%. Sumamos ingresos recurrentes por la licencia de monitoreo SCADA C5 y pólizas de mantenimiento.<br>
        <span class="notes-cue">[1:55]</span> En nuestro primer año, con solo 50 cruces en el Valle de México, proyectamos <strong>$2.14 millones de pesos de facturación</strong> y una utilidad neta de $890 mil pesos (41.5% de margen neto).
        </p>
        """
    },
    4: {
        "speaker": "Expositor 1",
        "cue": "2:05 - 2:35 (30 seg)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[2:05]</span> Pero lo más valioso no es lo que ahorra el municipio, sino lo que devuelve a la sociedad. Validado bajo metodologías del Departamento de Energía y la CONUEE, cada cruce FLUXA ahorra <strong>15,968 litros de gasolina al año</strong>.<br>
        <span class="notes-cue">[2:20]</span> Esto representa <strong>$391 mil pesos de ahorro directo en el bolsillo de los ciudadanos</strong> y evita 36.8 toneladas de CO₂ al año por cruce. En un corredor de 10 cruces son casi 4 millones de pesos al año. El retorno de inversión social se logra en <strong>menos de 90 días</strong>.
        </p>
        """
    },
    5: {
        "speaker": "Expositor 1",
        "cue": "2:35 - 3:00 (25 seg)",
        "text": """
        <p class="notes-body">
        <span class="notes-cue">[2:35]</span> FLUXA cuenta con un nivel de madurez <strong>TRL 6/7</strong>, validado con tráfico real en Coacalco, Ecatepec y Tultitlán, con protección de propiedad intelectual en trámite ante INDAUTOR e IMPI.<br>
        <span class="notes-cue">[2:48]</span> Con FLUXA, demostramos que en el Tecnológico Nacional de México creamos tecnología de clase mundial con impacto social tangible: más tiempo con nuestras familias, menos emisiones y ciudades vivas y eficientes. <strong>Muchas gracias.</strong>
        </p>
        """
    }
}

full_pitch_html = get_base_html(
    title="PITCH (3 Min)",
    total_seconds=180,
    slides_html="".join(slides),
    notes_dict=json.dumps(notes_pitch),
    speaker_tag="Expositor 1 (Pitch)"
)

with open(os.path.join(OUTPUT_DIR, 'pitch_3min.html'), 'w', encoding='utf-8') as f:
    f.write(full_pitch_html)

print("pitch_3min.html generado con éxito.")
