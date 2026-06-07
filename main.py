# Listas unificadas de símbolos terminales y gramática
PALABRAS_RESERVADAS = ["if", "then", "else", "end", "or", "and", "not"]
BOOLEANOS_DISPOSITIVO = ["ON", "off"]
BOOLEANOS_SENSOR = ["True", "False", "true", "false"] # Agregadas minúsculas por si acaso
OPERADORES = ["+", "-", "*", "/", "=", "<", ">", "!"]
ATRIBUTOS = ["estado", "brillo", "color_val", "pocentaje_val", "modo", "temp_obj", "discreto_val", "posicion", "hora_val", "fecha","volumen","mute", "mensaje", "email_notif", "activada"]
IDENTIFICADORES = ["foco", "aire", "persiana", "cerradura", "reloj", "altavoz", "alarma", "sensor"] # 'sensor' agregado

activado = True

def clasificar_caracter(caracter):
    match caracter:
        case '%': return 'Porcentaje'
        case '°': return 'Grados'
        case ":": return 'Separador_horario'
        case "/": return 'Separador_fecha'
        case "-": return 'Menos'
        case ".": return 'Selector'
        case "_": return 'Guion'
        case " ": return 'Espacio'
        case "@": return 'Arroba'
        case _ if caracter in OPERADORES: return 'Operador'
        case _ if caracter.isdigit(): return 'Numero'
        case _ if caracter.isalpha(): return 'Letra'
        case _: return 'Desconocido'

# Tabla combinada de transiciones
tabla_transiciones = {
    "INICIO":{
        "Letra": "PALABRA",
        "Menos": "DIGITO",
        "Numero": "DIGITO",
        "Operador": "OPERADOR",
        "Espacio": "INICIO" # Ignora los espacios basura de arranque
    },
    "ERROR":{
        "Letra": "ERROR",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "INICIO"
    },
    "DIGITO":{
        "Letra": "TIEMPO/LUZ",
        "Numero": "DIGITO",
        "Porcentaje": "PORCENTAJE",
        "Grados": "GRADOS",
        "Espacio": "ACEPTACION"
    },
    "OPERADOR":{
        "Letra": "ERROR",
        "Numero": "ERROR",
        "Operador": "OPERADOR",
        "Espacio": "ACEPTACION"
    },
    "GRADOS":{
        "Letra": "TEMPERATURA",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "ERROR"
    },
    "TEMPERATURA":{
        "Letra": "ERROR",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "ACEPTACION"
    },
    "TIEMPO/LUZ":{
        "Letra": "TIEMPO/LUZ",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "ACEPTACION"
    },
    "TIEMPO":{
        "Letra": "ERROR",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "ACEPTACION"
    },
    "LUZ":{
        "Letra": "LUZ",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "ACEPTACION"
    },
    "PALABRA":{
        "Letra": "PALABRA",
        "Numero": "MAIL_POSIBLE",  # Conexión hacia la validación de mail
        "Operador": "ERROR",
        "Guion": "IDENTIFICADOR",  # Conexión hacia la validación del sistema (ej. sensor_)
        "Espacio": "ACEPTACION",
        "Arroba": "DOMINIO_MAIL"   # Conexión hacia mail si es todo texto y un arroba
    }, 
    "PORCENTAJE":{
        "Letra": "ERROR",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Espacio": "ACEPTACION"
    },
    "IDENTIFICADOR":{
        "Letra": "IDENTIFICADOR",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Guion": "IDENTIFICADOR", # Ajustado para soportar múltiples '_' (ej. sensor_humo_id)
        "Selector": "SELECTOR",
        "Espacio": "ERROR"
    },
    "SELECTOR":{
        "Letra": "ATRIBUTO",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Guion": "ERROR",
        "Selector": "ERROR",
        "Espacio": "ERROR"
    },
    "ATRIBUTO":{
        "Letra": "ATRIBUTO",
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Guion": "ATRIBUTO",
        "Selector": "ERROR",
        "Espacio": "ACEPTACION"
    },
    # --------- ESTADOS NUEVOS (EMAILS) ---------
    "MAIL_POSIBLE":{
        "Letra": "MAIL_POSIBLE",
        "Numero": "MAIL_POSIBLE",
        "Espacio": "ERROR",
        "Arroba" : "DOMINIO_MAIL",
    },
    "DOMINIO_MAIL":{
        "Letra": "DOMINIO_MAIL",
        "Numero": "DOMINIO_MAIL",
        "Selector": "EXTENSION1",
        "Espacio": "ERROR"
    },
    "EXTENSION1":{
        "Letra": "EXTENSION2",
        "Numero": "EXTENSION2",
        "Espacio": "ERROR",    
    },
    "EXTENSION2":{
        "Letra": "EXTENSION3",
        "Numero": "EXTENSION3",
        "Espacio": "ACEPTACION",
     },
     "EXTENSION3":{
        "Letra": "EXTENSION4",
        "Numero": "EXTENSION4",
        "Espacio": "ACEPTACION",
     },
     "EXTENSION4":{
        "Letra": "ERROR",
        "Numero": "ERROR",
        "Espacio": "ACEPTACION",
     }
}

def motor_lexer(string):
    estado_anterior = "INICIO"
    estado_actual = "INICIO"
    acumulador = ""
    tokens = []
    
    for caracter in string:
        categoria = clasificar_caracter(caracter)
        acumulador += caracter
        
        if categoria in tabla_transiciones[estado_actual]:
            estado_anterior = estado_actual
            estado_actual = tabla_transiciones[estado_actual][categoria]
            
            # --- Validaciones dinámicas (En tiempo de tránsito) ---
            match estado_actual:
                case "PORCENTAJE":
                    if not (acumulador[-1] == "%" and int(acumulador[:-1]) >= 0 and int(acumulador[:-1]) <= 100):
                        return "Error token Porcentaje: El símbolo debe ser '%' y el valor numérico entre 0 y 100."
                case "TEMPERATURA":
                    if acumulador[-1] == "c":
                        rango = int(acumulador[:-2])
                        if not (-30 <= rango <= 50): return "Error Temperatura: Fuera de rango (-30 a 50)"
                    else:
                        return "Error Temperatura: Falta la letra 'c' (°c)"
                case "TIEMPO/LUZ":
                    if acumulador[-1] in ["h", "m", "s"] and int(acumulador[:-1]) > 0:
                        estado_anterior = "TIEMPO"
                        estado_actual = "ACEPTACION"
                    elif acumulador[-1] =="l" and int(acumulador[:-1]) > 0 and int(acumulador[:-1]) <= 1000:
                        estado_actual = "LUZ"
                    else:
                        return "Error Tiempo/Luz: Letra no válida o rango excedido."
                case "OPERADOR":
                    if acumulador[-1:].strip() in OPERADORES:
                        if len(acumulador.strip()) > 2 or (len(acumulador) == 2 and acumulador[1] != "="):
                            return "Error Operador: Operador no reconocido o límite excedido."
                    else:
                        return "Error Operador: Símbolo inválido."
                case "IDENTIFICADOR":
                    base = acumulador.split("_", 1)[0]
                    if base not in IDENTIFICADORES:
                        return "Error: '{}' no es un identificador válido.".format(base)
                case "SELECTOR":
                    tokens.append("IDENTIFICADOR: " + acumulador[:-1])
                    tokens.append(estado_actual + ": " + acumulador[-1])
                case "ATRIBUTO":
                    if not any(p.startswith(acumulador.split(".", 1)[1]) for p in ATRIBUTOS):
                        return "Error: '{}' no es un atributo válido.".format(acumulador)
            
            if estado_actual == "LUZ":
                if not (acumulador[-1] == "l" or acumulador[-2:] == "lu" or acumulador [-3:] == "lux"):
                    return "Error Luz: Debe finalizar en lux"
                if acumulador [-3:] == "lux":
                    estado_actual = "ACEPTACION"
            
            # --- Validaciones de Aceptación y Clasificación Final ---
            if estado_actual == "ACEPTACION":
                # Como transita con un espacio, evaluamos todo menos el espacio final
                valor = acumulador[:-1]
                
                if estado_anterior == "PALABRA":
                    if valor in BOOLEANOS_DISPOSITIVO:
                        tokens.append("BOOLEANO DISPOSITIVO: " + valor)
                    elif valor in BOOLEANOS_SENSOR:
                        tokens.append("BOOLEANO SENSOR: " + valor)
                    elif valor in PALABRAS_RESERVADAS:
                        tokens.append("PALABRA RESERVADA: " + valor)
                    else:
                        tokens.append("PALABRA: " + valor)
                
                elif estado_anterior in ["EXTENSION2", "EXTENSION3", "EXTENSION4"]:
                    tokens.append("EMAIL: " + valor)
                
                elif estado_anterior == "ATRIBUTO":
                    tokens.append("ATRIBUTO: " + valor.split(".",1)[1])
                
                else:
                    tokens.append(estado_anterior + ": " + valor)
                
                # Reseteamos para el próximo token
                acumulador = ""
                estado_actual = "INICIO"
        else:
            return "Transición no definida para el caracter '{}' en el estado '{}' (acumulado: {})".format(caracter, estado_actual, acumulador)
            
    # Manejo del token que queda pendiente si el string no termina en espacio
    if acumulador:
        valor = acumulador.strip()
        match estado_actual:
            case "ERROR" | "MAIL_POSIBLE" | "DOMINIO_MAIL" | "EXTENSION1":
                return "Error léxico: Token inválido o incompleto '{}' (Fase: {})".format(valor, estado_actual)
            case "TEMPERATURA" | "PORCENTAJE" | "OPERADOR":
                tokens.append(estado_actual + ": " + valor)
            case "PALABRA":
                if valor in BOOLEANOS_DISPOSITIVO:
                    tokens.append("BOOLEANO DISPOSITIVO: " + valor)
                elif valor in BOOLEANOS_SENSOR:
                    tokens.append("BOOLEANO SENSOR: " + valor)
                elif valor in PALABRAS_RESERVADAS:
                    tokens.append("PALABRA RESERVADA: " + valor)
                else:
                    tokens.append("PALABRA: " + valor)
            case "EXTENSION2" | "EXTENSION3" | "EXTENSION4":
                tokens.append("EMAIL: " + valor)
            case "ATRIBUTO":
                tokens.append(estado_actual + ": " + valor.split(".",1)[1])
            case _:
                tokens.append(estado_actual + ": " + valor)

    if tokens:
        return tokens
    else:
        return "No se encontraron tokens válidos"

while activado:
    input_string = input("\nIngrese el string de entrada: ")
    print(motor_lexer(input_string))
    
    opcion = input("Para continuar presione ENTER, para salir presione 0: ")
    if opcion == "0":
        activado = False
