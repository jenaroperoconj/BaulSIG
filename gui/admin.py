import os
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from db.archivos import registrar_archivo, registrar_log, _buscar_archivo_id, actualizar_nombre_archivo, actualizar_ruta_archivo
from gui.login import iniciar_login
from tkinterdnd2 import DND_FILES, TkinterDnD

class ExploradorAdmin:
    def __init__(self, master, modo_oscuro=False, es_admin=True, user_id=None):
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
    
    def _mostrar_popup_solicitudes(self):
        import psycopg2
        ventana = tk.Toplevel(self.master)
        ventana.title("Solicitudes de Descarga")
        ventana.geometry("1350x520")

        tabla = ttk.Treeview(ventana, columns=("Usuario", "Archivo", "Estado", "Motivo", "Fecha solicitud"), show="headings")
        for col in tabla["columns"]:
            tabla.heading(col, text=col)
        tabla.pack(fill="both", expand=True, padx=10, pady=10)

        def cargar():
            conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
            cur = conn.cursor()
            cur.execute("""
                SELECT sd.id, u.nombre, a.nombre_archivo, sd.estado, sd.motivo, sd.fecha_solicitud
                FROM solicitudes_descarga sd
                JOIN usuarios u ON u.id = sd.usuario_id
                JOIN archivos a ON a.id = sd.archivo_id
                WHERE sd.estado = 'pendiente'
            """)
            resultados = cur.fetchall()
            conn.close()
            for row in tabla.get_children():
                tabla.delete(row)
            for fila in resultados:
                tabla.insert("", "end", iid=fila[0], values=fila[1:])

        def aprobar():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Seleccionar", "Selecciona una solicitud para aprobar.")
                return
            motivo = tabla.item(item_id, "values")[3]  # Motivo ya ingresado por el usuario
            conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
            cur = conn.cursor()
            cur.execute("UPDATE solicitudes_descarga SET estado = %s, fecha_aprobacion = %s WHERE id = %s",
                        ('aprobado', datetime.now(), item_id))
            cur.execute("INSERT INTO historial_motivos (solicitud_id, motivo) VALUES (%s, %s)", (item_id, motivo))
            conn.commit()
            conn.close()
            cargar()
            messagebox.showinfo("Aprobada", "La solicitud fue aprobada.")

        def rechazar():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Seleccionar", "Selecciona una solicitud para rechazar.")
                return
            motivo = tabla.item(item_id, "values")[3]  # Motivo ya ingresado por el usuario
            conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
            cur = conn.cursor()
            cur.execute("UPDATE solicitudes_descarga SET estado = %s WHERE id = %s",
                        ('rechazado', item_id))
            cur.execute("INSERT INTO historial_motivos (solicitud_id, motivo) VALUES (%s, %s)", (item_id, motivo))
            conn.commit()
            conn.close()
            cargar()
            messagebox.showinfo("Rechazada", "La solicitud fue rechazada.")

        btn_frame = tk.Frame(ventana)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="✅ Aprobar", command=aprobar, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="❌ Rechazar", command=rechazar, bg="#F44336", fg="white").pack(side="left", padx=5)

        def ver_historial():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Seleccionar", "Selecciona una solicitud para ver el historial.")
                return

            ventana_historial = tk.Toplevel(ventana)
            ventana_historial.title("Historial de motivos")
            ventana_historial.geometry("600x300")

            tabla_hist = ttk.Treeview(ventana_historial, columns=("Fecha", "Motivo"), show="headings")
            tabla_hist.heading("Fecha", text="Fecha")
            tabla_hist.heading("Motivo", text="Motivo")
            tabla_hist.pack(fill="both", expand=True, padx=10, pady=10)

            conn = psycopg2.connect(dbname="sistema_archivos", user="postgres", password="sig2025", host="localhost", port="5433")
            cur = conn.cursor()
            cur.execute("""
                SELECT fecha, motivo
                FROM historial_motivos
                WHERE solicitud_id = %s
                ORDER BY fecha DESC
            """, (item_id,))
            filas = cur.fetchall()
            conn.close()

            for fila in filas:
                tabla_hist.insert("", "end", values=(fila[0].strftime("%d/%m/%Y %H:%M"), fila[1]))

        tk.Button(btn_frame, text="📜 Ver historial", command=ver_historial, bg="#2196F3", fg="white").pack(side="left", padx=5)

        cargar()
    
    def _crear_widgets(self):
        barra_sup = tk.Frame(self.master, bg="#333333", padx=12, pady=10, bd=2, relief="groove")
        tk.Button(barra_sup, text="📥 Ver solicitudes", command=self._mostrar_popup_solicitudes).pack(side="left", padx=5)
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
        item = self.arbol.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0)

        if item:
            ruta = self._obtener_ruta_completa(item)
            menu.add_command(label="🔍 Abrir", command=lambda: self._navegar_a(ruta))
            menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, True))
            menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
            menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))  # ✅ Añadido aquí
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta (raíz)", command=lambda: self._crear_carpeta(self.BASE_DIR))

        menu.tk_popup(event.x_root, event.y_root)


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
                menu.add_command(label="💾 Descargar", command=lambda: self._descargar(ruta))
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
                    registrar_log(self.es_admin, archivo_id, tipo, motivo_log, nombre_original)
                    actualizar_nombre_archivo(archivo_id, nuevo)

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo renombrar:\n{str(e)}")

    def _eliminar(self, ruta):
        nombre_original = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        es_carpeta = ruta.is_dir()

        if es_carpeta:
            # Primera confirmación
            confirmar1 = messagebox.askyesno("Confirmar eliminación", f"¿Seguro que deseas eliminar la carpeta '{nombre_original}'?")
            if not confirmar1:
                return

            # Verificar contenido
            contenido = list(ruta.rglob("*"))
            archivos_encontrados = [p for p in contenido if p.is_file()]
            carpetas_encontradas = [p for p in contenido if p.is_dir()]

            if archivos_encontrados or carpetas_encontradas:
                msg = (f"La carpeta '{nombre_original}' contiene:\n"
                    f"📄 {len(archivos_encontrados)} archivo(s)\n"
                    f"📁 {len(carpetas_encontradas)} subcarpeta(s)\n\n"
                    f"¿Estás seguro que deseas eliminar todo?")
                confirmar2 = messagebox.askyesno("Advertencia: carpeta con contenido", msg)
                if not confirmar2:
                    return
        else:
            confirmar = messagebox.askyesno("Confirmar eliminación", f"¿Seguro que deseas eliminar '{nombre_original}'?")
            if not confirmar:
                return

        try:
            esta_abierta = ruta == self.ruta_actual
            archivos_contados = 0
            carpetas_contadas = 0

            if es_carpeta:
                # Registrar logs por cada archivo o subcarpeta interna
                for subelemento in ruta.rglob("*"):
                    if subelemento.is_file() or subelemento.is_dir():
                        ruta_sub = str(subelemento.parent.relative_to(self.BASE_DIR))
                        nombre_sub = subelemento.name
                        tipo = "carpeta_eliminada" if subelemento.is_dir() else "archivo_eliminado"
                        archivo_id = _buscar_archivo_id(nombre_sub, ruta_sub)
                        if archivo_id:
                            registrar_log(self.es_admin, archivo_id, tipo, "Eliminado dentro de carpeta eliminada", nombre_sub)
                        if subelemento.is_file():
                            archivos_contados += 1
                        elif subelemento.is_dir():
                            carpetas_contadas += 1

                shutil.rmtree(ruta)
            else:
                ruta.unlink()
                archivos_contados = 1

            if esta_abierta:
                self._navegar_a(ruta.parent)
            else:
                self._actualizar_tabla(self.ruta_actual)

            # Refrescar árbol
            self.arbol.delete(*self.arbol.get_children())
            self._poblar_arbol(self.BASE_DIR)

            # Log principal del elemento eliminado
            archivo_id = _buscar_archivo_id(nombre_original, ruta_relativa)
            if archivo_id:
                tipo = "carpeta_eliminada" if es_carpeta else "archivo_eliminado"
                registrar_log(self.es_admin, archivo_id, tipo, "Elemento eliminado", nombre_original)

            # Mostrar resumen
            if es_carpeta:
                messagebox.showinfo("Eliminación completa", f"🗑 Carpeta eliminada con éxito.\n"
                                                            f"📄 Archivos eliminados: {archivos_contados}\n"
                                                            f"📁 Subcarpetas eliminadas: {carpetas_contadas}")
            else:
                messagebox.showinfo("Eliminación completa", "🗑 Archivo eliminado con éxito.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{str(e)}")
    

    def _descargar(self, ruta):
        destino = filedialog.asksaveasfilename(defaultextension="", initialfile=ruta.name)
        if destino:
            shutil.copy2(ruta, destino)

    def _subir_archivo(self):
        archivo = filedialog.askopenfilename()
        if archivo:
            nombre_archivo = os.path.basename(archivo)
            destino = self.ruta_actual / nombre_archivo

            # ❌ Verificar si ya existe
            if destino.exists():
                messagebox.showwarning(
                    "Archivo existente",
                    f"Ya existe un archivo llamado '{nombre_archivo}' en esta carpeta.\nPor favor, cambia el nombre o elimínalo primero."
                )
                return

            try:
                shutil.copy2(archivo, destino)

                # 🔗 Registrar en base de datos
                ruta_relativa = str(self.ruta_actual.relative_to(self.BASE_DIR))

                archivo_id = registrar_archivo(nombre_archivo, ruta_relativa, self.es_admin, es_carpeta=False)
                if archivo_id:
                    registrar_log(self.es_admin, archivo_id, "subido", "Archivo cargado al sistema", nombre_archivo)

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
                archivo_id = registrar_archivo(nombre, ruta_relativa, self.es_admin, es_carpeta=True)

                if archivo_id:
                    registrar_log(self.es_admin, archivo_id, "carpeta_creada", "Carpeta creada manualmente", nombre)

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

                # 🚫 Validar que no se mueva carpeta dentro de sí misma o sus subcarpetas
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
                    registrar_log(self.es_admin, archivo_id, "movido",
                                f"Movido de '{ruta_anterior}' a '{ruta_nueva}'", ruta_origen.name)

                self._actualizar_tabla(self.ruta_actual)
                self.arbol.delete(*self.arbol.get_children())
                self._poblar_arbol(self.BASE_DIR)

                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo mover:\n{str(e)}")

        tk.Button(ventana, text="Mover aquí", command=mover).pack(pady=10)

if __name__ == "__main__":
    from gui.login import iniciar_login
    iniciar_login()

def abrir_menu_admin(user_id, username, modo_oscuro):
    root = TkinterDnD.Tk()  # ← NO usar tk.Tk()
    app = ExploradorAdmin(root, modo_oscuro=modo_oscuro, es_admin=True)
    app.user_id = user_id
    root.mainloop()