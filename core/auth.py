from tkinter import messagebox
from db.db_manager import conectar

def verificar_login(usuario, contrasena, ventana_login, modo_oscuro):
    """
    Verifica el login usando hash seguro de PostgreSQL.
    Utiliza la función crypt() para validación segura de contraseñas.
    """
    conn = conectar()
    if not conn:
        messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
        return

    try:
        cursor = conn.cursor()
        # Usar PostgreSQL crypt() para verificación segura
        cursor.execute("""
            SELECT id, rol 
            FROM usuarios 
            WHERE nombre = %s 
            AND contrasena = crypt(%s, contrasena)
        """, (usuario, contrasena))
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

def crear_usuario_seguro(nombre, contrasena, rol='usuario'):
    """
    Crea un nuevo usuario con contraseña hasheada usando PostgreSQL crypt().
    
    Args:
        nombre: Nombre de usuario
        contrasena: Contraseña en texto plano (será hasheada)
        rol: Rol del usuario ('admin' o 'usuario')
    
    Returns:
        bool: True si el usuario fue creado exitosamente
    """
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        
        # Verificar si el usuario ya existe
        cursor.execute("SELECT id FROM usuarios WHERE nombre = %s", (nombre,))
        if cursor.fetchone():
            messagebox.showerror("Error", "El usuario ya existe.")
            return False
        
        # Crear usuario con contraseña hasheada usando crypt()
        cursor.execute("""
            INSERT INTO usuarios (nombre, contrasena, rol) 
            VALUES (%s, crypt(%s, gen_salt('bf')), %s)
        """, (nombre, contrasena, rol))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo crear el usuario: {e}")
        conn.rollback()
        conn.close()
        return False

def cambiar_contrasena_segura(usuario_id, nueva_contrasena):
    """
    Cambia la contraseña de un usuario usando hash seguro.
    
    Args:
        usuario_id: ID del usuario
        nueva_contrasena: Nueva contraseña en texto plano
    
    Returns:
        bool: True si la contraseña fue cambiada exitosamente
    """
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        
        # Actualizar contraseña con hash seguro
        cursor.execute("""
            UPDATE usuarios 
            SET contrasena = crypt(%s, gen_salt('bf'))
            WHERE id = %s
        """, (nueva_contrasena, usuario_id))
        
        if cursor.rowcount == 0:
            messagebox.showerror("Error", "Usuario no encontrado.")
            return False
            
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cambiar la contraseña: {e}")
        conn.rollback()
        conn.close()
        return False