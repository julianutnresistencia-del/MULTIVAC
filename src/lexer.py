"""
Módulo lexer: Analizador léxico para el lenguaje Smart Home.
Convierte un texto (archivo .smart) en una lista de objetos Token.
"""

import re  # Expresiones regulares: nos permiten buscar patrones en el texto

# ------------------------------------------------------------------
# Clase Token: representa cada pieza significativa del código fuente
# ------------------------------------------------------------------
class Token:
    """
    Un token tiene:
    - tipo:   categoría (por ejemplo "IDENT", "ON", "ASSIGN", ...)
    - valor:  el texto exacto que se encontró (ej: "foco_entrada", "ON")
    - linea:  número de línea donde aparece (para errores)
    - columna: posición dentro de la línea (para errores)
    """
    def __init__(self, tipo, valor, linea, columna):
        # self es el objeto que estamos creando.
        # Guardamos los parámetros como atributos del objeto.
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        self.columna = columna

    def __repr__(self):
        # Este método especial hace que cuando imprimamos un Token con print()
        # se vea bonito, en lugar de algo como <__main__.Token object at 0x...>
        return f"Token({self.tipo}, {self.valor!r}, {self.linea}:{self.columna})"


# ------------------------------------------------------------------
# Clase Lexer: se encarga de recorrer el texto y generar tokens
# ------------------------------------------------------------------
class Lexer:
    def __init__(self, texto):
        """
        Constructor del lexer.
        - texto: el contenido completo del archivo .smart (string)
        """
        self.texto = texto          # guardamos el texto fuente
        self.pos = 0                # índice del carácter actual (0 = inicio)
        self.linea = 1              # número de línea actual (empezamos en 1)
        self.columna = 1            # columna dentro de la línea actual
        self.tokens = []            # aquí acumularemos la lista de tokens

        # --------------------------------------------------------------
        # Tabla de patrones: cada entrada es (tipo_de_token, expresion_regular)
        # Se probarán en ESTE ORDEN. El primero que coincida, gana.
        # Las expresiones van precedidas de 'r' para indicar raw string
        # (evita que Python interprete las barras invertidas).
        # --------------------------------------------------------------
        patrones = [
            # Comentarios (hasta fin de línea)
            ("COMENTARIO", r"//[^\n]*"),

            # Palabras reservadas y valores booleanos (en orden para que no interfieran con identificadores)
            ("WHEN",   r"WHEN"),
            ("DO",     r"DO"),
            ("END",    r"END"),
            ("IF",     r"IF"),
            ("THEN",   r"THEN"),
            ("ELSE",   r"ELSE"),
            ("EVERY",  r"EVERY"),
            ("AND",    r"AND"),
            ("OR",     r"OR"),
            ("NOT",    r"NOT"),
            ("ON",       r"ON"),           # literal ON
            ("OFF",      r"OFF"),          # literal OFF
            ("TRUE",     r"TRUE"),         # valor booleano TRUE
            ("FALSE",    r"FALSE"),        # valor booleano FALSE

            #Operadores de Comparación
            ("EQ",     r"=="),    # igual
            ("NE",     r"!="),     # no igual
            ("LE",     r"<="),    # menor o igual
            ("GE",     r">="),    # mayor o igual
            ("LT",     r"<"),     # menor
            ("GT",     r">"),     # mayor
            ("ASSIGN", r"="),     # asignación (un solo igual)

            # Literales con unidad (deben ir antes que NUMBER)
            ("TEMPERATURA", r"-?\d+(?:\.\d+)?°C"),
            ("PORCENTAJE",  r"-?\d+(?:\.\d+)?%"),
            ("TIEMPO",      r"\d+(?:\.\d+)?[smh]"),
            ("ILUMINANCIA", r"\d+lux"),

            # Hora (HH:MM, 24h)
            ("HORA", r"(?:[01]\d|2[0-3]):[0-5]\d"),

             # Fecha (DD/MM/AAAA, con validación parcial)
            ("FECHA", r"(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(19|20)\d{2}"),

            # Email (simple pero cubre la mayoría de casos del enunciado)
            ("EMAIL", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"),

            # Cadena entre comillas dobles
            ("STRING", r'"[^"\\]*(?:\\.[^"\\]*)*"'),

            # Identificadores: nombres de sensores, dispositivos, atributos
            # Regla: letra o guión bajo, seguido de letras/números/guiones bajo
            ("IDENT",    r"[a-zA-Z_][a-zA-Z0-9_]*"),

            # Números simples (sin unidad todavía). Atrapa enteros y decimales.
            # \d+     = uno o más dígitos
            # (?:\.\d+)? = grupo opcional: punto seguido de más dígitos
            ("NUMBER",   r"\d+(?:\.\d+)?"),

            # Punto (para notación dispositivo.atributo)
            ("DOT", r"\."),

            # Espacios y tabulaciones (se ignoran)
            ("WS", r"[ \t]+"),

            # Salto de línea
            ("NEWLINE", r"\n"),

            # Cualquier otro carácter (error)
            ("UNKNOWN", r"."),
        ]

        # Compilamos todas las regex de una vez para eficiencia
        self.regex_patrones = []
        for tipo, patron in patrones:
            # Usamos re.IGNORECASE para que no distinga mayúsculas/minúsculas
            # Pero OJO: luego para el HTML queremos preservar el valor original.
            # Por eso guardaremos el valor tal cual, y para comparar usaremos upper().
            regex = re.compile(patron, re.IGNORECASE | re.UNICODE)
            self.regex_patrones.append((tipo, regex))


    # ------------------------------------------------------------------
    # Método principal: recorre el texto y llena self.tokens
    # ------------------------------------------------------------------
    def tokenizar(self):
        """
        Recorre el texto desde self.pos hasta el final, aplicando los patrones
        en orden. Cada vez que uno coincide, crea un Token (excepto WS y NEWLINE
        que solo actualizan posición pero no se agregan a la lista).
        Al final, retorna la lista de tokens.
        """
        while self.pos < len(self.texto):
            inicio_linea = self.linea
            inicio_col = self.columna
            match = None
            tipo_token = None
            regex_usada = None

            #Se intenta cada patron en orden
            for tipo, regex in self.regex_patrones:
                # match() busca la regex a partir de self.pos, pero solo al inicio.
                # Es decir, la coincidencia debe comenzar exactamente en self.pos.
                match = regex.match(self.texto, self.pos)
                if match:
                    tipo_token = tipo
                    regex_usada = regex
                    break  # salimos del for, nos quedamos con el primer patrón que coincide

            # Si ningún patrón coincidió, es un error léxico (carácter inválido)
            if not match:
                # Obtenemos el carácter problemático
                caracter = self.texto[self.pos] if self.pos < len(self.texto) else "EOF"
                raise SyntaxError(
                    f"Error léxico: carácter '{caracter}' no reconocido "
                    f"en línea {self.linea}, columna {self.columna}"
                )

            # Obtenemos el texto que coincidió
            texto_coincidente = match.group(0)
            longitud = len(texto_coincidente)

            # Actualizamos la posición (avanzamos)
            self.pos = match.end()
            self.columna += longitud

            # Dependiendo del tipo de token, decidimos qué hacer
            if tipo_token == "COMENTARIO":
                # Los comentarios se ignoran completamente, pero no afectan líneas.
                # no hay salto de línea dentro del comentario
                # No agregamos token, solo continuamos
                continue

            elif tipo_token == "NEWLINE":
                # Salto de línea: incrementamos línea, reiniciamos columna a 1
                self.linea += 1
                self.columna = 1
                # NO agregamos un token NEWLINE (lo ignoramos)
                continue

            elif tipo_token == "WS":
                # Espacios/tabulaciones: solo avanzamos columna, no generamos token
                continue

            elif tipo_token == 'UNKNOWN':
                #Error: caracter que no coincide con nada (deberia haber sido capturado antes)
                raise SyntaxError(
                    f'Error léxico: caracter {texto_coincidente} no valido '
                    f"en línea {self.linea}, columna {self.columna - longitud}"
                )
            else: 
                # Para el resto de los tokens, creamos el objeto Token.
                # Para las palabras reservadas y booleanos, aunque la regex es case-insensitive,
                # guardamos el valor original (tal como apareció en el texto).
                # Pero para facilitar el parser, podríamos convertir a mayúsculas.
                # Decidimos guardar el valor original, y el parser lo normalizará si necesita comparar.
                token = Token(
                    tipo=tipo_token,
                    valor=texto_coincidente,   # valor original
                    linea=inicio_linea,        # línea donde comenzó el token
                    columna=inicio_col
                )
                self.tokens.append(token)

        return self.tokens

           