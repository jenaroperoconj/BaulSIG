import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ARCHIVOS_COMPARTIDOS_DIR = "//DESKTOP-PPFK9U5/Users/jenar/OneDrive/Escritorio/CARPETALAN"

DATABASE_CONFIG = {
    'dbname': "sistema_archivos",
    'user': "postgres", 
    'password': "sig2025",
    'host': "localhost",
    'port': "5433"
}

def get_database_config():
    return DATABASE_CONFIG.copy()