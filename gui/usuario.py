import os
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from db.archivos import registrar_archivo, registrar_log, _buscar_archivo_id, actualizar_nombre_archivo, actualizar_ruta_archivo
from gui.login import iniciar_login
from tkinterdnd2 import DND_FILES, TkinterDnD

if __name__ == "__main__":
    from gui.login import iniciar_login
    iniciar_login()

def abrir_menu_usuario(user_id, username, modo_oscuro):
    root = TkinterDnD.Tk()
    app = ExploradorAdmin(root, modo_oscuro=modo_oscuro, es_admin=False)
    app.user_id = user_id
    root.mainloop()

class ExploradorAdmin:
    def __init__(self, master, modo_oscuro=False, es_admin=False, user_id=None):
        self.user_id = user_id
        self.es_admin = es_admin
        self.orden_columna = None
        self.orden_descendente = False
        self.master = master
        self.modo_oscuro = modo_oscuro
        self.master.title("Explorador de Archivos - Administrador")
        self.master.geometry("1200x700")
        self.master.configure(bg="#1e1e1e")

        self.historial = []
        self.historial_pos = -1
        self.BASE_DIR = Path("uploads")
        self.ruta_actual = self.BASE_DIR

        if not self.BASE_DIR.exists():
            self.BASE_DIR.mkdir()

        self._crear_widgets()
        self._aplicar_estilo()
        self._poblar_arbol(self.BASE_DIR)
        self._navegar_a(self.BASE_DIR)


    def _cerrar_sesion(self):
        self.master.destroy()
        iniciar_login(modo=self.modo_oscuro)
    
    def _limpiar_emoji(self, texto):
        if texto.startswith(("📁", "📄", "❓")):
            return texto[2:].strip()
        return texto
    
    def _crear_widgets(self):
        barra_sup = tk.Frame(self.master, bg="#333333", padx=12, pady=10, bd=2, relief="groove")
        btn_mis_solicitudes = tk.Button(barra_sup, text="📄 Mis solicitudes", command=self._mostrar_mis_solicitudes)
        btn_mis_solicitudes.pack(side="left", padx=(0, 10))
        # Contenedor para búsqueda y cerrar sesión
        panel_derecho = tk.Frame(barra_sup, bg="#333333")
        panel_derecho.pack(side="right")

        # Botón cerrar sesión
        btn_logout = tk.Button(panel_derecho, text="🔒 Cerrar sesión", command=self._cerrar_sesion,
                            bg="#aa3333", fg="white", font=("Segoe UI", 9, "bold"))
        btn_logout.pack(side="right", padx=(5, 0))

        # Lupa y entrada de búsqueda
        label_lupa = tk.Label(panel_derecho, text="🔍", bg="#333333", fg="white", font=("Segoe UI", 10))
        label_lupa.pack(side="left", padx=(0, 0), pady=2)

        self.entrada_busqueda = tk.Entry(panel_derecho, width=25)
        self.entrada_busqueda.pack(side="left", padx=(0, 5), pady=2)
        self.entrada_busqueda.insert(0, "Buscar...")
        self.entrada_busqueda.bind("<FocusIn>", lambda e: self._limpiar_placeholder_busqueda())
        self.entrada_busqueda.bind("<FocusOut>", lambda e: self._restaurar_placeholder_busqueda())
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self._actualizar_tabla(self.ruta_actual))
        barra_sup.pack(fill="x", padx=10, pady=5)

        tk.Button(barra_sup, text="←", command=lambda: self._navegar_historial(-1)).pack(side="left")
        tk.Button(barra_sup, text="→", command=lambda: self._navegar_historial(1)).pack(side="left")

        self.ruta_label = tk.Frame(barra_sup, bg="#2d2d2d")
        self.ruta_label.pack(side="left", padx=10)

        contenedor = tk.Frame(self.master)
        contenedor.pack(fill="both", expand=True)

        self.panel_izq = tk.Frame(contenedor, width=300, bg="#1e1e1e")
        self.panel_izq.pack(side="left", fill="y")

        # Encabezado para el árbol
        tk.Label(self.panel_izq, text="📂 Directorio de Carpetas", bg="#1e1e1e", fg="#d4d4d4",
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=5, pady=(5, 0))

        self.arbol = ttk.Treeview(self.panel_izq)
        self.arbol.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self.panel_der = tk.Frame(contenedor, bg="#1e1e1e")
        self.panel_der.pack(side="right", fill="both", expand=True)

        columnas = ("Nombre", "Tipo", "Tamaño", "Fecha modificación")
        self.tabla = ttk.Treeview(self.panel_der, columns=columnas, show="headings", selectmode="browse")

        
        for col in columnas:
            self.tabla.heading(col, text=col, command=lambda c=col: self._ordenar_por_columna(c))
            self.tabla.column(col, anchor="w")
        
        self.tabla.pack(fill="both", expand=True, padx=10, pady=10)

        self.arbol.bind("<<TreeviewSelect>>", self._al_seleccionar_carpeta)
        self.tabla.bind("<Double-1>", self._abrir_item_tabla)
        self.arbol.bind("<Button-3>", self._menu_contexto_arbol)
        self.tabla.bind("<Button-3>", self._menu_contexto_tabla)

    def _mostrar_mis_solicitudes(self):
        import psycopg2
        ventana = tk.Toplevel(self.master)
        ventana.title("Mis solicitudes de descarga")
        ventana.geometry("900x400")

        columnas = ("Archivo", "Motivo", "Estado", "Fecha solicitud", "Acción")
        tabla = ttk.Treeview(ventana, columns=columnas, show="headings", height=18)
        ventana.geometry("1350x520")
        for col in columnas:
            tabla.heading(col, text=col)
            tabla.column(col, anchor="center")
        tabla.tag_configure("aprobado", background="#d4edda", foreground="#155724")      # verde más fuerte
        tabla.tag_configure("pendiente", background="#fff3cd", foreground="#856404")     # amarillo fuerte
        tabla.tag_configure("rechazado", background="#f8d7da", foreground="#721c24")     # rojo fuerte
        tabla.tag_configure("descargado", background="#e2e3e5", foreground="#383d41")    # gris medio
        tabla.pack(fill="both", expand=True, padx=10, pady=10)
        tabla.bind("<Double-1>", lambda e: _accion_descarga(e, tabla))

        def _accion_descarga(event, tabla):
                region = tabla.identify("region", event.x, event.y)
                col = tabla.identify_column(event.x)
                if region == "cell" and col == "#5":  # Columna Acción
                    item_id = tabla.identify_row(event.y)
                    if not item_id:
                        return
                    accion = tabla.item(item_id)["values"][4]
                    accion = str(accion).lower()
                    if "descargar" in accion:
                        descargar()
                    elif "modificar" in accion:
                        modificar_motivo()
                    else:
                        messagebox.showinfo("No disponible", "Esta acción no está disponible.")
        
        def modificar_motivo():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Selecciona", "Selecciona una solicitud para modificar.")
                return

            valores = tabla.item(item_id)["values"]
            motivo_actual = valores[1]

            nueva_ventana = tk.Toplevel(ventana)
            nueva_ventana.title("Modificar motivo")
            nueva_ventana.geometry("400x200")

            tk.Label(nueva_ventana, text="Motivo actual:", font=("Segoe UI", 10, "bold")).pack(pady=5)
            tk.Label(nueva_ventana, text=motivo_actual, wraplength=380, fg="gray").pack(pady=2)

            tk.Label(nueva_ventana, text="Nuevo motivo:", font=("Segoe UI", 10, "bold")).pack(pady=5)
            entry = tk.Entry(nueva_ventana, width=40)
            entry.pack(pady=5)

            def guardar_motivo():
                nuevo_motivo = entry.get().strip()
                if not nuevo_motivo:
                    messagebox.showerror("Error", "Debes ingresar un nuevo motivo.")
                    return

                try:
                    conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
                    cur = conn.cursor()
                    # Guardar motivo anterior en historial
                    cur.execute("""
                        INSERT INTO historial_motivos (solicitud_id, motivo, fecha)
                        SELECT id, motivo, NOW() FROM solicitudes_descarga WHERE id = %s
                    """, (item_id,))
                    # Actualizar nuevo motivo
                    cur.execute("""
                        UPDATE solicitudes_descarga SET motivo = %s WHERE id = %s
                    """, (nuevo_motivo, item_id))
                    conn.commit()
                    conn.close()

                    messagebox.showinfo("Éxito", "Motivo actualizado.")
                    nueva_ventana.destroy()
                    cargar()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo modificar el motivo:\n{str(e)}")

            tk.Button(nueva_ventana, text="Guardar", command=guardar_motivo, bg="#5FB7B6", fg="white").pack(pady=10)

        def cargar():
            conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
            cur = conn.cursor()
            cur.execute("""
                SELECT sd.id, a.nombre_archivo, sd.motivo, sd.estado, sd.fecha_solicitud, a.ruta
                FROM solicitudes_descarga sd
                JOIN archivos a ON a.id = sd.archivo_id
                WHERE sd.usuario_id = %s
                ORDER BY sd.fecha_solicitud DESC
            """, (self.user_id,))
            resultados = cur.fetchall()
            conn.close()

            for row in tabla.get_children():
                tabla.delete(row)
            for fila in resultados:
                fecha_formateada = fila[4].strftime("%d/%m/%Y %H:%M")
                solicitud_id = fila[0]
                estado = fila[3]
                if estado == "aprobado":
                    accion = "📥 DESCARGAR"
                elif estado == "pendiente":
                    accion = "✏ Modificar motivo"
                else:
                    accion = "—"
                valores = (fila[1], fila[2], fila[3], fecha_formateada, accion)
                tabla.insert("", "end", iid=solicitud_id, values=valores, tags=(estado,))

        def descargar():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Selecciona", "Selecciona una solicitud aprobada para descargar.")
                return
            estado = tabla.item(item_id)["values"][2]
            if estado != "aprobado":
                messagebox.showerror("No permitido", "Solo puedes descargar archivos aprobados.")
                return

            conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
            cur = conn.cursor()
            cur.execute("""
                SELECT a.nombre_archivo, a.ruta
                FROM solicitudes_descarga sd
                JOIN archivos a ON a.id = sd.archivo_id
                WHERE sd.id = %s
            """, (item_id,))
            archivo = cur.fetchone()
            conn.close()

            if not archivo:
                messagebox.showerror("Error", "Archivo no encontrado.")
                return

            nombre, ruta_relativa = archivo
            archivo_path = self.BASE_DIR / ruta_relativa / nombre

            if not archivo_path.exists():
                messagebox.showerror("Error", "El archivo ya no está disponible.")
                return

            destino = filedialog.asksaveasfilename(defaultextension="", initialfile=nombre)
            if destino:
                try:
                    shutil.copy2(archivo_path, destino)
                    conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
                    cur = conn.cursor()
                    cur.execute("UPDATE solicitudes_descarga SET estado = 'descargado' WHERE id = %s", (item_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Descarga", "Archivo descargado correctamente.")
                    cargar()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo descargar: {str(e)}")

        btn_frame = tk.Frame(ventana)
        btn_frame.pack(pady=5)
        cargar()

    def _limpiar_placeholder_busqueda(self):
        if self.entrada_busqueda.get() == "Buscar...":
            self.entrada_busqueda.delete(0, "end")

    def _restaurar_placeholder_busqueda(self):
        if not self.entrada_busqueda.get():
            self.entrada_busqueda.insert(0, "Buscar...")

    def _aplicar_estilo(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#1e1e1e", foreground="#d4d4d4",
                        rowheight=25, fieldbackground="#1e1e1e",
                        font=('Segoe UI', 10))
        style.configure("Treeview.Heading",
                        background="#333333", foreground="white",
                        font=('Segoe UI', 10, 'bold'))
        style.map("Treeview",
                  background=[('selected', '#44475a')],
                  foreground=[('selected', '#f8f8f2')])
    
    def _ordenar_por_columna(self, columna):
        if self.orden_columna == columna:
            self.orden_descendente = not self.orden_descendente
        else:
            self.orden_columna = columna
            self.orden_descendente = False
        self._actualizar_tabla(self.ruta_actual)

    def _actualizar_barra_ruta(self, path: Path):
        for widget in self.ruta_label.winfo_children():
            widget.destroy()
        partes = list(path.parts)
        ruta = Path(partes[0])
        for parte in partes[1:]:
            ruta = ruta / parte
            b = tk.Button(self.ruta_label, text=parte, relief="flat", bg="#2d2d2d", fg="white",
                          command=lambda p=ruta: self._navegar_a(p))
            b.pack(side="left")
            tk.Label(self.ruta_label, text=">", bg="#2d2d2d", fg="#aaa").pack(side="left")

    def _navegar_historial(self, direccion):
        nueva_pos = self.historial_pos + direccion
        if 0 <= nueva_pos < len(self.historial):
            self.historial_pos = nueva_pos
            self._navegar_a(self.historial[self.historial_pos], agregar_historial=False)

    def _navegar_a(self, ruta: Path, agregar_historial=True):
        self.ruta_actual = ruta
        self._actualizar_barra_ruta(ruta)
        self._actualizar_tabla(ruta)
        if agregar_historial:
            self.historial = self.historial[:self.historial_pos + 1]
            self.historial.append(ruta)
            self.historial_pos += 1
    
    def _obtener_tipo_archivo(self, ruta: Path) -> str:
        if ruta.is_dir():
            return "Carpeta de archivos"
        elif ruta.is_file():
            ext = ruta.suffix.lower()
            if ext in [".zip"]:
                return "Archivo ZIP"
            elif ext in [".rar"]:
                return "Archivo WinRAR"
            elif ext in [".txt"]:
                return "Archivo de texto"
            elif ext in [".pdf"]:
                return "Archivo PDF"
            elif ext in [".jpg", ".jpeg", ".png"]:
                return "Imagen"
            elif ext in [".exe"]:
                return "Ejecutable"
            elif ext in [".doc", ".docx"]:
                return "Documento Word"
            elif ext in [".xls", ".xlsx"]:
                return "Documento Excel"
            else:
                return f"Archivo ({ext[1:]})" if ext else "Archivo"
        else:
            return "Desconocido"

    def _actualizar_tabla(self, ruta: Path):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        filtro = self.entrada_busqueda.get().strip().lower()
        if filtro == "buscar...":
            filtro = ""

        elementos = []
        try:
            items = ruta.rglob("*") if filtro else ruta.iterdir()
            for item in items:
                if not item.exists():
                    continue

                nombre_limpio = item.name.lower()
                if filtro and filtro not in nombre_limpio:
                    continue

                icono = "📶" if item.is_file() else "🗀"
                nombre = f"{icono} {item.name}"
                tipo = self._obtener_tipo_archivo(item)
                size_bytes = item.stat().st_size if item.is_file() else -1
                size_str = f"{size_bytes // 1024} KB" if item.is_file() else "-"
                fecha_mod = item.stat().st_mtime
                fecha_str = datetime.fromtimestamp(fecha_mod).strftime("%d/%m/%Y %H:%M")

                elementos.append((nombre, tipo, size_bytes, size_str, fecha_mod, fecha_str))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo acceder al directorio:\n{str(e)}")
            return

        # Ordenamiento por columna
        if self.orden_columna == "Nombre":
            elementos.sort(key=lambda x: x[0].lower(), reverse=self.orden_descendente)
        elif self.orden_columna == "Tipo":
            elementos.sort(key=lambda x: x[1].lower(), reverse=self.orden_descendente)
        elif self.orden_columna == "Tamaño":
            elementos.sort(key=lambda x: x[2], reverse=self.orden_descendente)
        elif self.orden_columna == "Fecha modificación":
            elementos.sort(key=lambda x: x[4], reverse=self.orden_descendente)
        else:
            elementos.sort(key=lambda x: x[0].lower())  # Por nombre A-Z por defecto

        for nombre, tipo, _, size_str, _, fecha_str in elementos:
            self.tabla.insert("", "end", values=(nombre, tipo, size_str, fecha_str))

    def _poblar_arbol(self, ruta: Path, nodo_padre=""):
        for item in sorted(ruta.iterdir(), key=lambda x: x.name.lower()):
            if item.is_dir():
                nombre = f"🗀 {item.name}"
                nodo = self.arbol.insert(nodo_padre, "end", text=nombre, open=False)
                self._poblar_arbol(item, nodo)

    def _obtener_ruta_completa(self, nodo):
        partes = []
        while nodo:
            texto = self.arbol.item(nodo)["text"]
            if texto.startswith("🗀 "):
                texto = texto[2:].strip()
            partes.insert(0, texto)
            nodo = self.arbol.parent(nodo)
        return self.BASE_DIR.joinpath(*partes)


    def _al_seleccionar_carpeta(self, event):
        seleccionado = self.arbol.selection()
        if seleccionado:
            ruta = self._obtener_ruta_completa(seleccionado[0])
            if ruta.exists():
                self._navegar_a(ruta)

    # ---------------- Menús Contextuales ----------------

    def _menu_contexto_arbol(self, event):
        item = self.tabla.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0)

        if item:
            nombre = self.tabla.item(item, "values")[0]
            if nombre.startswith(("📁", "📄", "🗀", "📶", "❓")):
                nombre = nombre[2:].strip()

            ruta = self.ruta_actual / nombre

            if ruta.is_file():
                menu.add_command(label="🔍 Abrir", command=lambda: os.startfile(ruta))
                menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
            elif ruta.is_dir():
                menu.add_command(label="🔍 Abrir", command=lambda: self._navegar_a(ruta))
                menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                if not any(ruta.iterdir()):
                    menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(self.ruta_actual))
            menu.add_command(label="⬆ Subir archivo", command=self._subir_archivo)


    def _menu_contexto_tabla(self, event):
        item = self.tabla.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0)

        if item:
            nombre = self.tabla.item(item, "values")[0]
            if nombre.startswith(("📁", "📄", "🗀", "📶", "❓")):
                nombre = nombre[2:].strip()

            ruta = self.ruta_actual / nombre

            if ruta.is_file():
                menu.add_command(label="🔍 Abrir", command=lambda: os.startfile(ruta))
                menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📥 Solicitar descarga", command=lambda: self._solicitar_descarga(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
            elif ruta.is_dir():
                menu.add_command(label="🔍 Abrir", command=lambda: self._navegar_a(ruta))
                menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(self.ruta_actual))
            menu.add_command(label="⬆ Subir archivo", command=self._subir_archivo)

        menu.tk_popup(event.x_root, event.y_root)


    # ---------------- Acciones ----------------

    def _renombrar(self, ruta, item, es_arbol):
        nombre_original = ruta.name
        nombre_original = self._limpiar_emoji(nombre_original)

        extension_original = ruta.suffix
        nombre_sin_extension = ruta.stem

        es_carpeta = ruta.is_dir()

        nuevo = simpledialog.askstring(
            "Renombrar",
            "Nuevo nombre:",
            initialvalue=nombre_sin_extension + extension_original
        )

        if nuevo:
            nuevo_path = Path(nuevo)

            if ruta.is_file():
                if not nuevo_path.suffix:
                    nuevo += extension_original
                elif nuevo_path.suffix != extension_original:
                    continuar = messagebox.askyesno(
                        "Cambiar extensión",
                        f"Estás cambiando la extensión del archivo de '{extension_original}' a '{nuevo_path.suffix}'.\n"
                        "Esto puede hacer que el archivo no funcione correctamente.\n\n¿Deseas continuar?"
                    )
                    if not continuar:
                        return

            nuevo_ruta = ruta.parent / nuevo

            try:
                ruta.rename(nuevo_ruta)

                if es_arbol:
                    self.arbol.item(item, text=f"📁 {nuevo}")
                self._actualizar_tabla(self.ruta_actual)

                # Logs DB
                
                ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
                tipo = "carpeta_renombrada" if es_carpeta else "archivo_renombrado"
                motivo_log = f"Renombrado de '{nombre_original}' a '{nuevo}'"

                # Buscar archivo_id por nombre anterior
                archivo_id = _buscar_archivo_id(nombre_original, ruta_relativa)
                if archivo_id:
                    registrar_log(self.user_id, archivo_id, tipo, motivo_log, nombre_original)
                    actualizar_nombre_archivo(archivo_id, nuevo)

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo renombrar:\n{str(e)}")

    def _eliminar(self, ruta):
        nombre_original = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        es_carpeta = ruta.is_dir()
        
        

        # 🚫 Bloquear eliminación de archivos
        if not es_carpeta:
            messagebox.showwarning("Acceso denegado", "No tienes permiso para eliminar archivos.")
            return

        # 🚫 Bloquear carpetas con contenido
        if any(ruta.iterdir()):
            messagebox.showwarning("Acceso denegado", "Solo puedes eliminar carpetas vacías.")
            return

        # ✅ Permitir eliminación de carpeta vacía
        confirmar = messagebox.askyesno("Confirmar eliminación", f"¿Seguro que deseas eliminar la carpeta vacía '{nombre_original}'?")
        if not confirmar:
            return

        try:
            esta_abierta = ruta == self.ruta_actual
            shutil.rmtree(ruta)

            if esta_abierta:
                self._navegar_a(ruta.parent)
            else:
                self._actualizar_tabla(self.ruta_actual)

            self.arbol.delete(*self.arbol.get_children())
            self._poblar_arbol(self.BASE_DIR)

            archivo_id = _buscar_archivo_id(nombre_original, ruta_relativa)
            if archivo_id:
                registrar_log(self.user_id, archivo_id, "carpeta_eliminada", "Carpeta vacía eliminada por usuario", nombre_original)

            messagebox.showinfo("Éxito", "🗑 Carpeta vacía eliminada correctamente.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{str(e)}")
    
    def _solicitar_descarga(self, ruta: Path):
        from psycopg2 import connect
        ventana = tk.Toplevel(self.master)
        ventana.title("Solicitud de descarga")
        ventana.geometry("400x250")

        tk.Label(ventana, text="Selecciona el motivo:", font=("Segoe UI", 10, "bold")).pack(pady=5)
        motivo_combo = ttk.Combobox(ventana, values=[
            "Solicitud", "Trabajo interno", "Modificación de datos", "Otro motivo"
        ], state="readonly")
        motivo_combo.pack(pady=5)

        entry_motivo = tk.Entry(ventana, width=40)
        entry_motivo.pack(pady=5)

        entry_motivo_label = tk.Label(ventana, text="", font=("Segoe UI", 9))
        entry_motivo_label.pack()

        def actualizar_placeholder(event):
            seleccion = motivo_combo.get()
            entry_motivo.delete(0, tk.END)
            entry_motivo.config(validate="none")

            if seleccion == "Solicitud":
                entry_motivo_label.config(text="Ingresa el número de solicitud:")

                # Validar solo números
                def solo_numeros(texto):
                    return texto.isdigit() or texto == ""
                vcmd = ventana.register(solo_numeros)
                entry_motivo.config(validate="key", validatecommand=(vcmd, '%P'))

            elif seleccion == "Trabajo interno":
                entry_motivo_label.config(text="Ingresa el nombre del trabajo interno:")
            elif seleccion == "Modificación de datos":
                entry_motivo_label.config(text="¿Por qué se modificará el archivo?")
            elif seleccion == "Otro motivo":
                entry_motivo_label.config(text="Describe el motivo exacto:")

        motivo_combo.bind("<<ComboboxSelected>>", actualizar_placeholder)

        def enviar():
            tipo = motivo_combo.get()
            detalle = entry_motivo.get().strip()
            if not tipo or not detalle:
                messagebox.showerror("Faltan datos", "Selecciona un motivo e ingresa el detalle.")
                return

            nombre_archivo = ruta.name
            ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))

            from db.archivos import _buscar_archivo_id
            archivo_id = _buscar_archivo_id(nombre_archivo, ruta_relativa)
            if not archivo_id:
                messagebox.showerror("Error", "No se encontró el archivo en la base de datos.")
                return

            try:
                conn = connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO solicitudes_descarga (usuario_id, archivo_id, motivo, estado, fecha_solicitud)
                    VALUES (%s, %s, %s, 'pendiente', %s)
                """, (self.user_id, archivo_id, f"{tipo}: {detalle}", datetime.now()))
                conn.commit()
                conn.close()
                messagebox.showinfo("Solicitud enviada", "Tu solicitud fue enviada correctamente.")
                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error BD", str(e))

        tk.Button(ventana, text="📤 Enviar solicitud", command=enviar, bg="#5FB7B6", fg="white").pack(pady=10)

    def _subir_archivo(self):
        archivo = filedialog.askopenfilename()
        if archivo:
            nombre_archivo = os.path.basename(archivo)
            destino = self.ruta_actual / nombre_archivo

            if destino.exists():
                messagebox.showwarning(
                    "Archivo existente",
                    f"Ya existe un archivo llamado '{nombre_archivo}' en esta carpeta.\nPor favor, cambia el nombre o elimínalo primero."
                )
                return

            try:
                shutil.copy2(archivo, destino)

                # Registrar en base de datos
                ruta_relativa = str(self.ruta_actual.relative_to(self.BASE_DIR))

                archivo_id = registrar_archivo(nombre_archivo, ruta_relativa, self.user_id, es_carpeta=False)
                if archivo_id:
                    registrar_log(self.user_id, archivo_id, "subido", "Archivo cargado al sistema", nombre_archivo)

                self._actualizar_tabla(self.ruta_actual)

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo subir el archivo:\n{str(e)}")

    def _crear_carpeta(self, donde):
        nombre = simpledialog.askstring("Nueva Carpeta", "Nombre de la carpeta:")
        if nombre:
            nueva = donde / nombre
            try:
                nueva.mkdir(exist_ok=False)

                # Base de datos
                ruta_relativa = str(donde.relative_to(self.BASE_DIR))
                archivo_id = registrar_archivo(nombre, ruta_relativa, self.user_id, es_carpeta=True)

                if archivo_id:
                    registrar_log(self.user_id, archivo_id, "carpeta_creada", "Carpeta creada manualmente", nombre)

                # Refrescar
                self._actualizar_tabla(self.ruta_actual)
                self.arbol.delete(*self.arbol.get_children())
                self._poblar_arbol(self.BASE_DIR)

            except FileExistsError:
                messagebox.showerror("Error", "Ya existe una carpeta con ese nombre.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta:\n{str(e)}")

    def _abrir_item_tabla(self, event):
        item_id = self.tabla.identify_row(event.y)
        if not item_id:
            return
        nombre_completo = self.tabla.item(item_id, "values")[0]
        nombre_limpio = nombre_completo[2:].strip() if nombre_completo.startswith(("📶", "🗀")) else nombre_completo
        ruta = self.ruta_actual / nombre_limpio
        if ruta.is_dir():
            self._navegar_a(ruta)
        elif ruta.is_file():
            try:
                os.startfile(ruta)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")

    def _mover_a(self, ruta_origen):
        ventana = tk.Toplevel(self.master)
        ventana.title("Seleccionar carpeta destino")
        ventana.geometry("300x400")

        arbol_destino = ttk.Treeview(ventana)
        arbol_destino.pack(fill="both", expand=True, padx=10, pady=10)

        def poblar_arbol_carpeta(ruta, nodo_padre=""):
            for item in ruta.iterdir():
                if item.is_dir():
                    nodo = arbol_destino.insert(nodo_padre, "end", text=item.name)
                    poblar_arbol_carpeta(item, nodo)

        poblar_arbol_carpeta(self.BASE_DIR)

        def mover():
            nodo = arbol_destino.selection()
            if not nodo:
                messagebox.showerror("Error", "Selecciona una carpeta destino")
                return

            partes = []
            while nodo:
                partes.insert(0, arbol_destino.item(nodo)["text"])
                nodo = arbol_destino.parent(nodo)

            carpeta_destino = self.BASE_DIR.joinpath(*partes)
            nuevo_ruta = carpeta_destino / ruta_origen.name

            try:
                if ruta_origen.resolve() == nuevo_ruta.resolve():
                    messagebox.showwarning("Aviso", "El origen y el destino son iguales.")
                    return

                # Validar que no se mueva carpeta dentro de sí misma o sus subcarpetas
                if ruta_origen.is_dir() and nuevo_ruta.resolve().is_relative_to(ruta_origen.resolve()):
                    messagebox.showerror("Error", "No puedes mover una carpeta dentro de sí misma o de una subcarpeta.")
                    return

                shutil.move(str(ruta_origen), str(nuevo_ruta))

                # Base de datos
                from db.archivos import _buscar_archivo_id, actualizar_ruta_archivo, registrar_log
                
                ruta_anterior = str(ruta_origen.parent.relative_to(self.BASE_DIR))
                ruta_nueva = str(carpeta_destino.relative_to(self.BASE_DIR))
                archivo_id = _buscar_archivo_id(ruta_origen.name, ruta_anterior)

                if archivo_id:
                    actualizar_ruta_archivo(archivo_id, ruta_nueva)
                    registrar_log(self.user_id, archivo_id, "movido",
                                f"Movido de '{ruta_anterior}' a '{ruta_nueva}'", ruta_origen.name)

                self._actualizar_tabla(self.ruta_actual)
                self.arbol.delete(*self.arbol.get_children())
                self._poblar_arbol(self.BASE_DIR)

                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo mover:\n{str(e)}")

        tk.Button(ventana, text="Mover aquí", command=mover).pack(pady=10)

