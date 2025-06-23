# BaulSIG - Baúl de Archivos Seguro

## 1. Introducción

BaulSIG es una aplicación de escritorio para la gestión segura de archivos, diseñada con un modelo cliente-servidor. Permite a los usuarios explorar un repositorio centralizado de archivos y solicitar descargas, las cuales deben ser aprobadas por un administrador. El objetivo principal es mantener un control estricto sobre el acceso y la distribución de los documentos.

La aplicación cuenta con dos roles principales:
- **Usuario Estándar:** Puede navegar por los archivos, buscar y solicitar permisos para descargar.
- **Administrador:** Tiene control total sobre los archivos (subir, modificar, eliminar) y gestiona las solicitudes de los usuarios.

## 2. Características

### Para Usuarios
- **Explorador de Archivos:** Interfaz intuitiva con vista de árbol de directorios y lista de archivos.
- **Navegación y Búsqueda:** Permite navegar por la estructura de carpetas y buscar archivos por nombre.
- **Sistema de Solicitud de Descarga:** Para descargar un archivo o carpeta, el usuario debe enviar una solicitud explicando el motivo.
- **Panel de "Mis Solicitudes":** Un apartado donde el usuario puede ver el estado de sus solicitudes (`pendiente`, `aprobado`, `rechazado`).
- **Descarga Segura:** Una vez que una solicitud es aprobada, el usuario puede descargar el archivo directamente desde su panel de solicitudes.
- **Cierre de Sesión:** Funcionalidad para terminar la sesión de forma segura.

### Para Administradores
- **Gestión Total de Archivos:** Los administradores pueden realizar operaciones CRUD completas sobre archivos y carpetas:
  - Subir archivos y carpetas completas.
  - Crear nuevas carpetas.
  - Renombrar y mover archivos/carpetas.
  - Eliminar archivos/carpetas del repositorio.
- **Descarga Directa:** Pueden descargar cualquier archivo o carpeta sin necesidad de una solicitud previa.
- **Panel de Gestión de Solicitudes:** Una vista centralizada para revisar todas las solicitudes de descarga pendientes de los usuarios.
- **Aprobación/Rechazo de Solicitudes:** Pueden aprobar o rechazar solicitudes de forma individual.
- **Aprobación Masiva:** Opción para aprobar todas las solicitudes pendientes con un solo clic.
- **Historial de Solicitudes:** Posibilidad de ver el historial de cambios y motivos de una solicitud.

## 3. Tecnologías Utilizadas

- **Lenguaje:** Python 3
- **Interfaz Gráfica (GUI):**
  - `Tkinter` (la biblioteca estándar de Python para GUI)
  - `ttkbootstrap`: Para aplicar temas modernos y estilos a los componentes de Tkinter.
  - `tkinterdnd2`: Para la funcionalidad de arrastrar y soltar (Drag and Drop).
- **Base de Datos:**
  - `PostgreSQL`: Como sistema de gestión de bases de datos.
  - `psycopg2-binary`: El adaptador de Python para PostgreSQL.
  - `pgcrypto`: Extensión de PostgreSQL utilizada para el hash seguro de contraseñas.
- **Otras dependencias notables:**
  - `Pillow`: Para el manejo de imágenes (aunque su uso no es prominente en la GUI principal).
  - `fastapi` y `uvicorn`: Incluidas en las dependencias, posiblemente para futuras funcionalidades de API web.

## 4. Prerrequisitos

Antes de empezar, asegúrate de tener instalado lo siguiente:
- **Python 3.8 o superior.**
- **PostgreSQL 12 o superior.**
- **Git** (para clonar el repositorio).

## 5. Configuración de la Base de Datos

Es crucial configurar la base de datos correctamente para que la aplicación funcione.

### Paso 1: Crear la Base de Datos
Abre `psql` o tu cliente de PostgreSQL preferido y ejecuta:
```sql
CREATE DATABASE sistema_archivos;
```

### Paso 2: Habilitar la extensión `pgcrypto`
Conéctate a la base de datos recién creada y habilita la extensión `pgcrypto`, que es fundamental para la seguridad de las contraseñas.
```sql
\c sistema_archivos
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Paso 3: Crear las Tablas
Ejecuta las siguientes sentencias `SQL` para crear las tablas necesarias. Se basan en el uso observado en el código fuente.

```sql
-- Tabla para almacenar los usuarios y sus roles
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    contrasena TEXT NOT NULL, -- Se almacena el hash generado por pgcrypto
    rol VARCHAR(50) NOT NULL DEFAULT 'usuario' -- 'usuario' o 'admin'
);

-- Tabla para registrar los archivos y carpetas
CREATE TABLE archivos (
    id SERIAL PRIMARY KEY,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta TEXT NOT NULL, -- Ruta relativa dentro del directorio compartido
    subido_por INT REFERENCES usuarios(id),
    fecha_subida TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    carpeta BOOLEAN NOT NULL DEFAULT FALSE -- True si es una carpeta
);

-- Tabla para las solicitudes de descarga
CREATE TABLE solicitudes_descarga (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id),
    archivo_id INT NOT NULL REFERENCES archivos(id),
    motivo TEXT,
    estado VARCHAR(50) NOT NULL DEFAULT 'pendiente', -- 'pendiente', 'aprobado', 'rechazado'
    fecha_solicitud TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para registrar cambios de motivo en las solicitudes
CREATE TABLE historial_motivos (
    id SERIAL PRIMARY KEY,
    solicitud_id INT NOT NULL REFERENCES solicitudes_descarga(id) ON DELETE CASCADE,
    motivo TEXT NOT NULL,
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de logs para auditoría
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id),
    archivo_id INT REFERENCES archivos(id),
    accion VARCHAR(255) NOT NULL,
    motivo TEXT,
    fecha_hora TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    nombre_archivo VARCHAR(255)
);
```

## 6. Instalación y Configuración del Proyecto

### Paso 1: Clonar el Repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd BaulSIG
```

### Paso 2: Crear un Entorno Virtual (Recomendado)
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### Paso 3: Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar la Conexión
La configuración de la base de datos se encuentra hardcodeada en el archivo `core/config.py`.

Abre `core/config.py` y ajusta el diccionario `DATABASE_CONFIG` si tus credenciales de PostgreSQL son diferentes:
```python
DATABASE_CONFIG = {
    'dbname': "sistema_archivos",
    'user': "postgres", 
    'password': "sig2025",
    'host': "localhost",
    'port': "5433"
}
```
También, verifica la ruta de la carpeta compartida en `ARCHIVOS_COMPARTIDOS_DIR` para que apunte a una ubicación válida en tu sistema o red.
```python
ARCHIVOS_COMPARTIDOS_DIR = "//TU_SERVIDOR/TU_CARPETA_COMPARTIDA" # O una ruta local como "C:/Ruta/A/Tu/Carpeta"
```

## 7. Cómo Ejecutar la Aplicación
Una vez que la base de datos y la configuración estén listas, puedes iniciar la aplicación ejecutando el script principal:
```bash
python main.py
```
Se abrirá la ventana de inicio de sesión. Para empezar, necesitarás crear un usuario administrador directamente en la base de datos.

### Crear un Usuario Administrador de Ejemplo
Usa esta sentencia SQL para crear un usuario `admin` con la contraseña `admin`. La aplicación se encargará de hashear la contraseña al crear usuarios desde la propia interfaz, pero para el primer inicio de sesión esto es necesario.

```sql
INSERT INTO usuarios (nombre, contrasena, rol) 
VALUES ('admin', crypt('admin', gen_salt('bf')), 'admin');
```

## 8. Estructura del Proyecto

```
BaulSIG/
├── core/         # Lógica central y configuración
│   ├── auth.py   # Autenticación, gestión de usuarios y contraseñas
│   ├── config.py # Configuración de BD y rutas
│   ├── ui_config.py # Configuración de estilos de la GUI
│   └── utils.py  # Funciones de utilidad (ej. centrar ventanas)
├── db/           # Módulos de interacción con la base de datos
│   ├── db_manager.py     # Gestor del pool de conexiones a la BD
│   └── file_manager.py   # Lógica para operaciones de archivos en la BD
├── gui/          # Componentes de la Interfaz Gráfica de Usuario
│   ├── admin.py  # Ventana y lógica para el rol de administrador
│   ├── login.py  # Ventana de inicio de sesión
│   └── usuario.py# Ventana y lógica para el rol de usuario
├── main.py       # Punto de entrada de la aplicación
├── README.md     # Esta documentación
└── requirements.txt # Dependencias del proyecto
```