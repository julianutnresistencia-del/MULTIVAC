# =============================================================================
# SMART HOME — Punto de entrada
# =============================================================================
# Dos modos de ejecución (ver PDF, sección 6.1):
#   1) Modo interactivo: analiza strings ingresados manualmente.
#   2) Modo archivo: analiza un archivo .smart pasado como argumento por
#      línea de comandos.
#
# Uso:
#   python3 main.py                  -> modo interactivo
#   python3 main.py script.smart     -> modo archivo
#
# Control de errores de ejecución (PDF, sección 6):
#   - archivo de entrada inexistente
#   - archivo con extensión incorrecta (debe ser ".smart")
# =============================================================================

import sys
import os

from lexer import motor_lexer

EXTENSION_ESPERADA = ".smart"


def modo_interactivo():
    """Analiza strings ingresados manualmente por el usuario."""
    print("SMART HOME Lexer — Modo interactivo")
    print("Escribí 'salir' para terminar.\n")
    activado = True
    while activado:
        entrada = input("Ingrese el string de entrada: ")
        if entrada.strip().lower() == 'salir':
            activado = False
            continue

        tokens, errores = motor_lexer(entrada)
        _mostrar_resultado(tokens, errores)

        continuar = input("Para continuar presione enter, para salir presione 0: ")
        if continuar == "0":
            activado = False


def modo_archivo(ruta):
    """Analiza el contenido de un archivo .smart pasado por línea de comandos.

    Errores de ejecución controlados (no léxicos):
      - el archivo no existe / no es un archivo regular
      - la extensión no es ".smart"
      - el archivo no se puede leer (permisos, encoding, etc.)
    """
    # --- Validación de extensión ---
    _, extension = os.path.splitext(ruta)
    if extension.lower() != EXTENSION_ESPERADA:
        print(f"Error de ejecución: extensión inválida '{extension or '(sin extensión)'}'.")
        print(f"  El archivo debe tener la extensión \"{EXTENSION_ESPERADA}\".")
        return False

    # --- Validación de existencia ---
    if not os.path.exists(ruta):
        print(f"Error de ejecución: el archivo '{ruta}' no existe.")
        return False

    if not os.path.isfile(ruta):
        print(f"Error de ejecución: '{ruta}' no es un archivo válido.")
        return False

    # --- Lectura del archivo ---
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error de ejecución: no se pudo leer '{ruta}'.")
        print(f"  Detalle: {e}")
        return False

    print(f"SMART HOME Lexer — Analizando archivo: {ruta}\n")

    # Se analiza el contenido completo (no línea por línea) para que el
    # lexer mantenga su propio conteo de línea/columna de forma consistente
    # con un análisis multilinea real.
    tokens, errores = motor_lexer(contenido)
    _mostrar_resultado(tokens, errores)

    if errores:
        print(f"\nResultado: el archivo tiene {len(errores)} error(es) léxico(s).")
    else:
        print(f"\nResultado: análisis léxico exitoso, sin errores ({len(tokens)} token(s)).")

    return not errores


def _mostrar_resultado(tokens, errores):
    """Imprime tokens y errores de una pasada del lexer."""
    if tokens:
        print(f"  {len(tokens)} token(s) reconocido(s):")
        for t in tokens:
            print(f"    {t}")
    if errores:
        print(f"  {len(errores)} error(es):")
        for e in errores:
            print(f"    {e}")
    if not tokens and not errores:
        print("  (sin tokens)")
    print()


def main():
    argumentos = sys.argv[1:]

    if len(argumentos) == 0:
        modo_interactivo()
    elif len(argumentos) == 1:
        modo_archivo(argumentos[0])
    else:
        print("Uso:")
        print("  python3 main.py                  -> modo interactivo")
        print("  python3 main.py archivo.smart    -> modo archivo")
        sys.exit(1)


if __name__ == '__main__':
    main()
