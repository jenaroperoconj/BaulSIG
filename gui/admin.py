import os
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from db.file_manager import archivo_manager
from gui.login import iniciar_login
from tkinterdnd2 import DND_FILES, TkinterDnD
from core.utils import centrar_ventana
from core.config import ARCHIVOS_COMPARTIDOS_DIR
from core.ui_config import (
    configurar_ventana_principal, obtener_fuente, crear_boton_estilizado,
    aplicar_estilo_tabla, COLORES, ESPACIOS
)

# Clase principal del explorador de archivos para el administrador
class ExploradorAdmin:
    def __init__(self, master, modo_oscuro=False, es_admin=True, user_id=None):
        """
        Inicializa la ventana principal del explorador de archivos para el administrador.
        Configura la interfaz, carga los widgets y establece la ruta base.
        """
        self.user_id = user_id
        self.es_admin = es_admin
        self.orden_columna = None
        self.orden_descendente = False
        self.master = master
        self.BASE_DIR = Path(ARCHIVOS_COMPARTIDOS_DIR)
        self.modo_oscuro = modo_oscuro
        # Configuración de la ventana principal
        self.master.title("🔧 EXPLORADOR DE ARCHIVOS - ADMINISTRADOR")
        configurar_ventana_principal(self.master, 'admin_principal')
        self.historial = []
        self.historial_pos = -1
        self.ruta_actual = self.BASE_DIR
        if not self.BASE_DIR.exists():
            self.BASE_DIR.mkdir()
        self._crear_widgets()
        self._aplicar_estilo()
        self._poblar_arbol(self.BASE_DIR)
        self._navegar_a(self.BASE_DIR)

    def _cerrar_sesion(self):
        """Cierra la sesión actual y vuelve a la pantalla de login."""
        self.master.destroy()
        iniciar_login(modo=self.modo_oscuro)
    
    def _limpiar_emoji(self, texto):
        """Elimina emojis de los nombres de archivos/carpetas para operaciones internas."""
        if texto.startswith(("📁", "📄", "❓", "🗀", "📶")):
            return texto[2:].strip()
        return texto
    
    def _mostrar_popup_solicitudes(self):
        """
        Muestra la ventana emergente para gestionar las solicitudes de descarga pendientes.
        Permite aprobar, rechazar, ver historial y aprobar todas las solicitudes.
        """
        ventana = tk.Toplevel(self.master)
        ventana.title("📥 Solicitudes de Descarga - Panel de Administración")
        ventana.configure(bg="#f5f5f5")
        centrar_ventana(ventana, 1400, 600)
        ventana.resizable(True, True)
        ventana.minsize(1000, 500)
        contenedor_principal = tk.Frame(ventana, bg="#f5f5f5")
        contenedor_principal.pack(fill="both", expand=True, padx=15, pady=15)
        # Encabezado de la ventana
        header_frame = tk.Frame(contenedor_principal, bg="#2196F3", relief="raised", bd=3, height=60)
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.pack_propagate(False)
        titulo_label = tk.Label(header_frame, text="📥 GESTIÓN DE SOLICITUDES DE DESCARGA", 
                               bg="#2196F3", fg="#ffffff",
                               font=("Segoe UI", 16, "bold"), 
                               anchor="center")
        titulo_label.pack(fill="both", expand=True, pady=15)
        # Contenedor para la tabla de solicitudes
        tabla_container = tk.Frame(contenedor_principal, bg="#ffffff", relief="groove", bd=2)
        tabla_container.pack(fill="both", expand=True, pady=(0, 15))
        tabla_header = tk.Frame(tabla_container, bg="#4CAF50", relief="raised", bd=2)
        tabla_header.pack(fill="x", padx=8, pady=8)
        tk.Label(tabla_header, text="📋 SOLICITUDES PENDIENTES", 
                bg="#4CAF50", fg="#ffffff",
                font=("Segoe UI", 12, "bold"), 
                anchor="center", pady=6).pack(fill="x")
        # Tabla de solicitudes
        tabla = ttk.Treeview(tabla_container, columns=("Usuario", "Archivo", "Estado", "Motivo", "Fecha solicitud"), show="headings")
        tabla.column("#0", width=0, stretch=False)
        tabla.column("Usuario", width=150, minwidth=120, anchor="w")
        tabla.column("Archivo", width=300, minwidth=200, anchor="w")
        tabla.column("Estado", width=120, minwidth=100, anchor="center")
        tabla.column("Motivo", width=250, minwidth=200, anchor="w")
        tabla.column("Fecha solicitud", width=150, minwidth=130, anchor="center")
        for col in tabla["columns"]:
            tabla.heading(col, text=col, anchor="center")
        tabla.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        # Función para cargar solicitudes pendientes
        def cargar():
            solicitudes = archivo_manager.obtener_solicitudes_pendientes()
            for row in tabla.get_children():
                tabla.delete(row)
            for fila in solicitudes:
                fecha = fila[5].strftime("%d/%m/%Y %H:%M") if fila[5] else ""
                valores = (fila[1], fila[2], fila[3], fila[4], fecha)
                tabla.insert("", "end", iid=fila[0], values=valores)
        # Función para aprobar una solicitud seleccionada
        def aprobar():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Seleccionar", "Selecciona una solicitud para aprobar.")
                return
            motivo = tabla.item(item_id, "values")[3]
            exito = archivo_manager.aprobar_solicitud(item_id, motivo)
            if exito:
                cargar()
                messagebox.showinfo("Aprobada", "La solicitud fue aprobada.", parent=ventana)
                ventana.lift()
                ventana.focus_force()
        # Función para rechazar una solicitud seleccionada
        def rechazar():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Seleccionar", "Selecciona una solicitud para rechazar.")
                return
            motivo = tabla.item(item_id, "values")[3]
            exito = archivo_manager.rechazar_solicitud(item_id, motivo)
            if exito:
                cargar()
                messagebox.showinfo("Rechazada", "La solicitud fue rechazada.", parent=ventana)
                ventana.lift()
                ventana.focus_force()
        # Función para ver el historial de motivos de una solicitud
        def ver_historial():
            item_id = tabla.focus()
            if not item_id:
                messagebox.showwarning("Seleccionar", "Selecciona una solicitud para ver el historial.")
                return

            ventana_historial = tk.Toplevel(ventana)
            ventana_historial.title("📜 Historial Completo de Motivos")
            ventana_historial.configure(bg="#f5f5f5")
            centrar_ventana(ventana_historial, 800, 450)
            ventana_historial.resizable(True, True)
            ventana_historial.minsize(600, 300)
            
            # Contenedor principal
            contenedor_hist = tk.Frame(ventana_historial, bg="#f5f5f5")
            contenedor_hist.pack(fill="both", expand=True, padx=15, pady=15)
            
            # Encabezado estilizado
            header_hist = tk.Frame(contenedor_hist, bg="#FF9800", relief="raised", bd=3, height=50)
            header_hist.pack(fill="x", pady=(0, 15))
            header_hist.pack_propagate(False)
            
            tk.Label(header_hist, text="📜 HISTORIAL DETALLADO DE SOLICITUD", 
                    bg="#FF9800", fg="#ffffff",
                    font=("Segoe UI", 14, "bold"), 
                    anchor="center").pack(fill="both", expand=True, pady=12)
            
            # Contenedor de tabla con estilo
            tabla_hist_container = tk.Frame(contenedor_hist, bg="#ffffff", relief="groove", bd=2)
            tabla_hist_container.pack(fill="both", expand=True)
            
            # Subencabezado
            tabla_hist_header = tk.Frame(tabla_hist_container, bg="#4CAF50", relief="raised", bd=2)
            tabla_hist_header.pack(fill="x", padx=8, pady=8)
            
            tk.Label(tabla_hist_header, text="📋 REGISTRO DE CAMBIOS Y MOTIVOS", 
                    bg="#4CAF50", fg="#ffffff",
                    font=("Segoe UI", 11, "bold"), 
                    anchor="center", pady=4).pack(fill="x")

            tabla_hist = ttk.Treeview(tabla_hist_container, columns=("Fecha", "Motivo"), show="headings")
            
            # Configurar columnas
            tabla_hist.column("#0", width=0, stretch=False)
            tabla_hist.column("Fecha", width=200, minwidth=150, anchor="center")
            tabla_hist.column("Motivo", width=400, minwidth=300, anchor="w")
            
            tabla_hist.heading("Fecha", text="📅 FECHA Y HORA", anchor="center")
            tabla_hist.heading("Motivo", text="📝 MOTIVO DETALLADO", anchor="center")
            
            tabla_hist.pack(fill="both", expand=True, padx=12, pady=(8, 12))

            try:
                historial = archivo_manager.obtener_historial_solicitud(item_id)
                for fila in historial:
                    fecha_val = fila[0]
                    motivo = fila[1]
                    # Si la fecha es string, intentar convertirla a datetime
                    if isinstance(fecha_val, str):
                        try:
                            fecha_val = datetime.strptime(fecha_val, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            try:
                                fecha_val = datetime.strptime(fecha_val, "%Y-%m-%d %H:%M:%S.%f")
                            except Exception:
                                pass  # Si falla, dejar como string
                    if hasattr(fecha_val, 'strftime'):
                        fecha = fecha_val.strftime("%d/%m/%Y %H:%M")
                    else:
                        fecha = str(fecha_val)
                    tabla_hist.insert("", "end", values=(fecha, motivo))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el historial:\n{str(e)}")

        # Función para aprobar todas las solicitudes pendientes
        def aprobar_todas():
            if not messagebox.askyesno("Confirmar", 
                "¿Estás seguro de que deseas aprobar todas las solicitudes pendientes?\nEsta acción no se puede deshacer."):
                return
            exito = archivo_manager.aprobar_todas_solicitudes()
            if exito:
                cargar()
                messagebox.showinfo("Éxito", "Todas las solicitudes pendientes han sido aprobadas.", parent=ventana)
                ventana.lift()
                ventana.focus_force()
            else:
                messagebox.showerror("Error", "No se pudieron aprobar todas las solicitudes.", parent=ventana)
        # Frame de botones de acción
        btn_frame = tk.Frame(contenedor_principal, bg="#f5f5f5")
        btn_frame.pack(fill="x", pady=(0, 5))
        # Botón para aprobar todas las solicitudes
        btn_aprobar_todas = tk.Button(btn_frame, text="✅ APROBAR TODAS", 
                               command=aprobar_todas, 
                               bg="#4CAF50", fg="#ffffff",
                               font=("Segoe UI", 11, "bold"), 
                               padx=20, pady=10,
                               relief="raised", bd=2,
                               cursor="hand2")
        btn_aprobar_todas.pack(side="left", padx=(0, 10))
        # Botón para aprobar una solicitud
        btn_aprobar = tk.Button(btn_frame, text="✅ APROBAR SOLICITUD", 
                               command=aprobar, 
                               bg="#388e3c", fg="#ffffff",
                               font=("Segoe UI", 11, "bold"), 
                               padx=20, pady=10,
                               relief="raised", bd=2,
                               cursor="hand2")
        btn_aprobar.pack(side="left", padx=(0, 10))
        # Botón para rechazar una solicitud
        btn_rechazar = tk.Button(btn_frame, text="❌ RECHAZAR SOLICITUD", 
                                command=rechazar, 
                                bg="#F44336", fg="#ffffff",
                                font=("Segoe UI", 11, "bold"), 
                                padx=20, pady=10,
                                relief="raised", bd=2,
                                cursor="hand2")
        btn_rechazar.pack(side="left", padx=(0, 10))
        # Botón para ver historial completo
        btn_historial = tk.Button(btn_frame, text="📜 VER HISTORIAL COMPLETO", 
                                 command=ver_historial, 
                                 bg="#2196F3", fg="#ffffff",
                                 font=("Segoe UI", 11, "bold"), 
                                 padx=20, pady=10,
                                 relief="raised", bd=2,
                                 cursor="hand2")
        btn_historial.pack(side="left", padx=(0, 10))
        # Botón para actualizar la lista
        btn_actualizar = tk.Button(btn_frame, text="🔄 ACTUALIZAR LISTA", 
                                  command=cargar, 
                                  bg="#FF9800", fg="#ffffff",
                                  font=("Segoe UI", 11, "bold"), 
                                  padx=20, pady=10,
                                  relief="raised", bd=2,
                                  cursor="hand2")
        btn_actualizar.pack(side="right")
        # Efectos hover para los botones
        def on_enter(e, btn, color):
            btn.configure(bg=color)
        def on_leave(e, btn, original_color):
            btn.configure(bg=original_color)
        btn_aprobar_todas.bind("<Enter>", lambda e: on_enter(e, btn_aprobar_todas, "#45a049"))
        btn_aprobar_todas.bind("<Leave>", lambda e: on_leave(e, btn_aprobar_todas, "#4CAF50"))
        btn_aprobar.bind("<Enter>", lambda e: on_enter(e, btn_aprobar, "#45a049"))
        btn_aprobar.bind("<Leave>", lambda e: on_leave(e, btn_aprobar, "#4CAF50"))
        btn_rechazar.bind("<Enter>", lambda e: on_enter(e, btn_rechazar, "#d32f2f"))
        btn_rechazar.bind("<Leave>", lambda e: on_leave(e, btn_rechazar, "#F44336"))
        btn_historial.bind("<Enter>", lambda e: on_enter(e, btn_historial, "#1976D2"))
        btn_historial.bind("<Leave>", lambda e: on_leave(e, btn_historial, "#2196F3"))
        
        btn_actualizar.bind("<Enter>", lambda e: on_enter(e, btn_actualizar, "#F57C00"))
        btn_actualizar.bind("<Leave>", lambda e: on_leave(e, btn_actualizar, "#FF9800"))
        
        cargar()
    
    def _crear_widgets(self):
        # Barra superior con espaciado mejorado
        barra_sup = tk.Frame(self.master, bg="#dddddd", padx=20, pady=15, bd=3, relief="groove")
        
        # Botón de solicitudes con fuente más grande
        btn_solicitudes = tk.Button(barra_sup, text="📥 VER SOLICITUDES", 
                                  command=self._mostrar_popup_solicitudes,
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

        # Eventos de selección y menú contextual
        self.arbol.bind("<<TreeviewSelect>>", self._al_seleccionar_carpeta)
        self.tabla.bind("<Double-1>", self._abrir_item_tabla)
        self.arbol.bind("<Button-3>", self._menu_contexto_arbol)
        self.tabla.bind("<Button-3>", self._menu_contexto_tabla)
        # Configurar responsividad para la barra de ruta
        self.master.bind('<Configure>', self._on_window_resize)

    def _limpiar_placeholder_busqueda(self):
        """Limpia el texto de placeholder en la barra de búsqueda."""
        if self.entrada_busqueda.get() == "Buscar archivos...":
            self.entrada_busqueda.delete(0, "end")

    def _restaurar_placeholder_busqueda(self):
        """Restaura el texto de placeholder si la barra de búsqueda está vacía."""
        if not self.entrada_busqueda.get():
            self.entrada_busqueda.insert(0, "Buscar archivos...")

    def _aplicar_estilo(self):
        """Aplica estilos personalizados a los widgets de la interfaz."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#ffffff", foreground="#222222",
                        rowheight=30, fieldbackground="#ffffff",
                        font=('Segoe UI', 11))
        style.configure("Treeview.Heading",
                        background="#e0e0e0", foreground="#000000",
                        font=('Segoe UI', 12, 'bold'))
        style.map("Treeview",
                  background=[('selected', '#2196F3')],
                  foreground=[('selected', '#ffffff')])
        style.configure("TCombobox", font=('Segoe UI', 11))

    def _ordenar_por_columna(self, columna):
        """Ordena la tabla por la columna seleccionada."""
        if self.orden_columna == columna:
            self.orden_descendente = not self.orden_descendente
        else:
            self.orden_columna = columna
            self.orden_descendente = False
        self._actualizar_tabla(self.ruta_actual)

    def _actualizar_barra_ruta(self, path: Path):
        """Actualiza la barra de ruta para mostrar la ubicación actual."""
        for widget in self.ruta_label.winfo_children():
            widget.destroy()
        self.master.after(50, lambda: self._dibujar_ruta_responsiva(path))

    def _dibujar_ruta_responsiva(self, path: Path):
        """Dibuja la barra de ruta de forma responsiva, priorizando mostrar las carpetas finales."""
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
                          font=("Segoe UI", 10, "bold"),
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
                                 font=("Segoe UI", 10, "bold"),
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
                               bg="#ffffcc", fg="#333333", font=("Segoe UI", 9),
                               justify="left", padx=8, pady=4)
                label.pack()
            def ocultar_tooltip(event=None):
                if tooltip[0] is not None:
                    tooltip[0].destroy()
                    tooltip[0] = None
            btn_puntos.bind("<Enter>", mostrar_tooltip)
            btn_puntos.bind("<Leave>", ocultar_tooltip)
            tk.Label(self.ruta_label, text="▶", bg="#e8e8e8", fg="#666666",
                    font=("Segoe UI", 10)).pack(side="left", padx=2)
        for i, (parte, ruta_completa) in enumerate(zip(elementos_a_mostrar, rutas_a_mostrar)):
            btn = tk.Button(self.ruta_label, text=parte, relief="flat",
                          bg="#e8e8e8", fg="#000000",
                          font=("Segoe UI", 10, "bold"),
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
                        font=("Segoe UI", 10)).pack(side="left", padx=2)

    def _on_window_resize(self, event):
        """Manejar el redimensionamiento de la ventana para actualizar la barra de ruta"""
        # Solo responder al redimensionamiento de la ventana principal, no de widgets internos
        if event.widget == self.master:
            # Usar un pequeño delay para evitar actualizaciones excesivas
            if hasattr(self, '_resize_timer'):
                self.master.after_cancel(self._resize_timer)
            self._resize_timer = self.master.after(100, 
                lambda: self._dibujar_ruta_responsiva(self.ruta_actual))

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
                messagebox.showwarning("Acceso denegado", "No puedes salir del directorio compartido.")
                return
        except Exception:
            messagebox.showerror("Error", "Ruta inválida o acceso denegado.")
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
            # Si hay filtro, búsqueda recursiva; si no, solo el directorio actual
            if filtro:
                items = ruta.rglob("*")
            else:
                items = ruta.iterdir()
            for item in items:
                if not item.exists():
                    continue
                if filtro:
                    nombre_limpio = item.name.lower()
                    if filtro not in nombre_limpio:
                        continue
                icono = "📁" if item.is_dir() else "📄"
                nombre = f"{icono} {item.name}"
                tipo = self._obtener_tipo_archivo(item)
                if item.is_file():
                    size_bytes = item.stat().st_size
                    size_str = f"{size_bytes // 1024} KB" if size_bytes >= 1024 else f"{size_bytes} B"
                else:
                    size_bytes = -1
                    size_str = "-"
                fecha_mod = item.stat().st_mtime
                fecha_str = datetime.fromtimestamp(fecha_mod).strftime("%d/%m/%Y %H:%M")
                elementos.append((nombre, tipo, size_bytes, size_str, fecha_mod, fecha_str))
        except PermissionError:
            messagebox.showerror("Error", "No tienes permisos para acceder a este directorio.")
            return
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo acceder al directorio:\n{str(e)}")
            return
        # Ordenar: carpetas primero, luego archivos, según la columna seleccionada
        def sort_key(x):
            nombre, tipo, size_bytes, _, fecha_mod, _ = x
            es_carpeta = size_bytes == -1
            if self.orden_columna == "Nombre":
                return (not es_carpeta, x[0].lower())
            elif self.orden_columna == "Tipo":
                return (not es_carpeta, x[1].lower())
            elif self.orden_columna == "Tamaño":
                return (not es_carpeta, x[2])
            elif self.orden_columna == "Fecha modificación":
                return (not es_carpeta, x[4])
            else:
                return (not es_carpeta, x[0].lower())
        elementos.sort(key=sort_key, reverse=self.orden_descendente)
        for nombre, tipo, _, size_str, _, fecha_str in elementos:
            self.tabla.insert("", "end", values=(nombre, tipo, size_str, fecha_str))

    def _poblar_arbol(self, ruta: Path, nodo_padre=""):
        """
        Llena el árbol de directorios de la barra lateral izquierda de forma recursiva.
        """
        try:
            items = sorted(ruta.iterdir(), key=lambda x: x.name.lower())
            for item in items:
                if item.is_dir():
                    nombre = f"📁 {item.name}"
                    nodo = self.arbol.insert(nodo_padre, "end", text=nombre, open=False)
                    try:
                        self._poblar_arbol(item, nodo)
                    except (PermissionError, OSError):
                        pass  # Ignora carpetas sin permisos
        except (PermissionError, OSError):
            pass

    def _obtener_ruta_completa(self, nodo):
        """
        Devuelve la ruta absoluta de un nodo del árbol de directorios.
        """
        partes = []
        while nodo:
            texto = self.arbol.item(nodo)["text"]
            if texto.startswith(("📁 ", "🗀 ")):
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

    def _menu_contexto_arbol(self, event):
        """
        Muestra el menú contextual al hacer clic derecho en el árbol de carpetas.
        """
        item = self.arbol.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0)
        if item:
            ruta = self._obtener_ruta_completa(item)
            menu.add_command(label="🔍 Abrir", command=lambda: self._navegar_a(ruta))
            menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, True))
            menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
            menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta (raíz)", command=lambda: self._crear_carpeta(self.BASE_DIR))
            menu.add_command(label="⬆ Subir archivo", command=self._subir_archivo)
            menu.add_command(label="📦 Subir carpeta", command=self._subir_carpeta)
        menu.tk_popup(event.x_root, event.y_root)

    def _menu_contexto_tabla(self, event):
        """
        Muestra el menú contextual al hacer clic derecho en la tabla de archivos/carpetas.
        """
        item = self.tabla.identify_row(event.y)
        menu = tk.Menu(self.master, tearoff=0)
        if item:
            nombre = self.tabla.item(item, "values")[0]
            if nombre.startswith(("📁", "📄", "🗀", "📶", "❓")):
                nombre = nombre[2:].strip()
            ruta = self.ruta_actual / nombre
            if ruta.is_file():
                menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="💾 Descargar", command=lambda: self._descargar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
            elif ruta.is_dir():
                menu.add_command(label="🔍 Abrir", command=lambda: self._navegar_a(ruta))
                menu.add_command(label="✏ Renombrar", command=lambda: self._renombrar(ruta, item, False))
                menu.add_command(label="🗑 Eliminar", command=lambda: self._eliminar(ruta))
                menu.add_command(label="📁 Mover a...", command=lambda: self._mover_a(ruta))
                menu.add_command(label="💾 Descargar", command=lambda: self._descargar_carpeta(ruta))
        else:
            menu.add_command(label="➕ Nueva carpeta", command=lambda: self._crear_carpeta(self.ruta_actual))
            menu.add_command(label="⬆ Subir archivo", command=self._subir_archivo)
            menu.add_command(label="📦 Subir carpeta", command=self._subir_carpeta)
        menu.tk_popup(event.x_root, event.y_root)

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
                ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
                tipo = "carpeta_renombrada" if es_carpeta else "archivo_renombrado"
                motivo_log = f"Renombrado de '{nombre_original}' a '{nuevo}'"
                archivo_id = archivo_manager.buscar_archivo_id(nombre_original, ruta_relativa)
                if archivo_id:
                    archivo_manager.registrar_log(self.user_id, archivo_id, tipo, motivo_log, nombre_original)
                    archivo_manager.actualizar_nombre_archivo(archivo_id, nuevo, ruta_relativa, nombre_original)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo renombrar:\n{str(e)}")

    def _eliminar(self, ruta):
        """
        Elimina archivos o carpetas (con todo su contenido) y registra la acción en la base de datos.
        """
        nombre_original = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        es_carpeta = ruta.is_dir()
        if es_carpeta:
            confirmar1 = messagebox.askyesno("Confirmar eliminación", f"¿Seguro que deseas eliminar la carpeta '{nombre_original}'?")
            if not confirmar1:
                return
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
                for subelemento in ruta.rglob("*"):
                    if subelemento.is_file() or subelemento.is_dir():
                        ruta_sub = str(subelemento.parent.relative_to(self.BASE_DIR))
                        nombre_sub = subelemento.name
                        tipo = "carpeta_eliminada" if subelemento.is_dir() else "archivo_eliminado"
                        archivo_id = archivo_manager.buscar_archivo_id(nombre_sub, ruta_sub)
                        if archivo_id:
                            archivo_manager.registrar_log(self.user_id, archivo_id, tipo, "Eliminado dentro de carpeta eliminada", nombre_sub)
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
                self.arbol.delete(*self.arbol.get_children())
            self._poblar_arbol(self.BASE_DIR)
            archivo_id = archivo_manager.buscar_archivo_id(nombre_original, ruta_relativa)
            if archivo_id:
                tipo = "carpeta_eliminada" if es_carpeta else "archivo_eliminado"
                archivo_manager.registrar_log(self.user_id, archivo_id, tipo, "Elemento eliminado", nombre_original)
            if es_carpeta:
                messagebox.showinfo("Eliminación completa", f"🗑 Carpeta eliminada con éxito.\n"
                                                            f"📄 Archivos eliminados: {archivos_contados}\n"
                                                            f"📁 Subcarpetas eliminadas: {carpetas_contadas}")
            else:
                messagebox.showinfo("Eliminación completa", "🗑 Archivo eliminado con éxito.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{str(e)}")

    def _descargar(self, ruta):
        """
        Permite al administrador descargar un archivo, solicitando un motivo y registrando la descarga en la base de datos.
        """
        # Obtener información del archivo
        nombre_archivo = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        
        # Log de información inicial
        print(f"=== INICIANDO DESCARGA ===")
        print(f"Archivo: {nombre_archivo}")
        print(f"Ruta relativa: {ruta_relativa}")
        print(f"Usuario ID: {self.user_id}")
          # Crear ventana para seleccionar motivo con estilo mejorado
        ventana_motivo = tk.Toplevel(self.master)
        ventana_motivo.title("📥 Motivo de Descarga")
        ventana_motivo.geometry("550x450")  # Ventana más grande
        ventana_motivo.resizable(False, False)
        ventana_motivo.transient(self.master)  # Hace que sea modal
        ventana_motivo.grab_set()  # Evita interacciones con la ventana principal
        ventana_motivo.configure(bg="#f8f9fa")
          # Header con estilo moderno
        header_frame = tk.Frame(ventana_motivo, bg="#4CAF50", height=70)  # Header más alto
        header_frame.pack(fill="x", pady=0)
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(header_frame, 
                               text="📥 DESCARGA DE ARCHIVO",
                               bg="#4CAF50", fg="white",
                               font=("Segoe UI", 18, "bold"))  # Texto más grande
        header_label.pack(expand=True)
        
        # Contenedor principal con padding
        main_frame = tk.Frame(ventana_motivo, bg="#f8f9fa", padx=25, pady=15)
        main_frame.pack(fill="both", expand=True)
        
        # Sección de información del archivo
        info_frame = tk.LabelFrame(main_frame, text="📄 Información del Archivo", 
                                  bg="#f8f9fa", fg="#333333",
                                  font=("Segoe UI", 11, "bold"),
                                  padx=15, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(info_frame, text=f"Nombre: {nombre_archivo}", 
                bg="#f8f9fa", fg="#000000",
                font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
        
        tk.Label(info_frame, text=f"Ruta: {ruta_relativa}", 
                bg="#f8f9fa", fg="#666666",
                font=("Segoe UI", 10)).pack(anchor="w", pady=2)
        
        # Sección de motivo
        motivo_frame = tk.LabelFrame(main_frame, text="📋 Motivo de Descarga", 
                                    bg="#f8f9fa", fg="#333333",
                                    font=("Segoe UI", 11, "bold"),
                                    padx=15, pady=10)
        motivo_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(motivo_frame, text="Selecciona el motivo:", 
                bg="#f8f9fa", fg="#2c3e50",
                font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5, 5))
        
        motivo_combo = ttk.Combobox(motivo_frame, values=[
            "Solicitud", "Trabajo interno", "Modificación de datos", "Otro motivo"
        ], state="readonly", font=("Segoe UI", 10), width=40)
        motivo_combo.pack(fill="x", pady=(0, 10))
        motivo_combo.set("Trabajo interno")  # Valor por defecto
        
        # Label para el detalle (cambia según la selección)
        label_detalle = tk.Label(motivo_frame, text="Nombre del trabajo:", 
                               bg="#f8f9fa", fg="#2c3e50",
                               font=("Segoe UI", 10, "bold"))
        label_detalle.pack(anchor="w", pady=(5, 5))
        
        # Entry para el detalle con estilo mejorado
        entry_detalle = tk.Entry(motivo_frame, width=48, 
                              font=("Segoe UI", 10),
                              relief="solid", bd=1)
        entry_detalle.pack(fill="x", pady=(0, 5))
        
        # Función para actualizar el label según la selección
        def actualizar_label(event):
            seleccion = motivo_combo.get()
            entry_detalle.delete(0, tk.END)
            
            if seleccion == "Solicitud":
                label_detalle.config(text="Número de solicitud (solo números):")
                entry_detalle.config(bg="#e8f5e8")
            elif seleccion == "Trabajo interno":
                label_detalle.config(text="Nombre del trabajo:")
                entry_detalle.config(bg="#e3f2fd")
            elif seleccion == "Modificación de datos":
                label_detalle.config(text="Justifica la modificación:")
                entry_detalle.config(bg="#fff3e0")
            elif seleccion == "Otro motivo":
                label_detalle.config(text="Describe el motivo exacto:")
                entry_detalle.config(bg="#fce4ec")
                
            entry_detalle.focus_set()
            print(f"Tipo de motivo seleccionado: {seleccion}")
        
        # Vincular función al evento de selección del combobox
        motivo_combo.bind("<<ComboboxSelected>>", actualizar_label)
        
        # Variables para almacenar el resultado
        descarga_exitosa = [False, ""]  # [éxito, motivo]
        
        # Función para procesar la descarga
        def procesar_descarga():
            tipo = motivo_combo.get()
            detalle = entry_detalle.get().strip()
            
            print(f"Procesando descarga:")
            print(f"- Tipo de motivo: {tipo}")
            print(f"- Detalle: {detalle}")
            
            # Validaciones
            if not tipo or not detalle:
                messagebox.showerror("⚠️ Error", "Debes completar tanto el motivo como el detalle.", parent=ventana_motivo)
                print("ERROR: Campos incompletos")
                return
            
            # Validar que para solicitud solo sean números
            if tipo == "Solicitud" and not detalle.isdigit():
                messagebox.showerror("⚠️ Formato inválido", "Para solicitudes, solo se permiten números.", parent=ventana_motivo)
                print("ERROR: Formato inválido para solicitud (no son números)")
                return
            
            motivo_final = f"{tipo}: {detalle}"
            print(f"- Motivo final: {motivo_final}")
            
            # Diálogo para seleccionar dónde guardar el archivo
            destino = filedialog.asksaveasfilename(
                parent=ventana_motivo,
                title="Guardar archivo como...",
                defaultextension="", 
                initialfile=nombre_archivo,
                filetypes=[("Todos los archivos", "*.*")]
            )
            
            if not destino:
                print("Descarga cancelada: No se seleccionó destino")
                return
            
            print(f"- Destino seleccionado: {destino}")
            
            try:
                # Buscar el ID del archivo en la base de datos
                archivo_id = archivo_manager.buscar_archivo_id(nombre_archivo, ruta_relativa)
                print(f"- ID del archivo en DB: {archivo_id}")
                
                if not archivo_id:
                    messagebox.showerror("❌ Error", "No se encontró el archivo en la base de datos.", parent=ventana_motivo)
                    print("ERROR: Archivo no encontrado en la base de datos")
                    return
                
                # Copiar el archivo
                shutil.copy2(ruta, destino)
                print(f"- Archivo copiado exitosamente de {ruta} a {destino}")
                
                # Registrar la descarga en la base de datos
                print(f"- Registrando en DB: user_id={self.user_id}, archivo_id={archivo_id}, motivo={motivo_final}")
                exito = archivo_manager.crear_solicitud_descarga_admin(self.user_id, archivo_id, motivo_final)
                print(f"- Resultado del registro: {'EXITOSO' if exito else 'FALLIDO'}")
                
                if exito:
                    descarga_exitosa[0] = True
                    descarga_exitosa[1] = motivo_final
                    ventana_motivo.destroy()
                else:
                    messagebox.showwarning("⚠️ Advertencia", 
                                        "Archivo descargado pero no registrado en la base de datos.", 
                                        parent=ventana_motivo)
                    ventana_motivo.destroy()
                
            except Exception as e:
                print(f"ERROR en la descarga: {str(e)}")
                messagebox.showerror("❌ Error", f"Error al copiar el archivo: {str(e)}", parent=ventana_motivo)
        
        # Función para cancelar
        def cancelar():
            print("Descarga cancelada por el usuario")
            ventana_motivo.destroy()
            
        # Función para efectos hover
        def on_enter(e, btn, color):
            btn.configure(bg=color)
        
        def on_leave(e, btn, original_color):
            btn.configure(bg=original_color)
        
        # Botones con estilo moderno
        botones_frame = tk.Frame(main_frame, bg="#f8f9fa")
        botones_frame.pack(fill="x", pady=(10, 0))
        
        # Botón Cancelar
        btn_cancelar = tk.Button(botones_frame, text="❌ Cancelar", 
                               command=cancelar,
                               bg="#F44336", fg="white",
                               font=("Segoe UI", 11, "bold"),
                               padx=20, pady=8,
                               relief="flat", cursor="hand2")
        btn_cancelar.pack(side="right", padx=(10, 0))
        
        # Botón Descargar
        btn_descargar = tk.Button(botones_frame, text="💾 Descargar Archivo", 
                             command=procesar_descarga,
                             bg="#4CAF50", fg="white",
                             font=("Segoe UI", 11, "bold"),
                             padx=25, pady=8,
                             relief="flat", cursor="hand2")
        btn_descargar.pack(side="right")
        
        # Aplicar efectos hover
        btn_descargar.bind("<Enter>", lambda e: on_enter(e, btn_descargar, "#45a049"))
        btn_descargar.bind("<Leave>", lambda e: on_leave(e, btn_descargar, "#4CAF50"))
        
        btn_cancelar.bind("<Enter>", lambda e: on_enter(e, btn_cancelar, "#d32f2f"))
        btn_cancelar.bind("<Leave>", lambda e: on_leave(e, btn_cancelar, "#F44336"))
          # Centrar ventana
        centrar_ventana(ventana_motivo, 550, 450)  # Dimensiones actualizadas
        
        # Esperar a que se cierre la ventana
        self.master.wait_window(ventana_motivo)
        
        # Mostrar mensaje de éxito si la descarga fue exitosa
        if descarga_exitosa[0]:
            print(f"=== DESCARGA COMPLETADA ===")
            messagebox.showinfo("✅ Descarga Completada", 
                             f"Archivo descargado y registrado: {nombre_archivo}\nMotivo: {descarga_exitosa[1]}")
        else:
            print(f"=== DESCARGA NO COMPLETADA ===")

    def _subir_archivo(self):
        """
        Permite al administrador subir un archivo al directorio actual y lo registra en la base de datos.
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
        Permite al administrador subir una carpeta completa (con su contenido) al directorio actual y lo registra en la base de datos.
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

                # Usar sistema optimizado
                ruta_relativa = str(donde.relative_to(self.BASE_DIR))
                archivo_id = archivo_manager.registrar_archivo(nombre, ruta_relativa, self.user_id, es_carpeta=True)

                if archivo_id:
                    archivo_manager.registrar_log(self.user_id, archivo_id, "carpeta_creada", "Carpeta creada manualmente", nombre)

                self._actualizar_tabla(self.ruta_actual)
                self.arbol.delete(*self.arbol.get_children())
                self._poblar_arbol(self.BASE_DIR)

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
        nombre_limpio = nombre_completo[2:].strip() if nombre_completo.startswith(("📁", "📄", "🗀", "📶", "❓")) else nombre_completo
        ruta = self.ruta_actual / nombre_limpio
        # Solo permitir navegación en carpetas, no abrir archivos
        if ruta.is_dir():
            self._navegar_a(ruta)

    def _mover_a(self, ruta_origen):
        """
        Permite mover un archivo o carpeta a otra ubicación dentro del directorio base, actualizando la base de datos.
        """
        ventana = tk.Toplevel(self.master)
        ventana.title("Seleccionar carpeta destino")
        centrar_ventana(ventana, 300, 400)

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

                if ruta_origen.is_dir() and nuevo_ruta.resolve().is_relative_to(ruta_origen.resolve()):
                    messagebox.showerror("Error", "No puedes mover una carpeta dentro de sí misma o de una subcarpeta.")
                    return

                shutil.move(str(ruta_origen), str(nuevo_ruta))

                # Usar sistema optimizado
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

                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo mover:\n{str(e)}")

        tk.Button(ventana, text="Mover aquí", command=mover).pack(pady=10)

    def _descargar_carpeta(self, ruta):
        """
        Permite al administrador descargar una carpeta como ZIP, solicitando un motivo y registrando la descarga en la base de datos.
        """
        nombre_carpeta = ruta.name
        ruta_relativa = str(ruta.parent.relative_to(self.BASE_DIR))
        carpeta_id = archivo_manager.buscar_archivo_id(nombre_carpeta, ruta_relativa)
        if not carpeta_id:
            messagebox.showerror("❌ Error", "No se encontró la carpeta en la base de datos.")
            return
        ventana_motivo = tk.Toplevel(self.master)
        ventana_motivo.title("📥 Motivo de Descarga de Carpeta")
        ventana_motivo.geometry("550x450")
        ventana_motivo.resizable(False, False)
        ventana_motivo.transient(self.master)
        ventana_motivo.grab_set()
        ventana_motivo.configure(bg="#f8f9fa")
        header_frame = tk.Frame(ventana_motivo, bg="#4CAF50", height=70)
        header_frame.pack(fill="x", pady=0)
        header_frame.pack_propagate(False)
        header_label = tk.Label(header_frame, text="📥 DESCARGA DE CARPETA", bg="#4CAF50", fg="white", font=("Segoe UI", 18, "bold"))
        header_label.pack(expand=True)
        main_frame = tk.Frame(ventana_motivo, bg="#f8f9fa", padx=25, pady=15)
        main_frame.pack(fill="both", expand=True)
        info_frame = tk.LabelFrame(main_frame, text="📁 Información de la Carpeta", bg="#f8f9fa", fg="#333333", font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))
        tk.Label(info_frame, text=f"Nombre: {nombre_carpeta}", bg="#f8f9fa", fg="#000000", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
        tk.Label(info_frame, text=f"Ruta: {ruta_relativa}", bg="#f8f9fa", fg="#666666", font=("Segoe UI", 10)).pack(anchor="w", pady=2)
        motivo_frame = tk.LabelFrame(main_frame, text="📋 Motivo de Descarga", bg="#f8f9fa", fg="#333333", font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        motivo_frame.pack(fill="x", pady=(0, 5))
        tk.Label(motivo_frame, text="Selecciona el motivo:", bg="#f8f9fa", fg="#2c3e50", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5, 5))
        motivo_combo = ttk.Combobox(motivo_frame, values=["Solicitud", "Trabajo interno", "Modificación de datos", "Otro motivo"], state="readonly", font=("Segoe UI", 10), width=40)
        motivo_combo.pack(fill="x", pady=(0, 10))
        motivo_combo.set("Trabajo interno")
        label_detalle = tk.Label(motivo_frame, text="Nombre del trabajo:", bg="#f8f9fa", fg="#2c3e50", font=("Segoe UI", 10, "bold"))
        label_detalle.pack(anchor="w", pady=(5, 5))
        entry_detalle = tk.Entry(motivo_frame, width=48, font=("Segoe UI", 10), relief="solid", bd=1)
        entry_detalle.pack(fill="x", pady=(0, 5))
        def actualizar_label(event):
            seleccion = motivo_combo.get()
            entry_detalle.delete(0, tk.END)
            if seleccion == "Solicitud":
                label_detalle.config(text="Número de solicitud (solo números):")
                entry_detalle.config(bg="#e8f5e8")
            elif seleccion == "Trabajo interno":
                label_detalle.config(text="Nombre del trabajo:")
                entry_detalle.config(bg="#e3f2fd")
            elif seleccion == "Modificación de datos":
                label_detalle.config(text="Justifica la modificación:")
                entry_detalle.config(bg="#fff3e0")
            elif seleccion == "Otro motivo":
                label_detalle.config(text="Describe el motivo exacto:")
                entry_detalle.config(bg="#fce4ec")
            entry_detalle.focus_set()
        motivo_combo.bind("<<ComboboxSelected>>", actualizar_label)
        descarga_exitosa = [False, ""]
        def procesar_descarga():
            tipo = motivo_combo.get()
            detalle = entry_detalle.get().strip()
            if not tipo or not detalle:
                messagebox.showerror("⚠️ Error", "Debes completar tanto el motivo como el detalle.", parent=ventana_motivo)
                return
            if tipo == "Solicitud" and not detalle.isdigit():
                messagebox.showerror("⚠️ Formato inválido", "Para solicitudes, solo se permiten números.", parent=ventana_motivo)
                return
            motivo_final = f"{tipo}: {detalle}"
            destino = filedialog.asksaveasfilename(
                parent=ventana_motivo,
                title="Guardar carpeta como...",
                defaultextension=".zip",
                initialfile=f"{nombre_carpeta}.zip",
                filetypes=[("Archivo ZIP", "*.zip")]
            )
            if not destino:
                return
            try:
                shutil.make_archive(destino.replace('.zip',''), 'zip', ruta)
                exito = archivo_manager.crear_solicitud_descarga_admin(self.user_id, carpeta_id, motivo_final)
                if exito:
                    descarga_exitosa[0] = True
                    descarga_exitosa[1] = motivo_final
                    ventana_motivo.destroy()
                else:
                    messagebox.showwarning("⚠️ Advertencia", "La carpeta fue descargada pero no registrada en la base de datos.", parent=ventana_motivo)
                    ventana_motivo.destroy()
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo descargar la carpeta: {str(e)}", parent=ventana_motivo)
        # Botones con estilo moderno y bien posicionados
        botones_frame = tk.Frame(main_frame, bg="#f8f9fa")
        botones_frame.pack(fill="x", pady=(10, 0))

        # Botón Cancelar
        btn_cancelar = tk.Button(botones_frame, text="❌ Cancelar", 
                               command=ventana_motivo.destroy,
                               bg="#F44336", fg="white",
                               font=("Segoe UI", 11, "bold"),
                               padx=20, pady=8,
                               relief="flat", cursor="hand2")
        btn_cancelar.pack(side="right", padx=(10, 0))

        # Botón Descargar
        btn_descargar = tk.Button(botones_frame, text="💾 Descargar Carpeta", 
                             command=procesar_descarga,
                             bg="#4CAF50", fg="white",
                             font=("Segoe UI", 11, "bold"),
                             padx=25, pady=8,
                             relief="flat", cursor="hand2")
        btn_descargar.pack(side="right")

        # Efectos hover
        def on_enter(e, btn, color):
            btn.configure(bg=color)
        def on_leave(e, btn, original_color):
            btn.configure(bg=original_color)
        btn_descargar.bind("<Enter>", lambda e: on_enter(e, btn_descargar, "#45a049"))
        btn_descargar.bind("<Leave>", lambda e: on_leave(e, btn_descargar, "#4CAF50"))
        btn_cancelar.bind("<Enter>", lambda e: on_enter(e, btn_cancelar, "#d32f2f"))
        btn_cancelar.bind("<Leave>", lambda e: on_leave(e, btn_cancelar, "#F44336"))
        centrar_ventana(ventana_motivo, 550, 450)
        ventana_motivo.wait_window()
        if descarga_exitosa[0]:
            messagebox.showinfo("✅ Descarga completada", f"La carpeta '{nombre_carpeta}' fue descargada y registrada correctamente.\nMotivo: {descarga_exitosa[1]}")

if __name__ == "__main__":
    from gui.login import iniciar_login
    iniciar_login()

def abrir_menu_admin(user_id, username, modo_oscuro):
    root = TkinterDnD.Tk()
    root.geometry("1400x800")
    centrar_ventana(root, 1400, 800)
    app = ExploradorAdmin(root, modo_oscuro=modo_oscuro, es_admin=True)
    app.user_id = user_id
    root.mainloop()
