import psycopg2

def conectar():
    try:
        conn = psycopg2.connect(
            dbname="sistema_archivos",
            user="postgres",
            password="sig2025",
            host="localhost",
            port="5433"
        )
        return conn
    except psycopg2.Error as e:
        print("Error al conectar a la base de datos:", e)
        return None