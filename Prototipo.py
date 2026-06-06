# Palabras reservadas y listas de clasificación
PALABRAS_RESERVADAS = ["if", "then", "else", "end", "or", "and", "not",
                       "when", "every", "do", "then", "else"]
OPERADORES = ["+", "-", "*", "/", "<", ">"]

ATRIBUTOS = ["estado", "brillo", "color_val", "pocentaje_val", "modo", "temp_obj", "discreto_val",
             "temp_obj", "posicion", "hora_val", "fecha", "volumen",
             "mute", "mensaje", "email_notif", "activada"]

activado = True


# CLASIFICADOR DE CARACTERES
def clasificar_caracter(caracter):
    match caracter:
        case '%':  return 'Porcentaje'
        case '=':  return 'asignacion'
        case '°':  return 'Grados'
        case ':':  return 'Separador_horario'
        case '/':  return 'Separador_fecha'
        case '-':  return 'Menos'
        case '.':  return 'Selector'
        case '_':  return 'Guion'
        case ' ':  return 'Espacio'
        case _ if caracter in OPERADORES: return 'Operador'
        case _ if caracter.isdigit(): return 'Digito'
        case _ if caracter.isalpha(): return 'Letra'
        case _: return 'Desconocido'


# FUNCIONES AUXILIARES DE CLASIFICACIÓN
def clasificar_dispositivo(palabra):
    p = palabra.lower()
    if p.startswith("foco_"):      return "IDENTIFICADOR_FOCO"
    if p.startswith("aire_"):      return "IDENTIFICADOR_AIRE"
    if p.startswith("persiana_"):  return "IDENTIFICADOR_PERSIANA"
    if p.startswith("cerradura_"): return "IDENTIFICADOR_CERRADURA"
    if p.startswith("reloj_"):     return "IDENTIFICADOR_RELOJ"
    if p.startswith("altavoz_"):   return "IDENTIFICADOR_ALTAVOZ"
    if p.startswith("alarma_"):    return "IDENTIFICADOR_ALARMA"
    return "IDENTIFICADOR_DESCONOCIDO"

def clasificar_atributo(palabra):
    if palabra.lower() in ATRIBUTOS:
        return "ATRIBUTO"
    return "ATRIBUTO_DESCONOCIDO"





tabla_transiciones = {
    "INICIO": {
        "Letra":      "PALABRA",
        "Digito":     "NUMERO",
        "Operador":   "OPERADOR",
        "Espacio":    "INICIO",
        "asignacion": "ASIGNACION",
    },
    #  PALABRA: acumula letras, dígitos y guiones 
    "PALABRA": {
        "Letra":"PALABRA",
        "Digito":"PALABRA",
        "Guion":"PALABRA",      # para foco_sala, sensor_luz
        "Selector":"SELECTOR",     # cuando aparece '.' continua acumulando
        "Operador":"ACEPTACION",
        "Espacio":"ACEPTACION",
        "asignacion":"ACEPTACION",
    },
    # SELECTOR: acumula el atributo después del punto 
    "SELECTOR": {
        "Letra": "SELECTOR",
        "Digito":"SELECTOR",
        "Guion":"SELECTOR",    
        "Espacio":"ACEPTACION",
        "asignacion":"ACEPTACION",   # foco_sala.estado=ON sin espacio
    },
    #  NUMERO: puede derivar en HORA 
    "NUMERO": {
        "Digito": "NUMERO",
        "Separador_horario": "SEPARADOR_HORARIO",
        "Espacio": "ACEPTACION",
    },
    "SEPARADOR_HORARIO": {
        "Digito": "HORA_M1",
    },
    "HORA_M1": {
        "Digito": "ACEPTACION",
    },
    "OPERADOR": {
        "Letra":    "ACEPTACION",
        "Digito":   "NUMERO",
        "Operador": "OPERADOR",
        "Espacio":  "ACEPTACION",
    },
    #  ASIGNACION DELIMITADOR: solo el signo = 
    "ASIGNACION": {
        "Espacio": "ACEPTACION",
        "Letra":   "ACEPTACION",
        "Digito":  "ACEPTACION",
    },
}


# VALIDADOR DE HORA, para comprobar que sea entre 00:00 hasta 23:59

def validar_hora(acumulador):
    partes = acumulador.split(":")
    hh = int(partes[0])
    mm = int(partes[1])
    return 0 <= hh <= 23 and 0 <= mm <= 59


def motor_lexer(string):
    estado_anterior = "INICIO"
    estado_actual = "INICIO"
    acumulador = ""
    tokens = []

    for caracter in string:   
        categoria = clasificar_caracter(caracter)

        if categoria in tabla_transiciones[estado_actual]:
            estado_anterior = estado_actual
            estado_actual = tabla_transiciones[estado_actual][categoria]
            # print(estado_actual)
            if estado_actual == "ACEPTACION":

                #HORA: HH:MM
                if ":" in acumulador:
                    if validar_hora(acumulador):
                        tokens.append("HORA: " + acumulador)
                    else:
                        tokens.append("ERROR_RANGO_HORA: " + acumulador)

                #  SELECTOR: identificador.atributo 
                elif "." in acumulador:
                    partes = acumulador.split(".")
                    identificador = partes[0]
                    atributo = partes[1]
                    tipo_id  = clasificar_dispositivo(identificador)
                    tipo_atr = clasificar_atributo(atributo)
                    tokens.append(tipo_id  + ": " + identificador)
                    tokens.append("SELECTOR: .")
                    tokens.append(tipo_atr + ": " + atributo)

                #  ASIGNACION DELIMITADOR 
                elif estado_anterior == "ASIGNACION":
                    tokens.append("ASIGNACION: =")

                #  PALABRA o PALABRA_RESERVADA 
                else:
                    if (acumulador) in PALABRAS_RESERVADAS:
                        tokens.append("PALABRA_RESERVADA" + ": " + acumulador)
                    else:
                        tokens.append(estado_anterior + ": " + acumulador)
                    

                acumulador    = ""
                estado_actual = "INICIO"

            else:
                acumulador += caracter

        else:
            return "Error: Transición no definida para el caracter '{}' en el estado '{}'".format(caracter, estado_actual)
    if acumulador:
        tokens.append(estado_anterior + ": " + acumulador)
    acumulador = ""
    estado_actual = "INICIO"
    return tokens


# MAIN

while activado:
    input_string = input("Ingrese el string de entrada: ")
    print(motor_lexer(input_string))
    continuar = input("Para continuar presione enter, para salir presione 0: ")
    if continuar == "0":
        activado = False