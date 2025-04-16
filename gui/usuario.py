import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
from pdf2image import convert_from_path
import os
import shutil
from db.conexion import conectar
from core.colores import colores
from core.utils import centrar_ventana, aplicar_tema, cambiar_tema
from core.config import POPLER_PATH


modo_oscuro = True

def abrir_menu_usuario(user_id, username, passed_modo_oscuro):
    global modo_oscuro
    modo_oscuro = passed_modo_oscuro
    tema = "oscuro" if modo_oscuro else "claro"

    ventana = tk.Tk()
    ventana.title("Panel del Usuario")
    centrar_ventana(ventana, 1000, 650)
    ventana.configure(bg=colores[tema]["bg"])

    frame_superior = tk.Frame(ventana, bg=colores[tema]["bg"])
    frame_superior.pack(fill="x", pady=(10, 0), padx=20)

    tk.Label(frame_superior, text=f"Bienvenido, {username}", font=("Arial", 18, "bold"),
             bg=colores[tema]["bg"], fg=colores[tema]["fg"]).pack(side="left")

    btn_tema = tk.Button(
        frame_superior,
        text="☀️" if modo_oscuro else "🌙",
        command=lambda: cambiar_modo(ventana, btn_tema),
        borderwidth=0,
        font=("Arial", 12),
        cursor="hand2",
        bg=colores[tema]["bg"],
        fg=colores[tema]["fg"]
    )
    btn_tema.pack(side="right")

    frame_contenido = tk.Frame(ventana, bg=colores[tema]["bg"])
    frame_contenido.pack(expand=True, fill="both", padx=20, pady=20)

    lista_archivos = tk.Listbox(frame_contenido, width=100, height=15, font=("Consolas", 10),
                                 bg=colores[tema]["listbox_bg"], fg=colores[tema]["listbox_fg"])
    lista_archivos.pack(pady=10)

    frame_botones = tk.Frame(frame_contenido, bg=colores[tema]["bg"])
    frame_botones.pack(pady=10)

    botones = [
        ("Actualizar lista", lambda: cargar_lista(lista_archivos)),
        ("Visualizar archivo", lambda: visualizar_archivo_seguro(user_id, lista_archivos)),
        ("Descargar archivo", lambda: descargar_con_motivo(user_id, lista_archivos)),
        ("Cerrar sesión", lambda: cerrar_sesion(ventana))
    ]

    for texto, comando in botones:
        tk.Button(frame_botones, text=texto, command=comando, width=25, font=("Arial", 10),
                  bg=colores[tema]["button_bg"], fg=colores[tema]["button_fg"]).pack(pady=3)

    cargar_lista(lista_archivos)
    aplicar_tema(ventana, tema)
    ventana.mainloop()


# Funciones auxiliares ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓

def cambiar_modo(ventana, boton):
    global modo_oscuro
    modo_oscuro = cambiar_tema(ventana, boton, modo_oscuro)

def cerrar_sesion(ventana_actual):
    global modo_oscuro
    from gui.login import iniciar_login  # << aquí dentro
    tema_actual = modo_oscuro
    ventana_actual.destroy()
    iniciar_login(tema_actual)

def cargar_lista(lista):
    lista.delete(0, tk.END)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_archivo, fecha_subida FROM archivos ORDER BY fecha_subida DESC")
    archivos = cursor.fetchall()
    conn.close()
    for archivo in archivos:
        nombre, fecha = archivo
        lista.insert(tk.END, f"{nombre} - {fecha.strftime('%Y-%m-%d %H:%M')}")

def descargar_con_motivo(user_id, lista):
    seleccion = lista.curselection()
    if not seleccion:
        messagebox.showwarning("Atención", "Debes seleccionar un archivo.")
        return
    nombre_archivo = lista.get(seleccion[0]).split(" - ")[0]
    motivo = simpledialog.askstring("Motivo", "¿Por qué deseas descargar este archivo?")
    if not motivo:
        messagebox.showinfo("Cancelado", "Debes ingresar un motivo.")
        return
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ruta FROM archivos WHERE nombre_archivo = %s", (nombre_archivo,))
    resultado = cursor.fetchone()
    if not resultado:
        messagebox.showerror("Error", "Archivo no encontrado.")
        return
    archivo_id, origen = resultado
    if not os.path.exists(origen):
        messagebox.showerror("Error", "Archivo no existe físicamente.")
        return
    destino_dir = filedialog.askdirectory(title="Selecciona carpeta de destino")
    if not destino_dir:
        return
    shutil.copy(origen, os.path.join(destino_dir, nombre_archivo))
    cursor.execute("""
        INSERT INTO logs (usuario_id, archivo_id, nombre_archivo, accion, motivo)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, archivo_id, nombre_archivo, "descarga", motivo))
    conn.commit()
    conn.close()
    messagebox.showinfo("Éxito", "Archivo descargado correctamente.")

def visualizar_archivo_seguro(user_id, lista):
    seleccion = lista.curselection()
    if not seleccion:
        messagebox.showwarning("Atención", "Debes seleccionar un archivo.")
        return
    nombre_archivo = lista.get(seleccion[0]).split(" - ")[0]
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ruta FROM archivos WHERE nombre_archivo = %s", (nombre_archivo,))
    resultado = cursor.fetchone()
    if not resultado:
        messagebox.showerror("Error", "Archivo no encontrado.")
        return
    archivo_id, ruta = resultado
    ext = os.path.splitext(ruta)[1].lower()

    ventana_preview = tk.Toplevel()
    ventana_preview.title(f"Visualizando: {nombre_archivo}")
    centrar_ventana(ventana_preview, 800, 600)

    if ext == ".pdf":
        paginas = convert_from_path(ruta, dpi=100, poppler_path=POPLER_PATH)
        img = paginas[0].resize((750, 550))
    elif ext in [".jpg", ".jpeg", ".png"]:
        img = Image.open(ruta).resize((750, 550))
    else:
        messagebox.showinfo("No compatible", "Solo se pueden visualizar PDF o imágenes.")
        ventana_preview.destroy()
        return

    img_tk = ImageTk.PhotoImage(img)
    lbl_img = tk.Label(ventana_preview, image=img_tk)
    lbl_img.image = img_tk
    lbl_img.pack(padx=10, pady=10)

    # Registro de visualización
    try:
        cursor.execute("""
            INSERT INTO logs (usuario_id, archivo_id, nombre_archivo, accion, motivo)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, archivo_id, nombre_archivo, "visualización", "Vista segura (sin descarga)"))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar visualización: {e}")
    conn.close()
