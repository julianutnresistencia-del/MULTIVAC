# =============================================================================
# SMART HOME — Interfaz gráfica (Tkinter)
# =============================================================================
# Esta GUI NO modifica lexer.py ni parser.py: los importa y los usa tal cual.
# Pantallas (frames dentro de una misma ventana):
#   1) Presentacion   -> bienvenida al programa
#   2) Seleccion      -> elegir archivo .smart o escribir código a mano
#   3) Analizando     -> barra de progreso mientras corre el análisis
#   4) Resultados     -> pestañas: Tokens / Errores léxicos / Análisis sintáctico
#
# Integración con el parser (aún no terminado):
#   parsear() actualmente imprime por consola. En vez de esperar a que
#   devuelva datos estructurados, redirigimos sys.stdout con
#   contextlib.redirect_stdout mientras se ejecuta, y mostramos ese texto
#   capturado en la pestaña "Análisis sintáctico". A medida que el parser
#   se vaya completando, esta pantalla va a mostrar automáticamente más
#   información, sin tocar un solo archivo de este proyecto.
# 
#   para ejecutar -> python gui.py
#
# =============================================================================

import os
import sys
import io
import threading
import contextlib
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from lexer import motor_lexer
from parser import parsear
from html_generator import guardar_html

EXTENSION_ESPERADA = ".smart"

# --- Paleta simple, para no andar repitiendo colores por todos lados -------
COLOR_FONDO = "#1e1e2e"
COLOR_PANEL = "#282a3a"
COLOR_TEXTO = "#e6e6e6"
COLOR_ACCENTO = "#7aa2f7"
COLOR_ERROR = "#f7768e"
COLOR_OK = "#9ece6a"


def hacer_solo_lectura_pero_copiable(text_widget):
    """Deja un tk.Text de solo lectura (no se puede escribir) pero permite
    seleccionar con el mouse y copiar (Ctrl+C / Ctrl+A), a diferencia de
    state="disabled", que en Tkinter también bloquea la selección."""

    def bloquear_tecla(event):
        # Ctrl+C (copiar) y Ctrl+A (seleccionar todo) siempre permitidos
        control_presionado = (event.state & 0x4) != 0
        if control_presionado and event.keysym.lower() in ("c", "a"):
            if event.keysym.lower() == "a":
                text_widget.tag_add("sel", "1.0", "end")
                return "break"
            return  # dejar pasar Ctrl+C
        # Teclas de navegación permitidas (no modifican el contenido)
        if event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End",
            "Prior", "Next", "Shift_L", "Shift_R", "Control_L", "Control_R"
        ):
            return
        return "break"  # bloquea cualquier otra tecla (edición)

    text_widget.bind("<Key>", bloquear_tecla)
    # El cursor de "texto" (I-beam) confunde si parece editable; mejor
    # mantenerlo, ya que igual se puede seleccionar y copiar.
    return text_widget


def copiar_seleccion_treeview(treeview, event=None):
    """Copia al portapapeles las filas seleccionadas de un Treeview,
    una por línea, con las columnas separadas por tabulador."""
    filas = treeview.selection()
    if not filas:
        return
    lineas = []
    for fila in filas:
        valores = treeview.item(fila, "values")
        lineas.append("\t".join(str(v) for v in valores))
    texto = "\n".join(lineas)
    treeview.clipboard_clear()
    treeview.clipboard_append(texto)


class SmartHomeApp(tk.Tk):
    """Ventana principal. Administra el estado compartido y el cambio de pantallas."""

    def __init__(self):
        super().__init__()
        self.title("SMART HOME — Analizador Léxico/Sintáctico")
        self.geometry("880x620")
        self.minsize(760, 560)
        self.configure(bg=COLOR_FONDO)

        # --- Estado compartido entre pantallas ---
        self.ruta_archivo = None      # None si se usó modo "texto directo"
        self.codigo_fuente = ""
        self.tokens = []
        self.errores = []
        self.salida_parser = ""
        self.ruta_html_generado = None

        self._crear_menu()

        # Contenedor donde se apilan los frames
        self.contenedor = tk.Frame(self, bg=COLOR_FONDO)
        self.contenedor.pack(fill="both", expand=True)
        self.contenedor.grid_rowconfigure(0, weight=1)
        self.contenedor.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (PantallaPresentacion, PantallaSeleccion, PantallaAnalizando, PantallaResultados):
            frame = F(self.contenedor, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.mostrar("PantallaPresentacion")

    # ------------------------------------------------------------------
    def _crear_menu(self):
        menubar = tk.Menu(self)

        menu_archivo = tk.Menu(menubar, tearoff=0)
        menu_archivo.add_command(label="Nuevo análisis", command=self.reiniciar)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Salir", command=self.destroy)
        menubar.add_cascade(label="Archivo", menu=menu_archivo)

        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menu_ayuda.add_command(label="Acerca de", command=self._acerca_de)
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda)

        self.config(menu=menubar)

    def _acerca_de(self):
        messagebox.showinfo(
            "Acerca de",
            "SMART HOME — Analizador léxico/sintáctico\n"
            "Interfaz gráfica construida sobre el motor de lexer.py y parser.py."
        )

    def mostrar(self, nombre_frame):
        frame = self.frames[nombre_frame]
        frame.tkraise()
        if hasattr(frame, "al_mostrar"):
            frame.al_mostrar()

    def reiniciar(self):
        self.ruta_archivo = None
        self.codigo_fuente = ""
        self.tokens = []
        self.errores = []
        self.salida_parser = ""
        self.ruta_html_generado = None
        self.mostrar("PantallaSeleccion")

    def iniciar_analisis(self):
        self.mostrar("PantallaAnalizando")


# =============================================================================
# PANTALLA 1 — Presentación
# =============================================================================
class PantallaPresentacion(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_FONDO)
        self.app = app

        centro = tk.Frame(self, bg=COLOR_FONDO)
        centro.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(
            centro, text="SMART HOME", font=("Segoe UI", 34, "bold"),
            bg=COLOR_FONDO, fg=COLOR_ACCENTO
        ).pack(pady=(0, 6))

        tk.Label(
            centro, text="Analizador léxico y sintáctico",
            font=("Segoe UI", 14), bg=COLOR_FONDO, fg=COLOR_TEXTO
        ).pack(pady=(0, 30))

        tk.Button(
            centro, text="Comenzar", font=("Segoe UI", 12, "bold"),
            bg=COLOR_ACCENTO, fg="#1e1e2e", activebackground="#5a7fd0",
            relief="flat", padx=24, pady=10, cursor="hand2",
            command=lambda: app.mostrar("PantallaSeleccion")
        ).pack()

        tk.Label(
            self, text="Trabajo Práctico — Teoría de Lenguajes de Programación",
            font=("Segoe UI", 9), bg=COLOR_FONDO, fg="#8a8fa3"
        ).pack(side="bottom", pady=14)


# =============================================================================
# PANTALLA 2 — Selección de entrada (archivo .smart o texto libre)
# =============================================================================
class PantallaSeleccion(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_FONDO)
        self.app = app

        tk.Label(
            self, text="Elegí cómo querés ingresar el código",
            font=("Segoe UI", 18, "bold"), bg=COLOR_FONDO, fg=COLOR_TEXTO
        ).pack(pady=(30, 20))

        # --- Selector de modo ---
        modos = tk.Frame(self, bg=COLOR_FONDO)
        modos.pack(pady=(0, 10))

        self.modo = tk.StringVar(value="archivo")
        tk.Radiobutton(
            modos, text="Archivo .smart", variable=self.modo, value="archivo",
            command=self._actualizar_modo, bg=COLOR_FONDO, fg=COLOR_TEXTO,
            selectcolor=COLOR_PANEL, activebackground=COLOR_FONDO,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=12)
        tk.Radiobutton(
            modos, text="Escribir código directamente", variable=self.modo, value="texto",
            command=self._actualizar_modo, bg=COLOR_FONDO, fg=COLOR_TEXTO,
            selectcolor=COLOR_PANEL, activebackground=COLOR_FONDO,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=12)

        # --- Panel modo archivo ---
        self.panel_archivo = tk.Frame(self, bg=COLOR_PANEL)
        self.lbl_ruta = tk.Label(
            self.panel_archivo, text="Ningún archivo seleccionado",
            bg=COLOR_PANEL, fg="#8a8fa3", font=("Segoe UI", 10), wraplength=600
        )
        self.lbl_ruta.pack(pady=(20, 10))
        tk.Button(
            self.panel_archivo, text="Seleccionar archivo .smart...",
            font=("Segoe UI", 11), bg=COLOR_ACCENTO, fg="#1e1e2e",
            relief="flat", padx=14, pady=8, cursor="hand2",
            command=self._elegir_archivo
        ).pack(pady=(0, 20))

        # --- Panel modo texto ---
        self.panel_texto = tk.Frame(self, bg=COLOR_PANEL)
        tk.Label(
            self.panel_texto, text="Escribí o pegá el código a analizar:",
            bg=COLOR_PANEL, fg=COLOR_TEXTO, font=("Segoe UI", 10)
        ).pack(anchor="w", padx=14, pady=(14, 4))
        self.txt_codigo = tk.Text(
            self.panel_texto, height=12, width=70, bg="#11121a", fg=COLOR_TEXTO,
            insertbackground=COLOR_TEXTO, relief="flat", font=("Consolas", 11)
        )
        self.txt_codigo.pack(padx=14, pady=(0, 14))

        # --- Botones de navegación ---
        nav = tk.Frame(self, bg=COLOR_FONDO)
        nav.pack(side="bottom", pady=20)
        tk.Button(
            nav, text="← Volver", font=("Segoe UI", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO,
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=lambda: app.mostrar("PantallaPresentacion")
        ).pack(side="left", padx=8)
        tk.Button(
            nav, text="Analizar →", font=("Segoe UI", 11, "bold"), bg=COLOR_OK, fg="#1e1e2e",
            relief="flat", padx=18, pady=8, cursor="hand2",
            command=self._confirmar
        ).pack(side="left", padx=8)

        self._actualizar_modo()

    def _actualizar_modo(self):
        self.panel_archivo.pack_forget()
        self.panel_texto.pack_forget()
        if self.modo.get() == "archivo":
            self.panel_archivo.pack(pady=10, padx=40, fill="x")
        else:
            self.panel_texto.pack(pady=10, padx=20)

    def _elegir_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo .smart",
            filetypes=[("Archivos SMART", "*.smart"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            self.lbl_ruta.config(text=ruta, fg=COLOR_TEXTO)
            self._ruta_elegida = ruta

    def _confirmar(self):
        app = self.app
        if self.modo.get() == "archivo":
            ruta = getattr(self, "_ruta_elegida", None)
            if not ruta:
                messagebox.showwarning("Falta un archivo", "Primero seleccioná un archivo .smart.")
                return

            _, ext = os.path.splitext(ruta)
            if ext.lower() != EXTENSION_ESPERADA:
                messagebox.showerror(
                    "Extensión inválida",
                    f"El archivo debe tener extensión \"{EXTENSION_ESPERADA}\".\n"
                    f"Se recibió: \"{ext or '(sin extensión)'}\""
                )
                return
            if not os.path.isfile(ruta):
                messagebox.showerror("Archivo inválido", f"'{ruta}' no es un archivo válido.")
                return

            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except (OSError, UnicodeDecodeError) as e:
                messagebox.showerror("Error de lectura", f"No se pudo leer el archivo.\n\nDetalle: {e}")
                return

            app.ruta_archivo = ruta
            app.codigo_fuente = contenido
        else:
            contenido = self.txt_codigo.get("1.0", "end-1c")
            if not contenido.strip():
                messagebox.showwarning("Falta código", "Escribí o pegá algún código para analizar.")
                return
            app.ruta_archivo = None
            app.codigo_fuente = contenido

        app.iniciar_analisis()


# =============================================================================
# PANTALLA 3 — Analizando (barra de progreso, corre en un thread aparte)
# =============================================================================
class PantallaAnalizando(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_FONDO)
        self.app = app

        centro = tk.Frame(self, bg=COLOR_FONDO)
        centro.place(relx=0.5, rely=0.45, anchor="center")

        self.lbl_estado = tk.Label(
            centro, text="Analizando código...", font=("Segoe UI", 15),
            bg=COLOR_FONDO, fg=COLOR_TEXTO
        )
        self.lbl_estado.pack(pady=(0, 16))

        estilo = ttk.Style()
        estilo.theme_use("default")
        estilo.configure("Custom.Horizontal.TProgressbar", background=COLOR_ACCENTO)

        self.barra = ttk.Progressbar(
            centro, mode="indeterminate", length=380,
            style="Custom.Horizontal.TProgressbar"
        )
        self.barra.pack()

    def al_mostrar(self):
        self.barra.start(12)
        self.lbl_estado.config(text="Analizando código...")
        threading.Thread(target=self._ejecutar_analisis, daemon=True).start()

    def _ejecutar_analisis(self):
        app = self.app
        codigo = app.codigo_fuente

        # 1) Análisis léxico
        tokens, errores = motor_lexer(codigo)
        app.tokens = tokens
        app.errores = errores

        # 2) Análisis sintáctico (solo si el léxico no tuvo errores,
        #    igual que hace main.py). Se captura todo lo que parsear()
        #    imprima por consola para poder mostrarlo en la GUI, sin
        #    tener que modificar parser.py.
        salida = ""
        resultado_parser = None
        if not errores:
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    resultado_parser = parsear(tokens)
            except Exception as e:
                buffer.write(f"\n[La GUI capturó una excepción del parser: {e}]\n")
            salida = buffer.getvalue()
        else:
            salida = "(No se ejecuta el análisis sintáctico: hay errores léxicos que resolver primero.)"

        app.salida_parser = salida

        # 3) Generación del HTML (mismo paso que hace main.py en modo archivo/
        #    interactivo, que antes faltaba acá: la GUI corría el parser pero
        #    nunca escribía el dashboard a disco).
        app.ruta_html_generado = None
        if resultado_parser:
            if app.ruta_archivo:
                base, _ = os.path.splitext(app.ruta_archivo)
                ruta_html = base + ".html"
            else:
                ruta_html = "gui_dashboard.html"
            try:
                if guardar_html(resultado_parser, ruta_html):
                    app.ruta_html_generado = os.path.abspath(ruta_html)
            except OSError as e:
                app.salida_parser += f"\n[No se pudo escribir el HTML ({ruta_html}): {e}]\n"

        # Volver al hilo principal de Tkinter para cambiar de pantalla
        self.after(0, self._finalizar)

    def _finalizar(self):
        self.barra.stop()
        self.app.mostrar("PantallaResultados")


# =============================================================================
# PANTALLA 4 — Resultados (pestañas: Tokens / Errores / Sintáctico)
# =============================================================================
class PantallaResultados(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_FONDO)
        self.app = app

        header = tk.Frame(self, bg=COLOR_FONDO)
        header.pack(fill="x", padx=20, pady=(16, 6))
        self.lbl_titulo = tk.Label(
            header, text="Resultados del análisis", font=("Segoe UI", 16, "bold"),
            bg=COLOR_FONDO, fg=COLOR_TEXTO
        )
        self.lbl_titulo.pack(side="left")

        self.btn_abrir_html = tk.Button(
            header, text="Abrir HTML generado", font=("Segoe UI", 9, "bold"),
            bg=COLOR_OK, fg="#1e1e2e", relief="flat", padx=12, pady=6,
            cursor="hand2", command=self._abrir_html
        )
        # Se muestra/oculta según haya (o no) HTML generado; ver al_mostrar().

        estilo = ttk.Style()
        estilo.theme_use("default")
        estilo.configure("TNotebook", background=COLOR_FONDO, borderwidth=0)
        estilo.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Pestaña Tokens ---
        self.tab_tokens = tk.Frame(self.notebook, bg=COLOR_FONDO)
        cols = ("#", "Token")
        self.tabla_tokens = ttk.Treeview(
            self.tab_tokens, columns=cols, show="headings", selectmode="extended"
        )
        self.tabla_tokens.heading("#", text="#")
        self.tabla_tokens.heading("Token", text="Token")
        self.tabla_tokens.column("#", width=60, anchor="center")
        self.tabla_tokens.column("Token", width=680, anchor="w")
        scroll_tok = ttk.Scrollbar(self.tab_tokens, orient="vertical", command=self.tabla_tokens.yview)
        self.tabla_tokens.configure(yscrollcommand=scroll_tok.set)
        self.tabla_tokens.pack(side="left", fill="both", expand=True, padx=(0, 0), pady=8)
        scroll_tok.pack(side="right", fill="y", pady=8)
        self.notebook.add(self.tab_tokens, text="Tokens")

        # Copiar con Ctrl+C, y también con clic derecho -> menú contextual
        self.tabla_tokens.bind(
            "<Control-c>", lambda e: copiar_seleccion_treeview(self.tabla_tokens)
        )
        self._menu_tokens = tk.Menu(self.tabla_tokens, tearoff=0)
        self._menu_tokens.add_command(
            label="Copiar fila(s) seleccionada(s)",
            command=lambda: copiar_seleccion_treeview(self.tabla_tokens)
        )
        self._menu_tokens.add_command(
            label="Seleccionar todo",
            command=lambda: self.tabla_tokens.selection_set(self.tabla_tokens.get_children())
        )

        def _abrir_menu_tokens(event):
            fila = self.tabla_tokens.identify_row(event.y)
            if fila and fila not in self.tabla_tokens.selection():
                self.tabla_tokens.selection_set(fila)
            self._menu_tokens.tk_popup(event.x_root, event.y_root)

        self.tabla_tokens.bind("<Button-3>", _abrir_menu_tokens)

        # --- Pestaña Errores léxicos ---
        self.tab_errores = tk.Frame(self.notebook, bg=COLOR_FONDO)
        self.txt_errores = tk.Text(
            self.tab_errores, bg="#11121a", fg=COLOR_ERROR, insertbackground=COLOR_TEXTO,
            relief="flat", font=("Consolas", 11), wrap="word"
        )
        self.txt_errores.pack(fill="both", expand=True, padx=8, pady=8)
        hacer_solo_lectura_pero_copiable(self.txt_errores)
        self.notebook.add(self.tab_errores, text="Errores léxicos")

        # --- Pestaña Análisis sintáctico ---
        self.tab_sint = tk.Frame(self.notebook, bg=COLOR_FONDO)
        self.txt_sint = tk.Text(
            self.tab_sint, bg="#11121a", fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO,
            relief="flat", font=("Consolas", 11), wrap="word"
        )
        self.txt_sint.pack(fill="both", expand=True, padx=8, pady=8)
        hacer_solo_lectura_pero_copiable(self.txt_sint)
        self.notebook.add(self.tab_sint, text="Análisis sintáctico")

        # --- Navegación ---
        nav = tk.Frame(self, bg=COLOR_FONDO)
        nav.pack(side="bottom", pady=14)
        tk.Button(
            nav, text="← Analizar otro", font=("Segoe UI", 10, "bold"),
            bg=COLOR_ACCENTO, fg="#1e1e2e", relief="flat", padx=16, pady=8,
            cursor="hand2", command=app.reiniciar
        ).pack(side="left", padx=8)
        tk.Button(
            nav, text="Salir", font=("Segoe UI", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO,
            relief="flat", padx=16, pady=8, cursor="hand2", command=app.destroy
        ).pack(side="left", padx=8)

    def _abrir_html(self):
        if self.app.ruta_html_generado:
            webbrowser.open(f"file://{self.app.ruta_html_generado}")

    def al_mostrar(self):
        app = self.app
        origen = app.ruta_archivo if app.ruta_archivo else "(código escrito directamente)"
        self.lbl_titulo.config(text=f"Resultados — {origen}")

        if app.ruta_html_generado:
            self.btn_abrir_html.pack(side="right")
        else:
            self.btn_abrir_html.pack_forget()

        # Tokens
        self.tabla_tokens.delete(*self.tabla_tokens.get_children())
        for i, t in enumerate(app.tokens, start=1):
            self.tabla_tokens.insert("", "end", values=(i, str(t)))

        # Errores léxicos
        self.txt_errores.config(state="normal")
        self.txt_errores.delete("1.0", "end")
        if app.errores:
            for e in app.errores:
                self.txt_errores.insert("end", f"• {e}\n")
        else:
            self.txt_errores.insert("end", "Sin errores léxicos. ✔")

        # Análisis sintáctico
        self.txt_sint.config(state="normal")
        self.txt_sint.delete("1.0", "end")
        self.txt_sint.insert("end", app.salida_parser or "(sin salida)")

        # Título de pestañas con conteos
        self.notebook.tab(self.tab_tokens, text=f"Tokens ({len(app.tokens)})")
        self.notebook.tab(self.tab_errores, text=f"Errores léxicos ({len(app.errores)})")


# =============================================================================
if __name__ == "__main__":
    app = SmartHomeApp()
    app.mainloop()
