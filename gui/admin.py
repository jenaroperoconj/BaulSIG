import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil
import platform
import subprocess
from db.conexion import conectar
from core.utils import centrar_ventana, aplicar_tema, cambiar_tema
from core.colores import colores
from gui.admin_logs import mostrar_logs

modo_oscuro = True
ventana_logs_abierta = None
UPLOAD_DIR = "uploads"

def abrir_menu_admin(admin_id, passed_modo_oscuro):
    global modo_oscuro
    modo_oscuro = passed_modo_oscuro
    tema = "oscuro" if modo_oscuro else "claro"

    ventana = tk.Tk()
    ventana.title("Panel del Administrador")
    centrar_ventana(ventana, 1200, 750)
    ventana.configure(bg=colores[tema]["bg"])

    frame_contenido = tk.Frame(ventana, bg=colores[tema]["bg"])
    frame_contenido.pack(expand=True, fill="both", padx=20, pady=20)

    tk.Label(frame_contenido, text="Panel del Administrador", font=("Arial", 18, "bold"),
             bg=colores[tema]["bg"], fg=colores[tema]["fg"]).pack(pady=10)

    lista_archivos = tk.Listbox(frame_contenido, width=100, height=15, font=("Consolas", 10),
                                 bg=colores[tema]["listbox_bg"], fg=colores[tema]["listbox_fg"])
    lista_archivos.pack(pady=10)

    frame_botones = tk.Frame(frame_contenido, bg=colores[tema]["bg"])
    frame_botones.pack(pady=10)

    botones = [
        ("Subir archivo", lambda: subir_archivo(admin_id)),
        ("Actualizar lista", lambda: cargar_lista_archivos(lista_archivos)),
        ("Abrir archivo", lambda: abrir_archivo(lista_archivos)),
        ("Descargar archivo", lambda: descargar_archivo(lista_archivos)),
        ("Eliminar archivo", lambda: eliminar_archivo(admin_id, lista_archivos)),
        ("Ver logs del sistema", lambda: mostrar_logs(modo_oscuro)),
        ("Cerrar sesión", lambda: cerrar_sesion(ventana))
    ]

    for texto, comando in botones:
        tk.Button(frame_botones, text=texto, command=comando, width=25, font=("Arial", 10),
                  bg=colores[tema]["button_bg"], fg=colores[tema]["button_fg"]).pack(pady=3)

    btn_tema = tk.Button(
        ventana,
        text="☀️" if modo_oscuro else "🌙",
        command=lambda: cambiar_modo(ventana, btn_tema),
        borderwidth=0,
        font=("Arial", 12),
        cursor="hand2",
        bg=colores[tema]["bg"],
        fg=colores[tema]["fg"]
    )
    btn_tema.place(relx=0.985, rely=0.015, anchor="ne")

    cargar_lista_archivos(lista_archivos)
    aplicar_tema(ventana, tema)
    ventana.mainloop()

# Funciones de acción ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓

def cambiar_modo(ventana, boton):
    global modo_oscuro
    modo_oscuro = cambiar_tema(ventana, boton, modo_oscuro)

def cerrar_sesion(ventana_actual):
    global ventana_logs_abierta
    from gui.login import iniciar_login
    tema_actual = modo_oscuro
    ventana_actual.destroy()
    if ventana_logs_abierta and ventana_logs_abierta.winfo_exists():
        ventana_logs_abierta.destroy()
    ventana_logs_abierta = None
    iniciar_login(tema_actual)


def subir_archivo(admin_id):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    filepath = filedialog.askopenfilename()
    if not filepath:
        return
    try:
        nombre_archivo = os.path.basename(filepath)
        destino = os.path.join(UPLOAD_DIR, nombre_archivo)
        shutil.copy(filepath, destino)

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO archivos (nombre_archivo, ruta, subido_por)
            VALUES (%s, %s, %s)
        """, (nombre_archivo, destino, admin_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Éxito", f"Archivo '{nombre_archivo}' subido correctamente.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo subir el archivo: {e}")

def cargar_lista_archivos(lista):
    lista.delete(0, tk.END)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_archivo, fecha_subida FROM archivos ORDER BY fecha_subida DESC")
    archivos = cursor.fetchall()
    conn.close()
    for archivo in archivos:
        nombre, fecha = archivo
        lista.insert(tk.END, f"{nombre} - {fecha.strftime('%Y-%m-%d %H:%M')}")

def abrir_archivo(lista):
    seleccion = lista.curselection()
    if not seleccion:
        messagebox.showwarning("Atención", "Debes seleccionar un archivo.")
        return
    nombre_archivo = lista.get(seleccion[0]).split(" - ")[0]
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT ruta FROM archivos WHERE nombre_archivo = %s", (nombre_archivo,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        ruta = resultado[0]
        if platform.system() == 'Windows':
            os.startfile(ruta)
        elif platform.system() == 'Darwin':
            subprocess.call(['open', ruta])
        else:
            subprocess.call(['xdg-open', ruta])

def descargar_archivo(lista):
    seleccion = lista.curselection()
    if not seleccion:
        messagebox.showwarning("Atención", "Debes seleccionar un archivo.")
        return
    nombre_archivo = lista.get(seleccion[0]).split(" - ")[0]
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT ruta FROM archivos WHERE nombre_archivo = %s", (nombre_archivo,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        origen = resultado[0]
        destino_dir = filedialog.askdirectory(title="Selecciona una carpeta para guardar el archivo")
        if destino_dir:
            destino = os.path.join(destino_dir, nombre_archivo)
            shutil.copy(origen, destino)
            messagebox.showinfo("Éxito", f"Archivo guardado en:\n{destino}")

def eliminar_archivo(admin_id, lista):
    seleccion = lista.curselection()
    if not seleccion:
        messagebox.showwarning("Atención", "Debes seleccionar un archivo.")
        return
    nombre_archivo = lista.get(seleccion[0]).split(" - ")[0]
    if not messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre_archivo}'?"):
        return
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ruta FROM archivos WHERE nombre_archivo = %s", (nombre_archivo,))
    resultado = cursor.fetchone()
    if resultado:
        archivo_id, ruta = resultado
        if os.path.exists(ruta):
            os.remove(ruta)
        cursor.execute("DELETE FROM archivos WHERE id = %s", (archivo_id,))
        cursor.execute("""
            INSERT INTO logs (usuario_id, archivo_id, nombre_archivo, accion, motivo)
            VALUES (%s, %s, %s, %s, %s)
        """, (admin_id, archivo_id, nombre_archivo, "eliminación", "Eliminación manual por administrador"))
        conn.commit()
    conn.close()
    cargar_lista_archivos(lista)
    messagebox.showinfo("Éxito", f"Archivo '{nombre_archivo}' eliminado.")