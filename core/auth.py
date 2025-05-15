from tkinter import messagebox
from db.conexion import conectar

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
            from gui.admin import abrir_menu_admin
            abrir_menu_admin(user_id, usuario, modo_oscuro)
        else:
            from gui.usuario import abrir_menu_usuario
            abrir_menu_usuario(user_id, usuario, modo_oscuro)
    else:
        messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.")