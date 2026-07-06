# =============================================================================
# SMART HOME — Punto de Entrada Principal (Main) — Versión Explicada
# =============================================================================
# ¿Qué hace este archivo?
# Es el encargado de arrancar el programa. Maneja los dos modos de uso que nos
# pidió la cátedra en el enunciado (sección 6.1):
#   1) Modo interactivo: Escribís código en la consola directamente renglón por renglón.
#   2) Modo archivo: Le pasás un script listo (ej: script.smart) para que lo lea completo.
#
# También controla errores de entorno: que el archivo exista y que termine en ".smart".
# =============================================================================

import sys
import os

# Importamos los tres motores que creamos en los otros archivos
from lexer import motor_lexer
from parser import parsear
from html_generator_simple import guardar_html

EXTENSION_ESPERADA = ".smart"
# Nombre del HTML por defecto si usamos el modo interactivo en la consola
NOMBRE_HTML_MODO_INTERACTIVO = "main.html"  


# =============================================================================
# MODO 1: CONSOLA INTERACTIVA
# =============================================================================
def modo_interactivo():
    """
    Te abre una mini-consola adentro de la terminal para meter líneas a mano.
    Ideal para probar expresiones rápidas antes de armar un script gigante.
    """
    print("SMART HOME — Modo Interactivo")
    print("Escribí 'salir' para terminar el programa.\n")
    
    activado = True
    while activado:
        # Nos quedamos esperando que el usuario escriba algo
        entrada = input("Ingrese el string de entrada: ")
        
        # Condición de escape para no dejar colgado al usuario
        if entrada.strip().lower() == 'salir':
            activado = False
            continue

        # Pasada rápida del lexer para ver si por lo menos las palabras existen
        tokens, errores = motor_lexer(entrada)
        
        # Mandamos lo que juntamos a procesar y mostrar resultados
        _mostrar_resultado(tokens, errores, NOMBRE_HTML_MODO_INTERACTIVO)


# =============================================================================
# MODO 2: PROCESAR UN ARCHIVO (.smart)
# =============================================================================
def modo_archivo(ruta_archivo):
    """
    Se encarga de abrir un archivo de texto, leer todo su contenido de un tirón,
    pasárselo al compilador y generar el tablero HTML si no hubo fallas.
    """
    print(f"SMART HOME — Procesando archivo: '{ruta_archivo}'")

    # --- CONTROL DE SEGURIDAD 1: ¿El archivo existe de verdad? ---
    if not os.path.exists(ruta_archivo):
        print(f"✖ Error de ejecución: El archivo '{ruta_archivo}' no existe.")
        print("Sugerencia: Revisá que hayas escrito bien el nombre o que esté en la misma carpeta.")
        return

    # --- CONTROL DE SEGURIDAD 2: ¿Tiene la extensión correcta? ---
    if not ruta_archivo.endswith(EXTENSION_ESPERADA):
        print(f"Error de ejecución: Extensión inválida. El archivo debe terminar en '{EXTENSION_ESPERADA}'.")
        print(f"Sugerencia: Cambiale el nombre a tu archivo (ejemplo: script.smart).")
        return

    # Si pasó los controles, abrimos y leemos el archivo de forma segura con 'with'
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
    except Exception as e:
        print(f"Error crítico al intentar abrir o leer el archivo: {e}")
        return

    # Ejecutamos el lexer sobre todo el contenido del archivo
    tokens, errores = motor_lexer(contenido)

    # El HTML de salida va a llamarse igual que el script pero terminado en .html
    nombre_base = os.path.splitext(ruta_archivo)[0]
    ruta_html_salida = nombre_base + ".html"

    # Procesamos los datos y tiramos el reporte final
    _mostrar_resultado(tokens, errores, ruta_html_salida)


# =============================================================================
# REPORTE DE RESULTADOS Y DISPARADOR DEL PARSER / HTML
# =============================================================================
def _mostrar_resultado(tokens, errores, ruta_salida):
    """
    Muestra en limpio qué tokens se reconocieron, qué errores saltaron en el lexer,
    y si todo viene limpio, le da luz verde al Parser para analizar la sintaxis
    y exportar el Dashboard web.
    """
    # 1. Mostramos las palabras que el lexer logró rescatar
    if tokens:
        print(f"\n{len(tokens)} token(s) reconocido(s):")
        for t in tokens:
            print(f"    {t}")
            
    # 2. Mostramos si el lexer atrapó caracteres ilegales
    if errores:
        print(f"\n Se encontraron {len(errores)} error(es) léxico(s):")
        for e in errores:
            print(f"    {e}")
            
    if not tokens and not errores:
        print("  (El archivo o la línea ingresada está vacía)")
    print()

    # --- EL FILTRO DORADO ---
    # Si el lexer tiró aunque sea un solo error, NO avanzamos al parser.
    # No tiene sentido revisar la gramática de una oración si hay palabras rotas.
    if not errores:
        print("--- Iniciando Análisis Sintáctico (Parser) ---")
        
        # Le pasamos la posta al parser para que valide el orden y la semántica cruzada
        data = parsear(tokens)

        # Si el parser terminó bien (aceptó el string y nos devolvió la lista [sensores, dispositivos])
        if data:
            # Mandamos la data limpia al generador de HTML para plasmar el Dashboard
            if guardar_html(data, ruta_salida):
                print(f"Dashboard HTML generado con éxito en: {os.path.abspath(ruta_salida)}")
        else:
            # Si el parser imprimió "STRING RECHAZADO" (devolvió False/None), avisamos que no hay web
            print("El análisis sintáctico falló: No se generó el Dashboard HTML.")
    else:
        print("Análisis sintáctico cancelado debido a los errores léxicos previos.")


# =============================================================================
# INTERCEPTOR DE LA LÍNEA DE COMANDOS (PUNTO DE ARRANQUE)
# =============================================================================
def main():
    # Agarramos los argumentos extras que metieron en la consola al llamar a Python
    # sys.argv[0] es siempre 'main.py', así que lo salteamos con el recorte [1:]
    argumentos = sys.argv[1:]

    if len(argumentos) == 0:
        # Si no pasaron parámetros -> Modo Consola
        modo_interactivo()
    elif len(argumentos) == 1:
        # Si pasaron un parámetro -> Modo Archivo (asumimos que es la ruta del .smart)
        modo_archivo(argumentos[0])
    else:
        # Si metieron un montón de palabras raras en la terminal, los acomodamos
        print("Error de uso en la terminal.")
        print("Formas correctas de ejecutar el programa:")
        print("  python main.py                  -> Para usar la consola interactiva")
        print("  python main.py nombre_archivo.smart -> Para procesar un script listo")


# El clásico gancho de Python para asegurar que corra el main solo si se ejecuta este archivo directamente
if __name__ == "__main__":
    main()