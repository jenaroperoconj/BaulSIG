import tkinter as tk
from core.utils import centrar_ventana
from core.auth import verificar_login
from core.ui_config import (
    configurar_ventana_principal, obtener_fuente, crear_boton_estilizado,
    COLORES, ESPACIOS
)

modo_oscuro = False  # estado global 

def iniciar_login(modo=None):
    """
    Inicializa y muestra la ventana de inicio de sesión del sistema.
    Permite al usuario ingresar sus credenciales y acceder según su perfil.
    """
    global modo_oscuro
    modo_oscuro = False
    tema = "oscuro" if modo_oscuro else "claro"

    ventana = tk.Tk()
    ventana.title("🔐 BaulSIG - Inicio de Sesión")
    
    # Aplica la configuración visual centralizada
    configurar_ventana_principal(ventana, 'login')

    # Frame principal con padding para dar aspecto cuadrado y espacioso
    frame = tk.Frame(ventana, bg=COLORES['fondo_panel'], relief='raised', bd=2, padx=40, pady=40)
    frame.pack(expand=True, padx=ESPACIOS['padding_ventana'], pady=ESPACIOS['padding_ventana'])

    # Título principal
    tk.Label(frame, 
             text="🔐 Iniciar Sesión", 
             font=obtener_fuente('login_titulo'), 
             bg=COLORES['fondo_panel'], 
             fg=COLORES['texto_principal']).pack(pady=(20, 30))

    # Campo de usuario
    tk.Label(frame, 
             text="Usuario:", 
             font=obtener_fuente('login_label'), 
             bg=COLORES['fondo_panel'], 
             fg=COLORES['texto_principal']).pack(pady=(0, 5))
    
    entry_usuario = tk.Entry(frame, 
                            font=obtener_fuente('login_entrada'), 
                            width=25, 
                            relief='solid', 
                            bd=1)
    entry_usuario.pack(pady=(0, 15), ipady=8)

    # Campo de contraseña  
    tk.Label(frame, 
             text="Contraseña:", 
             font=obtener_fuente('login_label'), 
             bg=COLORES['fondo_panel'], 
             fg=COLORES['texto_principal']).pack(pady=(0, 5))
    
    entry_contrasena = tk.Entry(frame, 
                               show="*", 
                               font=obtener_fuente('login_entrada'), 
                               width=25,
                               relief='solid', 
                               bd=1)
    entry_contrasena.pack(pady=(0, 25), ipady=8)
    
    # Permite iniciar sesión presionando Enter
    ventana.bind("<Return>", lambda event: verificar_login(entry_usuario.get(), entry_contrasena.get(), ventana, modo_oscuro))
    # Botón de ingresar con estilo
    crear_boton_estilizado(
        frame,
        "🚀 Ingresar",
        comando=lambda: verificar_login(entry_usuario.get(), entry_contrasena.get(), ventana, modo_oscuro),
        tipo='exito'
    ).pack(pady=20, ipady=5, ipadx=20)

    ventana.mainloop()
