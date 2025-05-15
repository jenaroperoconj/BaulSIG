-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    contrasena TEXT NOT NULL
);

-- Tabla de archivos
CREATE TABLE IF NOT EXISTS archivos (
    id SERIAL PRIMARY KEY,
    nombre_archivo TEXT NOT NULL,
    ruta_relativa TEXT NOT NULL,
    subido_por_admin BOOLEAN NOT NULL,
    es_carpeta BOOLEAN NOT NULL
);

-- Tabla de logs
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    usuario_es_admin BOOLEAN NOT NULL,
    archivo_id INTEGER NOT NULL REFERENCES archivos(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    motivo TEXT NOT NULL,
    nombre_archivo TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de solicitudes de descarga
CREATE TABLE IF NOT EXISTS solicitudes_descarga (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    archivo_id INTEGER NOT NULL REFERENCES archivos(id) ON DELETE CASCADE,
    estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'aprobado', 'descargado')),
    motivo TEXT, -- Motivo final aprobado
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion TIMESTAMP
);

-- Tabla de historial de motivos
CREATE TABLE IF NOT EXISTS historial_motivos (
    id SERIAL PRIMARY KEY,
    solicitud_id INTEGER NOT NULL REFERENCES solicitudes_descarga(id) ON DELETE CASCADE,
    motivo TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO usuarios (nombre, contrasena, rol)
VALUES ('admin', 'admin123', 'admin')
ON CONFLICT DO NOTHING;