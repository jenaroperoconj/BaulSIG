import os
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from db.file_manager import archivo_manager
from db.db_manager import conectar
from gui.login import iniciar_login
from tkinterdnd2 import DND_FILES, TkinterDnD
from core.utils import centrar_ventana
from core.config import ARCHIVOS_COMPARTIDOS_DIR
from core.ui_config import (
    COLORES, ESPACIOS, obtener_fuente, configurar_ventana_principal
)

if __name__ == "__main__":
    from gui.login import iniciar_login
    iniciar_login()

def abrir_menu_usuario(user_id, username, modo_oscuro):
    root = TkinterDnD.Tk()
    configurar_ventana_principal(root, 'usuario_principal')
    app = ExploradorAdmin(root, modo_oscuro=modo_oscuro, es_admin=False)
    app.user_id = user_id
    root.mainloop()

class ExploradorAdmin:
    def __init__(self, master, modo_oscuro=False, es_admin=False, user_id=None):
        """
        Inicializa la ventana principal del explorador de archivos para el usuario.
        Configura la interfaz, carga los widgets y establece la ruta base.
        """
        self.user_id = user_id
        self.es_admin = es_admin
        self.orden_columna = None
        self.orden_descendente = False
        self.master = master
        self.modo_oscuro = modo_oscuro
        self.master.title("📂 EXPLORADOR DE ARCHIVOS - USUARIO")
        self.master.configure(bg=COLORES['fondo_principal'])
        self.historial = []
        self.historial_pos = -1
        self.BASE_DIR = Path(ARCHIVOS_COMPARTIDOS_DIR)
        self.ruta_actual = self.BASE_DIR
        if not self.BASE_DIR.exists():
            self.BASE_DIR.mkdir()
        self._crear_widgets()
        self._aplicar_estilo()
        self._poblar_arbol(self.BASE_DIR)
        self._navegar_a(self.BASE_DIR)
        self.master.bind('<Configure>', self._on_window_resize)

    def _cerrar_sesion(self):
        """
        Cierra la sesión actual y vuelve a la pantalla de login.
        """
        self.master.destroy()
        iniciar_login(modo=self.modo_oscuro)
    
    def _limpiar_emoji(self, texto):
        """
        Elimina emojis de los nombres de archivos/carpetas para operaciones internas.
        """
        if texto.startswith(("📁", "📄", "❓")):
            return texto[2:].strip()
        return texto
    
    def _crear_widgets(self):
        """
        Crea y organiza todos los widgets de la interfaz principal del usuario.
        Incluye barra superior, paneles, tabla y eventos.
        """
        # Barra superior con espaciado mejorado
        barra_sup = tk.Frame(self.master, bg="#dddddd", padx=20, pady=15, bd=3, relief="groove")
        
        # Botón de solicitudes con fuente más grande (diferente a admin)
        btn_solicitudes = tk.Button(barra_sup, text="📥 MIS SOLICITUDES", 
                                  command=self._mostrar_mis_solicitudes,
                                  font=("Segoe UI", 12, "bold"), 
                                  padx=20, pady=10,
                                  bg="#FF9800", fg="#ffffff",
                                  relief="raised", bd=2)
        btn_solicitudes.pack(side="left", padx=(0, 20))
        
        # Panel derecho para búsqueda y cerrar sesión
        panel_derecho = tk.Frame(barra_sup, bg="#dddddd")
        panel_derecho.pack(side="right")

        # Botón cerrar sesión más prominente
        btn_logout = tk.Button(panel_derecho, text="🔒 CERRAR SESIÓN", 
                            command=self._cerrar_sesion,
                            bg="#d32f2f", fg="#ffffff", 
                            font=("Segoe UI", 12, "bold"), 
                            padx=20, pady=10,
                            relief="raised", bd=2)
        btn_logout.pack(side="right", padx=(10, 0))

        # Lupa y entrada de búsqueda más grandes
        label_lupa = tk.Label(panel_derecho, text="🔍", bg="#dddddd", fg="#000000", 
                            font=("Segoe UI", 16, "bold"))
        label_lupa.pack(side="left", padx=(0, 8), pady=2)

        self.entrada_busqueda = tk.Entry(panel_derecho, width=30, font=("Segoe UI", 12))
        self.entrada_busqueda.pack(side="left", padx=(0, 10), pady=2)
        self.entrada_busqueda.insert(0, "Buscar archivos...")
        self.entrada_busqueda.bind("<FocusIn>", lambda e: self._limpiar_placeholder_busqueda())
        self.entrada_busqueda.bind("<FocusOut>", lambda e: self._restaurar_placeholder_busqueda())
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self._actualizar_tabla(self.ruta_actual))
        
        barra_sup.pack(fill="x", padx=15, pady=10)

        # Botones de navegación más grandes
        tk.Button(barra_sup, text="◀", command=lambda: self._navegar_historial(-1),
                 font=("Segoe UI", 14, "bold"), padx=15, pady=10,
                 bg="#2196F3", fg="#ffffff", relief="raised", bd=2).pack(side="left", padx=(0, 8))
        tk.Button(barra_sup, text="▶", command=lambda: self._navegar_historial(1),
                 font=("Segoe UI", 14, "bold"), padx=15, pady=10,
                 bg="#2196F3", fg="#ffffff", relief="raised", bd=2).pack(side="left")

        # Barra de ruta mejorada
        self.ruta_label = tk.Frame(barra_sup, bg="#e8e8e8", relief="sunken", bd=1)
        self.ruta_label.pack(side="left", padx=20, fill="x", expand=True)

        # Contenedor principal
        contenedor = tk.Frame(self.master)
        contenedor.pack(fill="both", expand=True, padx=10, pady=5)

        # Panel izquierdo mejorado
        self.panel_izq = tk.Frame(contenedor, width=350, bg="#f0f0f0", relief="groove", bd=2)
        self.panel_izq.pack(side="left", fill="y", padx=(0, 10))
        self.panel_izq.pack_propagate(False)

        # Encabezado del árbol más prominente
        header_frame = tk.Frame(self.panel_izq, bg="#4CAF50", relief="raised", bd=2)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(header_frame, text="📂 DIRECTORIO DE CARPETAS", 
                bg="#4CAF50", fg="#ffffff",
                font=("Segoe UI", 13, "bold"), 
                anchor="center", pady=8).pack(fill="x")

        # Árbol de directorios
        self.arbol = ttk.Treeview(self.panel_izq)
        self.arbol.pack(fill="both", expand=True, padx=8, pady=(5, 8))

        # Panel derecho mejorado
        self.panel_der = tk.Frame(contenedor, bg="#f0f0f0", relief="groove", bd=2)
        self.panel_der.pack(side="right", fill="both", expand=True)

        # Encabezado de la tabla
        header_tabla = tk.Frame(self.panel_der, bg="#2196F3", relief="raised", bd=2)
        header_tabla.pack(fill="x", padx=5, pady=5)
        
        tk.Label(header_tabla, text="📋 CONTENIDO DEL DIRECTORIO", 
                bg="#2196F3", fg="#ffffff",
                font=("Segoe UI", 13, "bold"), 
                anchor="center", pady=8).pack(fill="x")

        # Tabla de archivos con columnas mejoradas
        columnas = ("Nombre", "Tipo", "Tamaño", "Fecha modificación")
        self.tabla = ttk.Treeview(self.panel_der, columns=columnas, show="headings", selectmode="browse")

        for col in columnas:
            self.tabla.heading(col, text=col, command=lambda c=col: self._ordenar_por_columna(c))
            self.tabla.column(col, anchor="w")
        
        # Configurar anchos de columnas
        self.tabla.column("Nombre", width=250, minwidth=200)
        self.tabla.column("Tipo", width=180, minwidth=150)
        self.tabla.column("Tamaño", width=100, minwidth=80)
        self.tabla.column("Fecha modificación", width=150, minwidth=120)
        
        self.tabla.pack(fill="both", expand=True, padx=12, pady=(5, 12))

        self.arbol.bind("<<TreeviewSelect>>", self._al_seleccionar_carpeta)
        self.tabla.bind("<Double-1>", self._abrir_item_tabla)
        self.arbol.bind("<Button-3>", self._menu_contexto_arbol)
        self.tabla.bind("<Button-3>", self._menu_contexto_tabla)
        # Configurar responsividad para la barra de ruta
        self.master.bind('<Configure>', self._on_window_resize)

    def _mostrar_mis_solicitudes(self):
        """
        Muestra la ventana donde el usuario puede ver, modificar y descargar sus solicitudes de descarga.
        """
        ventana = tk.Toplevel(self.master)
        ventana.title("📄 MIS SOLICITUDES DE DESCARGA")
        centrar_ventana(ventana, 1500, 600)
        ventana.configure(bg="#f5f5f5")

        # Encabezado de la ventana
        header = tk.Frame(ventana, bg="#2196F3", relief="raised", bd=3)
        header.pack(fill="x", padx=10, pady=10)
        
        tk.Label(header, text="📋 GESTIÓN DE SOLICITUDES DE DESCARGA", 
                bg="#2196F3", fg="#ffffff",
                font=obtener_fuente('titulo'), 
                anchor="center", pady=12).pack(fill="x")

        # Frame para la tabla
        tabla_frame = tk.Frame(ventana, bg="#ffffff", relief="sunken", bd=2)
        tabla_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columnas = ("Archivo", "Motivo", "Estado", "Fecha solicitud", "Acción")
        tabla = ttk.Treeview(tabla_frame, columns=columnas, show="headings", height=20)
        
        for col in columnas:
            tabla.heading(col, text=col)
            tabla.column(col, anchor="center")
            
        # Configurar colores más vibrantes para estados
        tabla.tag_configure("aprobado", background="#c8e6c9", foreground="#1b5e20")      # verde más fuerte
        tabla.tag_configure("pendiente", background="#fff3e0", foreground="#e65100")     # naranja fuerte
        tabla.tag_configure("rechazado", background="#ffcdd2", foreground="#b71c1c")     # rojo fuerte
        tabla.tag_configure("descargado", background="#e1f5fe", foreground="#01579b")    # azul fuerte
        
        tabla.pack(fill="both", expand=True, padx=8, pady=8)
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
                messagebox.showwarning("⚠️ Selección requerida", "Selecciona una solicitud para modificar.")
                return

            valores = tabla.item(item_id)["values"]
            motivo_actual = valores[1]
            tipo_actual, _, *detalle_split = motivo_actual.partition(":")
            detalle_actual = detalle_split[0].strip() if detalle_split else ""

            nueva_ventana = tk.Toplevel(ventana)
            nueva_ventana.title("✏️ MODIFICAR MOTIVO")
            centrar_ventana(nueva_ventana, 500, 350)
            nueva_ventana.configure(bg="#f5f5f5")

            nueva_ventana.transient(ventana)
            nueva_ventana.grab_set()
            nueva_ventana.focus()

            # Header de la ventana
            header = tk.Frame(nueva_ventana, bg="#FF9800", relief="raised", bd=2)
            header.pack(fill="x", padx=10, pady=10)
            tk.Label(header, text="🔧 MODIFICACIÓN DE MOTIVO", 
                    bg="#FF9800", fg="#ffffff",
                    font=obtener_fuente('titulo'), 
                    anchor="center", pady=8).pack(fill="x")

            tk.Label(nueva_ventana, text="Tipo de motivo:", 
                    font=obtener_fuente('normal'), bg="#f5f5f5").pack(pady=(10, 5))
            motivo_combo = ttk.Combobox(nueva_ventana, values=[
                "Solicitud", "Trabajo interno", "Modificación de datos", "Otro motivo"
            ], state="readonly", font=obtener_fuente('normal'), width=40)
            motivo_combo.set(tipo_actual)
            motivo_combo.pack(pady=5)

            tk.Label(nueva_ventana, text="Detalle:", 
                    font=obtener_fuente('normal'), bg="#f5f5f5").pack(pady=(10, 5))
            entry = tk.Entry(nueva_ventana, width=50, font=obtener_fuente('normal'))
            entry.insert(0, detalle_actual)
            entry.pack(pady=5)

            def guardar_motivo():
                tipo = motivo_combo.get().strip()
                detalle = entry.get().strip()
                
                if not tipo or not detalle:
                    messagebox.showerror("❌ Error", "Debes seleccionar un motivo e ingresar el detalle.")
                    return

                nuevo_motivo = f"{tipo}: {detalle}"

                try:
                    conn = conectar()
                    cur = conn.cursor()

                    # Guardar historial
                    cur.execute("""
                        INSERT INTO historial_motivos (solicitud_id, motivo, fecha)
                        SELECT id, motivo, NOW() FROM solicitudes_descarga WHERE id = %s
                    """, (item_id,))
                    
                    # Actualizar motivo nuevo
                    cur.execute("""
                        UPDATE solicitudes_descarga SET motivo = %s WHERE id = %s
                    """, (nuevo_motivo, item_id))

                    conn.commit()
                    conn.close()

                    messagebox.showinfo("✅ Éxito", "Motivo actualizado correctamente.", parent=nueva_ventana)
                    nueva_ventana.destroy()
                    cargar()
                except Exception as e:
                    messagebox.showerror("❌ Error", f"No se pudo modificar el motivo:\n{str(e)}")

            tk.Button(nueva_ventana, text="💾 GUARDAR CAMBIOS", command=guardar_motivo, 
                     bg="#4CAF50", fg="#ffffff", font=obtener_fuente('boton'),
                     padx=20, pady=10, relief="raised", bd=2).pack(pady=15)

            nueva_ventana.wait_window()
        
        def cargar():
            # Usar sistema optimizado para obtener solicitudes
            solicitudes = archivo_manager.obtener_solicitudes_usuario(self.user_id)

            for row in tabla.get_children():
                tabla.delete(row)
            for fila in solicitudes:
                fecha_formateada = fila[4].strftime("%d/%m/%Y %H:%M")
                solicitud_id = fila[0]
                estado = fila[3]
                if estado == "aprobado":
                    accion = "📥 DESCARGAR AHORA"
                elif estado == "pendiente":
                    accion = "✏️ Modificar motivo"
                else:
                    accion = "—"
                valores = (fila[1], fila[2], fila[3], fecha_formateada, accion)
                tabla.insert("", "end", iid=solicitud_id, values=valores, tags=(estado,))

        def descargar():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("⚠️ Selección requerida", "Selecciona una solicitud aprobada para descargar.")
                return
                
            estado = tabla.item(item_id)["values"][2]
            if estado != "aprobado":
                messagebox.showerror("🚫 No permitido", "Solo puedes descargar archivos aprobados.")
                return

            conn = conectar()
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
                messagebox.showerror("❌ Error", "Archivo no encontrado.")
                return
                
            nombre, ruta_relativa = archivo
            archivo_path = self.BASE_DIR / ruta_relativa / nombre
            
            if not archivo_path.exists():
                messagebox.showerror("❌ Error", "El archivo ya no está disponible.")
                return
                
            destino = filedialog.asksaveasfilename(defaultextension="", initialfile=nombre)
            if destino:
                try:
                    shutil.copy2(archivo_path, destino)
                    conn = conectar()
                    cur = conn.cursor()
                    cur.execute("UPDATE solicitudes_descarga SET estado = 'descargado' WHERE id = %s", (item_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("✅ Descarga completada", "Archivo descargado correctamente.")
                    cargar()
                except Exception as e:
                    messagebox.showerror("❌ Error", f"No se pudo descargar: {str(e)}")

        # Frame para botones con estilo moderno
        btn_frame = tk.Frame(ventana, bg="#f5f5f5")
        btn_frame.pack(fill="x", pady=(0, 10), padx=10)

        # Botones con estilo moderno y consistente
        btn_descargar = tk.Button(btn_frame, text="📥 DESCARGAR ARCHIVO", 
                                command=descargar, 
                                bg="#4CAF50", fg="#ffffff",
                                font=obtener_fuente('boton'), 
                                padx=20, pady=10,
                                relief="raised", bd=2,
                                cursor="hand2")
        btn_descargar.pack(side="left", padx=(0, 10))
        
        btn_modificar = tk.Button(btn_frame, text="✏️ MODIFICAR MOTIVO", 
                                command=modificar_motivo, 
                                bg="#2196F3", fg="#ffffff",
                                font=obtener_fuente('boton'), 
                                padx=20, pady=10,
                                relief="raised", bd=2,
                                cursor="hand2")
        btn_modificar.pack(side="left", padx=(0, 10))
        
        # Botón de actualizar
        btn_actualizar = tk.Button(btn_frame, text="🔄 ACTUALIZAR LISTA", 
                                command=cargar, 
                                bg="#FF9800", fg="#ffffff",
                                font=obtener_fuente('boton'), 
                                padx=20, pady=10,
                                relief="raised", bd=2,
                                cursor="hand2")
        btn_actualizar.pack(side="right")

        # Efectos hover para los botones
        def on_enter(e, btn, color):
            btn.configure(bg=color)
        def on_leave(e, btn, original_color):
            btn.configure(bg=original_color)

        # Aplicar efectos hover a los botones
        btn_descargar.bind("<Enter>", lambda e: on_enter(e, btn_descargar, "#45a049"))
        btn_descargar.bind("<Leave>", lambda e: on_leave(e, btn_descargar, "#4CAF50"))
        
        btn_modificar.bind("<Enter>", lambda e: on_enter(e, btn_modificar, "#1976D2"))
        btn_modificar.bind("<Leave>", lambda e: on_leave(e, btn_modificar, "#2196F3"))
        
        btn_actualizar.bind("<Enter>", lambda e: on_enter(e, btn_actualizar, "#F57C00"))
        btn_actualizar.bind("<Leave>", lambda e: on_leave(e, btn_actualizar, "#FF9800"))

        cargar()

    def _limpiar_placeholder_busqueda(self):
        """
        Limpia el texto de placeholder en la barra de búsqueda.
        """
        if self.entrada_busqueda.get() == "Buscar archivos...":
            self.entrada_busqueda.delete(0, "end")
            self.entrada_busqueda.config(fg="#000000")

    def _restaurar_placeholder_busqueda(self):
        """
        Restaura el texto de placeholder si la barra de búsqueda está vacía.
        """
        if not self.entrada_busqueda.get():
            self.entrada_busqueda.insert(0, "Buscar archivos...")
            self.entrada_busqueda.config(fg="#888888")

    def _aplicar_estilo(self):
        """
        Aplica estilos personalizados a los widgets de la interfaz.
        """
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configurar estilo de Treeview con fuentes más grandes
        style.configure("Treeview",
                        background="#ffffff", foreground="#222222",
                        rowheight=30, fieldbackground="#ffffff",  # Filas más altas
                        font=obtener_fuente('normal'))  # Fuente más grande
        style.configure("Treeview.Heading",
                        background="#e0e0e0", foreground="#000000",
                        font=obtener_fuente('titulo'))  # Encabezados más grandes y negritas
        style.map("Treeview",
                  background=[('selected', '#2196F3')],
                  foreground=[('selected', '#ffffff')])
          # Configurar estilo de Combobox
        style.configure("TCombobox", font=obtener_fuente('normal'))
    
    def _ordenar_por_columna(self, columna):
        """
        Ordena la tabla por la columna seleccionada.
        """
        if self.orden_columna == columna:
            self.orden_descendente = not self.orden_descendente
        else:
            self.orden_columna = columna
            self.orden_descendente = False
        self._actualizar_tabla(self.ruta_actual)

    def _actualizar_barra_ruta(self, path: Path):
        """
        Actualiza la barra de ruta para mostrar la ubicación actual.
        """
        for widget in self.ruta_label.winfo_children():
            widget.destroy()
        
        # Actualizar para obtener el ancho real después de que la ventana se haya dibujado
        self.master.after(50, lambda: self._dibujar_ruta_responsiva(path))
    
    def _dibujar_ruta_responsiva(self, path: Path):
        """
        Dibuja la barra de ruta de forma responsiva, priorizando mostrar las carpetas finales.
        """
        # Limpiar widgets existentes
        for widget in self.ruta_label.winfo_children():
            widget.destroy()
        
        # Obtener la ruta relativa a BASE_DIR
        try:
            rel_path = path.relative_to(self.BASE_DIR)
        except Exception:
            rel_path = path
        partes = list(rel_path.parts)
        # Si estamos en la raíz, mostrar el nombre de la carpeta base
        if len(partes) == 0:
            nombre_base = self.BASE_DIR.name
            btn = tk.Button(self.ruta_label, text=nombre_base, relief="flat",
                          bg="#e8e8e8", fg="#000000",
                          font=obtener_fuente('normal'),
                          padx=8, pady=4,
                          cursor="hand2",
                          command=lambda p=self.BASE_DIR: self._navegar_a(p))
            btn.pack(side="left", padx=2)
            return
        
        # Obtener ancho disponible (restar un margen de seguridad)
        self.ruta_label.update_idletasks()
        ancho_disponible = max(200, self.ruta_label.winfo_width() - 40)
        
        # Crear todos los elementos de la ruta para calcular sus tamaños
        elementos_ruta = []
        rutas_completas = []
        ruta_acumulada = self.BASE_DIR
        for parte in partes:
            ruta_acumulada = ruta_acumulada / parte
            rutas_completas.append(ruta_acumulada)
            elementos_ruta.append(parte)
        
        # Calcular el ancho que ocuparía cada elemento
        anchos_estimados = []
        for parte in elementos_ruta:
            ancho_texto = len(parte) * 8 + 20  # padding del botón
            ancho_separador = 25  # ancho del separador ▶
            anchos_estimados.append(ancho_texto + ancho_separador)
        
        ancho_puntos = 60
        elementos_a_mostrar = []
        rutas_a_mostrar = []
        ancho_total = 0
        mostrar_puntos = False
        for i in range(len(elementos_ruta) - 1, -1, -1):
            ancho_necesario = anchos_estimados[i]
            if not elementos_a_mostrar or (ancho_total + ancho_necesario <= ancho_disponible):
                elementos_a_mostrar.insert(0, elementos_ruta[i])
                rutas_a_mostrar.insert(0, rutas_completas[i])
                ancho_total += ancho_necesario
            else:
                if len(elementos_a_mostrar) < len(elementos_ruta):
                    mostrar_puntos = True
                break
        if mostrar_puntos and ancho_total + ancho_puntos <= ancho_disponible:
            ancho_restante = ancho_disponible - ancho_total - ancho_puntos
            for i in range(len(elementos_ruta) - len(elementos_a_mostrar)):
                if anchos_estimados[i] <= ancho_restante:
                    elementos_a_mostrar.insert(0, elementos_ruta[i])
                    rutas_a_mostrar.insert(0, rutas_completas[i])
                    ancho_total += anchos_estimados[i]
                    break
        if mostrar_puntos:
            btn_puntos = tk.Button(self.ruta_label, text="...", relief="flat",
                                 bg="#d0d0d0", fg="#666666",
                                 font=obtener_fuente('normal'),
                                 padx=8, pady=4,
                                 cursor="hand2")
            btn_puntos.pack(side="left", padx=2)
            tooltip = [None]
            def mostrar_tooltip(event):
                if tooltip[0] is not None:
                    return
                tooltip[0] = tk.Toplevel()
                tooltip[0].wm_overrideredirect(True)
                tooltip[0].configure(bg="#ffffcc", relief="solid", bd=1)
                x = event.x_root + 10
                y = event.y_root + 10
                tooltip[0].geometry(f"+{x}+{y}")
                # Mostrar la ruta relativa desde la carpeta compartida
                ruta_relativa = ' ▶ '.join(partes)
                label = tk.Label(tooltip[0], text=ruta_relativa, 
                               bg="#ffffcc", fg="#333333", font=obtener_fuente('normal'),
                               justify="left", padx=8, pady=4)
                label.pack()
            def ocultar_tooltip(event=None):
                if tooltip[0] is not None:
                    tooltip[0].destroy()
                    tooltip[0] = None
            btn_puntos.bind("<Enter>", mostrar_tooltip)
            btn_puntos.bind("<Leave>", ocultar_tooltip)
            tk.Label(self.ruta_label, text="▶", bg="#e8e8e8", fg="#666666",
                    font=obtener_fuente('normal')).pack(side="left", padx=2)
        for i, (parte, ruta_completa) in enumerate(zip(elementos_a_mostrar, rutas_a_mostrar)):
            btn = tk.Button(self.ruta_label, text=parte, relief="flat",
                          bg="#e8e8e8", fg="#000000",
                          font=obtener_fuente('normal'),
                          padx=8, pady=4,
                          cursor="hand2",
                          command=lambda p=ruta_completa: self._navegar_a(p))
            btn.pack(side="left", padx=2)
            def on_enter(e, btn=btn):
                btn.configure(bg="#d4d4d4")
            def on_leave(e, btn=btn):
                btn.configure(bg="#e8e8e8")
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            if i < len(elementos_a_mostrar) - 1:
                tk.Label(self.ruta_label, text="▶", bg="#e8e8e8", fg="#666666",
                        font=obtener_fuente('normal')).pack(side="left", padx=2)

    def _navegar_historial(self, direccion):
        """
        Navega hacia atrás o adelante en el historial de rutas visitadas.
        """
        nueva_pos = self.historial_pos + direccion
        if 0 <= nueva_pos < len(self.historial):
            self.historial_pos = nueva_pos
            self._navegar_a(self.historial[self.historial_pos], agregar_historial=False)

    def _navegar_a(self, ruta: Path, agregar_historial=True):
        """
        Cambia la ruta actual a la ruta indicada y actualiza la interfaz.
        Previene salir del directorio base.
        """
        try:
            if not ruta.resolve().is_relative_to(self.BASE_DIR.resolve()):
                messagebox.showwarning("🚫 Acceso denegado", "No puedes salir del directorio compartido.")
                return
        except Exception:
            messagebox.showerror("❌ Error", "Ruta inválida o acceso denegado.")
            return
        self.ruta_actual = ruta
        self._actualizar_barra_ruta(ruta)
        self._actualizar_tabla(ruta)
        if agregar_historial:
            self.historial = self.historial[:self.historial_pos + 1]
            self.historial.append(ruta)
            self.historial_pos += 1
    
    def _obtener_tipo_archivo(self, ruta: Path) -> str:
        """
        Retorna una descripción legible del tipo de archivo según su extensión.
        """
        if ruta.is_dir():
            return "📁 Carpeta de archivos"
        elif ruta.is_file():
            ext = ruta.suffix.lower()
            if ext in [".zip"]:
                return "📦 Archivo ZIP"
            elif ext in [".rar"]:
                return "📦 Archivo WinRAR"
            elif ext in [".txt"]:
                return "📄 Archivo de texto"
            elif ext in [".pdf"]:
                return "📕 Archivo PDF"
            elif ext in [".jpg", ".jpeg", ".png"]:
                return "🖼️ Imagen"
            elif ext in [".exe"]:
                return "⚙️ Ejecutable"
            elif ext in [".doc", ".docx"]:
                return "📘 Documento Word"
            elif ext in [".xls", ".xlsx"]:
                return "📊 Documento Excel"
            else:
                return f"📄 Archivo ({ext[1:]})" if ext else "📄 Archivo"
        else:
            return "❓ Desconocido"

    def _actualizar_tabla(self, ruta: Path):
        """
        Actualiza la tabla de archivos/carpetas según la ruta actual y el filtro de búsqueda.
        Ordena y muestra los elementos con iconos y datos relevantes.
        """
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        filtro = self.entrada_busqueda.get().strip().lower()
        if filtro == "buscar archivos...":
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

                icono = "📄" if item.is_file() else "📁"
                nombre = f"{icono} {item.name}"
                tipo = self._obtener_tipo_archivo(item)
                size_bytes = item.stat().st_size if item.is_file() else -1
                size_str = f"{size_bytes // 1024:,} KB" if item.is_file() else "—"
                fecha_mod = item.stat().st_mtime
                fecha_str = datetime.fromtimestamp(fecha_mod).strftime("%d/%m/%Y %H:%M")

                elementos.append((nombre, tipo, size_bytes, size_str, fecha_mod, fecha_str))
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo acceder al directorio:\n{str(e)}")
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
        """
        Llena el árbol de directorios de la barra lateral izquierda de forma recursiva.
        """
        for item in sorted(ruta.iterdir(), key=lambda x: x.name.lower()):
            if item.is_dir():
                nombre = f"📁 {item.name}"
                nodo = self.arbol.insert(nodo_padre, "end", text=nombre, open=False)
                self._poblar_arbol(item, nodo)

    def _obtener_ruta_completa(self, nodo):
        """
        Devuelve la ruta absoluta de un nodo del árbol de directorios.
        """
        partes = []
        while nodo:
            texto = self.arbol.item(nodo)["text"]
            if texto.startswith("📁 "):
                texto = texto[2:].strip()
            partes.insert(0, texto)
            nodo = self.arbol.parent(nodo)
        return self.BASE_DIR.joinpath(*partes)

    def _al_seleccionar_carpeta(self, event):
        """
        Evento: actualiza la vista al seleccionar una carpeta en el árbol.
        """
        seleccionado = self.arbol.selection()
        if seleccionado:
            ruta = self._obtener_ruta_completa(seleccionado[0])
            if ruta.exists():
                self._navegar_a(ruta)

    # ---------------- Menús Contextuales ----------------

    def _menu_contexto_arbol(self, event):
        """
        Muestra el menú contextual al hacer clic derecho en el árbol de carpetas.
        """
        item = self.arbol.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0, font=obtener_fuente('normal'))

        if item:
            self.arbol.selection_set(item)
            ruta = self._obtener_ruta_completa(item)
            if ruta.is_dir():
                menu.add_command(label="🔍 Abrir carpeta", command=lambda: self._navegar_a(ruta))
                menu.add_command(label="✏️ Renombrar", command=lambda: self._renombrar(ruta, item, True))
                if not any(ruta.iterdir()):
                    menu.add_command(label="🗑️ Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
            else:
                menu.add_command(label="🔍 Abrir carpeta", command=lambda: self._navegar_a(ruta))
                menu.add_command(label="✏️ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑️ Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(self.ruta_actual))
            menu.add_command(label="⬆️ Subir archivo", command=self._subir_archivo)
            menu.add_command(label="📦 Subir carpeta", command=self._subir_carpeta)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _menu_contexto_tabla(self, event):
        """
        Muestra el menú contextual al hacer clic derecho en la tabla de archivos/carpetas.
        """
        item = self.tabla.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0, font=obtener_fuente('normal'))

        if item:
            nombre = self.tabla.item(item, "values")[0]
            if nombre.startswith(("📁", "📄", "🗀", "📶", "❓")):
                nombre = nombre[2:].strip()

            ruta = self.ruta_actual / nombre

            if ruta.is_file():
                menu.add_command(label="✏️ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑️ Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📥 Solicitar descarga", command=lambda: self._solicitar_descarga(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
            elif ruta.is_dir():
                menu.add_command(label="🔍 Abrir carpeta", command=lambda: self._navegar_a(ruta))
                menu.add_command(label="✏️ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑️ Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
                menu.add_command(label="📥 Solicitar descarga", command=lambda: self._solicitar_descarga_carpeta(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(self.ruta_actual))
            menu.add_command(label="⬆️ Subir archivo", command=self._subir_archivo)
            menu.add_command(label="📦 Subir carpeta", command=self._subir_carpeta)
        
        menu.tk_popup(event.x_root, event.y_root)

    # ---------------- Acciones ----------------
    def _renombrar(self, ruta, item, es_arbol):
        """
        Permite renombrar archivos o carpetas, actualizando la base de datos y la interfaz.
        """
        nombre_original = ruta.name
        nombre_original = self._limpiar_emoji(nombre_original)

        extension_original = ruta.suffix
        nombre_sin_extension = ruta.stem
        es_carpeta = ruta.is_dir()

        nuevo = simpledialog.askstring(
            "✏️ Renombrar",
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
                        "⚠️ Cambiar extensión",
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

                # Logs DB usando sistema optimizado
                ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
                tipo = "carpeta_renombrada" if es_carpeta else "archivo_renombrado"
                motivo_log = f"Renombrado de '{nombre_original}' a '{nuevo}'"

                # Buscar archivo_id usando sistema optimizado
                archivo_id = archivo_manager.buscar_archivo_id(nombre_original, ruta_relativa)
                if archivo_id:
                    archivo_manager.registrar_log(self.user_id, archivo_id, tipo, motivo_log, nombre_original)
                    archivo_manager.actualizar_nombre_archivo(archivo_id, nuevo, ruta_relativa, nombre_original)

                messagebox.showinfo("✅ Éxito", f"'{nombre_original}' renombrado correctamente a '{nuevo}'.")

            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo renombrar:\n{str(e)}")
                
    def _eliminar(self, ruta):
        """
        Elimina archivos o carpetas (con todo su contenido) y registra la acción en la base de datos.
        """
        nombre_original = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        es_carpeta = ruta.is_dir()

        # 🚫 Bloquear eliminación de archivos
        if not es_carpeta:
            messagebox.showwarning("🚫 Acceso denegado", "No tienes permiso para eliminar archivos.")
            return

        # 🚫 Bloquear carpetas con contenido
        if any(ruta.iterdir()):
            messagebox.showwarning("🚫 Acceso denegado", "Solo puedes eliminar carpetas vacías.")
            return

        # ✅ Permitir eliminación de carpeta vacía
        confirmar = messagebox.askyesno("⚠️ Confirmar eliminación", 
                                      f"¿Seguro que deseas eliminar la carpeta vacía '{nombre_original}'?")
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
              # Registrar eliminación usando sistema optimizado
            archivo_id = archivo_manager.buscar_archivo_id(nombre_original, ruta_relativa)
            if archivo_id:
                archivo_manager.registrar_log(self.user_id, archivo_id, "carpeta_eliminada", 
                                            "Carpeta vacía eliminada por usuario", nombre_original)
            messagebox.showinfo("✅ Éxito", "🗑️ Carpeta vacía eliminada correctamente.")
            
        except Exception as e:            messagebox.showerror("❌ Error", f"No se pudo eliminar:\n{str(e)}")
                
    def _solicitar_descarga(self, ruta: Path):
        """
        Permite al usuario solicitar la descarga de un archivo, registrando la solicitud para aprobación del administrador.
        """
        # Obtener información del archivo
        nombre_archivo = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        size_bytes = ruta.stat().st_size if ruta.is_file() else 0
        size_str = f"{size_bytes // 1024} KB" if size_bytes >= 1024 else f"{size_bytes} B"
        fecha_mod = datetime.fromtimestamp(ruta.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        
        # Log de información inicial
        print(f"=== INICIANDO SOLICITUD DE DESCARGA ===")
        print(f"Archivo: {nombre_archivo}")
        print(f"Ruta relativa: {ruta_relativa}")
        print(f"Tamaño: {size_str}")
        print(f"Usuario ID: {self.user_id}")
        
        # Crear ventana para solicitar descarga con estilo mejorado
        ventana = tk.Toplevel(self.master)
        ventana.title("📥 Solicitud de Descarga")
        ventana.geometry("550x600")  # Tamaño compacto igual que la solicitud de carpeta
        ventana.resizable(True, True)
        ventana.transient(self.master)  # Hace que sea modal
        ventana.grab_set()  # Evita interacciones con la ventana principal
        ventana.configure(bg="#f8f9fa")
        
        # Header con estilo moderno (azul para diferenciarlo de admin que usa verde)
        header_frame = tk.Frame(ventana, bg="#2196F3", height=70)  # Header más alto
        header_frame.pack(fill="x", pady=0)
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(header_frame, 
                               text="📥 SOLICITUD DE DESCARGA",
                               bg="#2196F3", fg="white",
                               font=obtener_fuente('titulo'))  # Texto más grande
        header_label.pack(expand=True)
        
        # Contenedor principal con padding
        main_frame = tk.Frame(ventana, bg="#f8f9fa", padx=25, pady=15)
        main_frame.pack(fill="both", expand=False)

        # Sección de información del archivo
        info_frame = tk.LabelFrame(main_frame, text="📄 Información del Archivo", 
                                  bg="#f8f9fa", fg="#333333",
                                  font=obtener_fuente('subtitulo'),
                                  padx=15, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))

        tk.Label(info_frame, text=f"Nombre: {nombre_archivo}", 
                bg="#f8f9fa", fg="#000000",
                font=obtener_fuente('normal')).pack(anchor="w", pady=2)
        
        tk.Label(info_frame, text=f"Ruta: {ruta_relativa}", 
                bg="#f8f9fa", fg="#666666",
                font=obtener_fuente('normal')).pack(anchor="w", pady=2)
                
        tk.Label(info_frame, text=f"Tamaño: {size_str}", 
                bg="#f8f9fa", fg="#666666",
                font=obtener_fuente('normal')).pack(anchor="w", pady=2)
                
        tk.Label(info_frame, text=f"Fecha modificación: {fecha_mod}", 
                bg="#f8f9fa", fg="#666666",
                font=obtener_fuente('normal')).pack(anchor="w", pady=2)
        
        # Sección de motivo
        motivo_frame = tk.LabelFrame(main_frame, text="📋 Motivo de Solicitud", 
                                    bg="#f8f9fa", fg="#333333",
                                    font=obtener_fuente('subtitulo'),
                                    padx=15, pady=10)
        motivo_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(motivo_frame, text="Selecciona el motivo:", 
                bg="#f8f9fa", fg="#2c3e50",
                font=obtener_fuente('normal')).pack(anchor="w", pady=(5, 5))
        
        motivo_combo = ttk.Combobox(motivo_frame, values=[
            "Solicitud", "Trabajo interno", "Modificación de datos", "Otro motivo"
        ], state="readonly", font=obtener_fuente('normal'), width=40)
        motivo_combo.pack(fill="x", pady=(0, 10))
        motivo_combo.set("Trabajo interno")  # Valor por defecto
        
        # Label para el detalle (cambia según la selección)
        label_detalle = tk.Label(motivo_frame, text="Nombre del trabajo:", 
                               bg="#f8f9fa", fg="#2c3e50",
                               font=obtener_fuente('normal'))
        label_detalle.pack(anchor="w", pady=(5, 5))
        
        # Text widget para el detalle más grande (en lugar de Entry en admin.py)
        text_container = tk.Frame(motivo_frame, bg="#f8f9fa")
        text_container.pack(fill="x")
        
        entry_detalle = tk.Text(text_container, width=40, height=4, 
                             font=obtener_fuente('normal'), wrap=tk.WORD,
                             relief="solid", bd=1)
        entry_detalle.pack(side="left", fill="x", expand=False)
        
        # Scrollbar para text widget
        scrollbar = tk.Scrollbar(text_container, orient="vertical", command=entry_detalle.yview)
        scrollbar.pack(side="right", fill="y")
        entry_detalle.config(yscrollcommand=scrollbar.set)
        entry_detalle.config(bg="#e3f2fd")  # Color de fondo azul claro
        
        # Función para actualizar el label según la selección
        def actualizar_label(event):
            seleccion = motivo_combo.get()
            entry_detalle.delete("1.0", tk.END)
            
            if seleccion == "Solicitud":
                label_detalle.config(text="Número de solicitud y justificación:")
                entry_detalle.config(bg="#e8f5e8")  # Verde claro
            elif seleccion == "Trabajo interno":
                label_detalle.config(text="Nombre y descripción del trabajo:")
                entry_detalle.config(bg="#e3f2fd")  # Azul claro
            elif seleccion == "Modificación de datos":
                label_detalle.config(text="Justifica detalladamente la modificación:")
                entry_detalle.config(bg="#fff3e0")  # Naranja claro
            elif seleccion == "Otro motivo":
                label_detalle.config(text="Describe con detalle el motivo exacto:")
                entry_detalle.config(bg="#fce4ec")  # Rosa claro
                
            entry_detalle.focus_set()
            print(f"Tipo de motivo seleccionado: {seleccion}")
        
        # Vincular función al evento de selección del combobox
        motivo_combo.bind("<<ComboboxSelected>>", actualizar_label)
        
        # Variables para almacenar el resultado
        solicitud_exitosa = [False, ""]  # [éxito, motivo]
        
        # Función para procesar la solicitud de descarga
        def procesar_solicitud():
            tipo = motivo_combo.get()
            detalle = entry_detalle.get("1.0", tk.END).strip()
            print(f"Procesando solicitud de descarga:")
            print(f"- Tipo de motivo: {tipo}")
            print(f"- Detalle: {detalle}")

            # Validaciones
            if not tipo or not detalle:
                messagebox.showerror("⚠️ Error", "Debes completar tanto el motivo como el detalle.", parent=ventana)
                print("ERROR: Campos incompletos")
                return

            if tipo == "Solicitud":
                # Solo permitir números y espacios
                if not all(c.isdigit() or c.isspace() for c in detalle):
                    messagebox.showerror("⚠️ Formato inválido", "Para 'Solicitud' solo se permiten números y espacios.", parent=ventana)
                    print("ERROR: Formato inválido para solicitud (solo números y espacios)")
                    return
                if len(detalle.replace(' ', '')) < 1:
                    messagebox.showerror("⚠️ Error", "Debes ingresar al menos un número para la solicitud.", parent=ventana)
                    print("ERROR: Solicitud vacía")
                    return
            else:
                # Para otros motivos, solo validar que no esté vacío
                if len(detalle) < 1:
                    messagebox.showerror("⚠️ Error", "Debes ingresar un detalle para el motivo.", parent=ventana)
                    print("ERROR: Detalle vacío")
                    return

            motivo_final = f"{tipo}: {detalle}"
            print(f"- Motivo final: {motivo_final}")
            
            try:
                # Buscar el ID del archivo en la base de datos
                archivo_id = archivo_manager.buscar_archivo_id(nombre_archivo, ruta_relativa)
                print(f"- ID del archivo en DB: {archivo_id}")
                
                if not archivo_id:
                    messagebox.showerror("❌ Error", "No se encontró el archivo en la base de datos.", parent=ventana)
                    print("ERROR: Archivo no encontrado en la base de datos")
                    return
                
                # Registrar la solicitud en la base de datos
                print(f"- Registrando solicitud en DB: user_id={self.user_id}, archivo_id={archivo_id}, motivo={motivo_final}")
                exito = archivo_manager.crear_solicitud_descarga(self.user_id, archivo_id, motivo_final)
                print(f"- Resultado del registro: {'EXITOSO' if exito else 'FALLIDO'}")
                
                if exito:
                    solicitud_exitosa[0] = True
                    solicitud_exitosa[1] = motivo_final
                    ventana.destroy()
                else:
                    messagebox.showwarning("⚠️ Advertencia", 
                                        "No se pudo registrar la solicitud en la base de datos.", 
                                        parent=ventana)
                
            except Exception as e:
                print(f"ERROR en la solicitud: {str(e)}")
                messagebox.showerror("❌ Error", f"Error al procesar la solicitud: {str(e)}", parent=ventana)
        
        # Función para cancelar
        def cancelar():
            print("Solicitud cancelada por el usuario")
            ventana.destroy()
            
        # Función para efectos hover
        def on_enter(e, btn, color):
            btn.configure(bg=color)
        
        def on_leave(e, btn, original_color):
            btn.configure(bg=original_color)
        
        # Separador para dar más énfasis a los botones
        separador = tk.Frame(main_frame, bg="#e0e0e0", height=1)
        separador.pack(fill="x", pady=(15, 15))
        
        # Botones con estilo moderno y bien posicionados
        botones_frame = tk.Frame(main_frame, bg="#f8f9fa")
        botones_frame.pack(fill="x", pady=(10, 5))
        btn_solicitar = tk.Button(botones_frame, text="📤 Enviar Solicitud", bg="#2196F3", fg="white", font=obtener_fuente('boton'), padx=25, pady=8, relief="flat", cursor="hand2")
        btn_cancelar = tk.Button(botones_frame, text="❌ Cancelar", command=cancelar, bg="#F44336", fg="white", font=obtener_fuente('boton'), padx=20, pady=8, relief="flat", cursor="hand2")
        btn_solicitar.pack(side="left", padx=(0, 20))
        btn_cancelar.pack(side="left")
        botones_frame.pack_configure(anchor="center")
        
        # Aplicar efectos hover
        btn_solicitar.bind("<Enter>", lambda e: on_enter(e, btn_solicitar, "#1976D2"))  # Azul más oscuro
        btn_solicitar.bind("<Leave>", lambda e: on_leave(e, btn_solicitar, "#2196F3"))
        
        btn_cancelar.bind("<Enter>", lambda e: on_enter(e, btn_cancelar, "#d32f2f"))
        btn_cancelar.bind("<Leave>", lambda e: on_leave(e, btn_cancelar, "#F44336"))
        
        # Centrar ventana
        centrar_ventana(ventana, 550, 600)
        
        # Esperar a que se cierre la ventana
        self.master.wait_window(ventana)
        
        # Mostrar mensaje de éxito si la solicitud fue exitosa
        if solicitud_exitosa[0]:
            print(f"=== SOLICITUD ENVIADA EXITOSAMENTE ===")
            messagebox.showinfo("✅ Solicitud Enviada", 
                             f"La solicitud para '{nombre_archivo}' ha sido enviada.\n" +
                             "Se te notificará cuando sea procesada.")
        else:
            print(f"=== SOLICITUD NO COMPLETADA ===")

    def _subir_archivo(self):
        """
        Permite al usuario subir un archivo al directorio actual y lo registra en la base de datos.
        """
        archivo = filedialog.askopenfilename(title="Seleccionar archivo para subir")
        if archivo:
            nombre_archivo = os.path.basename(archivo)
            destino = self.ruta_actual / nombre_archivo

            if destino.exists():
                messagebox.showwarning(
                    "⚠️ Archivo existente",
                    f"Ya existe un archivo llamado '{nombre_archivo}' en esta carpeta.\nPor favor, cambia el nombre o elimínalo primero."
                )
                return

            try:
                shutil.copy2(archivo, destino)

                # Registrar en base de datos usando sistema optimizado
                ruta_relativa = str(self.ruta_actual.relative_to(self.BASE_DIR))

                archivo_id = archivo_manager.registrar_archivo(nombre_archivo, ruta_relativa, self.user_id, es_carpeta=False)
                if archivo_id:
                    archivo_manager.registrar_log(self.user_id, archivo_id, "subido", "Archivo cargado al sistema", nombre_archivo)

                self._actualizar_tabla(self.ruta_actual)
                messagebox.showinfo("✅ Éxito", f"Archivo '{nombre_archivo}' subido correctamente.")

            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo subir el archivo:\n{str(e)}")

    def _subir_carpeta(self):
        """
        Permite al usuario subir una carpeta completa (con su contenido) al directorio actual y lo registra en la base de datos.
        """
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para subir")
        if not carpeta:
            return

        carpeta_path = Path(carpeta)
        nombre_carpeta = carpeta_path.name
        destino = self.ruta_actual / nombre_carpeta

        if destino.exists():
            messagebox.showwarning(
                "⚠️ Carpeta existente",
                f"Ya existe una carpeta llamada '{nombre_carpeta}' en esta ubicación.\nPor favor, cambia el nombre o elimínala primero."
            )
            return

        # Confirmar subida
        confirmar = messagebox.askyesno(
            "📁 Subir carpeta",
            f"¿Deseas subir la carpeta '{nombre_carpeta}' y todo su contenido?"
        )
        if not confirmar:
            return

        try:
            # Crear la carpeta destino
            destino.mkdir(exist_ok=True)
            
            # Registrar la carpeta en la base de datos
            ruta_relativa = str(self.ruta_actual.relative_to(self.BASE_DIR))
            carpeta_id = archivo_manager.registrar_archivo(nombre_carpeta, ruta_relativa, self.user_id, es_carpeta=True)
            
            if carpeta_id:
                archivo_manager.registrar_log(self.user_id, carpeta_id, "carpeta_creada", 
                                           "Carpeta creada por subida masiva", nombre_carpeta)

            # Copiar todo el contenido
            archivos_copiados = 0
            carpetas_creadas = 0
            
            for item in carpeta_path.rglob("*"):
                if item.is_file():
                    # Calcular ruta relativa dentro de la carpeta
                    ruta_relativa_item = item.relative_to(carpeta_path)
                    destino_item = destino / ruta_relativa_item
                    
                    # Crear subcarpetas si es necesario
                    destino_item.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copiar archivo
                    shutil.copy2(item, destino_item)
                    archivos_copiados += 1
                    
                    # Registrar archivo en la base de datos
                    ruta_relativa_db = str((destino / ruta_relativa_item.parent).relative_to(self.BASE_DIR))
                    archivo_id = archivo_manager.registrar_archivo(
                        item.name, ruta_relativa_db, self.user_id, es_carpeta=False
                    )
                    if archivo_id:
                        archivo_manager.registrar_log(
                            self.user_id, archivo_id, "subido", 
                            "Archivo subido como parte de carpeta masiva", 
                            item.name
                        )
                elif item.is_dir():
                    carpetas_creadas += 1

            # Actualizar interfaz
            self._actualizar_tabla(self.ruta_actual)
            self.arbol.delete(*self.arbol.get_children())
            self._poblar_arbol(self.BASE_DIR)

            messagebox.showinfo(
                "✅ Éxito", 
                f"Carpeta '{nombre_carpeta}' subida correctamente.\n"
                f"Archivos copiados: {archivos_copiados}\n"
                f"Carpetas creadas: {carpetas_creadas}"
            )

        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo subir la carpeta:\n{str(e)}")

    def _crear_carpeta(self, donde):
        """
        Crea una nueva carpeta en la ubicación indicada y la registra en la base de datos.
        """
        nombre = simpledialog.askstring("📁 Nueva Carpeta", "Nombre de la carpeta:")
        if nombre:
            nueva = donde / nombre
            try:
                nueva.mkdir(exist_ok=False)

                # Base de datos usando sistema optimizado
                ruta_relativa = str(donde.relative_to(self.BASE_DIR))
                archivo_id = archivo_manager.registrar_archivo(nombre, ruta_relativa, self.user_id, es_carpeta=True)

                if archivo_id:
                    archivo_manager.registrar_log(self.user_id, archivo_id, "carpeta_creada", "Carpeta creada manualmente", nombre)

                # Refrescar
                self._actualizar_tabla(self.ruta_actual)
                self.arbol.delete(*self.arbol.get_children())
                self._poblar_arbol(self.BASE_DIR)

                messagebox.showinfo("✅ Éxito", f"Carpeta '{nombre}' creada correctamente.")

            except FileExistsError:
                messagebox.showerror("❌ Error", "Ya existe una carpeta con ese nombre.")
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo crear la carpeta:\n{str(e)}")

    def _abrir_item_tabla(self, event):
        """
        Permite navegar a una carpeta al hacer doble clic en la tabla. No abre archivos.
        """
        item_id = self.tabla.identify_row(event.y)
        if not item_id:
            return
        nombre_completo = self.tabla.item(item_id, "values")[0]
        nombre_limpio = nombre_completo[2:].strip() if nombre_completo.startswith(("📄", "📁")) else nombre_completo
        ruta = self.ruta_actual / nombre_limpio
        if ruta.is_dir():
            self._navegar_a(ruta)

    def _mover_a(self, ruta_origen):
        """
        Permite mover un archivo o carpeta a otra ubicación dentro del directorio base, actualizando la base de datos.
        """
        ventana = tk.Toplevel(self.master)
        ventana.title("📁 SELECCIONAR CARPETA DESTINO")
        centrar_ventana(ventana, 400, 500)
        ventana.configure(bg="#f5f5f5")

        # Header
        header = tk.Frame(ventana, bg="#FF9800", relief="raised", bd=2)
        header.pack(fill="x", padx=10, pady=10)
        tk.Label(header, text="📁 MOVER A CARPETA", 
                bg="#FF9800", fg="#ffffff",
                font=obtener_fuente('titulo'), 
                anchor="center", pady=8).pack(fill="x")

        arbol_destino = ttk.Treeview(ventana)
        arbol_destino.pack(fill="both", expand=True, padx=15, pady=10)

        def poblar_arbol_carpeta(ruta, nodo_padre=""):
            for item in ruta.iterdir():
                if item.is_dir():
                    nodo = arbol_destino.insert(nodo_padre, "end", text=f"📁 {item.name}")
                    poblar_arbol_carpeta(item, nodo)

        poblar_arbol_carpeta(self.BASE_DIR)

        def mover():
            nodo = arbol_destino.selection()
            if not nodo:
                messagebox.showerror("❌ Error", "Selecciona una carpeta destino")
                return

            partes = []
            actual = nodo[0]
            while actual:
                texto = arbol_destino.item(actual)["text"]
                if texto.startswith("📁 "):
                    texto = texto[2:].strip()
                partes.insert(0, texto)
                actual = arbol_destino.parent(actual)

            carpeta_destino = self.BASE_DIR.joinpath(*partes)
            nuevo_ruta = carpeta_destino / ruta_origen.name

            try:
                if ruta_origen.resolve() == nuevo_ruta.resolve():
                    messagebox.showwarning("⚠️ Aviso", "El origen y el destino son iguales.")
                    return

                # Validar que no se mueva carpeta dentro de sí misma o sus subcarpetas
                if ruta_origen.is_dir() and nuevo_ruta.resolve().is_relative_to(ruta_origen.resolve()):
                    messagebox.showerror("❌ Error", "No puedes mover una carpeta dentro de sí misma o de una subcarpeta.")
                    return
                
                shutil.move(str(ruta_origen), str(nuevo_ruta))
                
                # Base de datos usando sistema optimizado
                ruta_anterior = str(ruta_origen.parent.relative_to(self.BASE_DIR))
                ruta_nueva = str(carpeta_destino.relative_to(self.BASE_DIR))
                archivo_id = archivo_manager.buscar_archivo_id(ruta_origen.name, ruta_anterior)

                if archivo_id:
                    archivo_manager.actualizar_ruta_archivo(archivo_id, ruta_nueva, ruta_origen.name, ruta_anterior)
                    archivo_manager.registrar_log(self.user_id, archivo_id, "movido",
                                f"Movido de '{ruta_anterior}' a '{ruta_nueva}'", ruta_origen.name)

                self._actualizar_tabla(self.ruta_actual)
                self.arbol.delete(*self.arbol.get_children())
                self._poblar_arbol(self.BASE_DIR)

                messagebox.showinfo("✅ Éxito", f"'{ruta_origen.name}' movido correctamente.")
                ventana.destroy()
                
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo mover:\n{str(e)}")

    def _on_window_resize(self, event):
        """
        Maneja el redimensionamiento de la ventana para actualizar la barra de ruta.
        """
        # Solo responder al redimensionamiento de la ventana principal, no de widgets internos
        if event.widget == self.master:
            # Usar un pequeño delay para evitar actualizaciones excesivas
            if hasattr(self, '_resize_timer'):
                self.master.after_cancel(self._resize_timer)
            self._resize_timer = self.master.after(100, 
                lambda: self._dibujar_ruta_responsiva(self.ruta_actual))

    def _solicitar_descarga_carpeta(self, ruta: Path):
        """
        Permite al usuario solicitar la descarga de una carpeta, registrando la solicitud para aprobación del administrador.
        """
        nombre_carpeta = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        fecha_mod = datetime.fromtimestamp(ruta.stat().st_mtime).strftime("%d/%m/%Y %H:%M")

        ventana = tk.Toplevel(self.master)
        ventana.title("📥 Solicitud de Descarga de Carpeta")
        ventana.geometry("550x600")
        ventana.resizable(False, False)
        ventana.transient(self.master)
        ventana.grab_set()
        ventana.configure(bg="#f8f9fa")

        header_frame = tk.Frame(ventana, bg="#2196F3", height=70)
        header_frame.pack(fill="x", pady=0)
        header_frame.pack_propagate(False)
        header_label = tk.Label(header_frame, text="📥 SOLICITUD DE DESCARGA DE CARPETA", bg="#2196F3", fg="white", font=obtener_fuente('titulo'))
        header_label.pack(expand=True)

        main_frame = tk.Frame(ventana, bg="#f8f9fa", padx=25, pady=15)
        main_frame.pack(fill="both", expand=False)

        info_frame = tk.LabelFrame(main_frame, text="📁 Información de la Carpeta", bg="#f8f9fa", fg="#333333", font=obtener_fuente('subtitulo'), padx=15, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))
        tk.Label(info_frame, text=f"Nombre: {nombre_carpeta}", bg="#f8f9fa", fg="#000000", font=obtener_fuente('normal')).pack(anchor="w", pady=2)
        tk.Label(info_frame, text=f"Ruta: {ruta_relativa}", bg="#f8f9fa", fg="#666666", font=obtener_fuente('normal')).pack(anchor="w", pady=2)
        tk.Label(info_frame, text=f"Fecha modificación: {fecha_mod}", bg="#f8f9fa", fg="#666666", font=obtener_fuente('normal')).pack(anchor="w", pady=2)

        motivo_frame = tk.LabelFrame(main_frame, text="📋 Motivo de Solicitud", bg="#f8f9fa", fg="#333333", font=obtener_fuente('subtitulo'), padx=15, pady=10)
        motivo_frame.pack(fill="x", pady=(0, 5))
        tk.Label(motivo_frame, text="Selecciona el motivo:", bg="#f8f9fa", fg="#2c3e50", font=obtener_fuente('normal')).pack(anchor="w", pady=(5, 5))
        motivo_combo = ttk.Combobox(motivo_frame, values=["Solicitud", "Trabajo interno", "Modificación de datos", "Otro motivo"], state="readonly", font=obtener_fuente('normal'), width=40)
        motivo_combo.pack(fill="x", pady=(0, 8))
        entry_detalle = tk.Text(motivo_frame, height=3, font=obtener_fuente('normal'))
        entry_detalle.pack(fill="x", pady=(0, 5))

        separador = tk.Frame(main_frame, bg="#e0e0e0", height=1)
        separador.pack(fill="x", pady=(15, 15))
        botones_frame = tk.Frame(main_frame, bg="#f8f9fa")
        botones_frame.pack(fill="x", pady=(0, 0))
        btn_solicitar = tk.Button(botones_frame, text="📤 Enviar Solicitud", bg="#2196F3", fg="white", font=obtener_fuente('boton'), padx=25, pady=8, relief="flat", cursor="hand2")
        btn_cancelar = tk.Button(botones_frame, text="❌ Cancelar", command=ventana.destroy, bg="#F44336", fg="white", font=obtener_fuente('boton'), padx=20, pady=8, relief="flat", cursor="hand2")
        btn_solicitar.pack(side="left", padx=(0, 20))
        btn_cancelar.pack(side="left")
        botones_frame.pack_configure(anchor="center")

        def procesar_solicitud():
            tipo = motivo_combo.get()
            detalle = entry_detalle.get("1.0", tk.END).strip()
            if not tipo or not detalle:
                messagebox.showerror("⚠️ Error", "Debes completar tanto el motivo como el detalle.", parent=ventana)
                return
            motivo_final = f"{tipo}: {detalle}"
            try:
                carpeta_id = archivo_manager.buscar_archivo_id(nombre_carpeta, ruta_relativa)
                if not carpeta_id:
                    messagebox.showerror("❌ Error", "No se encontró la carpeta en la base de datos.", parent=ventana)
                    return
                exito = archivo_manager.crear_solicitud_descarga(self.user_id, carpeta_id, motivo_final)
                if exito:
                    ventana.destroy()
                    messagebox.showinfo("✅ Solicitud Enviada", f"La solicitud para la carpeta '{nombre_carpeta}' ha sido enviada.\nSe te notificará cuando sea procesada.")
                else:
                    messagebox.showwarning("⚠️ Advertencia", "No se pudo registrar la solicitud en la base de datos.", parent=ventana)
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error al procesar la solicitud: {str(e)}", parent=ventana)

        btn_solicitar.config(command=procesar_solicitud)
        centrar_ventana(ventana, 550, 600)
        self.master.wait_window(ventana)
