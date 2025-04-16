from tkinter import messagebox
from db.conexion import conectar
from gui.admin import abrir_menu_admin
from gui.usuario import abrir_menu_usuario

def verificar_login(usuario, contrasena, ventana_login, modo_oscuro):
    conn = conectar()
    if not conn:
        messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, rol FROM usuarios WHERE nombre=%s AND contrasena=%s", (usuario, contrasena))
        resultado = cursor.fetchone()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo verificar el usuario: {e}")
        return

    if resultado:
        user_id, rol = resultado
        ventana_login.destroy()
        if rol == 'admin':
            abrir_menu_admin(user_id, modo_oscuro)
        else:
            abrir_menu_usuario(user_id, usuario, modo_oscuro)
    else:
        messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.")
