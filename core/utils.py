import tkinter as tk
from core.colores import colores

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

def aplicar_tema(widget, tema):
    config = colores[tema]
    try:
        widget.configure(bg=config["bg"])
    except:
        pass
    for hijo in widget.winfo_children():
        try:
            if isinstance(hijo, (tk.Label, tk.Button, tk.Frame, tk.Toplevel)):
                hijo.configure(bg=config["bg"])
            if isinstance(hijo, tk.Label):
                hijo.configure(fg=config["fg"])
            if isinstance(hijo, tk.Button):
                hijo.configure(
                    bg=config["button_bg"], fg=config["button_fg"],
                    activebackground=config["highlight"], activeforeground=config["fg"]
                )
            if isinstance(hijo, tk.Entry):
                hijo.configure(bg=config["entry_bg"], fg=config["entry_fg"])
            if isinstance(hijo, tk.Listbox):
                hijo.configure(bg=config["listbox_bg"], fg=config["listbox_fg"])
        except:
            pass
        aplicar_tema(hijo, tema)

def cambiar_tema(ventana, boton, modo_oscuro):
    nuevo_modo = not modo_oscuro
    tema = "oscuro" if nuevo_modo else "claro"
    boton.config(text="☀️" if nuevo_modo else "🌙")
    boton.configure(bg=colores[tema]["bg"], fg=colores[tema]["fg"])
    aplicar_tema(ventana, tema)
    return nuevo_modo
