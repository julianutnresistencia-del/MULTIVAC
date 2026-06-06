#Estas son las palabras reservadas que tiene la gramática: 
#Son palabras fijas que están presentes como símbolos terminales del lenguaje. 
PALABRAS_RESERVADAS =["or", "and", "not"]
OPERADORES = ["!", "=", "<", ">"]
ATRIBUTOS = ["estado", "brillo", "color_val", "pocentaje_val", "modo", "temp_obj", "discreto_val","temp_obj", "posicion", "hora_val", "fecha","volumen","mute", "mensaje", "email_notif", "activada"]
IDENTIFICADORES = ["foco", "aire", "persiana", "cerradura", "reloj", "altavoz","alarma"]

#Controlador del while para mantener el programa en ejecución.
activado = True

#Función para clasificar los caracteres recibidos. Utiliza una estructura match-case para determinar la categoría de un caracter ingresado como argumento de la función.
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
        case _ if caracter in OPERADORES: return 'Operador'
        case _ if caracter.isdigit(): return 'Numero'
        case _ if caracter.isalpha(): return 'Letra'
        case _: return 'Desconocido'

#Tabla de transición de estados:
#Esta tabla consiste en un diccionario de diccionarios que define un aceptor de estados finitos. 
#Este es simplemente un pequeño ejemplo que sirve como ilustración para implementar luego en toda la gramática completa. Aquí solo quiero dar una idea de cómo funciona.
#Cada clave del diccionario corresponde con un estado, y su valor es otro diccionario que define las transiciones posibles desde ese estado.
tabla_transiciones = {
    "INICIO":{
        "Letra": "PALABRA",
        "Menos": "DIGITO",
        "Numero": "DIGITO",
        "Operador": "OPERADOR",
        "comentario": "COMENTARIO",
        "Espacio": "INICIO"
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
        "Numero": "ERROR",
        "Operador": "ERROR",
        "Guion": "IDENTIFICADOR",
        "Espacio": "ACEPTACION"
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
        "Guion": "ERROR",
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
    }
}

def motor_lexer(string):
    estado_anterior = "INICIO"
    estado_actual = "INICIO"
    acumulador = ""
    tokens = []
    for caracter in string:
        categoria = clasificar_caracter(caracter)
        print(categoria)
        acumulador += caracter
        if categoria in tabla_transiciones[estado_actual]:
            estado_anterior = estado_actual
            estado_actual = tabla_transiciones[estado_actual][categoria]
            print(estado_actual + " | " + acumulador ) #-->Activar para ver los estados en cada iteración.
            match estado_actual:
                case "PORCENTAJE":
                    if acumulador[-1] == "%" and int(acumulador[:-1]) >= 0 and int(acumulador[:-1]) <= 100:
                        continue
                    else:
                        return "Error token Porcentaje: El símbolo aceptado al final del token es '%'. Además, el valor numérico debe estar entre 0 y 100."
                
                case "TEMPERATURA":
                    if acumulador[-1] == "c":
                        rango = int(acumulador[:-2])  # saca el "°c"
                        if -30 <= rango <= 50:
                            continue
                        else:
                            return "Error token Temperatura: Temperatura fuera de rango (-30 a 50)"
                    else:
                        return "Error token Temperatura: La letra aceptada al final del token es 'c' (°c)"
                
                case "TIEMPO/LUZ":
                        if acumulador[-1] in ["h", "m", "s"] and int(acumulador[:-1]) > 0:
                            estado_anterior = "TIEMPO"
                            estado_actual = "ACEPTACION"
                        elif acumulador[-1] =="l" and int(acumulador[:-1]) > 0 and int(acumulador[:-1]) <= 1000:
                            estado_actual = "LUZ"
                        else:
                            return "Error token Tiempo/Luz: La letra aceptada al final del token es 'h', 'm', 's' para tiempo o 'l' para luz. El valor de luz debe estar entre 0 y 1000."
                
                case "OPERADOR":
                        if acumulador[-1:].strip() in OPERADORES:
                            if len(acumulador.strip()) <= 2:
                                    if len(acumulador) == 2 and acumulador[1] != "=":
                                        return "Error token Operador: Operador no reconocido."
                                    else:
                                        continue
                            else:
                                return "Error token Operador: Un operador no puede tener más de dos símbolos."
                        else:
                            return "Error token Operador: El símbolo ingresado no es un operador válido."
                        
                case "PALABRA": #Esto es parte de la lógica de LÓGICO.
                    print("entra acá, acordate del lógico!")
                    continue

                case "IDENTIFICADOR":
                    print("este es el identificador: " + acumulador.split("_", 1)[0])
                    if acumulador.split("_", 1)[0] not in IDENTIFICADORES:
                        return "Error: '{}' no es un identificador válido. Los identificadores válidos deben comenzar con: {}".format(acumulador, ", ".join(IDENTIFICADORES))
               
                case "SELECTOR":
                    tokens.append("IDENTIFICADOR: " + acumulador[:-1])
                    tokens.append(estado_actual + ": " + acumulador[-1])
                
                case "ATRIBUTO":
                    if not any(p.startswith(acumulador.split(".", 1)[1]) for p in ATRIBUTOS):
                        return "Error: '{}' no es un atributo válido. Los atributos válidos son: {}".format(acumulador, ", ".join(ATRIBUTOS))


            if estado_actual == "LUZ":
                if acumulador[-1] == "l" or acumulador[-2:] == "lu":
                    continue
                elif acumulador [-3:] == "lux":
                    estado_actual = "ACEPTACION"
                else: 
                    return "Error token Luz: el valor de luz debe ser finalizar en lux"
            
            if estado_actual == "ACEPTACION":
                if estado_anterior == "ATRIBUTO":
                    tokens.append("ATRIBUTO: " + acumulador.split(".",1)[1])
                else:
                    tokens.append(estado_anterior + ": " + acumulador)
                acumulador = ""
                estado_actual = "INICIO"
        else:
            return "Transición no definida para el caracter '{}' en el estado '{}'".format(caracter, estado_actual)
    #Si al terminal el bucle, el acumulador aún tiene contenido, se verifica el estado actual y se procesa el token pendiente.    
    if acumulador:
        match estado_actual:
            case "ERROR":
                return "Error token: Token no reconocido '{}'".format(acumulador)
            case "TEMPERATURA":
                tokens.append(estado_actual + ": " + acumulador)
                acumulador = ""
                estado_actual = "INICIO"
            case "PORCENTAJE":
                tokens.append(estado_actual + ": " + acumulador)
                acumulador = ""
                estado_actual = "INICIO"
            case "OPERADOR":
                tokens.append(estado_actual + ": " + acumulador)
                acumulador = ""
                estado_actual = "INICIO"
            case "PALABRA": #Esto es parte de la lógica de LÓGICO.
                if acumulador in PALABRAS_RESERVADAS:
                    tokens.append(estado_actual + ": " + acumulador)
                    acumulador = ""
                    estado_actual = "INICIO"
                else:
                    return "Error token: '{}' no es una palabra reservada válida. Las palabras reservadas válidas son: {}".format(acumulador, ", ".join(PALABRAS_RESERVADAS))
            case "ATRIBUTO":
                tokens.append(estado_actual + ": " + acumulador.split(".",1)[1])
                acumulador = ""
                estado_actual = "INICIO"

    #Finalmente, se devuelve la lista de tokens encontrados o un mensaje indicando que no se encontraron tokens válidos.
    if tokens:
        return tokens
    else:
        return "No se encontraron tokens válidos"


while activado:
    #Input de entrada.
    input_string = input("Ingrese el string de entrada: ")

    #Ejemplo de uso de la función para clasificar el caracter ingresado.
    print(motor_lexer(input_string))

    input_string = input("para continuar presione enter, para salir presione 0: ")
    if input_string == "0":
        activado = False
