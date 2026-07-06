# =============================================================================
# SMART HOME — Analizador Léxico (Lexer)
# =============================================================================
# ¿Qué hace este archivo?
# Lee el archivo de texto que escribe el usuario con los comandos de la casa,
# limpia los espacios en blanco, junta las letras y números para armar "palabras"
# con sentido (Tokens) y avisa si el usuario escribió un caracter raro o inválido.
# =============================================================================

# -----------------------------------------------------------------------------
# PALABRAS Y SÍMBOLOS PERMITIDOS
# -----------------------------------------------------------------------------
# Estas listas las sacamos del enunciado del PDF. Son las palabras y símbolos
# que el lenguaje de la cátedra reconoce. Si no está acá, no sirve.

PALABRAS_RESERVADAS = [
    "if", "then", "else", "end", "or", "and", "not",
    "when", "every", "do"
]

# Modos de encendido/apagado para los aparatos y para los sensores
BOOLEANOS_DISPOSITIVO = ["on", "off"]
BOOLEANOS_SENSOR = ["true", "false"]

# Operadores de matemática y comparación
OPERADORES_BASICOS   = ["-", "*", "/", "=","<", ">", "!"]
OPERADORES_VALIDOS   = ["-", "*", "/", "=","<", ">", "!", "==", "!=", "<=", ">="]

# Qué propiedad (atributo) le pertenece a qué aparato.
# Esto nos sirve para que nadie intente hacer algo imposible, como cambiarle
# el "brillo" al "reloj". Cada aparato tiene sus opciones fijas.
ATRIBUTOS_POR_DISPOSITIVO = {
    "foco":      ["estado", "brillo", "color"],
    "aire":      ["estado", "modo", "temp_obj", "temp_act"],
    "persiana":  ["posicion"],
    "cerradura": ["estado"],
    "altavoz":   ["volumen", "mute", "mensaje", "email_notif"],
    "alarma":    ["estado", "activada"],
    "reloj":     ["hora", "fecha"],
}

# Una lista rápida con todos los atributos mezclados para buscar más fácil después
ATRIBUTOS_VALIDOS = sorted({a for lista in ATRIBUTOS_POR_DISPOSITIVO.values() for a in lista})

DISPOSITIVOS_VALIDOS = [
    "foco", "aire", "persiana", "cerradura", "reloj", "altavoz", "alarma"
]

SENSORES_VALIDOS = [
    "luz", "temp", "humedad", "movimiento", "humo"
]

# Valores específicos de texto que pueden tomar cosas como el color o el modo del aire
VALORES_DISCRETOS_VALIDOS = [
    "blanco", "rojo", "azul",          # Para foco.color
    "frio", "calor", "vent",           # Para aire.modo
]

# Datos fijos para controlar que las fechas que ingresen sean reales
DIAS_POR_MES = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
NOMBRE_MES   = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

# =============================================================================
# ESTRUCTURAS PRINCIPALES
# =============================================================================

class Token:
    """
    Es una cajita donde guardamos cada palabra válida que encontramos.
    Guardamos de qué tipo es (NÚMERO, OPERADOR, etc.), su texto real, 
    y en qué fila y columna estaba por si el parser después encuentra un error.
    """
    def __init__(self, tipo, valor, linea, columna):
        self.tipo    = tipo
        self.valor   = valor
        self.linea   = linea
        self.columna = columna

    def __repr__(self):
        return (f"Token({self.tipo}, {repr(self.valor)}, "
                f"linea={self.linea}, col={self.columna})")


class ErrorLexico:
    """
    Cajita para guardar cuando el usuario escribe algo que no corresponde.
    Guarda el mensaje de error y dónde pasó, para mostrarlo lindo en la pantalla.
    """
    def __init__(self, mensaje, linea, columna):
        self.mensaje = mensaje
        self.linea   = linea
        self.columna = columna

    def __repr__(self):
        return (f"Error léxico en línea {self.linea}, "
                f"columna {self.columna}: {self.mensaje}")

# =============================================================================
# FUNCIONES DE AYUDA (HELPERS)
# =============================================================================
# Funciones simples hechas a mano para no usar las de Python (.isdigit()),
# porque las de Python a veces aceptan caracteres raros de otros idiomas.

def es_digito(c):
    return '0' <= c <= '9'

def es_letra(c):
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z')

def es_solo_digitos(texto):
    if len(texto) == 0:
        return False
    for c in texto:
        if not es_digito(c):
            return False
    return True

# =============================================================================
# CLASIFICADOR DE CARACTERES
# =============================================================================
def clasificar_caracter(caracter):
    """
    Lee un caracter suelto y nos dice qué tipo de símbolo es.
    Esto le sirve a la tabla de abajo para saber a qué estado moverse.
    """
    match caracter:
        case '%':  return 'Porcentaje'
        case '°':  return 'Grados'
        case ':':  return 'Separador_horario'
        case '/':  return 'Barra'
        case '-':  return 'Menos'
        case '+':  return 'Mas'
        case '.':  return 'Selector'
        case '_':  return 'Guion'
        case '@':  return 'Arroba'
        case '"':  return 'Comillas'
        case '\n': return 'NuevaLinea'
        case ' ':  return 'Espacio'
        case '\t': return 'Espacio'
        case '\r': return 'Espacio'
        case _ if caracter in OPERADORES_BASICOS: return 'Operador'
        case _ if es_digito(caracter):    return 'Numero'
        case _ if es_letra(caracter):     return 'Letra'
        case _:    return 'Desconocido'

# =============================================================================
# TABLA DEL AUTÓMATA (DFA)
# =============================================================================
# Esta es la lógica del dibujo de estados. Dependiendo de en qué estado estemos
# y qué caracter venga, la tabla dice a qué estado pasar.
# Si dice "ACEPTACION", significa que la palabra terminó ahí; guardamos lo que
# juntamos y volvemos a empezar desde "INICIO" con el caracter actual.

tabla_transiciones = {
    "INICIO": {
        "Letra"          : "PALABRA",
        "Numero"         : "DIGITO",
        "Operador"       : "OPERADOR",
        "Espacio"        : "INICIO",
        "NuevaLinea"     : "INICIO",
        "Menos"          : "DIGITO",          # Por si meten un número negativo como -5°c
        "Barra"          : "BARRA_INICIAL",   # Puede terminar siendo un comentario '//'
        "Comillas"       : "COMILLA_ABIERTA", # Empieza un texto libre entre comillas
    },
    "PALABRA": {
        "Letra"          : "PALABRA",
        "Guion"          : "IDENTIFICADOR",   # Para nombres con guion bajo como sensor_luz
        "Numero"         : "MAIL_POSIBLE",    # Por si el correo tiene números: julian123@...
        "Mas"            : "MAIL_POSIBLE",    # Correos con signo más
        "Selector"       : "SELECTOR",        # El puntito de foco.estado
        "Operador"       : "ACEPTACION",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Arroba"         : "DOMINIO_MAIL",
        "Barra"          : "ERROR",
        "Comillas"       : "ERROR",
    },
    "DIGITO": {
        "Numero"         : "DIGITO",
        "Porcentaje"     : "PORCENTAJE",      # Si viene '%', va para porcentaje
        "Grados"         : "GRADOS",          # Si viene '°', va camino a temperatura
        "Barra"          : "FECHA_MES",       # Si viene '/', es una fecha (DD/)
        "Separador_horario" : "HORA_MIN",     # Si viene ':', es una hora (HH:)
        "Letra"          : "TIEMPO_LUZ",      # El código decidirá si son horas/minutos (h,m,s) o lux (l,lux)
        "Operador"       : "ACEPTACION",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Menos"          : "DIGITO",
    },
    "OPERADOR": {
        "Letra"          : "ACEPTACION",
        "Numero"         : "ACEPTACION",
        "Operador"       : "OPERADOR",        # Para operadores dobles como '==' o '>='
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Barra"          : "ERROR",
        "Comillas"       : "ERROR",
    },
    "GRADOS": {
        "Letra"          : "TEMPERATURA",     # Sí o sí tiene que venir la 'c' o 'C' después del '°'
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Espacio"        : "ERROR",
        "NuevaLinea"     : "ERROR",
    },
    "TEMPERATURA": {
        "Letra"          : "TEMPERATURA",
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "PORCENTAJE": {
        "Letra"          : "ERROR",
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "TIEMPO_LUZ": {
        "Letra"          : "TIEMPO_LUZ",
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "TIEMPO": {
        "Letra"          : "ERROR",
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "LUZ": {
        "Letra"          : "LUZ",
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "IDENTIFICADOR": {
        "Letra"          : "IDENTIFICADOR",
        "Selector"       : "SELECTOR",
        "Numero"         : "IDENTIFICADOR",   
        "Guion"          : "IDENTIFICADOR",   # Para nombres largos como foco_pieza_juan
        "Arroba"         : "DOMINIO_MAIL",    
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "SELECTOR": {
        "Letra"          : "ATRIBUTO",        # Después del punto del objeto, tiene que venir la propiedad
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Guion"          : "ERROR",
        "Selector"       : "ERROR",
        "Espacio"        : "ERROR",
        "NuevaLinea"     : "ERROR",
    },
    "ATRIBUTO": {
        "Letra"          : "ATRIBUTO",
        "Guion"          : "ATRIBUTO",
        "Arroba"         : "DOMINIO_MAIL",   
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Selector"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "FECHA_MES": {
        "Numero"         : "FECHA_MES",       # Junta los números del mes
        "Barra"          : "FECHA_ANIO",      # Segunda barra, pasa a juntar el año
    },
    "FECHA_ANIO": {
        "Numero"         : "FECHA_ANIO",      # Junta los números del año
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "HORA_MIN": {
        "Numero"         : "HORA_MIN",        # Junta los minutos después de los dos puntos
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "MAIL_POSIBLE": {
        "Letra"          : "MAIL_POSIBLE",
        "Numero"         : "MAIL_POSIBLE",
        "Selector"       : "MAIL_POSIBLE",
        "Guion"          : "MAIL_POSIBLE",
        "Mas"            : "MAIL_POSIBLE",
        "Arroba"         : "DOMINIO_MAIL",    # Si encuentra el arroba, es un correo cantado
        "Espacio"        : "ERROR",
        "NuevaLinea"     : "ERROR",
        "Operador"       : "ERROR",
    },
    "DOMINIO_MAIL": {
        "Letra"          : "DOMINIO_MAIL",
        "Numero"         : "DOMINIO_MAIL",
        "Menos"          : "DOMINIO_MAIL",
        "Guion"          : "DOMINIO_MAIL",
        "Mas"            : "DOMINIO_MAIL",
        "Selector"       : "EXTENSION1",      # El puntito antes del .com
        "Espacio"        : "ERROR",
        "NuevaLinea"     : "ERROR",
    },
    "EXTENSION1": {
        "Letra"          : "EXTENSION2",
        "Numero"         : "EXTENSION2",
        "Espacio"        : "ERROR",
    },
    "EXTENSION2": {
        "Letra"          : "EXTENSION3",
        "Numero"         : "EXTENSION3",
        "Selector"       : "EXTENSION1",      # Por si el mail termina en .com.ar (vuelve a pedir extensión)
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "EXTENSION3": {
        "Letra"          : "EXTENSION4",
        "Numero"         : "EXTENSION4",
        "Selector"       : "EXTENSION1",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "EXTENSION4": {
        "Letra"          : "ERROR",
        "Numero"         : "ERROR",
        "Selector"       : "EXTENSION1",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "BARRA_INICIAL": {
        "Barra"          : "COMENTARIO",      # Si vienen dos barras seguidas '//', es un comentario
    },
    "COMENTARIO": {
        # Adentro de un comentario nos tragamos todo lo que venga hasta encontrar un salto de línea
        "Letra"          : "COMENTARIO",
        "Numero"         : "COMENTARIO",
        "Operador"       : "COMENTARIO",
        "Espacio"        : "COMENTARIO",
        "Barra"          : "COMENTARIO",
        "Guion"          : "COMENTARIO",
        "Selector"       : "COMENTARIO",
        "Arroba"         : "COMENTARIO",
        "Comillas"       : "COMENTARIO",
        "Porcentaje"     : "COMENTARIO",
        "Grados"         : "COMENTARIO",
        "Menos"          : "COMENTARIO",
        "Desconocido"    : "COMENTARIO",
        "NuevaLinea"     : "ACEPTACION",     # Al cambiar de línea, se termina el comentario
    },
    "COMILLA_ABIERTA": {
        # Juntamos todo el texto libre hasta que aparezca la comilla de cierre
        "Letra"          : "TEXTO_COMILLAS",
        "Numero"         : "TEXTO_COMILLAS",
        "Espacio"        : "TEXTO_COMILLAS",
        "Operador"       : "TEXTO_COMILLAS",
        "Barra"          : "TEXTO_COMILLAS",
        "Guion"          : "TEXTO_COMILLAS",
        "Selector"       : "TEXTO_COMILLAS",
        "Arroba"         : "TEXTO_COMILLAS",
        "Porcentaje"     : "TEXTO_COMILLAS",
        "Grados"         : "TEXTO_COMILLAS",
        "Menos"          : "TEXTO_COMILLAS",
        "Mas"            : "TEXTO_COMILLAS",
        "Separador_horario" : "TEXTO_COMILLAS",
        "Desconocido"    : "TEXTO_COMILLAS",
        "Comillas"       : "COMILLA_CERRADA",
        "NuevaLinea"     : "ERROR",          # Error si te olvidás de cerrar las comillas en la misma línea
    },
    "TEXTO_COMILLAS": {
        "Letra"          : "TEXTO_COMILLAS",
        "Numero"         : "TEXTO_COMILLAS",
        "Espacio"        : "TEXTO_COMILLAS",
        "Operador"       : "TEXTO_COMILLAS",
        "Barra"          : "TEXTO_COMILLAS",
        "Guion"          : "TEXTO_COMILLAS",
        "Selector"       : "TEXTO_COMILLAS",
        "Arroba"         : "TEXTO_COMILLAS",
        "Porcentaje"     : "TEXTO_COMILLAS",
        "Grados"         : "TEXTO_COMILLAS",
        "Menos"          : "TEXTO_COMILLAS",
        "Mas"            : "TEXTO_COMILLAS",
        "Separador_horario" : "TEXTO_COMILLAS",
        "Desconocido"    : "TEXTO_COMILLAS",
        "Comillas"       : "COMILLA_CERRADA",
        "NuevaLinea"     : "ERROR",
    },
    "COMILLA_CERRADA": {
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    }
}

# =============================================================================
# MOTOR PRINCIPAL DEL LEXER
# =============================================================================

def motor_lexer(string):
    """
    Esta función recorre el texto letra por letra. Va acumulando caracteres
    y cuando la tabla dice que la palabra terminó, analiza qué es y guarda el Token.
    """
    estado_anterior  = "INICIO"
    estado_actual    = "INICIO"
    acumulador       = ""
    tokens           = []
    errores          = []

    # Punteros para saber exactamente la fila y columna del archivo
    linea            = 1
    columna          = 1
    linea_token      = 1
    columna_token    = 1

    def agregar_error(mensaje, linea_err, col_err):
        errores.append(ErrorLexico(mensaje, linea_err, col_err))

    def aceptar_token():
        """
        ¡Acá está el truco gordo! Cuando una palabra se corta, pasa por acá.
        Revisamos el texto acumulado y controlamos que cumpla con las condiciones del PDF.
        """
        nonlocal acumulador, estado_actual, estado_anterior, linea_token, columna_token
        if not acumulador:
            return

        valor = acumulador
        estado_origen = estado_actual

        # --- COMENTARIOS ---
        if estado_origen == "COMENTARIO":
            tokens.append(Token("COMENTARIO", valor, linea_token, columna_token))

        # --- TEXTOS ENTRE COMILLAS ---
        elif estado_origen in ("TEXTO_COMILLAS", "COMILLA_CERRADA"):
            if valor.startswith('"') and valor.endswith('"'):
                contenido = valor[1:-1] # Le sacamos las comillas físicas para guardar solo el texto limpio
                tokens.append(Token("TEXTO", contenido, linea_token, columna_token))
            else:
                agregar_error("Falta cerrar las comillas del texto", linea_token, columna_token)
       
        # --- NÚMEROS SUELTOS ---
        elif estado_origen == "DIGITO":
            if valor[-1] == "%":
                estado_origen = "PORCENTAJE" # Por si el autómata se pasó de estado
            elif es_solo_digitos(valor):
                tokens.append(Token("NUMERO", valor, linea_token, columna_token))
            else:
                agregar_error(f"Número inválido: {valor}", linea_token, columna_token)
        
        # --- CONTROL DE PORCENTAJES (Regla: 0% a 100%) ---
        elif estado_origen == "PORCENTAJE":
            if valor.endswith('%') and es_solo_digitos(valor[:-1]):
                num = int(valor[:-1])
                if 0 <= num <= 100:
                    tokens.append(Token("PORCENTAJE", valor, linea_token, columna_token))
                else:
                    agregar_error(f"El porcentaje no puede pasarse de 100 ni ser menor a 0: {num}%", linea_token, columna_token)
            else:
                agregar_error(f"Formato de porcentaje roto: {valor}", linea_token, columna_token)

        # --- CONTROL DE TEMPERATURA (Regla: -10°c a 50°c) ---
        elif estado_origen == "TEMPERATURA":
            valor_lower = valor.lower()
            if valor_lower.endswith('c') and '°' in valor_lower:
                num_part = valor_lower.replace('°', '').replace('c', '')
                if es_solo_digitos(num_part) or (num_part.startswith('-') and es_solo_digitos(num_part[1:])):
                    num = int(num_part)
                    if -10 <= num <= 50:
                        tokens.append(Token("TEMPERATURA", valor, linea_token, columna_token))
                    else:
                        agregar_error(f"La temperatura está fuera de lo que miden los sensores (-10 a 50): {num}°C", linea_token, columna_token)
                else:
                    agregar_error(f"El valor de la temperatura no es un número: {valor}", linea_token, columna_token)
            else:
                agregar_error(f"La temperatura tiene que terminar en °C o °c: {valor}", linea_token, columna_token)

        # --- CONTROL DE TIEMPO (ej: 10h, 5m, 30s) ---
        elif estado_origen == "TIEMPO":
            if valor[-1].lower() in ('h','m','s') and es_solo_digitos(valor[:-1]):
                num = int(valor[:-1])
                if num > 0:
                    tokens.append(Token("TIEMPO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"El tiempo de espera tiene que ser mayor a cero: {num}", linea_token, columna_token)
            else:
                agregar_error(f"Formato de tiempo incorrecto (ejemplo válido: 10h, 5m): {valor}", linea_token, columna_token)

        # --- CONTROL DE INTENSIDAD DE LUZ (Regla: 0 a 1000 l/lu/lux) ---
        elif estado_origen == "LUZ":
            valor_lower = valor.lower()
            if valor_lower.endswith('l') and es_solo_digitos(valor[:-1]):
                num = int(valor[:-1])
                if 0 <= num <= 1000: tokens.append(Token("LUZ", valor, linea_token, columna_token))
                else: agregar_error(f"Los lux de luz tienen que estar entre 0 y 1000: {num}", linea_token, columna_token)
            elif valor_lower.endswith('lu') and es_solo_digitos(valor[:-2]):
                num = int(valor[:-2])
                if 0 <= num <= 1000: tokens.append(Token("LUZ", valor, linea_token, columna_token))
                else: agregar_error(f"Los lux de luz tienen que estar entre 0 y 1000: {num}", linea_token, columna_token)
            elif valor_lower.endswith('lux') and es_solo_digitos(valor[:-3]):
                num = int(valor[:-3])
                if 0 <= num <= 1000: tokens.append(Token("LUZ", valor, linea_token, columna_token))
                else: agregar_error(f"Los lux de luz tienen que estar entre 0 y 1000: {num}", linea_token, columna_token)
            else:
                agregar_error(f"La unidad de luz tiene que ser l, lu o lux: {valor}", linea_token, columna_token)

        # --- CONTROL DE FECHAS (Pasa a otra función abajo) ---
        elif estado_origen in ("FECHA_ANIO", "FECHA_MES"):
            error = _validar_fecha_con_dia_mes(valor.strip())
            if error:
                agregar_error(error, linea_token, columna_token)
            else:
                tokens.append(Token("FECHA", valor, linea_token, columna_token))

        # --- CONTROL DE HORAS (Pasa a otra función abajo) ---
        elif estado_origen == "HORA_MIN":
            error = _validar_hora(valor.strip())
            if error:
                agregar_error(error, linea_token, columna_token)
            else:
                tokens.append(Token("HORA", valor, linea_token, columna_token))

        # --- CONTROL DE CORREOS ELECTRÓNICOS ---
        elif estado_origen in ("EXTENSION2", "EXTENSION3", "EXTENSION4", "DOMINIO_MAIL"):
            if '@' in valor and '.' in valor.split('@')[-1]:
                tokens.append(Token("EMAIL", valor, linea_token, columna_token))
            else:
                agregar_error(f"El correo electrónico está mal escrito: {valor}", linea_token, columna_token)

        # --- PALABRAS RESERVADAS Y APARATOS SIMPLES ---
        elif estado_origen == "PALABRA":
            if valor.strip().lower() in BOOLEANOS_DISPOSITIVO:
                tokens.append(Token("BOOLEANO_DISPOSITIVO", valor, linea_token, columna_token))
            elif valor.strip().lower() in BOOLEANOS_SENSOR:
                tokens.append(Token("BOOLEANO_SENSOR", valor, linea_token, columna_token))
            elif valor.lower().strip() in PALABRAS_RESERVADAS:
                tokens.append(Token("RESERVADA", valor, linea_token, columna_token))
            else:
                if valor.strip() in DISPOSITIVOS_VALIDOS:
                    tokens.append(Token("DISPOSITIVO", valor, linea_token, columna_token))
                elif valor == "bool_sensor":
                    tokens.append(Token("SENSOR", valor, linea_token, columna_token))
                elif valor.startswith("sensor_") and valor[7:] in SENSORES_VALIDOS:
                    tokens.append(Token("SENSOR", valor, linea_token, columna_token))
                elif valor.strip().lower() in VALORES_DISCRETOS_VALIDOS:
                    tokens.append(Token("VALOR_DISCRETO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"No sé qué significa la palabra '{valor}'", linea_token, columna_token)

        # --- APARATOS O SENSORES CON NOMBRE LARGO (ej: sensor_luz) ---
        elif estado_origen == "IDENTIFICADOR":
            if valor == "bool_sensor":
                tokens.append(Token("SENSOR", valor, linea_token, columna_token))
            elif valor.startswith("sensor_") or valor.startswith(" sensor_"):
                base_sensor = valor.split('_')[1]
                if base_sensor.strip() in SENSORES_VALIDOS:
                    tokens.append(Token("SENSOR", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Ese sensor no existe '{valor}'. Los válidos son: {SENSORES_VALIDOS}", linea_token, columna_token)
            else:
                base = valor.split('_')[0]
                if base.strip() in DISPOSITIVOS_VALIDOS:
                    tokens.append(Token("DISPOSITIVO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"El aparato '{valor}' debe empezar con un tipo válido como: {DISPOSITIVOS_VALIDOS}", linea_token, columna_token)

        # --- CONTROL DE COMPATIBILIDAD (Aparato.Propiedad, ej: foco.estado) ---
        elif estado_origen == "ATRIBUTO":
            if '.' in valor:
                dispositivo_parte, atributo_parte = valor.rsplit('.', 1)
                base = dispositivo_parte.split('_')[0].strip()
                
                # Acá controlamos si la propiedad realmente le pertenece a ese aparato
                if base not in DISPOSITIVOS_VALIDOS:
                    agregar_error(f"El aparato no es válido en '{valor}'", linea_token, columna_token)
                elif atributo_parte not in ATRIBUTOS_POR_DISPOSITIVO.get(base, []):
                    # ¡Acá salta el error si querés cambiarle el volumen a un foco!
                    agregar_error(
                        f"La propiedad '{atributo_parte}' no sirve para un '{base}'. "
                        f"Las opciones para este aparato son: {ATRIBUTOS_POR_DISPOSITIVO.get(base, [])}",
                        linea_token, columna_token
                    )
                else:
                    # Si todo está bien, lo rompemos en 3 tokens separados para que el Parser
                    # no tenga que renegar lidiando con los puntos.
                    col_dispositivo = columna_token
                    col_punto = columna_token + len(dispositivo_parte)
                    col_atributo = col_punto + 1
                    tokens.append(Token("DISPOSITIVO", dispositivo_parte, linea_token, col_dispositivo))
                    tokens.append(Token("PUNTO", ".", linea_token, col_punto))
                    tokens.append(Token("ATRIBUTO", atributo_parte, linea_token, col_atributo))
            else:
                if valor.strip() in ATRIBUTOS_VALIDOS:
                    tokens.append(Token("ATRIBUTO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Propiedad inválida '{valor}'", linea_token, columna_token)

        # --- OPERADORES ---
        elif estado_origen == "OPERADOR":
            if valor.strip() in OPERADORES_VALIDOS:
                tokens.append(Token("OPERADOR", valor, linea_token, columna_token))
            else:
                agregar_error(f"Este operador no existe en el lenguaje: '{valor}'", linea_token, columna_token)

        else:
            tokens.append(Token(estado_origen, valor, linea_token, columna_token))

        # Limpiamos el texto acumulado y volvemos al inicio para la siguiente palabra
        acumulador = ""
        estado_actual = "INICIO"

    # -------------------------------------------------------------------------
    # Bucle principal que recorre la cadena de texto
    # -------------------------------------------------------------------------
    idx = 0
    while idx < len(string):
        caracter = string[idx]
        categoria = clasificar_caracter(caracter)

        # Si hay un salto de línea, sumamos 1 al contador de filas y reseteamos la columna
        if categoria == 'NuevaLinea':
            if acumulador:
                aceptar_token()
            linea += 1
            columna = 1
            linea_token = linea
            columna_token = columna
            idx += 1
            continue

        # Si son espacios en blanco sueltos entre comandos, los salteamos
        if categoria == 'Espacio' and estado_actual == 'INICIO' and not acumulador:
            columna += 1
            idx += 1
            continue

        # Moverse entre los estados del dibujo según el caracter que vino
        if categoria in tabla_transiciones.get(estado_actual, {}):
            estado_anterior = estado_actual
            nuevo_estado = tabla_transiciones[estado_actual][categoria]
            
            # SI EL ESTADO DICE ACEPTACIÓN: Significa "pará acá". Guardamos lo que 
            # teníamos antes y volvemos a evaluar ESTE mismo caracter desde INICIO.
            # Por eso no sumamos 1 al índice 'idx' (se queda congelado una vuelta).
            if nuevo_estado == "ACEPTACION":
                if acumulador:
                    aceptar_token()
                estado_actual = "INICIO"
                continue
            else:
                estado_actual = nuevo_estado
                if not acumulador:
                    linea_token = linea
                    columna_token = columna
                acumulador += caracter

                # Arreglo rápido para distinguir si el número termina en tiempo (10h) o luz (100l)
                if estado_actual == "TIEMPO_LUZ" and acumulador:
                    if acumulador[-1].lower() in ('h','m','s'):
                        estado_actual = "TIEMPO"
                        estado_anterior = "TIEMPO_LUZ"
                    elif acumulador[-1].lower() == 'l':
                        estado_actual = "LUZ"

                # Si el autómata cayó en un callejón sin salida (Estado ERROR)
                if estado_actual == "ERROR":
                    agregar_error(f"Caracter '{caracter}' colapsó el análisis en esta posición", linea, columna)
                    acumulador = ""
                    estado_actual = "INICIO"
        else:
            # Si el caracter que vino no tiene ninguna flecha de salida en el estado actual
            agregar_error(f"No se esperaba el caracter '{caracter}' acá", linea, columna)
            acumulador = ""
            estado_actual = "INICIO"

        columna += 1
        idx += 1

    # Si al terminar el archivo quedó algo en el acumulador, lo procesamos antes de cerrar
    if acumulador:
        aceptar_token()

    return tokens, errores


# =============================================================================
# CONTROLES INTERNOS DE CALENDARIO Y RELOJ
# =============================================================================

def _validar_fecha_con_dia_mes(acumulador):
    """
    Controla que la fecha en formato DD/MM/AAAA sea coherente con la realidad.
    Evita que pongan cosas como 32 de enero o 31 de noviembre.
    """
    partes = acumulador.split('/')
    if len(partes) != 3:
        return f"Formato de fecha roto '{acumulador}': tiene que ser DD/MM/AAAA"

    dia_str, mes_str, anio_str = partes
    if not es_solo_digitos(dia_str): return f"El día tiene letras '{dia_str}'"
    if not es_solo_digitos(mes_str): return f"El mes tiene letras '{mes_str}'"
    if not es_solo_digitos(anio_str): return f"El año tiene letras '{anio_str}'"

    dia  = int(dia_str)
    mes  = int(mes_str)
    anio = int(anio_str)

    if dia < 1 or dia > 31:   return f"El día tiene que estar entre 1 y 31: ({dia})"
    if mes < 1 or mes > 12:   return f"El mes tiene que estar entre 1 y 12: ({mes})"
    if anio < 1900 or anio > 2099: return f"El año está fuera del rango permitido: ({anio})"

    # Control estricto: revisamos cuántos días máximos tiene este mes en particular
    max_dia = DIAS_POR_MES[mes]
    if dia > max_dia:
        nota = ("no contamos bisiestos" if mes == 2
                else f"el mes de {NOMBRE_MES[mes]} no tiene {dia} días")
        return f"Fecha imposible {dia}/{mes}/{anio}: {nota}"
    return None


def _validar_hora(acumulador):
    """
    Controla que la hora en formato de 24 horas (HH:MM) tenga sentido real.
    """
    partes = acumulador.split(':')
    if len(partes) != 2:
        return f"Formato de hora roto '{acumulador}': se esperaba HH:MM"

    hora_str, min_str = partes
    if len(hora_str) != 2 or not es_solo_digitos(hora_str):
        return f"La hora tiene que ser de dos dígitos obligatorios: '{hora_str}'"
    if len(min_str) != 2 or not es_solo_digitos(min_str):
        return f"Los minutos tienen que ser de dos dígitos obligatorios: '{min_str}'"

    hora   = int(hora_str)
    minuto = int(min_str)

    if hora < 0 or hora > 23:     return f"La hora no puede pasarse de 23 ni ser menor a 0: ({hora})"
    if minuto < 0 or minuto > 59: return f"Los minutos no pueden pasarse de 59: ({minuto})"

    return None