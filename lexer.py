# =============================================================================
# SMART HOME — Lexer unificado (versión corregida)
# =============================================================================
# Reconoce:
#   - Comentarios // línea
#   - Textos entre comillas dobles "texto"
#   - Porcentajes 0%..100%
#   - Temperaturas -30°c..50°c
#   - Tiempo 10h, 5m, 120s
#   - Luz 100l, 250lu, 500lux
#   - Fechas DD/MM/AAAA (validación día/mes)
#   - Correos electrónicos usuario@dominio.extension
#   - Palabras reservadas (if, then, else, end, or, and, not, when, every, do)
#   - Booleanos dispositivo (ON, off) y sensor (True, False, true, false)
#   - Dispositivos (foco, aire, persiana, cerradura, reloj, altavoz, alarma)
#   - Sensores (sensor_luz, sensor_temp, etc. y bool_sensor)
#   - Atributos (estado, brillo, ...)
#   - Operadores (+, -, *, /, =, <, >, !, ==, !=, <=, >=)
#   - Números enteros
# =============================================================================

# -----------------------------------------------------------------------------
# SÍMBOLOS TERMINALES (unificados)
# -----------------------------------------------------------------------------
PALABRAS_RESERVADAS = [
    "if", "then", "else", "end", "or", "and", "not",
    "when", "every", "do"
]
BOOLEANOS_DISPOSITIVO = ["on", "off"]
BOOLEANOS_SENSOR = ["true", "false"]
OPERADORES_BASICOS   = ["+", "-", "*", "/", "=", "<", ">", "!"]
OPERADORES_VALIDOS   = ["+", "-", "*", "/", "=", "<", ">", "!", "==", "!=", "<=", ">="]

ATRIBUTOS_VALIDOS = [
    "estado", "brillo", "color", "color_val", "porcentaje_val", "modo",
    "temp_obj", "temp_objetivo", "temp_act", "discreto_val", "posicion",
    "hora", "hora_val", "fecha", "volumen", "mute", "mensaje",
    "email", "email_notif", "activada"
]
DISPOSITIVOS_VALIDOS = [
    "foco", "aire", "persiana", "cerradura", "reloj", "altavoz", "alarma"
]
SENSORES_VALIDOS = [
    "luz", "temp", "humedad", "movimiento", "humo"
]

# Valores discretos (sin comillas) que puede tomar un atributo de tipo
# NOMBRE o DISCRETO, según la tabla de dispositivos del PDF (pág. 6).
# "blue" se incluye porque así aparece en el ejemplo oficial de la cátedra,
# aunque la tabla del PDF solo lista "blanco, rojo, azul".
VALORES_DISCRETOS_VALIDOS = [
    "blanco", "rojo", "azul", "blue",          # .color
    "frio", "calor", "vent",                   # .modo
]

DIAS_POR_MES = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
NOMBRE_MES   = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

# =============================================================================
# CLASE TOKEN
# =============================================================================
class Token:
    def __init__(self, tipo, valor, linea, columna):
        self.tipo    = tipo
        self.valor   = valor
        self.linea   = linea
        self.columna = columna

    def __repr__(self):
        return (f"Token({self.tipo}, {repr(self.valor)}, "
                f"linea={self.linea}, col={self.columna})")

# =============================================================================
# CLASE ERROR LÉXICO
# =============================================================================
class ErrorLexico:
    def __init__(self, mensaje, linea, columna):
        self.mensaje = mensaje
        self.linea   = linea
        self.columna = columna

    def __repr__(self):
        return (f"Error léxico en línea {self.linea}, "
                f"columna {self.columna}: {self.mensaje}")

# =============================================================================
# HELPERS (sin isdigit/alpha)
# =============================================================================
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
# TABLA DE TRANSICIONES (unificada y corregida)
# =============================================================================
tabla_transiciones = {
    "INICIO": {
        "Letra"          : "PALABRA",
        "Numero"         : "DIGITO",
        "Operador"       : "OPERADOR",
        "Espacio"        : "INICIO",
        "NuevaLinea"     : "INICIO",
        "Menos"          : "DIGITO",          # números negativos
        "Barra"          : "BARRA_INICIAL",   # posible inicio de comentario
        "Comillas"       : "COMILLA_ABIERTA", # inicio de texto entre comillas
    },
    "PALABRA": {
        "Letra"          : "PALABRA",
        "Guion"          : "IDENTIFICADOR",
        "Numero"         : "MAIL_POSIBLE",
        "Mas"            : "MAIL_POSIBLE",   # 'user+tag@...' -> nombre de usuario de email
        "Selector"       : "SELECTOR",       # 'reloj.hora' / 'user.name@...'
        "Operador"       : "ACEPTACION",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Arroba"         : "DOMINIO_MAIL",
        "Barra"          : "ERROR",
        "Comillas"       : "ERROR",
    },
    "DIGITO": {
        "Numero"         : "DIGITO",
        "Porcentaje"     : "PORCENTAJE",
        "Grados"         : "GRADOS",
        "Barra"          : "FECHA_MES",       # separador de fecha
        "Separador_horario" : "HORA_MIN",     # separador de hora HH:MM
        "Letra"          : "TIEMPO_LUZ",
        "Operador"       : "ACEPTACION",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Menos"          : "DIGITO",
    },
    "OPERADOR": {
        "Letra"          : "ACEPTACION",
        "Numero"         : "ACEPTACION",
        "Operador"       : "OPERADOR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Barra"          : "ERROR",
        "Comillas"       : "ERROR",
    },
    "GRADOS": {
        "Letra"          : "TEMPERATURA",
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
        "Numero"         : "IDENTIFICADOR",   # permite números después de letras
        "Guion"          : "IDENTIFICADOR",   # permite múltiples '_'
        "Arroba"         : "DOMINIO_MAIL",    # usuario de email con '_' (ej. user_name@...)
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "SELECTOR": {
        "Letra"          : "ATRIBUTO",
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
        "Arroba"         : "DOMINIO_MAIL",   # 'user.name@...' -> nombre de usuario de email
        "Numero"         : "ERROR",
        "Operador"       : "ERROR",
        "Selector"       : "ERROR",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
    },
    "FECHA_MES": {
        "Numero"         : "FECHA_MES",
        "Barra"          : "FECHA_ANIO",
    },
    "FECHA_ANIO": {
        "Numero"         : "FECHA_ANIO",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    # ---------- HORA HH:MM ----------
    "HORA_MIN": {
        "Numero"         : "HORA_MIN",
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    # ---------- EMAILS ----------
    "MAIL_POSIBLE": {
        "Letra"          : "MAIL_POSIBLE",
        "Numero"         : "MAIL_POSIBLE",
        "Selector"       : "MAIL_POSIBLE",
        "Guion"          : "MAIL_POSIBLE",
        "Mas"            : "MAIL_POSIBLE",
        "Arroba"         : "DOMINIO_MAIL",
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
        "Selector"       : "EXTENSION1",
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
        "Selector"       : "EXTENSION1",   # extensión multinivel, ej. .com.ar
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "EXTENSION3": {
        "Letra"          : "EXTENSION4",
        "Numero"         : "EXTENSION4",
        "Selector"       : "EXTENSION1",   # extensión multinivel, ej. .com.ar
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    "EXTENSION4": {
        "Letra"          : "ERROR",
        "Numero"         : "ERROR",
        "Selector"       : "EXTENSION1",   # extensión multinivel, ej. .com.ar
        "Espacio"        : "ACEPTACION",
        "NuevaLinea"     : "ACEPTACION",
        "Operador"       : "ACEPTACION",
    },
    # ---------- COMENTARIOS // ----------
    "BARRA_INICIAL": {
        "Barra"          : "COMENTARIO",
    },
    "COMENTARIO": {
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
        "NuevaLinea"     : "ACEPTACION",
    },
    # ---------- TEXTOS ENTRE COMILLAS ----------
    "COMILLA_ABIERTA": {
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
        "Desconocido"    : "TEXTO_COMILLAS",   # ej. coma, punto y coma, etc.
        "Comillas"       : "COMILLA_CERRADA",
        "NuevaLinea"     : "ERROR",
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
        "Desconocido"    : "TEXTO_COMILLAS",   # ej. coma, punto y coma, etc.
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
# MOTOR DEL LEXER (con reprocesamiento de caracteres)
# =============================================================================
def motor_lexer(string):
    estado_anterior  = "INICIO"
    estado_actual    = "INICIO"
    acumulador       = ""
    tokens           = []
    errores          = []

    linea            = 1
    columna          = 1
    linea_token      = 1
    columna_token    = 1

    def agregar_error(mensaje, linea_err, col_err):
        errores.append(ErrorLexico(mensaje, linea_err, col_err))

    def aceptar_token():
        nonlocal acumulador, estado_actual, estado_anterior, linea_token, columna_token
        if not acumulador:
            return

        valor = acumulador
        estado_origen = estado_actual

        # --- COMENTARIO ---
        if estado_origen == "COMENTARIO":
            tokens.append(Token("COMENTARIO", valor, linea_token, columna_token))

        # --- TEXTO ENTRE COMILLAS ---
        elif estado_origen == "TEXTO_COMILLAS" or estado_origen == "COMILLA_CERRADA":
            if valor.startswith('"') and valor.endswith('"'):
                contenido = valor[1:-1]
                tokens.append(Token("TEXTO", contenido, linea_token, columna_token))
            else:
                agregar_error("Formato inválido de texto entre comillas", linea_token, columna_token)
       
        # --- NÚMERO ---
        elif estado_origen == "DIGITO":
            if valor[-1] == "%":
                estado_origen = "PORCENTAJE"
            elif es_solo_digitos(valor):
                tokens.append(Token("NUMERO", valor, linea_token, columna_token))
            else:
                agregar_error(f"Número inválido: {valor}", linea_token, columna_token)
        
        # --- PORCENTAJE ---
        elif estado_origen == "PORCENTAJE":
            if valor.endswith('%') and es_solo_digitos(valor[:-1]):
                num = int(valor[:-1])
                if 0 <= num <= 100:
                    tokens.append(Token("PORCENTAJE", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Porcentaje fuera de rango (0-100): {num}", linea_token, columna_token)
            else:
                agregar_error(f"Formato de porcentaje inválido: {valor}", linea_token, columna_token)

        # --- TEMPERATURA ---

        elif estado_origen == "TEMPERATURA":
            valor_lower = valor.lower()
            if valor_lower.endswith('c') and '°' in valor_lower:
                num_part = valor_lower.replace('°', '').replace('c', '')
                if es_solo_digitos(num_part) or (num_part.startswith('-') and es_solo_digitos(num_part[1:])):
                    num = int(num_part)
                    if -30 <= num <= 50:
                        tokens.append(Token("TEMPERATURA", valor, linea_token, columna_token))
                    else:
                        agregar_error(f"Temperatura fuera de rango (-30 a 50): {num}", linea_token, columna_token)
                else:
                    agregar_error(f"Número inválido en temperatura: {valor}", linea_token, columna_token)
            else:
                agregar_error(f"Formato de temperatura incorrecto (debe terminar en 'c' o 'C'): {valor}", linea_token, columna_token)

        # --- TIEMPO ---
        elif estado_origen == "TIEMPO":
            if valor[-1].lower() in ('h','m','s') and es_solo_digitos(valor[:-1]):
                num = int(valor[:-1])
                if num > 0:
                    tokens.append(Token("TIEMPO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Tiempo debe ser positivo: {num}", linea_token, columna_token)
            else:
                agregar_error(f"Formato de tiempo inválido (ej: 10h, 5m, 30s): {valor}", linea_token, columna_token)

        # --- LUZ ---
        elif estado_origen == "LUZ":
            valor_lower = valor.lower()
            if valor_lower.endswith('l') and es_solo_digitos(valor[:-1]):
                num = int(valor[:-1])
                if 0 <= num <= 1000:
                    tokens.append(Token("LUZ", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Luz fuera de rango (0-1000): {num}", linea_token, columna_token)
            elif valor_lower.endswith('lu') and es_solo_digitos(valor[:-2]):
                num = int(valor[:-2])
                if 0 <= num <= 1000:
                    tokens.append(Token("LUZ", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Luz fuera de rango (0-1000): {num}", linea_token, columna_token)
            elif valor_lower.endswith('lux') and es_solo_digitos(valor[:-3]):
                num = int(valor[:-3])
                if 0 <= num <= 1000:
                    tokens.append(Token("LUZ", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Luz fuera de rango (0-1000): {num}", linea_token, columna_token)
            else:
                agregar_error(f"Formato de luz inválido (debe terminar en l, lu o lux): {valor}", linea_token, columna_token)

        # --- FECHA ---
        elif estado_origen in ("FECHA_ANIO", "FECHA_MES"):
            error = _validar_fecha_con_dia_mes(valor.strip())
            if error:
                agregar_error(error, linea_token, columna_token)
            else:
                tokens.append(Token("FECHA", valor, linea_token, columna_token))

        # --- HORA ---
        elif estado_origen == "HORA_MIN":
            error = _validar_hora(valor.strip())
            if error:
                agregar_error(error, linea_token, columna_token)
            else:
                tokens.append(Token("HORA", valor, linea_token, columna_token))

        # --- EMAIL ---
        elif estado_origen in ("EXTENSION2", "EXTENSION3", "EXTENSION4", "DOMINIO_MAIL"):
            if '@' in valor and '.' in valor.split('@')[-1]:
                tokens.append(Token("EMAIL", valor, linea_token, columna_token))
            else:
                agregar_error(f"Correo electrónico mal formado: {valor}", linea_token, columna_token)

        # --- PALABRA / RESERVADA / BOOLEANOS / IDENTIFICADOR SIMPLE ---
        elif estado_origen == "PALABRA":
            if valor.strip().lower() in BOOLEANOS_DISPOSITIVO:
                tokens.append(Token("BOOLEANO_DISPOSITIVO", valor, linea_token, columna_token))
            elif valor.strip().lower() in BOOLEANOS_SENSOR:
                tokens.append(Token("BOOLEANO_SENSOR", valor, linea_token, columna_token))
            elif valor.lower().strip() in PALABRAS_RESERVADAS:
                tokens.append(Token("RESERVADA", valor, linea_token, columna_token))
            else:
                # Puede ser dispositivo simple o sensor sin _
                if valor.strip() in DISPOSITIVOS_VALIDOS:
                    tokens.append(Token("DISPOSITIVO", valor, linea_token, columna_token))
                elif valor == "bool_sensor":
                    tokens.append(Token("SENSOR", valor, linea_token, columna_token))
                elif valor.startswith("sensor_") and valor[7:] in SENSORES_VALIDOS:
                    tokens.append(Token("SENSOR", valor, linea_token, columna_token))
                elif valor.strip().lower() in VALORES_DISCRETOS_VALIDOS:
                    tokens.append(Token("VALOR_DISCRETO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Identificador desconocido '{valor}'", linea_token, columna_token)

        # --- IDENTIFICADOR COMPUESTO (con guiones) ---
        elif estado_origen == "IDENTIFICADOR":
            if valor == "bool_sensor":
                tokens.append(Token("SENSOR", valor, linea_token, columna_token))
            elif valor.startswith("sensor_") or valor.startswith(" sensor_"):
                # Puede tener más guiones, ej. sensor_humo_id -> base "humo"
                base_sensor = valor.split('_')[1]
                if base_sensor.strip() in SENSORES_VALIDOS:
                    tokens.append(Token("SENSOR", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Sensor inválido '{valor}'. Tipos válidos: {SENSORES_VALIDOS}", linea_token, columna_token)
            else:
                base = valor.split('_')[0]
                if base.strip() in DISPOSITIVOS_VALIDOS:
                    tokens.append(Token("DISPOSITIVO", valor, linea_token, columna_token))
                else:
                    agregar_error(f"Dispositivo inválido '{valor}'. Debe comenzar con: {DISPOSITIVOS_VALIDOS}", linea_token, columna_token)

        # --- ATRIBUTO ---
        elif estado_origen == "ATRIBUTO":
            if '.' in valor:
                dispositivo_parte, atributo_parte = valor.rsplit('.', 1)
                base = dispositivo_parte.split('_')[0]
                if base.strip() not in DISPOSITIVOS_VALIDOS:
                    agregar_error(f"Dispositivo inválido en '{valor}'", linea_token, columna_token)
                elif atributo_parte not in ATRIBUTOS_VALIDOS:
                    agregar_error(f"Atributo inválido '{atributo_parte}'", linea_token, columna_token)
                else:
                    # Se emiten 3 tokens en vez de uno compuesto, para que el
                    # parser pueda distinguir el "Sujeto" (dispositivo) de su
                    # "Característica" (atributo) sin volver a parsear strings.
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
                    agregar_error(f"Atributo inválido '{valor}'", linea_token, columna_token)

        # --- OPERADOR ---
        elif estado_origen == "OPERADOR":
            if valor.strip() in OPERADORES_VALIDOS:
                tokens.append(Token("OPERADOR", valor, linea_token, columna_token))
            else:
                agregar_error(f"Operador no reconocido '{valor}'", linea_token, columna_token)

        # --- Fallback (no debería ocurrir) ---
        else:
            tokens.append(Token(estado_origen, valor, linea_token, columna_token))

        # Reiniciar acumulador y estado
        acumulador = ""
        estado_actual = "INICIO"

    # -------------------------------------------------------------------------
    # Bucle principal (con reprocesamiento)
    # -------------------------------------------------------------------------
    idx = 0
    while idx < len(string):
        caracter = string[idx]
        categoria = clasificar_caracter(caracter)

        # Saltos de línea: aceptar token pendiente, actualizar línea/columna
        if categoria == 'NuevaLinea':
            if acumulador:
                aceptar_token()
            linea += 1
            columna = 1
            linea_token = linea
            columna_token = columna
            idx += 1
            continue

        # Espacios/tabs cuando todavía no se empezó a acumular un token:
        # son puro separador, no deben formar parte del próximo token.
        # (Si ya hay acumulador, el espacio se sigue resolviendo más abajo
        # vía la tabla de transiciones, típicamente como "ACEPTACION".)
        if categoria == 'Espacio' and estado_actual == 'INICIO' and not acumulador:
            columna += 1
            idx += 1
            continue

        # Verificar transición
        if categoria in tabla_transiciones.get(estado_actual, {}):
            estado_anterior = estado_actual
            nuevo_estado = tabla_transiciones[estado_actual][categoria]
            #print(acumulador, estado_actual)
            # Si la transición lleva a ACEPTACION, aceptamos el token actual
            # (sin incluir este carácter) y luego reprocesamos el mismo carácter
            if nuevo_estado == "ACEPTACION":
                # Aceptar el token acumulado hasta ahora
                if acumulador:
                    aceptar_token()
                # Reiniciar posición para el mismo carácter
                # No avanzamos idx, y el carácter se procesará nuevamente desde INICIO
                # pero primero actualizamos estado_actual a INICIO para la próxima iteración
                estado_actual = "INICIO"
                # No acumulamos este carácter todavía, se procesará en la siguiente vuelta
                # Nota: no incrementamos idx, y no agregamos caracter a acumulador
                continue
            else:
                # Transición normal (no ACEPTACION)
                estado_actual = nuevo_estado
                # Guardar posición de inicio si es primer carácter del token
                if not acumulador:
                    linea_token = linea
                    columna_token = columna
                # Acumular el carácter
                acumulador += caracter

                # Lógica especial para TIEMPO_LUZ
                if estado_actual == "TIEMPO_LUZ" and acumulador:
                    if acumulador[-1].lower() in ('h','m','s'):
                        estado_actual = "TIEMPO"
                        estado_anterior = "TIEMPO_LUZ"
                    elif acumulador[-1].lower() == 'l':
                        estado_actual = "LUZ"

                # Si después de la transición el estado es ERROR, reportamos error
                if estado_actual == "ERROR":
                    agregar_error(f"Carácter '{caracter}' no esperado en contexto (estado {estado_anterior})", linea, columna)
                    acumulador = ""
                    estado_actual = "INICIO"
        else:
            # Transición no definida
            agregar_error(f"Transición no definida para '{caracter}' en estado '{estado_actual}'", linea, columna)
            acumulador = ""
            estado_actual = "INICIO"

        # Avanzar columna e índice (solo si no hubo reprocesamiento)
        columna += 1
        idx += 1

    # Fin del string: aceptar token pendiente
    if acumulador:
        aceptar_token()

    return tokens, errores


# =============================================================================
# VALIDACIÓN DE FECHA
# =============================================================================
def _validar_fecha_con_dia_mes(acumulador):
    partes = acumulador.split('/')
    if len(partes) != 3:
        return f"Formato inválido '{acumulador}': se esperaba DD/MM/AAAA"

    dia_str, mes_str, anio_str = partes
    if not es_solo_digitos(dia_str):
        return f"Día inválido '{dia_str}': debe ser un número"
    if not es_solo_digitos(mes_str):
        return f"Mes inválido '{mes_str}': debe ser un número"
    if not es_solo_digitos(anio_str):
        return f"Año inválido '{anio_str}': debe ser un número"

    dia = int(dia_str)
    mes = int(mes_str)
    anio = int(anio_str)

    if dia < 1 or dia > 31:
        return f"Día inválido '{dia}': debe estar entre 1 y 31"
    if mes < 1 or mes > 12:
        return f"Mes inválido '{mes}': debe estar entre 1 y 12"
    if anio < 1900 or anio > 2099:
        return f"Año inválido '{anio}': debe estar entre 1900 y 2099"

    max_dia = DIAS_POR_MES[mes]
    if dia > max_dia:
        nota = ("años bisiestos no considerados" if mes == 2
                else f"el día {dia} no existe en {NOMBRE_MES[mes]}")
        return (f"Fecha inválida {dia}/{mes}/{anio}: "
                f"{NOMBRE_MES[mes]} tiene como máximo {max_dia} días ({nota})")
    return None


# =============================================================================
# VALIDACIÓN DE HORA (formato HH:MM, 24 horas)
# =============================================================================
def _validar_hora(acumulador):
    partes = acumulador.split(':')
    if len(partes) != 2:
        return f"Formato inválido '{acumulador}': se esperaba HH:MM"

    hora_str, min_str = partes
    if len(hora_str) != 2 or not es_solo_digitos(hora_str):
        return f"Hora inválida '{hora_str}': debe ser de dos dígitos (00-23)"
    if len(min_str) != 2 or not es_solo_digitos(min_str):
        return f"Minutos inválidos '{min_str}': debe ser de dos dígitos (00-59)"

    hora = int(hora_str)
    minuto = int(min_str)

    if hora < 0 or hora > 23:
        return f"Hora inválida '{hora}': debe estar entre 00 y 23"
    if minuto < 0 or minuto > 59:
        return f"Minutos inválidos '{minuto}': debe estar entre 00 y 59"

    return None