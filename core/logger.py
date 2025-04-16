from db.conexion import conectar

def registrar_log(usuario_id, archivo_id, nombre_archivo, accion, motivo):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (usuario_id, archivo_id, nombre_archivo, accion, motivo)
            VALUES (%s, %s, %s, %s, %s)
        """, (usuario_id, archivo_id, nombre_archivo, accion, motivo))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] No se pudo registrar el log: {e}")
