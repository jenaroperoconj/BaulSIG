from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from db.db_manager import db_manager, conectar
import shutil
from tkinter import messagebox

class ArchivoManager:
    """
    Clase principal para la gestión de archivos y carpetas en la base de datos.
    Incluye registro de movimientos, creación, actualización, eliminación y consultas.
    """
    def __init__(self):
        self.db = db_manager

    def registrar_log(self, usuario_id, archivo_id, accion, motivo, nombre_archivo):
        """
        Inserta un registro en la tabla logs para compatibilidad con el código existente.
        """
        query = """
            INSERT INTO logs (usuario_id, archivo_id, accion, motivo, fecha_hora, nombre_archivo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (usuario_id, archivo_id, accion, motivo, datetime.now(), nombre_archivo)
        self.db.execute_query(query, params, fetch_all=False)

    def registrar_archivo(self, nombre_archivo: str, ruta_relativa: str, subido_por: int, es_carpeta: bool) -> Optional[int]:
        """
        Registra un archivo o carpeta en la base de datos.
        """
        query = """
            INSERT INTO archivos (nombre_archivo, ruta, subido_por, fecha_subida, carpeta)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (nombre_archivo, ruta_relativa, subido_por, datetime.now(), es_carpeta)
        archivo_id = self.db.execute_insert_returning(query, params)
        if archivo_id:
            print(f"[INFO] Archivo registrado: {nombre_archivo} (ID: {archivo_id})")
        return archivo_id

    def buscar_archivo_id(self, nombre_archivo: str, ruta_relativa: str) -> Optional[int]:
        """
        Busca el ID de un archivo en la base de datos.
        """
        query = """
            SELECT id FROM archivos
            WHERE nombre_archivo = %s AND ruta = %s
            ORDER BY id DESC LIMIT 1;
        """
        params = (nombre_archivo, ruta_relativa)
        result = self.db.execute_query(query, params, fetch_one=True)
        archivo_id = result[0] if result else None
        return archivo_id

    def actualizar_nombre_archivo(self, archivo_id: int, nuevo_nombre: str, ruta_relativa: str, nombre_anterior: str) -> bool:
        """
        Actualiza el nombre de un archivo.
        """
        query = """
            UPDATE archivos
            SET nombre_archivo = %s
            WHERE id = %s;
        """
        params = (nuevo_nombre, archivo_id)
        result = self.db.execute_query(query, params, fetch_all=False)
        return result is not None and result > 0

    def actualizar_ruta_archivo(self, archivo_id: int, nueva_ruta: str, nombre_archivo: str, ruta_anterior: str) -> bool:
        """
        Actualiza la ruta de un archivo.
        """
        query = """
            UPDATE archivos
            SET ruta = %s
            WHERE id = %s;
        """
        params = (nueva_ruta, archivo_id)
        result = self.db.execute_query(query, params, fetch_all=False)
        return result is not None and result > 0

    def eliminar_archivo(self, archivo_id: int) -> bool:
        """
        Elimina un archivo de la base de datos.
        """
        query = "DELETE FROM archivos WHERE id = %s"
        params = (archivo_id,)
        result = self.db.execute_query(query, params, fetch_all=False)
        return result is not None and result > 0

    def obtener_solicitudes_usuario(self, user_id: int) -> List[Tuple]:
        """
        Obtiene todas las solicitudes de descarga de un usuario.
        """
        query = """
            SELECT sd.id, a.nombre_archivo, sd.motivo, sd.estado, sd.fecha_solicitud, a.ruta
            FROM solicitudes_descarga sd
            JOIN archivos a ON a.id = sd.archivo_id
            WHERE sd.usuario_id = %s
            ORDER BY sd.fecha_solicitud DESC
        """
        params = (user_id,)
        result = self.db.execute_query(query, params)
        solicitudes = result if result else []
        return solicitudes

    def crear_solicitud_descarga(self, usuario_id: int, archivo_id: int, motivo: str) -> bool:
        """
        Crea una nueva solicitud de descarga.
        """
        query = """
            INSERT INTO solicitudes_descarga (usuario_id, archivo_id, motivo, estado, fecha_solicitud)
            VALUES (%s, %s, %s, 'pendiente', %s)
        """
        params = (usuario_id, archivo_id, motivo, datetime.now())
        result = self.db.execute_query(query, params, fetch_all=False)
        return result is not None and result > 0

    def actualizar_estado_solicitud(self, solicitud_id: int, nuevo_estado: str, usuario_id: int = None) -> bool:
        """
        Actualiza el estado de una solicitud.
        """
        query = "UPDATE solicitudes_descarga SET estado = %s WHERE id = %s"
        params = (nuevo_estado, solicitud_id)
        result = self.db.execute_query(query, params, fetch_all=False)
        return result is not None and result > 0

    def obtener_solicitudes_pendientes(self) -> List[Tuple]:
        """
        Obtiene todas las solicitudes de descarga pendientes para administradores.
        """
        query = """
            SELECT sd.id, u.nombre, a.nombre_archivo, sd.estado, sd.motivo, sd.fecha_solicitud
            FROM solicitudes_descarga sd
            JOIN usuarios u ON u.id = sd.usuario_id
            JOIN archivos a ON a.id = sd.archivo_id
            WHERE sd.estado = 'pendiente' AND u.rol != 'admin'
            ORDER BY sd.fecha_solicitud DESC
        """
        return self.db.execute_query(query, fetch_all=True) or []

    def aprobar_solicitud(self, solicitud_id: int, motivo: str) -> bool:
        """
        Aprueba una solicitud de descarga.
        """
        with self.db.get_connection() as conn:
            if conn is None:
                return False
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE solicitudes_descarga 
                    SET estado = 'aprobado' 
                    WHERE id = %s
                """, (solicitud_id,))
                conn.commit()
                return True
            except Exception as e:
                print(f"[ERROR] Error aprobando solicitud: {e}")
                conn.rollback()
                return False

    def rechazar_solicitud(self, solicitud_id: int, motivo: str) -> bool:
        """
        Rechaza una solicitud de descarga.
        """
        with self.db.get_connection() as conn:
            if conn is None:
                return False
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE solicitudes_descarga 
                    SET estado = 'rechazada' 
                    WHERE id = %s
                """, (solicitud_id,))
                conn.commit()
                return True
            except Exception as e:
                print(f"[ERROR] Error rechazando solicitud: {e}")
                conn.rollback()
                return False

    def obtener_historial_solicitud(self, solicitud_id: int) -> List[Tuple]:
        """
        Obtiene el historial completo de una solicitud, incluyendo todos los cambios de motivos.
        """
        query = """
            SELECT fecha, motivo
            FROM (
                -- Obtener el motivo actual de la solicitud
                SELECT fecha_solicitud as fecha, motivo
                FROM solicitudes_descarga
                WHERE id = %s
                UNION ALL
                -- Obtener el historial de cambios de motivos
                SELECT fecha, motivo
                FROM historial_motivos
                WHERE solicitud_id = %s
            ) historial
            ORDER BY fecha DESC
        """
        params = (solicitud_id, solicitud_id)
        return self.db.execute_query(query, params) or []

    def crear_solicitud_descarga_admin(self, usuario_id: int, archivo_id: int, motivo: str) -> bool:
        """
        Crea una solicitud de descarga directa para administradores (estado aprobada).
        """
        query = """
            INSERT INTO solicitudes_descarga (usuario_id, archivo_id, motivo, estado, fecha_solicitud)
            VALUES (%s, %s, %s, 'aprobado', %s)
        """
        params = (usuario_id, archivo_id, motivo, datetime.now())
        result = self.db.execute_query(query, params, fetch_all=False)
        return result is not None and result > 0

    def aprobar_todas_solicitudes(self) -> bool:
        """
        Aprueba todas las solicitudes de descarga pendientes.
        """
        with self.db.get_connection() as conn:
            if conn is None:
                return False
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE solicitudes_descarga 
                    SET estado = 'aprobado' 
                    WHERE estado = 'pendiente'
                """)
                conn.commit()
                return True
            except Exception as e:
                print(f"[ERROR] Error aprobando todas las solicitudes: {e}")
                conn.rollback()
                return False

# Instancia global del gestor de archivos
archivo_manager = ArchivoManager() 