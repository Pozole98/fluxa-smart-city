/*
 * ============================================================================
 * FLUXA Smart City - Controlador Semafórico Físico (Topología 2 Vías)
 * ============================================================================
 * Hardware Target: Arduino UNO R4 Minima (Renesas RA4M1 32-bit ARM Cortex-M4)
 * Protocolo: UART Serial 9600 bps, 8N1
 * Desarrollado para: Maqueta Vial con Inferencia IA RKNN en Orange Pi 5
 * ============================================================================
 */

// ----------------------------------------------------------------------------
// 1. ASIGNACIÓN ESTANDARIZADA DE PINES DIGITALES
// ----------------------------------------------------------------------------
// Semáforo Vía A (Sentido Principal)
const uint8_t PIN_VERDE_A    = 2;
const uint8_t PIN_AMARILLO_A = 3;
const uint8_t PIN_ROJO_A     = 4;

// Semáforo Vía B (Sentido Secundario)
const uint8_t PIN_VERDE_B    = 5;
const uint8_t PIN_AMARILLO_B = 6;
const uint8_t PIN_ROJO_B     = 8;

// ----------------------------------------------------------------------------
// 2. CONFIGURACIÓN DE SEGURIDAD Y WATCHDOG VIAL
// ----------------------------------------------------------------------------
// Si no se recibe ningún comando serial de la Orange Pi en este tiempo (ms),
// el semáforo entra en modo preventivo (destello ámbar) para evitar colisiones.
const unsigned long TIMEOUT_WATCHDOG_MS = 30000; 
unsigned long ultimoComandoMillis = 0;
char estadoActual = '5'; // Iniciar en '5' (Todo Rojo)

// Variables para el parpadeo preventivo no-bloqueante (sin delay)
unsigned long ultimoParpadeoMillis = 0;
bool estadoParpadeo = false;

// ----------------------------------------------------------------------------
// 3. FUNCIÓN ATÓMICA DE CONMUTACIÓN DE LUCES
// ----------------------------------------------------------------------------
// Garantiza que nunca se enciendan dos verdes simultáneos bajo ninguna condición.
void setLuces(bool vA, bool aA, bool rA, bool vB, bool aB, bool rB) {
  digitalWrite(PIN_VERDE_A,    vA ? HIGH : LOW);
  digitalWrite(PIN_AMARILLO_A, aA ? HIGH : LOW);
  digitalWrite(PIN_ROJO_A,     rA ? HIGH : LOW);
  
  digitalWrite(PIN_VERDE_B,    vB ? HIGH : LOW);
  digitalWrite(PIN_AMARILLO_B, aB ? HIGH : LOW);
  digitalWrite(PIN_ROJO_B,     rB ? HIGH : LOW);
}

void apagarTodas() {
  setLuces(false, false, false, false, false, false);
}

// ----------------------------------------------------------------------------
// 4. MÁQUINA DE ESTADOS COMPATIBLE CON PROTOCOLO FLUXA
// ----------------------------------------------------------------------------
void procesarComando(char cmd) {
  bool cambio = (cmd != estadoActual);
  switch (cmd) {
    case '1': // FASE 1: Verde Vía A | Rojo Vía B
      setLuces(true, false, false,   false, false, true);
      estadoActual = '1';
      if (cambio) Serial.println(F("[FLUXA] Fase 1: VERDE Vía A | ROJO Vía B"));
      break;

    case '2': // FASE 1 INTERMEDIA: Amarillo Vía A | Rojo Vía B
      setLuces(false, true, false,   false, false, true);
      estadoActual = '2';
      if (cambio) Serial.println(F("[FLUXA] Fase 1: AMARILLO Vía A | ROJO Vía B"));
      break;

    case '3': // FASE 2: Rojo Vía A | Verde Vía B
      setLuces(false, false, true,   true, false, false);
      estadoActual = '3';
      if (cambio) Serial.println(F("[FLUXA] Fase 2: ROJO Vía A | VERDE Vía B"));
      break;

    case '4': // FASE 2 INTERMEDIA: Rojo Vía A | Amarillo Vía B
      setLuces(false, false, true,   false, true, false);
      estadoActual = '4';
      if (cambio) Serial.println(F("[FLUXA] Fase 2: ROJO Vía A | AMARILLO Vía B"));
      break;

    case '5': // INTERVALO DE DESPEJE (TODO ROJO CANÓNICO)
    case '0':
      setLuces(false, false, true,   false, false, true);
      estadoActual = '5';
      if (cambio) Serial.println(F("[FLUXA] Despeje: TODO ROJO"));
      break;

    default:
      // Ignorar saltos de línea (\n, \r) o espacios
      break;
  }
}

// ----------------------------------------------------------------------------
// 5. INICIALIZACIÓN (SETUP)
// ----------------------------------------------------------------------------
void setup() {
  // Comunicación USB CDC nativa del Arduino UNO R4
  Serial.begin(9600);

  // Configuración de los 6 pines como SALIDA
  pinMode(PIN_VERDE_A,    OUTPUT);
  pinMode(PIN_AMARILLO_A, OUTPUT);
  pinMode(PIN_ROJO_A,     OUTPUT);
  pinMode(PIN_VERDE_B,    OUTPUT);
  pinMode(PIN_AMARILLO_B, OUTPUT);
  pinMode(PIN_ROJO_B,     OUTPUT);

  // --------------------------------------------------------------------------
  // AUTODIAGNÓSTICO AL ENCENDER (POST - Power-On Self Test)
  // Enciende todos los LEDs durante 1.5 segundos para que verifiques a simple
  // vista que todos los cables, resistencias y LEDs quedaron bien conectados.
  // --------------------------------------------------------------------------
  setLuces(true, true, true, true, true, true);
  delay(1500);

  // Estado inicial normativo seguro: Todo Rojo
  setLuces(false, false, true, false, false, true);

  // Banner informativo en el Monitor Serie
  Serial.println(F("=================================================="));
  Serial.println(F(" FLUXA Smart City - Controlador Físico (2 Vías)  "));
  Serial.println(F(" Plataforma: Arduino UNO R4 Minima                "));
  Serial.println(F(" Estado: Listo y esperando comandos de Orange Pi  "));
  Serial.println(F(" Comandos de prueba: 1, 2, 3, 4, 5                "));
  Serial.println(F("=================================================="));

  ultimoComandoMillis = millis();
}

// ----------------------------------------------------------------------------
// 6. BUCLE PRINCIPAL (LOOP)
// ----------------------------------------------------------------------------
void loop() {
  // A. Lectura de comandos enviados por FLUXA (Orange Pi 5)
  while (Serial.available() > 0) {
    char caracter = (char)Serial.read();
    if (caracter == '1' || caracter == '2' || caracter == '3' || 
        caracter == '4' || caracter == '5' || caracter == '0') {
      procesarComando(caracter);
      ultimoComandoMillis = millis(); // Reiniciar cronómetro del watchdog
    }
  }

  // B. Watchdog Fail-Safe de Seguridad
  // Si la Orange Pi o la IA se detienen por más de 15 segundos,
  // parpadear ambas luces ámbar a 1 Hz de forma no-bloqueante (sin usar delay).
  if (millis() - ultimoComandoMillis > TIMEOUT_WATCHDOG_MS) {
    unsigned long tiempoActual = millis();
    if (tiempoActual - ultimoParpadeoMillis >= 500) {
      ultimoParpadeoMillis = tiempoActual;
      estadoParpadeo = !estadoParpadeo;
      
      // Apagar verdes y rojos; destellar amarillos
      digitalWrite(PIN_VERDE_A, LOW);
      digitalWrite(PIN_ROJO_A, LOW);
      digitalWrite(PIN_VERDE_B, LOW);
      digitalWrite(PIN_ROJO_B, LOW);
      
      digitalWrite(PIN_AMARILLO_A, estadoParpadeo ? HIGH : LOW);
      digitalWrite(PIN_AMARILLO_B, estadoParpadeo ? HIGH : LOW);
    }
  }
}
