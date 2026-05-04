import tkinter as tk
from tkinter import ttk
import webbrowser
from collections import Counter
from backend_ui import cargar_visitas_gui, ejecutar_planificacion_gui, obtener_cuadrillas
from ui_utils import texto_cuadrilla_resumen, texto_cuadrilla_detalle
from sistema_dinamico import (asignacion_inicial_dinamica, inicializar_sistema, agregar_visita, actualizar_stock, cambiar_estado_cuadrilla, terminar_sistema)
from modelos import TipoVisita, Visita
from estado_dinamico import V, C, D, M
from estado_dinamico import V_HISTORICO

# APP CONFIG
root = tk.Tk()
root.title("Planificador de Cuadrillas")
root.geometry("1200x700")
root.configure(bg="#f4f6f9")

filtro_tipo = tk.StringVar(value="TODAS")
#visitas_cache = []

# STYLE COLORS
BG_APP = "#f4f6f9"
BG_MENU = "#111827"
BG_CARD = "#ffffff"
PRIMARY = "#2563eb"
TEXT = "#111827"
SUBTEXT = "#6b7280"


# LAYOUT
menu = tk.Frame(root, bg=BG_MENU, width=220)
menu.pack(side="left", fill="y")

content = tk.Frame(root, bg=BG_APP)
content.pack(side="right", expand=True, fill="both")

def limpiar():
    for w in content.winfo_children():
        w.destroy()


def calcular_stats(visitas):
    total = len(visitas)
    conteo = Counter(v.tipo.value for v in visitas)
    return total, conteo

# VISITAS DASHBOARD
def pantalla_visitas():

    TIPO_CONFIG = {
        "instalacion": {
            "icono": "🏗",
            "color": "#2563eb"
        },
        "tecnica": {
            "icono": "🔧",
            "color": "#16a34a"
        },
        "incidencia": {
            "icono": "⚠",
            "color": "#dc2626"
        },
        "TODAS": {
            "icono": "📊",
            "color": PRIMARY
        }
    }

    #global visitas_cache

    limpiar()
    #visitas_cache = cargar_visitas_gui()

    # HEADER
    total, conteo = calcular_stats(V_HISTORICO)

    header = tk.Frame(content, bg=BG_APP)
    header.pack(fill="x", pady=10)

    tk.Label(header, text="Dashboard de Visitas",
            font=("Segoe UI", 20, "bold"),
            bg=BG_APP, fg=TEXT).pack(anchor="w", padx=12)

    tk.Label(header, text="Gestión y monitorización de visitas registradas",
            font=("Segoe UI", 10),
            bg=BG_APP, fg=SUBTEXT).pack(anchor="w", padx=12)

    stats = tk.Frame(header, bg=BG_APP)
    stats.pack(fill="x", padx=12, pady=12)

    def card_stat(parent, titulo, valor, tipo):
        conf = TIPO_CONFIG.get(tipo, TIPO_CONFIG["TODAS"])

        card = tk.Frame(
            parent,
            bg=BG_CARD,
            padx=18,
            pady=14,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        card.pack(side="left", padx=10, fill="x", expand=True)

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="both", expand=True)

        tk.Label(
            row,
            text=conf["icono"],
            font=("Segoe UI Emoji", 28),
            bg=BG_CARD,
            fg=conf["color"]
        ).pack(side="left", padx=(0,14))

        text_col = tk.Frame(row, bg=BG_CARD)
        text_col.pack(side="left", fill="both", expand=True)

        tk.Label(
            text_col,
            text=titulo,
            font=("Segoe UI", 10),
            bg=BG_CARD,
            fg=SUBTEXT
        ).pack(anchor="w")

        tk.Label(
            text_col,
            text=valor,
            font=("Segoe UI", 20, "bold"),
            bg=BG_CARD,
            fg=TEXT
        ).pack(anchor="w")

        return card

    card_stat(stats, "Total visitas", total, "TODAS")

    for tipo, n in conteo.items():
        card_stat(stats, tipo.title(), n, tipo)

    # FILTERS
    filtro_frame = tk.Frame(content, bg=BG_APP)
    filtro_frame.pack(fill="x", pady=5)

    def set_filtro(valor):
        filtro_tipo.set(valor)
        render_filtros()
        render_lista()

    def render_filtros():
        for w in filtro_frame.winfo_children():
            w.destroy()

        tipos = ["TODAS"] + list(set(v.tipo.value for v in V_HISTORICO))

        tk.Label(
            filtro_frame,
            text="Filtrar por tipo:",
            bg=BG_APP, fg=SUBTEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(10,10))

        for t in tipos:
            conf = TIPO_CONFIG.get(t, TIPO_CONFIG["TODAS"])
            activo = filtro_tipo.get() == t

            bg_color = conf["color"] if activo else BG_CARD
            fg_color = "white" if activo else TEXT
            borde = conf["color"]

            btn = tk.Frame(
                filtro_frame,
                bg=bg_color,
                highlightthickness=1,
                highlightbackground=borde,
                padx=10,
                pady=6,
                cursor="hand2"
            )
            btn.pack(side="left", padx=6)

            tk.Label(
                btn,
                text=f"{conf['icono']}  {t.title()}",
                bg=bg_color,
                fg=fg_color,
                font=("Segoe UI", 9, "bold")
            ).pack()

            btn.bind("<Button-1>", lambda e, x=t: set_filtro(x))
            for child in btn.winfo_children():
                child.bind("<Button-1>", lambda e, x=t: set_filtro(x))

    render_filtros()

    lista_frame = tk.Frame(content, bg=BG_APP)
    lista_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(lista_frame, bg=BG_APP, highlightthickness=0)
    scroll = ttk.Scrollbar(lista_frame, orient="vertical", command=canvas.yview)

    inner = tk.Frame(canvas, bg=BG_APP)

    for i in range(4):
        inner.grid_columnconfigure(i, weight=1)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scroll.set)

    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    def icono_tipo(tipo):
        return TIPO_CONFIG.get(tipo, TIPO_CONFIG["TODAS"])["icono"]

    def color_prioridad(p):
        if p >= 8:
            return "#dc2626"
        if p >= 5:
            return "#d97706"
        return "#16a34a"

    def render_lista():
        
        for w in inner.winfo_children():
            w.destroy()

        filtro = filtro_tipo.get()

        if filtro == "TODAS":
            datos = V_HISTORICO
        else:
            datos = [v for v in V_HISTORICO if v.tipo.value == filtro]

        COLS = 4
        CARD_W = 460
        CARD_H = 140

        for i, v in enumerate(datos):
            r = i // COLS
            c = i % COLS

            card = tk.Frame(
                inner,
                bg=BG_CARD,
                width=CARD_W,
                height=CARD_H,
                highlightthickness=1,
                highlightbackground="#e5e7eb",
                padx=12,
                pady=10
            )
            card.grid(row=r, column=c, padx=12, pady=12, sticky="nsew")
            card.grid_propagate(False)

            top = tk.Frame(card, bg=BG_CARD)
            top.pack(fill="x")

            tk.Label(top,
                text=f"{icono_tipo(v.tipo.value)}  {v.nombre}",
                bg=BG_CARD, fg=TEXT,
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w")

            badges = tk.Frame(card, bg=BG_CARD)
            badges.pack(fill="x", pady=(4,8))

            tk.Label(
                badges,
                text=v.tipo.value,
                bg="#eef2ff",
                fg=PRIMARY,
                padx=8,
                pady=3,
                font=("Segoe UI", 8, "bold")
            ).pack(side="left")

            tk.Label(
                badges,
                text=f"Prioridad {v.prioridad}",
                bg=color_prioridad(v.prioridad),
                fg="white",
                padx=8,
                pady=3,
                font=("Segoe UI", 8, "bold")
            ).pack(side="right")

            tk.Label(card,
                text=f"⏱ {v.duracion} min",
                bg=BG_CARD, fg=SUBTEXT,
                font=("Segoe UI", 9)
            ).pack(anchor="w")

            tk.Label(card,
                text=f"📍 {v.latitud:.3f}, {v.longitud:.3f}",
                bg=BG_CARD, fg=SUBTEXT,
                font=("Segoe UI", 9)
            ).pack(anchor="w", pady=(0,6))


    render_lista()


def abrir_detalle(c):
    win = tk.Toplevel(root)
    win.title(f"Cuadrilla {c.id}")
    win.geometry("600x700")

    txt = tk.Text(win, wrap="word", font=("Consolas", 10))
    txt.pack(expand=True, fill="both")

    txt.insert("1.0", texto_cuadrilla_detalle(c))


# PLANIFICACIÓN
cuadrilla_seleccionada = None


def pantalla_planificacion():
    global cuadrilla_seleccionada

    limpiar()

    tk.Label(content, text="Planificación de cuadrillas",
             font=("Segoe UI", 18, "bold"),
             bg=BG_APP, fg=TEXT).pack(pady=10)

    topbar = tk.Frame(content, bg=BG_APP)
    topbar.pack(pady=10)

    tk.Button(topbar, text="GENERAR PLANIFICACIÓN",
              bg=PRIMARY, fg="white",
              font=("Segoe UI", 12, "bold"),
              command=generar_planificacion).pack(side="left", padx=10)

    tk.Button(topbar, text="Abrir mapa",
              command=lambda: webbrowser.open("mapa.html")).pack(side="left")

    main = tk.Frame(content, bg=BG_APP)
    main.pack(expand=True, fill="both")

    left = tk.Frame(main, bg=BG_APP)
    left.pack(side="left", fill="both", expand=True)

    right = tk.Frame(main, bg=BG_CARD, width=400)
    right.pack(side="right", fill="y")

    right.pack_propagate(False)

    cuadrillas = obtener_cuadrillas()

    if not cuadrillas:
        tk.Label(left, text="No hay planificación aún",
                 bg=BG_APP, fg=SUBTEXT).pack()
        return

    def render_detalle(c):
        for w in right.winfo_children():
            w.destroy()

        tk.Label(right, text=f"Cuadrilla {c.id}",
                 bg=BG_CARD, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(pady=10)

        tk.Label(right,
                 text=texto_cuadrilla_resumen(c),
                 bg=BG_CARD, fg=SUBTEXT,
                 justify="left").pack(pady=10)

        tk.Label(right,
                 text="📍 RUTA COMPLETA",
                 bg=BG_CARD, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=5)

        for v in c.ruta:
            tk.Label(right,
                    text=f"• {v.nombre} ({v.tipo.value}) "
                        f"| 📍 {v.latitud:.3f}, {v.longitud:.3f}",
                    bg=BG_CARD, fg=SUBTEXT,
                    justify="left",
                    wraplength=350).pack(anchor="w", padx=10)

    for c in cuadrillas:
        card = tk.Frame(left, bg=BG_CARD,
                        highlightthickness=1,
                        highlightbackground="#e5e7eb",
                        padx=10, pady=10)

        card.pack(fill="x", padx=10, pady=8)

        tk.Label(card, text=f"Cuadrilla {c.id}",
                 bg=BG_CARD, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")

        tk.Label(card,
                 text=texto_cuadrilla_resumen(c),
                 bg=BG_CARD, fg=SUBTEXT,
                 justify="left").pack(anchor="w")

        tk.Button(card,
                  text="Seleccionar",
                  bg="#e5e7eb",
                  command=lambda c=c: render_detalle(c)).pack(anchor="e", pady=5)
        
def pantalla_dinamico():
    limpiar()

    # HEADER
    header = tk.Frame(content, bg=BG_APP)
    header.pack(fill="x", pady=10)

    tk.Label(header, text="Sistema dinámico",
             font=("Segoe UI", 18, "bold"),
             bg=BG_APP, fg=TEXT).pack(anchor="w", padx=10)

    tk.Label(header,
             text="Gestión en tiempo real del estado de las cuadrillas",
             font=("Segoe UI", 10),
             bg=BG_APP, fg=SUBTEXT).pack(anchor="w", padx=10)

    acciones = tk.Frame(content, bg=BG_APP)
    acciones.pack(fill="x", pady=10)

    def card_accion(parent, titulo, icono, color, comando):
        card = tk.Frame(
            parent,
            bg=BG_CARD,
            padx=18, pady=16,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        card.pack(side="left", padx=10)

        tk.Label(card, text=icono,
                 font=("Segoe UI Emoji", 22),
                 bg=BG_CARD, fg=color).pack()

        tk.Label(card, text=titulo,
                 font=("Segoe UI", 11, "bold"),
                 bg=BG_CARD, fg=TEXT).pack(pady=(6,0))

        card.bind("<Button-1>", lambda e: comando())
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e: comando())

        return card

    card_accion(acciones, "Inicializar sistema", "▶️", PRIMARY, refrescar_inicializar)
    card_accion(acciones, "Añadir visita", "➕", "#16a34a", formulario_visita)
    card_accion(acciones, "Actualizar stock", "📦", "#d97706", formulario_stock)
    card_accion(acciones, "Finalizar jornada", "🛑", "#dc2626", terminar_sistema_gui)

    panel_estado = tk.Frame(
        content,
        bg=BG_CARD,
        highlightthickness=1,
        highlightbackground="#e5e7eb",
        padx=15, pady=15
    )
    panel_estado.pack(fill="both", expand=True, padx=10, pady=10)

    tk.Label(panel_estado,
             text="Estado del sistema",
             font=("Segoe UI", 13, "bold"),
             bg=BG_CARD, fg=TEXT).pack(anchor="w")

    global estado_frame
    estado_frame = tk.Frame(panel_estado, bg=BG_CARD)
    estado_frame.pack(fill="both", expand=True, pady=(10,0))

    render_estado()

def leer_tiempo(entry):
    try:
        return float(entry.get())
    except:
        return None

def obtener_tiempo_estimado(c):
    if getattr(c, "tiempo_estimado", None):
        return f"{c.tiempo_estimado:.1f} min"
    return "—"

def terminar_sistema_gui():
    terminar_sistema()
    render_estado()

def refrescar_inicializar():
    asignacion_inicial_dinamica()
    render_estado()

def texto_ubicacion_cuadrilla(c):
    if getattr(c, "visita_actual", None):
        v = c.visita_actual
        return f"{v.nombre} ({v.latitud:.3f}, {v.longitud:.3f})"

    return f"Nodo {c.posicion}"
    
def render_estado():
    for w in estado_frame.winfo_children():
        w.destroy()

    # HEADER
    stats = tk.Frame(estado_frame, bg=BG_CARD)
    stats.pack(fill="x", pady=(0, 10))

    def stat_card(texto):
        f = tk.Frame(
            stats,
            bg=BG_APP,
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        f.pack(side="left", padx=5)

        tk.Label(
            f,
            text=texto,
            bg=BG_APP,
            fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack()

    stat_card(f"Visitas: {len(V)}")
    stat_card(f"Cuadrillas: {len(C)}")

    def estado_visual(estado):
        if estado == "DESPLAZANDOSE":
            return "🚚 Desplazándose", "#2563eb"
        if estado == "TRABAJANDO":
            return "🔧 Trabajando", "#16a34a"
        if estado == "LIBRE":
            return "🟡 Libre", "#d97706"
        if estado == "INACTIVA":
            return "🏁 Jornada finalizada", "#dc2626"
        return "⚪ Desconocido", "#6b7280"

    grid = tk.Frame(estado_frame, bg=BG_CARD)
    grid.pack(fill="both", expand=True)

    COLS = 2

    for i, c in enumerate(C):
        r = i // COLS
        col = i % COLS

        card = tk.Frame(
            grid,
            bg=BG_APP,
            highlightthickness=1,
            highlightbackground="#e5e7eb",
            padx=10,
            pady=10
        )
        card.grid(row=r, column=col, padx=8, pady=8, sticky="nsew")
        grid.grid_columnconfigure(col, weight=1)

        # HEADER
        titulo, color_estado = estado_visual(c.estado.name)

        tk.Label(
            card,
            text=f"Cuadrilla {c.id}",
            bg=BG_APP,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        tk.Label(
            card,
            text=titulo,
            bg=BG_APP,
            fg=color_estado,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 3))

        ubicacion = texto_ubicacion_cuadrilla(c)

        tk.Label(
            card,
            text=f"📍 {ubicacion}",
            bg=BG_APP,
            fg=SUBTEXT,
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        acciones = tk.Frame(card, bg=BG_APP)
        acciones.pack(fill="x", pady=(8, 0))

        # DESPLAZÁNDOSE
        if c.estado.name == "DESPLAZANDOSE":

            tk.Label(
                card,
                text=f"⏱ Trayecto: {D[c.posicion][c.visita_actual.id]:.1f} min",
                bg=BG_APP,
                fg=SUBTEXT,
                font=("Segoe UI", 9)
            ).pack(anchor="w", pady=(4, 0))

            entry = tk.Entry(acciones, width=5)
            entry.pack(side="left", padx=4)

            def llegada(c=c, e=entry):
                tiempo = leer_tiempo(e)
                if tiempo is not None:
                    cambiar_estado_cuadrilla(c.id, tiempo)
                    render_estado()

            tk.Button(
                acciones,
                text="✔ Llegada",
                bg="#2563eb",
                fg="white",
                relief="flat",
                font=("Segoe UI", 8, "bold"),
                padx=6,
                pady=2,
                command=llegada
            ).pack(side="right")

        # TRABAJANDO
        elif c.estado.name == "TRABAJANDO":

            tk.Label(
                card,
                text=f"⏱ Trabajo: {c.visita_actual.duracion} min",
                bg=BG_APP,
                fg=SUBTEXT,
                font=("Segoe UI", 9)
            ).pack(anchor="w", pady=(4, 0))

            entry = tk.Entry(acciones, width=5)
            entry.pack(side="left", padx=4)

            def fin(c=c, e=entry):
                tiempo = leer_tiempo(e)
                if tiempo is not None:
                    cambiar_estado_cuadrilla(c.id, tiempo)
                    render_estado()

            tk.Button(
                acciones,
                text="🏁 Fin",
                bg="#16a34a",
                fg="white",
                relief="flat",
                font=("Segoe UI", 8, "bold"),
                padx=6,
                pady=2,
                command=fin
            ).pack(side="right")

def crear_modal_scrollable(titulo, ancho=420, alto=520):
    win = tk.Toplevel(root)
    win.title(titulo)
    win.configure(bg=BG_APP)
    win.geometry(f"{ancho}x{alto}")
    win.minsize(ancho, alto)

    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (ancho // 2)
    y = (win.winfo_screenheight() // 2) - (alto // 2)
    win.geometry(f"+{x}+{y}")

    container = tk.Frame(win, bg=BG_APP)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, bg=BG_APP, highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=BG_APP)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return win, scroll_frame

def campo_select(parent, label, row, col, valores):
    frame = tk.Frame(parent, bg=BG_CARD)
    frame.grid(row=row, column=col, sticky="ew", padx=10, pady=8)

    tk.Label(frame, text=label,
             font=("Segoe UI", 9),
             bg=BG_CARD, fg=SUBTEXT).pack(anchor="w")

    combo = ttk.Combobox(frame,
                         values=valores,
                         state="readonly",
                         font=("Segoe UI", 11))
    combo.pack(fill="x", ipady=4, pady=3)
    combo.current(0)

    return combo

def formulario_visita():
    win, parent = crear_modal_scrollable("Nueva visita", 720, 560)

    card = tk.Frame(parent, bg=BG_CARD, padx=22, pady=20,
                    highlightthickness=1, highlightbackground="#e5e7eb")
    card.pack(padx=20, pady=20, fill="both", expand=True)

    tk.Label(card, text="➕ Nueva visita",
             font=("Segoe UI", 17, "bold"),
             bg=BG_CARD, fg="#16a34a").pack(anchor="w")

    tk.Label(card,
             text="Registrar nueva visita en el sistema",
             font=("Segoe UI", 10),
             bg=BG_CARD, fg=SUBTEXT).pack(anchor="w", pady=(0,18))

    entries = {}

    def campo(parent, label, row, col, ejemplo=""):
        frame = tk.Frame(parent, bg=BG_CARD)
        frame.grid(row=row, column=col, sticky="ew", padx=10, pady=8)

        tk.Label(frame, text=label,
                font=("Segoe UI", 9),
                bg=BG_CARD, fg=SUBTEXT).pack(anchor="w")

        e = tk.Entry(frame, font=("Segoe UI", 11),
                    relief="flat", highlightthickness=1,
                    highlightbackground="#d1d5db")
        e.pack(fill="x", ipady=7, pady=3)

        if ejemplo:
            e.insert(0, ejemplo)
            e.config(fg="#9ca3af")

            def clear_hint(event):
                if e.get() == ejemplo:
                    e.delete(0, "end")
                    e.config(fg=TEXT)
            e.bind("<FocusIn>", clear_hint)

        return e
    
    form = tk.Frame(card, bg=BG_CARD)
    form.pack(fill="x")

    # dos columnas responsivas
    form.columnconfigure(0, weight=1)
    form.columnconfigure(1, weight=1)

    entries = {}

    entries["nombre"] = campo(form, "Cliente", 0, 0)
    entries["nombre"].master.grid(columnspan=2)

    entries["tipo"] = campo_select(
        form, "Tipo", 1, 0,
        ["instalacion", "tecnica", "incidencia"]
    )
    entries["prioridad"] = campo(form, "Prioridad", 1, 1, "1-10")

    entries["latitud"] = campo(form, "Latitud", 2, 0, "40.4168")
    entries["longitud"] = campo(form, "Longitud", 2, 1, "-3.7038")

    msg = tk.Label(card, text="", bg=BG_CARD, fg="#dc2626",
                   font=("Segoe UI", 9))
    msg.pack(pady=(8,0))

    def crear():
        try:
            tipo = TipoVisita(entries["tipo"].get().strip().lower())
            visita = Visita(
                tipo=tipo,
                prioridad=int(entries["prioridad"].get()),
                nombre=entries["nombre"].get(),
                latitud=float(entries["latitud"].get()),
                longitud=float(entries["longitud"].get())
            )

            agregar_visita(visita)
            render_estado()
            win.destroy()

        except:
            msg.config(text="Revisa los datos introducidos")

    tk.Button(card, text="Crear visita",
              command=crear,
              bg="#16a34a", fg="white",
              activebackground="#15803d",
              font=("Segoe UI", 11, "bold"),
              relief="flat", pady=12).pack(fill="x", pady=18)
    
def formulario_stock():
    win, parent = crear_modal_scrollable("Actualizar stock", 420, 420)

    card = tk.Frame(parent, bg=BG_CARD, padx=22, pady=20,
                    highlightthickness=1, highlightbackground="#e5e7eb")
    card.pack(padx=20, pady=20, fill="both", expand=True)

    tk.Label(card, text="📦 Actualizar stock",
             font=("Segoe UI", 17, "bold"),
             bg=BG_CARD, fg="#d97706").pack(anchor="w")

    tk.Label(card,
             text="Añadir material disponible",
             font=("Segoe UI", 10),
             bg=BG_CARD, fg=SUBTEXT).pack(anchor="w", pady=(0,18))

    def campo(label):
        frame = tk.Frame(card, bg=BG_CARD)
        frame.pack(fill="x", pady=10)

        tk.Label(frame, text=label,
                 font=("Segoe UI", 9),
                 bg=BG_CARD, fg=SUBTEXT).pack(anchor="w")

        e = tk.Entry(frame, font=("Segoe UI", 11),
                     relief="flat", highlightthickness=1,
                     highlightbackground="#d1d5db")
        e.pack(fill="x", ipady=7, pady=3)
        return e

    id_e = campo("ID material")
    c_e = campo("Cantidad")

    msg = tk.Label(card, text="", bg=BG_CARD, fg="#dc2626",
                   font=("Segoe UI", 9))
    msg.pack()

    def aplicar():
        try:
            if not actualizar_stock(int(id_e.get()), int(c_e.get())):
                msg.config(text="Material no encontrado")
                return
            render_estado()
            win.destroy()
        except:
            msg.config(text="Valores inválidos")

    tk.Button(card, text="Actualizar stock",
              command=aplicar,
              bg="#d97706", fg="white",
              activebackground="#b45309",
              font=("Segoe UI", 11, "bold"),
              relief="flat", pady=12).pack(fill="x", pady=18)

def formulario_estado():
    win = tk.Toplevel(root)
    win.title("Estado cuadrilla")

    tk.Label(win, text="ID cuadrilla").pack()
    id_e = tk.Entry(win)
    id_e.pack()

    tk.Label(win, text="Tiempo real (si aplica)").pack()
    t_e = tk.Entry(win)
    t_e.pack()

    def aplicar():
        tiempo = t_e.get()
        tiempo = float(tiempo) if tiempo else None

        cambiar_estado_cuadrilla(int(id_e.get()), tiempo)
        render_estado()
        win.destroy()

    tk.Button(win, text="Aplicar", command=aplicar).pack()


def generar_planificacion():
    ejecutar_planificacion_gui()
    pantalla_planificacion()


# SIDEBAR
boton_activo = None
botones_menu = {}

def boton(txt, cmd):
    def wrapper():
        global boton_activo

        if boton_activo:
            boton_activo.config(bg=BG_MENU)

        cmd()

        boton_activo = botones_menu[txt]
        boton_activo.config(bg=PRIMARY)

    btn = tk.Button(
        menu,
        text=txt,
        fg="white",
        bg=BG_MENU,
        activebackground=PRIMARY,
        activeforeground="white",
        relief="flat",
        font=("Segoe UI", 11),
        pady=15,
        command=wrapper
    )

    botones_menu[txt] = btn
    return btn

boton("Visitas", pantalla_visitas).pack(fill="x")
boton("Planificación", pantalla_planificacion).pack(fill="x")
boton("Sistema Dinámico", pantalla_dinamico).pack(fill="x")


# START
inicializar_sistema()
pantalla_visitas()
root.mainloop()