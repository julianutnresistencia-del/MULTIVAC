# =============================================================================
# SMART HOME — Analizador Sintáctico (Parser) — Versión Explicada
# =============================================================================
# ¿Qué hace este archivo?
# El lexer nos dio una lista de "palabras sueltas" (Tokens). El Parser se encarga
# de revisar que esas palabras estén ordenadas formando oraciones lógicas según 
# las reglas gramaticales que nos dio la cátedra en el PDF (WHEN, EVERY, IF, etc.).
#
# Además, acá hacemos los "controles cruzados" (Validaciones Semánticas).
# El lexer no sabe qué palabra viene antes o después; pero acá, como sabemos
# exactamente qué se está leyendo, controlamos locuras como:
#   * Que no intenten cambiarle la hora al reloj (el reloj es de solo lectura).
#   * Que si eligen foco.color, el texto sea un color real (blanco, rojo, azul).
#   * Que la temperatura deseada del aire esté en el rango de confort (16°C a 30°C).
# =============================================================================

from contextlib import contextmanager
from lexer import ATRIBUTOS_POR_DISPOSITIVO

# Datos fijos para las validaciones cruzadas de la casa
VALORES_COLOR = {"blanco", "rojo", "azul"}
VALORES_MODO_AIRE = {"frio", "calor", "vent"}
OPERADORES_RELACIONALES = ["==", "!=", ">", "<", ">=", "<="]


# =============================================================================
# CONTROL Y SEGUIMIENTO DE ERRORES
# =============================================================================
class ErrorSintactico(Exception):
    """
    Una cajita de errores mejorada. Cuando el usuario se olvida un 'end' o escribe
    mal un comando, no solo guardamos la fila y columna, sino también la 'pila de 
    contexto' para saber en qué regla de la gramática estábamos metidos, y le 
    tiramos una sugerencia bien amigable para que sepa cómo arreglarlo.
    """
    def __init__(self, mensaje, linea=None, columna=None, contexto=None, sugerencia=None):
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna
        self.contexto = list(contexto) if contexto else []
        self.sugerencia = sugerencia
        super().__init__(self._formatear())

    def _formatear(self):
        encabezado = "Error de sintaxis"
        if self.linea is not None:
            encabezado += f" en línea {self.linea}, columna {self.columna}"
        texto = f"{encabezado}: {self.mensaje}"
        if self.contexto:
            # Junta el camino para mostrar algo como: PROGRAMA -> BLOQUE_WHEN -> ASIGNACION
            texto += f"\n  Contexto (¿Dónde falló?): {' -> '.join(self.contexto)}"
        if self.sugerencia:
            texto += f"\n  Sugerencia para arreglarlo: {self.sugerencia}"
        return texto

    def __str__(self):
        return self._formatear()


# Esta lista va guardando el camino de funciones por las que va pasando el código
_pila_contexto = []

@contextmanager
def contexto(nombre):
    """
    Este truco con 'with' nos permite anotar en la lista qué regla estamos evaluando.
    Si algo falla adentro del 'with', el error vas a saber exactamente en qué bloque pasó.
    Al terminar el 'with', saca el nombre de la lista automáticamente.
    """
    _pila_contexto.append(nombre)
    try:
        yield
    finally:
        _pila_contexto.pop()


# =============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# =============================================================================
def parsear(tokens):
    """
    La función que llamamos desde afuera. Le pasamos los tokens del lexer,
    limpia los comentarios (porque a la gramática no le importan) y arranca
    a revisar desde la regla principal: parse_programa().
    """
    global pos, lista_tokens

    # Filtramos los comentarios para no tener que andar esquivándolos en cada función
    lista_tokens = [t for t in tokens if t.tipo != "COMENTARIO"]
    pos = 0
    _pila_contexto.clear()

    print("Tokens a parsear:", lista_tokens)

    try:
        parse_programa()
    except ErrorSintactico as e:
        print("######################")
        print("STRING RECHAZADO :(")
        print("######################")
        print(e)
        return False
    except Exception as e:
        # Si explota Python por algún bug nuestro en el parser, lo atajamos acá
        # para no tirarle un error crudo horrible al usuario.
        print("######################")
        print("ERROR INESPERADO DEL PARSER :(")
        print("######################")
        print(f"{type(e).__name__}: {e}")
        return False

    print("######################")
    print("STRING ACEPTADO! :)")
    print("######################")

    # Al final, separamos lo que leímos en dos grandes grupos (sensores y aparatos) 
    # por si necesitamos usar estos datos limpios más adelante.
    sensores = [token for token in lista_tokens if token.tipo in ("SENSOR", "BOOLEANO_SENSOR", "LUZ", "PORCENTAJE", "TEMPERATURA")]
    dispositivos = [token for token in lista_tokens if token.tipo in ("DISPOSITIVO", "ATRIBUTO", "VALOR_DISCRETO", "TEXTO", "EMAIL", "HORA", "FECHA", "BOOLEANO_DISPOSITIVO", "PORCENTAJE", "TEMPERATURA")]

    resultado = [sensores, dispositivos]
    return resultado


# -----------------------------------------------------------------------------
# FUNCIONES DE CONTROL DE AVANCE (HERRAMIENTAS INTERNAS)
# -----------------------------------------------------------------------------

def _token_actual():
    """Devuelve el token que toca evaluar ahora, o None si llegamos al final del archivo."""
    return lista_tokens[pos] if pos < len(lista_tokens) else None


def consumir(tipo_esperado, valor_esperado=None):
    """
    Es el motor de avance. Si el token actual es del tipo que esperamos, avanza 
    el puntero a la siguiente palabra. Si no coincide, frena todo y lanza un ErrorSintactico.
    También nos deja pasarle una lista de opciones (ej: los operadores de comparación).
    """
    global pos
    token_actual = _token_actual()

    # Si nos quedamos sin tokens antes de tiempo, es que faltó cerrar algo
    if token_actual is None:
        ultimo = lista_tokens[-1] if lista_tokens else None
        linea = ultimo.linea if ultimo else None
        columna = ultimo.columna if ultimo else None
        descripcion_esperada = tipo_esperado
        if valor_esperado is not None:
            opciones = valor_esperado if isinstance(valor_esperado, (list, tuple)) else [valor_esperado]
            descripcion_esperada += f" ({' o '.join(repr(o) for o in opciones)})"
        raise ErrorSintactico(
            f"se esperaba {descripcion_esperada}, pero el archivo terminó antes de tiempo.",
            linea, columna, _pila_contexto,
            sugerencia="Revisá que todo bloque WHEN / EVERY / IF tenga su 'end' correspondiente."
        )

    tipo, valor = token_actual.tipo, token_actual.valor
    linea, columna = token_actual.linea, token_actual.columna

    # Control de tipo de palabra
    if tipo != tipo_esperado:
        raise ErrorSintactico(
            f"se esperaba un token de tipo {tipo_esperado}, pero se encontró {tipo} ('{valor}').",
            linea, columna, _pila_contexto
        )

    # Control del valor exacto de la palabra (si correspondía filtrar por valor)
    if valor_esperado is not None:
        opciones = valor_esperado if isinstance(valor_esperado, (list, tuple)) else [valor_esperado]
        if valor.strip().lower() not in [o.lower() for o in opciones]:
            raise ErrorSintactico(
                f"se esperaba {' o '.join(repr(o) for o in opciones)}, pero se encontró '{valor}'.",
                linea, columna, _pila_contexto
            )

    pos += 1 # ¡Todo bien! Avanzamos al siguiente token
    return token_actual


def token_siguiente_es(tipo, valor=None):
    """
    Espía el token actual sin consumirlo (Lookahead). Nos súper sirve para tomar 
    decisiones en los caminos del código, por ejemplo: '¿Viene un if o viene un every?'.
    """
    t = _token_actual()
    if t is None or t.tipo != tipo:
        return False
    if valor is not None:
        opciones = valor if isinstance(valor, (list, tuple)) else [valor]
        return t.valor.strip().lower() in [o.lower() for o in opciones]
    return True


def _error_atributo_no_manejado(dispositivo, atributo, token):
    """
    Función de seguridad por si el lexer acepta una propiedad pero nos olvidamos 
    de programar su comportamiento acá en el parser.
    """
    validos = ATRIBUTOS_POR_DISPOSITIVO.get(dispositivo, [])
    raise ErrorSintactico(
        f"el atributo '{atributo}' no está contemplado en la gramática del parser para '{dispositivo}'.",
        token.linea, token.columna, _pila_contexto,
        sugerencia=f"Atributos válidos para {dispositivo}: {', '.join(validos)}."
    )


# =============================================================================
# REGLAS DE LA GRAMÁTICA (PRODUCCIONES DESCENTES RECURSIVAS)
# =============================================================================

# --- 1º REGLA: PROGRAMA ---
def parse_programa():
    with contexto("PROGRAMA"):
        parse_lista_sentencias()
        # Si terminamos de procesar las oraciones pero todavía sobran palabras, está mal
        if pos < len(lista_tokens):
            t = lista_tokens[pos]
            raise ErrorSintactico(
                f"se encontró contenido inesperado después de la última sentencia válida: '{t.valor}'.",
                t.linea, t.columna, _pila_contexto,
                sugerencia="Verificá que no sobre un 'end' o que no falte cerrar algún bloque anterior."
            )

# --- LISTA DE SENTENCIAS ---
def parse_lista_sentencias():
    with contexto("LISTA_SENTENCIAS"):
        parse_sentencia()
        while pos < len(lista_tokens):
            parse_sentencia()

# --- REGLA: SENTENCIA (¿Qué tipo de comando arrancó?) ---
def parse_sentencia():
    with contexto("SENTENCIA"):
        t = _token_actual()
        if t is None:
            raise ErrorSintactico(
                "se esperaba una sentencia (when / every / if / asignación) pero no hay más tokens.",
                None, None, _pila_contexto
            )
        
        # Miramos qué palabrita viene para saber a qué función llamar
        if token_siguiente_es("RESERVADA", "when"):
            parse_bloque_when()
        elif token_siguiente_es("RESERVADA", "every"):
            parse_bloque_every()
        elif token_siguiente_es("RESERVADA", "if"):
            parse_condicional()
        elif t.tipo == "DISPOSITIVO":
            parse_asignacion()
        elif t.tipo == "SENSOR":
            # Control semántico: Un sensor suelto (ej: sensor_movimiento) no hace nada solo
            raise ErrorSintactico(
                f"el sensor '{t.valor}' es de solo lectura y no puede usarse como sentencia independiente.",
                t.linea, t.columna, _pila_contexto,
                sugerencia="Los sensores solo pueden aparecer dentro de una condición (WHEN ... / IF ...)."
            )
        else:
            raise ErrorSintactico(
                f"se esperaba el inicio de una sentencia ('when', 'every', 'if' o un dispositivo), "
                f"pero se encontró {t.tipo} ('{t.valor}').",
                t.linea, t.columna, _pila_contexto
            )


# --- 2º REGLA: ESTRUCTURAS DE CONTROL (WHEN / EVERY) ---
def parse_bloque_when():
    with contexto("BLOQUE_WHEN"):
        consumir("RESERVADA", "when")
        print("✔ WHEN reconocido")
        parse_condicion()
        print("✔ condición válida")
        consumir("RESERVADA", "do")
        print("✔ bloque DO correcto")
        parse_lista_acciones()
        consumir("RESERVADA", "end")
        print("✔ END correcto")


def parse_bloque_every():
    with contexto("BLOQUE_EVERY"):
        consumir("RESERVADA", "every")
        consumir("TIEMPO")              # Controla que venga algo como 10m o 5s
        consumir("RESERVADA", "do")
        parse_lista_acciones()
        consumir("RESERVADA", "end")


# --- 3º REGLA: CONDICIONAL (IF / THEN / ELSE) ---
def parse_condicional():
    with contexto("CONDICIONAL"):
        consumir("RESERVADA", "if")
        parse_condicion()
        consumir("RESERVADA", "then")
        parse_lista_acciones()
        # El ELSE es opcional según el PDF, por eso usamos el espía 'token_siguiente_es'
        if token_siguiente_es("RESERVADA", "else"):
            consumir("RESERVADA", "else")
            parse_lista_acciones()
        consumir("RESERVADA", "end")


# --- 4º REGLA: LISTA DE ACCIONES (Lo que va adentro de los bloques) ---
def parse_lista_acciones():
    with contexto("LISTA_ACCIONES"):
        parse_accion()
        # Sigue leyendo acciones una atrás de otra hasta que se tope con un 'end' o un 'else'
        while not token_siguiente_es("RESERVADA", ["end", "else"]):
            parse_accion()


def parse_accion():
    with contexto("ACCION"):
        t = _token_actual()
        if t is None:
            raise ErrorSintactico(
                "se esperaba una acción (asignación de dispositivo o un 'if') pero no hay más tokens.",
                None, None, _pila_contexto,
                sugerencia="¿Falta cerrar el bloque con 'end'?"
            )
        if token_siguiente_es("RESERVADA", "if"):
            parse_condicional()
        elif t.tipo == "DISPOSITIVO":
            parse_asignacion()
        elif t.tipo == "SENSOR":
            # Control semántico: No podés "forzar" a un sensor a cambiar de valor en las acciones
            raise ErrorSintactico(
                f"el sensor '{t.valor}' es de solo lectura; no se le puede asignar un valor dentro de una acción.",
                t.linea, t.columna, _pila_contexto,
                sugerencia="Los sensores solo se usan para condiciones, nunca como acción."
            )
        else:
            raise ErrorSintactico(
                f"se esperaba una acción (asignación de dispositivo o 'if'), pero se encontró {t.tipo} ('{t.valor}').",
                t.linea, t.columna, _pila_contexto
            )


# --- 8º REGLA: CONDICIONES LOGICAS (OR / AND / NOT) ---
# Separamos las funciones para respetar la precedencia de la matemática (primero NOT, después AND, al final OR)
def parse_condicion():
    with contexto("CONDICION"):
        parse_condicion_and()
        while token_siguiente_es("RESERVADA", "or"):
            consumir("RESERVADA", "or")
            parse_condicion_and()


def parse_condicion_and():
    with contexto("CONDICION_AND"):
        parse_condicion_not()
        while token_siguiente_es("RESERVADA", "and"):
            consumir("RESERVADA", "and")
            parse_condicion_not()


def parse_condicion_not():
    with contexto("CONDICION_NOT"):
        if token_siguiente_es("RESERVADA", "not"):
            consumir("RESERVADA", "not")
            parse_condicion_not()
        else:
            parse_expresion()


# --- 9º REGLA: EXPRESION (Las comparaciones reales usando '==', '>', '<', etc.) ---
def parse_expresion():
    with contexto("EXPRESION"):
        t = _token_actual()
        if t is None:
            raise ErrorSintactico(
                "se esperaba una expresión (sensor o dispositivo) pero no hay más tokens.",
                None, None, _pila_contexto
            )
        if t.tipo == "SENSOR":
            _parse_expresion_sensor()
        elif t.tipo == "DISPOSITIVO":
            _parse_expresion_dispositivo()
        else:
            raise ErrorSintactico(
                f"se esperaba un sensor o un dispositivo para iniciar la expresión, "
                f"pero se encontró {t.tipo} ('{t.valor}').",
                t.linea, t.columna, _pila_contexto
            )


def _parse_expresion_sensor():
    """Valida cómo se compara cada tipo de sensor en las condiciones (Usa operadores dobles '==')"""
    with contexto("SENSOR"):
        token = consumir("SENSOR")
        partes = token.valor.split('_')
        subtipo = partes[1] if len(partes) > 1 else ""

        if subtipo == "humo":
            consumir("OPERADOR", "==")
            consumir("BOOLEANO_SENSOR")      # true o false
        elif subtipo == "movimiento":
            consumir("OPERADOR", "==")
            consumir("BOOLEANO_SENSOR")
        elif subtipo == "luz":
            consumir("OPERADOR", OPERADORES_RELACIONALES)
            consumir("LUZ")                  # Rango 0 a 1000 lux
        elif subtipo == "humedad":
            consumir("OPERADOR", OPERADORES_RELACIONALES)
            consumir("PORCENTAJE")           # Rango 0% a 100%
        elif subtipo == "temp":
            consumir("OPERADOR", OPERADORES_RELACIONALES)
            consumir("TEMPERATURA")          # Rango -10 a 50 °C
        else:
            raise ErrorSintactico(
                f"'{token.valor}' no corresponde a ningún sensor reconocido por la gramática.",
                token.linea, token.columna, _pila_contexto,
                sugerencia="Tipos de sensor válidos: humo, movimiento, luz, humedad, temp."
            )


def _parse_expresion_dispositivo():
    """
    Valida las lecturas de los aparatos dentro de un IF o WHEN.
    Acá se controla qué tipo de dato requiere cada propiedad (atributo) de cada aparato.
    """
    with contexto("DISPOSITIVO (lectura)"):
        token = consumir("DISPOSITIVO")
        dispositivo = token.valor.split('_')[0]

        if dispositivo == "foco":
            consumir("PUNTO")
            atributo = consumir("ATRIBUTO").valor
            if atributo == "estado":
                consumir("OPERADOR", "==")
                consumir("BOOLEANO_DISPOSITIVO")  # on / off
            elif atributo == "brillo":
                consumir("OPERADOR", OPERADORES_RELACIONALES)
                consumir("PORCENTAJE")
            elif atributo == "color":
                consumir("OPERADOR", "==")
                _consumir_color()                 # Control cruzado manual de colores
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "aire":
            consumir("PUNTO")
            atributo = consumir("ATRIBUTO").valor
            if atributo == "estado":
                consumir("OPERADOR", "==")
                consumir("BOOLEANO_DISPOSITIVO")
            elif atributo == "modo":
                consumir("OPERADOR", "==")
                _consumir_modo_aire()            # Control cruzado manual de modos del aire
            elif atributo == "temp_obj":
                consumir("OPERADOR", OPERADORES_RELACIONALES)
                # Control estricto de temperatura objetivo (16 a 30 grados)
                _consumir_temperatura_rango(16, 30, "aire.temp_obj")
            elif atributo == "temp_act":
                consumir("OPERADOR", OPERADORES_RELACIONALES)
                consumir("TEMPERATURA")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "persiana":
            consumir("PUNTO")
            consumir("ATRIBUTO", "posicion")
            consumir("OPERADOR", OPERADORES_RELACIONALES)
            consumir("PORCENTAJE")

        elif dispositivo == "cerradura":
            consumir("PUNTO")
            consumir("ATRIBUTO", "estado")
            consumir("OPERADOR", "==")
            consumir("BOOLEANO_DISPOSITIVO")

        elif dispositivo == "reloj":
            consumir("PUNTO")
            atributo = consumir("ATRIBUTO").valor
            if atributo == "hora":
                consumir("OPERADOR", OPERADORES_RELACIONALES)
                consumir("HORA")
            elif atributo == "fecha":
                consumir("OPERADOR", OPERADORES_RELACIONALES)
                consumir("FECHA")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "altavoz":
            consumir("PUNTO")
            atributo = consumir("ATRIBUTO").valor
            if atributo == "volumen":
                consumir("OPERADOR", OPERADORES_RELACIONALES)
                consumir("PORCENTAJE")
            elif atributo == "mute":
                consumir("OPERADOR", "==")
                consumir("BOOLEANO_DISPOSITIVO")
            elif atributo == "mensaje":
                consumir("OPERADOR", "==")
                consumir("TEXTO")
            elif atributo == "email_notif":
                consumir("OPERADOR", "==")
                consumir("EMAIL")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "alarma":
            consumir("PUNTO")
            atributo = consumir("ATRIBUTO").valor
            if atributo in ("estado", "activada"):
                consumir("OPERADOR", "==")
                consumir("BOOLEANO_DISPOSITIVO")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        else:
            raise ErrorSintactico(
                f"'{token.valor}' no corresponde a ningún dispositivo reconocido por la gramática.",
                token.linea, token.columna, _pila_contexto
            )


# --- 5º/6º/7º REGLA: ASIGNACION (Hacer cambios físicos, ej: foco.estado = on) ---
# ¡Ojo! Acá se usa el operador simple '=' a diferencia de las expresiones que usan '=='
def parse_asignacion():
    with contexto("ASIGNACION"):
        token = consumir("DISPOSITIVO")
        dispositivo = token.valor.split('_')[0]

        # Control Semántico: El reloj no se altera de prepo, se lee del sistema
        if dispositivo == "reloj":
            raise ErrorSintactico(
                f"'{token.valor}' es de solo lectura; no se le puede asignar un valor.",
                token.linea, token.columna, _pila_contexto,
                sugerencia="El reloj solo puede leerse dentro de condiciones (WHEN/IF), nunca asignarse en una acción."
            )

        consumir("PUNTO")
        atributo = consumir("ATRIBUTO").valor

        if dispositivo == "foco":
            if atributo == "estado":
                consumir("OPERADOR", "=")
                consumir("BOOLEANO_DISPOSITIVO")
            elif atributo == "brillo":
                consumir("OPERADOR", "=")
                consumir("PORCENTAJE")
            elif atributo == "color":
                consumir("OPERADOR", "=")
                _consumir_color()
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "aire":
            if atributo == "estado":
                consumir("OPERADOR", "=")
                consumir("BOOLEANO_DISPOSITIVO")
            elif atributo == "modo":
                consumir("OPERADOR", "=")
                _consumir_modo_aire()
            elif atributo == "temp_obj":
                consumir("OPERADOR", "=")
                _consumir_temperatura_rango(16, 30, "aire.temp_obj")
            elif atributo == "temp_act":
                # Control Semántico: La temperatura actual de la pieza la define el ambiente, no el comando
                raise ErrorSintactico(
                    "aire.temp_act es de solo lectura; no se le puede asignar un valor.",
                    token.linea, token.columna, _pila_contexto,
                    sugerencia="Usá aire.temp_obj para fijar la temperatura deseada."
                )
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "persiana":
            if atributo == "posicion":
                consumir("OPERADOR", "=")
                consumir("PORCENTAJE")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "cerradura":
            if atributo == "estado":
                consumir("OPERADOR", "=")
                consumir("BOOLEANO_DISPOSITIVO")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "altavoz":
            if atributo == "volumen":
                consumir("OPERADOR", "=")
                consumir("PORCENTAJE")
            elif atributo == "mute":
                consumir("OPERADOR", "=")
                consumir("BOOLEANO_DISPOSITIVO")
            elif atributo == "mensaje":
                consumir("OPERADOR", "=")
                consumir("TEXTO")
            elif atributo == "email_notif":
                consumir("OPERADOR", "=")
                consumir("EMAIL")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        elif dispositivo == "alarma":
            if atributo in ("estado", "activada"):
                consumir("OPERADOR", "=")
                consumir("BOOLEANO_DISPOSITIVO")
            else:
                _error_atributo_no_manejado(dispositivo, atributo, token)

        else:
            raise ErrorSintactico(
                f"'{token.valor}' no corresponde a ningún dispositivo reconocido por la gramática.",
                token.linea, token.columna, _pila_contexto
            )

        print("✔ asignación válida")


# =============================================================================
# FUNCIONES AUXILIARES PARA LOGICA Y CONTROL CRUZADO SEMÁNTICO
# =============================================================================

def _consumir_color():
    """Controla que la palabra de texto asignada a foco.color sea un color permitido por el PDF."""
    token = consumir("VALOR_DISCRETO")
    if token.valor.strip().lower() not in VALORES_COLOR:
        raise ErrorSintactico(
            f"'{token.valor}' no es un color válido para .color.",
            token.linea, token.columna, _pila_contexto,
            sugerencia=f"Colores válidos: {', '.join(sorted(VALORES_COLOR))}."
        )
    return token


def _consumir_modo_aire():
    """Controla que la palabra asignada a aire.modo sea un modo real del aire."""
    token = consumir("VALOR_DISCRETO")
    if token.valor.strip().lower() not in VALORES_MODO_AIRE:
        raise ErrorSintactico(
            f"'{token.valor}' no es un modo válido para aire.modo.",
            token.linea, token.columna, _pila_contexto,
            sugerencia=f"Modos válidos: {', '.join(sorted(VALORES_MODO_AIRE))}."
        )
    return token


def _consumir_temperatura_rango(minimo, maximo, nombre_campo):
    """
    El lexer solo valida el rango físico general de un termómetro (-10 a 50 °C).
    Pero acá en el parser sabemos si se está fijando la temperatura OBJETIVO del aire,
    así que le aplicamos el límite estricto de confort (16 a 30 °C) definido por el enunciado.
    """
    token = consumir("TEMPERATURA")
    texto_numero = token.valor.lower().replace('°', '').replace('c', '')
    try:
        num = int(texto_numero)
    except ValueError:
        return token # Defensivo por si falla la conversión de tipo, aunque el lexer ya la filtró.
    
    if not (minimo <= num <= maximo):
        raise ErrorSintactico(
            f"el valor de {nombre_campo} ({token.valor}) está fuera del rango permitido "
            f"({minimo}°C a {maximo}°C).",
            token.linea, token.columna, _pila_contexto,
            sugerencia="El lexer solo valida el rango general (-10 a 50 °C); acordate que el aire tiene límites propios."
        )
    return token