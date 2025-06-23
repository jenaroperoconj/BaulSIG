import psycopg2
from psycopg2 import pool
import threading
from contextlib import contextmanager
from typing import Optional
from core.config import get_database_config

class DBManager:
    """
    Gestor centralizado de conexiones y operaciones con la base de datos usando un pool de conexiones.
    """
    def __init__(self, minconn: int = 2, maxconn: int = 20):
        self.connection_params = get_database_config()
        self._lock = threading.Lock()
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self.minconn = minconn
        self.maxconn = maxconn
        self._initialize_pool()

    def _initialize_pool(self):
        """Inicializa el pool de conexiones"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                self.minconn,
                self.maxconn,
                **self.connection_params
            )
            print(f"[INFO] Pool de conexiones inicializado: {self.minconn}-{self.maxconn} conexiones")
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar el pool de conexiones: {e}")
            self._pool = None

    @contextmanager
    def get_connection(self):
        """
        Context manager que proporciona una conexión del pool.
        Se asegura de que la conexión se devuelva al pool automáticamente.
        """
        if not self._pool:
            try:
                conn = psycopg2.connect(**self.connection_params)
                try:
                    yield conn
                finally:
                    conn.close()
            except Exception as e:
                print(f"[ERROR] Error en conexión directa: {e}")
                yield None
            return
        conn = None
        try:
            with self._lock:
                conn = self._pool.getconn()
            if conn:
                if conn.closed:
                    with self._lock:
                        self._pool.putconn(conn, close=True)
                        conn = self._pool.getconn()
                yield conn
            else:
                yield None
        except Exception as e:
            print(f"[ERROR] Error al obtener conexión del pool: {e}")
            if conn:
                with self._lock:
                    self._pool.putconn(conn, close=True)
                conn = None
            yield None
        finally:
            if conn:
                try:
                    with self._lock:
                        self._pool.putconn(conn)
                except Exception as e:
                    print(f"[ERROR] Error al devolver conexión al pool: {e}")

    @contextmanager
    def get_cursor(self):
        """
        Context manager que proporciona un cursor listo para usar.
        Maneja automáticamente la conexión y el cursor.
        """
        with self.get_connection() as conn:
            if conn is None:
                yield None
                return
            cursor = None
            try:
                cursor = conn.cursor()
                yield cursor
                conn.commit()
            except Exception as e:
                if conn:
                    conn.rollback()
                print(f"[ERROR] Error en operación de base de datos: {e}")
                raise
            finally:
                if cursor:
                    cursor.close()

    def execute_query(self, query: str, params=None, fetch_one=False, fetch_all=True):
        """
        Ejecuta una consulta y retorna los resultados.
        """
        try:
            with self.get_cursor() as cursor:
                if cursor is None:
                    return None
                cursor.execute(query, params)
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.rowcount
        except Exception as e:
            print(f"[ERROR] Error ejecutando consulta: {e}")
            return None

    def execute_insert_returning(self, query: str, params=None):
        """
        Ejecuta un INSERT con RETURNING y retorna el valor.
        """
        try:
            with self.get_cursor() as cursor:
                if cursor is None:
                    return None
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"[ERROR] Error en INSERT con RETURNING: {e}")
            return None

    def close_all_connections(self):
        """Cierra todas las conexiones del pool"""
        if self._pool:
            with self._lock:
                self._pool.closeall()
            print("[INFO] Pool de conexiones cerrado")

    def get_pool_status(self):
        """Obtiene información sobre el estado del pool"""
        if not self._pool:
            return {"status": "No inicializado"}
        return {
            "status": "Activo",
            "min_connections": self.minconn,
            "max_connections": self.maxconn
        }

# Instancia global del gestor de base de datos
db_manager = DBManager()

# Función de compatibilidad con el código existente
def conectar():
    try:
        config = get_database_config()
        return psycopg2.connect(**config)
    except Exception as e:
        print(f"[ERROR] Error al conectar: {e}")
        return None 