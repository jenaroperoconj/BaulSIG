from db.conexion import conectar
from datetime import datetime

def registrar_archivo(nombre_archivo, ruta_relativa, subido_por, es_carpeta):
    conn = conectar()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO archivos (nombre_archivo, ruta, subido_por, fecha_subida, carpeta)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (nombre_archivo, ruta_relativa, subido_por, datetime.now(), es_carpeta))
            archivo_id = cur.fetchone()[0]
            conn.commit()
            return archivo_id
    except Exception as e:
        print("Error al registrar archivo:", e)
        conn.rollback()
        return None
    finally:
        conn.close()

def registrar_log(usuario_id, archivo_id, accion, motivo, nombre_archivo):
    conn = conectar()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO logs (usuario_id, archivo_id, accion, motivo, fecha_hora, nombre_archivo)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (usuario_id, archivo_id, accion, motivo, datetime.now(), nombre_archivo))
            conn.commit()
    except Exception as e:
        print("Error al registrar log:", e)
        conn.rollback()
    finally:
        conn.close()

def actualizar_nombre_archivo(archivo_id, nuevo_nombre):
    conn = conectar()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE archivos
                SET nombre_archivo = %s
                WHERE id = %s;
            """, (nuevo_nombre, archivo_id))
            conn.commit()
            return True
    except Exception as e:
        print("Error al actualizar nombre del archivo:", e)
        conn.rollback()
        return False
    finally:
        conn.close()

def _buscar_archivo_id(nombre_archivo, ruta_relativa):
    conn = conectar()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM archivos
                WHERE nombre_archivo = %s AND ruta = %s
                ORDER BY id DESC LIMIT 1;
            """, (nombre_archivo, ruta_relativa))
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        print("Error al buscar archivo_id:", e)
        return None
    finally:
        conn.close()

def actualizar_ruta_archivo(archivo_id, nueva_ruta):
    conn = conectar()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE archivos
                SET ruta = %s
                WHERE id = %s;
            """, (nueva_ruta, archivo_id))
            conn.commit()
            return True
    except Exception as e:
        print("Error al actualizar ruta:", e)
        conn.rollback()
        return False
    finally:
        conn.close()