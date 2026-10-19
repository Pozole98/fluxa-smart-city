#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE_DIR = '/home/fluxa/fluxa-smart-city'
DOCS_DIR = os.path.join(BASE_DIR, 'docs')

content = """# 🏆 FLUXA Smart Mobility — Guía Maestra de Exposición y Defensa
## InnovaTecNM 2026 • Etapa Regional • Región 5
**Folio Oficial:** 70785-17 | **Categoría:** Industria Eléctrica y Electrónica  
**Institución:** Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM  
**Equipo:** Moisés Emilio Martínez Arias (Líder / Dev Principal), Diego Alejandro Huichapeño González, Ethan Rafael Flores Medina, Citlalli Rojas Rico, Jerazan Becerra Mendoza  
**Asesor:** Mtro. Roberto Carlos Muñoz Celaya  

---

## 📌 1. Reglas y Dinámica en la Sala de Evaluación (Manual Oficial TecNM)
* **Tiempo Total en Sala:** 15 minutos exactos.
  * **Pitch (3 minutos):** Expone **1 solo estudiante**.
  * **Memoria Técnica y Plan de Negocios (7 minutos):** Exponen **2 estudiantes** (compartiendo responsabilidad de forma activa).
  * **Sesión de Preguntas y Respuestas (5 minutos):** Todo el equipo puede participar respondiendo.
* **Tiempo en Stand:** 8 minutos de demostración física del prototipo y retroalimentación técnica del jurado externo.
* **Documentación Personal Obligatoria a la Mano:**
  * Gafete oficial impreso del sistema InnovaTecNM (portarlo en todo momento).
  * Credencial de estudiante del TESCo vigente.
  * Identificación oficial (INE o Pasaporte).
  * Constancia de estudios y carnet de seguridad social con fotografía.
* **Vestimenta:** Rigurosamente formal para todo el equipo.
* **Prohibiciones Clave:** Prohibido llevar el prototipo a la sala de evaluación (se evalúa en el stand). Prohibido que el asesor intervenga (solo puede observar). Prohibido uso de celulares en sala. Prohibido video que se explique solo (debe narrarse en vivo y durar máximo 2 min).

---

## 🎤 2. Presentación 1: PITCH DE ALTO IMPACTO (3 Minutos • 1 Expositor)
* **Archivo de Presentación:** `presentaciones/pitch_3min.html`  
* **URL en vivo:** `http://localhost:5000/presentaciones/pitch_3min.html` (o abrir directamente en el navegador)
* **Atajos de teclado:** `Flecha Der` (avanzar), `T` (cronómetro), `N` (ver guion), `F` (pantalla completa).

### Guion Segundo a Segundo:

#### Diapositiva 1: Portada & Hook de Entrada (0:00 - 0:25 / 25s)
> *"Buenos días, miembros del jurado calificador y autoridades del Tecnológico Nacional de México. Les hago una pregunta muy honesta: **¿cuántas horas de sus vidas han perdido esperando en un semáforo en rojo viendo un carril completamente vacío?** En nuestro país, esto nos cuesta más de 3.5 mil millones de horas al año. Para resolver esto creamos **FLUXA**: una plataforma industrial de semaforización inteligente basada en Inteligencia Artificial en el Borde, desarrollada con orgullo en el TESCo para transformar semáforos ciegos en cruces autónomos sin obra civil."*

#### Diapositiva 2: La Crisis Urbana y la Barrera Presupuestal (0:25 - 0:55 / 30s)
> *"El 90% de los semáforos de nuestras ciudades siguen operando con temporizadores de los años 80. Esto genera pérdidas económicas por más de **94 mil millones de pesos anuales**, además de miles de toneladas de CO₂ por vehículos en ralentí. ¿Por qué los municipios no los cambian? Porque marcas extranjeras como Siemens o Econolite cobran **entre 350 mil y 750 mil pesos por una sola intersección**, exigen romper el asfalto para poner sensores que se rompen con los baches y cobran licencias en dólares con servidores en la nube. Es un costo prohibitivo para nuestras alcaldías."*

#### Diapositiva 3: La Solución FLUXA — Retrofit sin Obra Civil (0:55 - 1:30 / 35s)
> *"**Aquí es donde entra la disrupción de FLUXA:** operamos bajo una arquitectura **Retrofit Overlay**. Nos conectamos directamente al gabinete, cabezales y cableado existentes en **menos de 4 horas**, sin romper pavimento. En lugar de costosos servidores en la nube, colocamos una computadora de borde con la NPU Rockchip RK3588 de 6 TOPS. Ejecutamos redes neuronales YOLOv8 cuantizadas a INT8 con una latencia de **menos de 12 milisegundos**. El sistema ve los autos en tiempo real, calcula la demanda ponderada y ajusta las luces de forma 100% autónoma."*

#### Diapositiva 4: Modelo de Negocio B2G y Finanzas (1:30 - 2:05 / 35s)
> *"Nuestro modelo de negocio B2G es accesible y altamente rentable. Vendemos el kit industrial completo a **$28,500 MXN** por cruce de 4 vías: un **ahorro del 95%** frente a la competencia extranjera. Con un costo directo de fabricación de $10,750 MXN, logramos un margen bruto del 62.3%. Sumamos ingresos recurrentes por la licencia de monitoreo SCADA C5 y pólizas de mantenimiento. En nuestro primer año, con solo 50 cruces en el Valle de México, proyectamos **$2.14 millones de pesos de facturación** y una utilidad neta de $890 mil pesos con un margen neto del 41.5%."*

#### Diapositiva 5: Retorno Social y Ambiental (2:05 - 2:35 / 30s)
> *"Pero lo más valioso no es lo que ahorra el municipio, sino lo que devuelve a la sociedad. Validado bajo metodologías oficiales del Departamento de Energía de EE.UU., CONUEE e INECC, cada cruce FLUXA ahorra **15,968 litros de gasolina al año**. Esto representa **$391 mil pesos de ahorro directo en el bolsillo de los ciudadanos** y evita 36.8 toneladas de CO₂ al año por cruce. En un corredor de 10 cruces son casi 4 millones de pesos de beneficio social. El retorno de inversión social se logra en **menos de 90 días**."*

#### Diapositiva 6: Madurez Tecnológica y Cierre (2:35 - 3:00 / 25s)
> *"FLUXA cuenta con un nivel de madurez **TRL 6/7**, validado con tráfico real en Coacalco, Ecatepec y Tultitlán, con protección de propiedad intelectual en trámite ante INDAUTOR e IMPI. Con FLUXA, demostramos que en el Tecnológico Nacional de México creamos tecnología de clase mundial con impacto social tangible: más tiempo con nuestras familias, menos emisiones y ciudades vivas y eficientes. **Muchas gracias.**"*

---

## 🔬 3. Presentación 2: MEMORIA TÉCNICA Y PLAN DE NEGOCIOS (7 Minutos • 2 Expositores)
* **Archivo de Presentación:** `presentaciones/defensa_tecnica_negocios_7min.html`  
* **URL en vivo:** `http://localhost:5000/presentaciones/defensa_tecnica_negocios_7min.html`
* **División de Tiempo:** 3:30 min para Expositor 1 (Técnico) y 3:30 min para Expositor 2 (Negocios).

### BLOQUE 1: MEMORIA TÉCNICA (0:00 - 3:30) — Expositor 1

* **Slide 1: Ficha Técnica (0:00 - 0:25):** Presentación institucional, folio 70785-17, presentación de integrantes del TESCo y estructura de la defensa.
* **Slide 2: Obsolescencia en la Red Semafórica (0:25 - 1:05):** Diagnóstico de fallas en temporizadores de los 80, fragilidad de espiras inductivas bajo asfalto y el peligro de la latencia en la nube.
* **Slide 3: Arquitectura Hardware & Retrofit (1:05 - 1:45):** Gabinete NEMA IP66, Orange Pi 5 (RK3588, NPU 6 TOPS), relevadores SSR optoacoplados, microcontrolador Arduino UNO R4 Minima y conexión Plug & Play en &lt;4 horas sin obra civil.
* **Slide 4: Pipeline Inferencia NPU INT8 & Tracking (1:45 - 2:25):** YOLOv8 cuantizado a INT8 con RKNN-Toolkit2 (&lt;12ms por cuadro), BYTETracker con Filtro de Kalman, mapeo poligonal ROI y cálculo de Demanda Ponderada (TSP) para transporte público.
* **Slide 5: Orquestación Tri-Core & Ola Verde (2:25 - 3:00):** Hito de ingeniería: 1 sola placa Orange Pi 5 corre 3 cruces independientes en puertos 5000, 5001 y 5002 asignando 1 núcleo NPU por cruce. Módulo `corridor_sync.py` para Ola Verde adaptativa por detección de pelotones.
* **Slide 6: Matriz Fail-Safe & Normas Mexicanas (3:00 - 3:30):** 3 niveles de tolerancia a fallos: tiempo fijo si falla cámara, hot-swap a CPU PyTorch si falla NPU, y destello ámbar por watchdog de microcontrolador en 3s si se congela la placa. Cumplimiento de **NOM-034-SCT2-2011** y **NOM-001-SEDE-2012**. TRL 6/7 con 100% de pruebas PyTest aprobadas.
* **Frase de cambio:** *"Y para explicar cómo esta ingeniería se convierte en un modelo de negocio escalable y autosustentable, cedo la palabra a mi compañera/compañero..."*

### BLOQUE 2: PLAN DE NEGOCIOS (3:30 - 7:00) — Expositor 2

* **Slide 7: Validación de Mercado B2G (3:30 - 4:10):** Clientes institucionales (Tránsito Municipal, SEMOV, Centros C5). Validación en campo con técnicos de Coacalco, Ecatepec y Tultitlán. Estrategia de adopción mediante pilotos de 30 días y contratos de arrendamiento.
* **Slide 8: Costo Unitario BOM y Margen (4:10 - 4:50):** Costo directo de fabricación de $10,750 MXN desglosado componente por componente. Precio de venta de $28,500 MXN que genera un **62.3% de margen bruto** y un ahorro del 95% al municipio.
* **Slide 9: Modelo de Ingresos y Proyección Año 1 (4:50 - 5:30):** 3 vertientes: Venta de Edge Box + Licencia anual SCADA C5 ($8,400/año) + Póliza SLA ($6,000/año). Meta Año 1: 50 cruces = **$2.145 MDP de ingresos** y **$890,000 MXN de utilidad neta (41.5% margen)** con inversión inicial de solo $180,000 MXN.
* **Slide 10: Retorno de Inversión Social (5:30 - 6:10):** Factores oficiales (DOE, CONUEE, SEDATU, INECC). Por cruce: 15,968 litros de gasolina ahorrados, $391,234 MXN ahorrados a la ciudadanía y 36.8 toneladas de CO₂ mitigadas. Payback social en menos de 90 días.
* **Slide 11: Propiedad Intelectual & Ejes Transversales (6:10 - 6:40):** Registro INDAUTOR (Software y algoritmos FSM) y trámites IMPI (Modelo de Utilidad + Marca Clase 9). Cumplimiento de los 4 ejes: Inclusión (botonera asistida), Impacto Social (ambulancias C5), Sustentabilidad y Tecnologías Emergentes.
* **Slide 12: Hoja de Ruta y Conclusiones (6:40 - 7:00):** Escalamiento de Coacalco al Estado de México y a nivel nacional con la red TecNM. Cierre formal: *"Quedamos a su disposición para la sesión de preguntas y para recibirlos en nuestro stand. Muchas gracias."*

---

## 🎯 4. Batería de Preguntas Difíciles del Jurado (Q&A Defense)
1. **¿Qué pasa si se va la luz o se congela la computadora?**
   * *Respuesta:* *"El sistema cuenta con una matriz Fail-Safe de 3 niveles. El microcontrolador físico (Arduino UNO R4) tiene un Watchdog por hardware con aislamiento galvánico; si deja de recibir el pulso de latido de la Orange Pi durante más de 3 segundos, asume el control directo de los relevadores y activa de inmediato un destello preventivo en amarillo para evitar cualquier choque vial."*
2. **¿Por qué dicen que cuesta 95% menos que Siemens si usan componentes comerciales?**
   * *Respuesta:* *"Porque las marcas tradicionales venden gabinetes monopólicos de arquitectura cerrada que exigen obra civil pesada y sensores invasivos en el pavimento. FLUXA opera bajo la filosofía Retrofit Overlay: no reemplaza el poste, el cable ni los focos existentes, solo agrega la capa de cómputo en el borde (Edge) dentro del gabinete, reduciendo el CapEx de $500,000 a solo $28,500 MXN."*
3. **¿Cómo garantizan que la cámara funcione de noche o con lluvia?**
   * *Respuesta:* *"La cámara vial cuenta con sensor de alto rango dinámico (WDR) y óptica gran angular para intemperie IP66. Si las condiciones meteorológicas reducen la confianza de detección por debajo del umbral de seguridad, el algoritmo FSM conmuta automáticamente a modo de tiempo fijo normado hasta que la visibilidad se restablezca."*
4. **¿Cómo validaron los números de ahorro de gasolina y CO₂?**
   * *Respuesta:* *"No son estimaciones al azar. Aplicamos la fórmula oficial del Departamento de Energía de EE.UU. (0.70 L/hora en ralentí) y el aforo estándar de SEDATU (15,000 vehículos/día). Una reducción promedio de apenas 15 segundos de espera por auto da matemáticamente 15,968 litros de ahorro al año, que multiplicado por el factor INECC de 2.31 kg CO₂/litro nos da las 36.8 toneladas de CO₂ mitigadas."*
5. **¿Qué avances tienen en Propiedad Intelectual?**
   * *Respuesta:* *"Tenemos preparado el expediente para INDAUTOR como 'Programa de Computación' protegiendo el código fuente de la FSM, la arquitectura multicruce y la consola SCADA. Ante el IMPI protegemos el Modelo de Utilidad del ensamble físico antivandalismo y el registro marcario de FLUXA en la Clase 9."*

---

## 🚀 5. Protocolo de Demostración en el STAND (8 Minutos)
1. **Paso 1: Bienvenida e Impacto Visual (1 min):** Mostrar la maqueta a escala con los semáforos físicos y la consola WebUI SCADA proyectada en la pantalla de la laptop (`http://localhost:5000/admin`).
2. **Paso 2: Detección en Tiempo Real (2 min):** Mostrar cómo la cámara capta los carritos en la maqueta o el video demo, dibujar las ROIs dinámicas en pantalla y evidenciar cómo los cuadros delimitadores (bounding boxes) y el aforo aumentan instantáneamente.
3. **Paso 3: Conmutación Adaptativa de Luces (2 min):** Demostrar cómo al colocar vehículos en el sentido transversal, el semáforo calcula la Demanda Ponderada y conmuta las luces físicas pasando por ámbar y despeje seguro de todo-rojo.
4. **Paso 4: Demostración de Emergencia C5 (1.5 min):** Presionar en la WebUI el botón "Corredor de Emergencia C5" y mostrar cómo los semáforos despejan la vía en menos de 2 segundos para dar paso prioritario a una ambulancia.
5. **Paso 5: Resiliencia y Fail-Safe (1.5 min):** Explicar el Selector de Arduinos dinámico en la WebUI y la conmutación en caliente a CPU si la NPU se desconecta.
"""

with open(os.path.join(DOCS_DIR, 'GUIAS_EXPOSICION.md'), 'w', encoding='utf-8') as f:
    f.write(content)

print("docs/GUIAS_EXPOSICION.md generado exitosamente.")
