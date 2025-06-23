#!/usr/bin/env python3
"""
Sistema centralizado de configuración de UI para BaulSIG
Tamaños de fuentes y ventanas optimizados para fácil lectura
"""

# ===== CONFIGURACIÓN DE FUENTES AJUSTADAS =====
FUENTES = {
    # Fuentes principales (incrementadas para mejor legibilidad)
    'titulo': ('Segoe UI', 14, 'bold'),
    'subtitulo': ('Segoe UI', 12, 'bold'),
    'normal': ('Segoe UI', 10),
    'boton': ('Segoe UI', 10, 'bold'),
    'label': ('Segoe UI', 10, 'bold'),
    'pequeña': ('Segoe UI', 9),
    
    # Fuentes específicas (mejoradas)
    'login_titulo': ('Segoe UI', 16, 'bold'),
    'login_label': ('Segoe UI', 10, 'bold'),
    'login_entrada': ('Segoe UI', 10),
    'menu_principal': ('Segoe UI', 12, 'bold'),
    
    # Tablas y listas (más legibles)
    'tabla_header': ('Segoe UI', 10, 'bold'),
    'tabla_contenido': ('Segoe UI', 10),
    'arbol': ('Segoe UI', 10),
    
    # Fuentes adicionales para elementos específicos
    'barra_navegacion': ('Segoe UI', 9, 'bold'),
    'estado': ('Segoe UI', 9),
    'iconos': ('Segoe UI', 12),
}

# ===== TAMAÑOS DE VENTANAS AMPLIADOS =====
VENTANAS = {
    # Ventana principal de login (más grande)
    'login': {'width': 600, 'height': 500},
    
    # Ventanas de administrador (ampliadas)
    'admin_principal': {'width': 1600, 'height': 900},
    'admin_logs': {'width': 1700, 'height': 800},
    'admin_solicitudes': {'width': 1800, 'height': 900},
    
    # Ventanas de usuario (ampliadas)
    'usuario_principal': {'width': 1600, 'height': 900},
    'usuario_solicitudes': {'width': 1500, 'height': 700},
    
    # Ventanas de diálogo (más espaciosas)
    'dialogo_pequeño': {'width': 550, 'height': 400},
    'dialogo_mediano': {'width': 750, 'height': 500},
    'dialogo_grande': {'width': 1000, 'height': 650},
    
    # Ventanas específicas
    'mover_archivo': {'width': 500, 'height': 600},
    'crear_carpeta': {'width': 450, 'height': 250},
    'renombrar': {'width': 500, 'height': 200},
}

# ===== ESPACIADO Y PADDING =====
ESPACIOS = {
    'padding_ventana': 15,      # Espacio general en ventanas
    'padding_frame': 12,        # Espacio en frames
    'padding_boton': 10,        # Espacio alrededor de botones
    'margen_elementos': 8,      # Espacio entre elementos
    'altura_fila_tabla': 30,    # Altura de filas en tablas
}

# ===== COLORES MEJORADOS =====
COLORES = {
    # Fondo principal
    'fondo_principal': '#f5f5f5',
    'fondo_panel': '#ffffff',
    'fondo_barra': '#e8e8e8',
      # Botones
    'boton_normal': '#4a90e2',
    'boton_primario': '#4a90e2',
    'boton_secundario': '#6c757d',
    'boton_hover': '#357abd',
    'boton_peligro': '#d32f2f',
    'boton_exito': '#388e3c',
    'boton_advertencia': '#f57c00',
    
    # Texto
    'texto_principal': '#2c2c2c',
    'texto_secundario': '#666666',
    'texto_boton': '#ffffff',
    
    # Estados
    'seleccionado': '#e3f2fd',
    'hover': '#f0f0f0',
    'borde': '#d0d0d0',
}

def obtener_fuente(tipo='normal'):
    """Obtiene una fuente del sistema centralizado"""
    return FUENTES.get(tipo, FUENTES['normal'])

def obtener_tamaño_ventana(tipo):
    """Obtiene el tamaño de ventana apropiado"""
    return VENTANAS.get(tipo, VENTANAS['dialogo_mediano'])

def aplicar_estilo_tabla(tabla):
    """Aplica estilo consistente a una tabla Treeview"""
    import tkinter.ttk as ttk
    
    style = ttk.Style()
    style.theme_use("clam")
    
    # Configurar tabla
    style.configure("Treeview",
                    background=COLORES['fondo_panel'],
                    foreground=COLORES['texto_principal'],
                    rowheight=ESPACIOS['altura_fila_tabla'],
                    fieldbackground=COLORES['fondo_panel'],
                    font=FUENTES['tabla_contenido'])
    
    # Configurar encabezados
    style.configure("Treeview.Heading",
                    background=COLORES['fondo_barra'],
                    foreground=COLORES['texto_principal'],
                    font=FUENTES['tabla_header'])
    
    # Configurar selección
    style.map("Treeview",
              background=[('selected', COLORES['seleccionado'])],
              foreground=[('selected', COLORES['texto_principal'])])

def configurar_ventana_principal(ventana, tipo_ventana):
    """Configura una ventana con los parámetros estándar"""
    tamaño = obtener_tamaño_ventana(tipo_ventana)
    
    # Configurar tamaño
    ventana.geometry(f"{tamaño['width']}x{tamaño['height']}")
    
    # Centrar ventana
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (tamaño['width'] // 2)
    y = (ventana.winfo_screenheight() // 2) - (tamaño['height'] // 2)
    ventana.geometry(f"{tamaño['width']}x{tamaño['height']}+{x}+{y}")
    
    # Configurar colores
    ventana.configure(bg=COLORES['fondo_principal'])
    
    return tamaño

def crear_boton_estilizado(parent, texto, comando=None, tipo='normal', **kwargs):
    """Crea un botón con estilo consistente"""
    import tkinter as tk
    
    # Determinar colores según el tipo
    if tipo == 'peligro':
        bg_color = COLORES['boton_peligro']
    elif tipo == 'exito':
        bg_color = COLORES['boton_exito']
    elif tipo == 'advertencia':
        bg_color = COLORES['boton_advertencia']
    else:
        bg_color = COLORES['boton_normal']
    
    boton = tk.Button(
        parent,
        text=texto,
        command=comando,
        font=FUENTES['boton'],
        bg=bg_color,
        fg=COLORES['texto_boton'],
        relief='flat',
        padx=ESPACIOS['padding_boton'],
        pady=6,
        cursor='hand2',
        **kwargs
    )
    
    # Efectos hover
    def on_enter(e):
        boton.configure(bg=COLORES['boton_hover'])
    
    def on_leave(e):
        boton.configure(bg=bg_color)
    
    boton.bind("<Enter>", on_enter)
    boton.bind("<Leave>", on_leave)
    
    return boton

if __name__ == "__main__":
    print("🎨 Sistema de UI BaulSIG")
    print("=" * 30)
    print("Fuentes disponibles:")
    for nombre, fuente in FUENTES.items():
        print(f"  {nombre}: {fuente}")
    print("\nTamaños de ventana:")
    for nombre, tamaño in VENTANAS.items():
        print(f"  {nombre}: {tamaño['width']}x{tamaño['height']}")
