import tkinter as tk
import csv
from tkinter import filedialog, messagebox, ttk
from db.conexion import conectar
from core.utils import centrar_ventana, aplicar_tema
from core.colores import colores

ventana_logs_abierta = None

def mostrar_logs(modo_oscuro):
    global ventana_logs_abierta
    print("Abriendo logs...")
    if ventana_logs_abierta and ventana_logs_abierta.winfo_exists():
        ventana_logs_abierta.lift()
        return

    tema = "oscuro" if modo_oscuro else "claro"
    ventana_logs = tk.Toplevel()
    ventana_logs_abierta = ventana_logs
    ventana_logs.title("Registros del sistema")
    centrar_ventana(ventana_logs, 1100, 600)
    ventana_logs.configure(bg=colores[tema]["bg"])

    tk.Label(ventana_logs, text="Historial de acciones", font=("Arial", 18, "bold"), bg=colores[tema]["bg"], fg=colores[tema]["fg"]).pack(pady=10)

    frame_filtros = tk.Frame(ventana_logs, bg=colores[tema]["bg"])
    frame_filtros.pack(pady=10)

    tk.Label(frame_filtros, text="Usuario:", bg=colores[tema]["bg"], fg=colores[tema]["fg"]).grid(row=0, column=0, padx=5)
    entry_usuario = tk.Entry(frame_filtros, bg=colores[tema]["entry_bg"], fg=colores[tema]["entry_fg"])
    entry_usuario.grid(row=0, column=1, padx=5)

    tk.Label(frame_filtros, text="Fecha (DD/MM/YYYY):", bg=colores[tema]["bg"], fg=colores[tema]["fg"]).grid(row=0, column=2, padx=5)
    entry_fecha = tk.Entry(frame_filtros, bg=colores[tema]["entry_bg"], fg=colores[tema]["entry_fg"])
    entry_fecha.grid(row=0, column=3, padx=5)

    tk.Label(frame_filtros, text="Acción:", bg=colores[tema]["bg"], fg=colores[tema]["fg"]).grid(row=0, column=4, padx=5)
    combo_accion = ttk.Combobox(frame_filtros, state="readonly")
    combo_accion['values'] = ("Todos", "descarga", "visualización", "eliminación", "modificación")
    combo_accion.set("Todos")
    combo_accion.grid(row=0, column=5, padx=5)

    columnas = ("Fecha", "Hora", "Archivo", "Función", "Responsable", "Motivo")
    tabla_logs = ttk.Treeview(ventana_logs, columns=columnas, show="headings", height=20)
    estilo = ttk.Style()
    estilo.configure("Treeview.Heading", font=("Arial", 10, "bold"))
    estilo.configure("Treeview", font=("Consolas", 10))
    for col in columnas:
        tabla_logs.heading(col, text=col)
        tabla_logs.column(col, anchor="center", width=150 if col != "Motivo" else 300)
    tabla_logs.pack(padx=20, pady=10, fill="both", expand=True)

    def aplicar_filtro():
        cargar_logs(tabla_logs, entry_usuario.get(), entry_fecha.get(), combo_accion.get())

    def quitar_filtros():
        entry_usuario.delete(0, tk.END)
        entry_fecha.delete(0, tk.END)
        combo_accion.set("Todos")
        aplicar_filtro()

    def exportar_csv():
        if not tabla_logs.get_children():
            messagebox.showinfo("Sin datos", "No hay registros para exportar.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], title="Guardar como")
        if not ruta:
            return
        try:
            with open(ruta, mode="w", newline="", encoding="utf-8-sig") as archivo_csv:
                writer = csv.writer(archivo_csv, delimiter=';')
                writer.writerow(["Fecha", "Hora", "Archivo", "Función", "Responsable", "Motivo"])
                for row_id in tabla_logs.get_children():
                    writer.writerow(tabla_logs.item(row_id)["values"])
            messagebox.showinfo("Exportación exitosa", f"Archivo exportado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar el archivo: {e}")

    tk.Button(frame_filtros, text="Filtrar", command=aplicar_filtro, width=15, bg=colores[tema]["button_bg"], fg=colores[tema]["button_fg"], font=("Arial", 10)).grid(row=0, column=6, padx=10)
    tk.Button(frame_filtros, text="Quitar filtros", command=quitar_filtros, width=15, bg="#7f8c8d", fg="white", font=("Arial", 10)).grid(row=0, column=7, padx=5)
    tk.Button(ventana_logs, text="Exportar a CSV", command=exportar_csv, width=25, bg="#27ae60", fg="white", font=("Arial", 10)).pack(pady=10)

    aplicar_tema(ventana_logs, tema)
    aplicar_filtro()


def cargar_logs(tabla_logs, usuario_filtro, fecha_filtro, accion_filtro):
    for row in tabla_logs.get_children():
        tabla_logs.delete(row)

    query = """
        SELECT l.fecha_hora, 
               COALESCE(a.nombre_archivo, l.nombre_archivo) AS nombre_archivo, 
               l.accion, u.nombre, l.motivo
        FROM logs l
        JOIN usuarios u ON l.usuario_id = u.id
        LEFT JOIN archivos a ON l.archivo_id = a.id
        WHERE 1=1
    """
    params = []

    if usuario_filtro:
        query += " AND u.nombre ILIKE %s"
        params.append(f"%{usuario_filtro}%")
    if fecha_filtro:
        query += " AND TO_CHAR(l.fecha_hora, 'DD/MM/YYYY') LIKE %s"
        params.append(f"%{fecha_filtro}%")
    if accion_filtro and accion_filtro != "Todos":
        query += " AND l.accion = %s"
        params.append(accion_filtro.lower())

    query += " ORDER BY l.fecha_hora DESC"

    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        registros = cursor.fetchall()
        conn.close()

        for fila in registros:
            fecha_hora, archivo, accion, usuario, motivo = fila
            tabla_logs.insert("", "end", values=(
                fecha_hora.strftime("%d/%m/%Y"),
                fecha_hora.strftime("%H:%M"),
                archivo,
                accion.upper(),
                usuario,
                motivo
            ))
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el log: {e}")