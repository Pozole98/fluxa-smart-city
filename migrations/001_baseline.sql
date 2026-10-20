-- ==============================================================================
-- FLUXA Smart Mobility • Esquema Base Canónico de Base de Datos (001_baseline.sql)
-- Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
-- ==============================================================================
-- Compatible con: MariaDB 10.5+ (Armbian 24 / Debian / Ubuntu / Fedora / openSUSE)
-- Motor: InnoDB • Codificación: utf8mb4_unicode_ci

-- 1. Telemetría y métricas operacionales de aforo y rendimiento hardware
CREATE TABLE IF NOT EXISTS traffic_telemetry (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    topology VARCHAR(50) NOT NULL,
    active_phase VARCHAR(50) NOT NULL,
    total_cars INT NOT NULL,
    lane_counts_json TEXT NOT NULL,
    weighted_demand FLOAT NOT NULL,
    cpu_percent FLOAT,
    cpu_temp_c FLOAT,
    ram_percent FLOAT,
    fps FLOAT,
    INDEX idx_time (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Registro de eventos de sistema, auditoría operativa y conmutaciones de fase
CREATE TABLE IF NOT EXISTS system_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    message VARCHAR(255) NOT NULL,
    INDEX idx_time (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Infracciones viales por invasión en luz roja y analítica de placas
CREATE TABLE IF NOT EXISTS red_light_violations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    lane VARCHAR(50) NOT NULL,
    track_id INT NOT NULL,
    phase_state VARCHAR(50) NOT NULL,
    snapshot_path VARCHAR(255),
    license_plate VARCHAR(50) DEFAULT 'NO_DETECTADA',
    plate_confidence FLOAT DEFAULT 0.0,
    INDEX idx_time (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
