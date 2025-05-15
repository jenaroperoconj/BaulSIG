import tkinter as tk
from core.utils import centrar_ventana, aplicar_tema, cambiar_tema
from core.colores import colores
from core.auth import verificar_login

modo_oscuro = False  # estado global 

def iniciar_login(modo=None):
    global modo_oscuro
    modo_oscuro = modo if modo is not None else True
    tema = "oscuro" if modo_oscuro else "claro"

    ventana = tk.Tk()
    ventana.title("Inicio de Sesión")
    centrar_ventana(ventana, 900, 400)
    ventana.configure(bg=colores[tema]["bg"])

    # Botón para cambiar tema
    btn_tema = tk.Button(
        ventana,
        text="☀️" if modo_oscuro else "🌙",
        command=lambda: actualizar_tema(ventana, btn_tema),
        bg=colores[tema]["bg"],
        fg=colores[tema]["fg"],
        borderwidth=0,
        font=("Arial", 12),
        cursor="hand2"
    )
    btn_tema.place(relx=0.95, rely=0.02, anchor="ne")

    # Formulario
    frame = tk.Frame(ventana, bg=colores[tema]["bg"])
    frame.pack(expand=True)

    tk.Label(frame, text="Iniciar Sesión", font=("Arial", 16, "bold"), bg=colores[tema]["bg"], fg=colores[tema]["fg"]).pack(pady=10)

    tk.Label(frame, text="Usuario:", bg=colores[tema]["bg"], fg=colores[tema]["fg"]).pack()
    entry_usuario = tk.Entry(frame, font=("Arial", 11), width=30, bg=colores[tema]["entry_bg"], fg=colores[tema]["entry_fg"])
    entry_usuario.pack(pady=5)

    tk.Label(frame, text="Contraseña:", bg=colores[tema]["bg"], fg=colores[tema]["fg"]).pack()
    entry_contrasena = tk.Entry(frame, show="*", font=("Arial", 11), width=30, bg=colores[tema]["entry_bg"], fg=colores[tema]["entry_fg"])
    entry_contrasena.pack(pady=5)
    ventana.bind("<Return>", lambda event: verificar_login(entry_usuario.get(), entry_contrasena.get(), ventana, modo_oscuro))
    # Botón de ingresar
    tk.Button(
        frame,
        text="Ingresar",
        bg=colores[tema]["button_bg"],
        fg=colores[tema]["button_fg"],
        font=("Arial", 10),
        width=20,
        command=lambda: verificar_login(entry_usuario.get(), entry_contrasena.get(), ventana, modo_oscuro)
    ).pack(pady=10)

    aplicar_tema(ventana, tema)
    ventana.mainloop()


def actualizar_tema(ventana, boton):
    global modo_oscuro
    modo_oscuro = cambiar_tema(ventana, boton, modo_oscuro)
