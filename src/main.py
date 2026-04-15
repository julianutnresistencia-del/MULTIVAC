"""
Programa principal: recibe un archivo .smart por línea de comandos,
lo tokeniza, lo parsea y muestra los resultados.
"""

import sys
from lexer import Lexer
from parser import Parser

def main():
    # Verificamos que se haya pasado un argumento (el nombre del archivo)
    if len(sys.argv) != 2:
        print("Uso: python main.py archivo.smart")
        sys.exit(1)

    nombre_archivo = sys.argv[1]

    # Verificamos que tenga extensión .smart (opcional pero recomendado)
    if not nombre_archivo.endswith(".smart"):
        print("Advertencia: se recomienda usar archivos con extensión .smart")

    try:
        # Leemos todo el contenido del archivo
        with open(nombre_archivo, "r", encoding="utf-8") as f:
            texto = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{nombre_archivo}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        sys.exit(1)

    # ----------------------------------------------------------
    # FASE 1: Análisis léxico
    # ----------------------------------------------------------
    lexer = Lexer(texto)
    try:
        tokens = lexer.tokenizar()
        print("=== TOKENS GENERADOS ===")
        for tok in tokens:
            print(tok)
    except SyntaxError as e:
        print(f"Error léxico: {e}")
        sys.exit(1)

    # ----------------------------------------------------------
    # FASE 2: Análisis sintáctico
    # ----------------------------------------------------------
    parser = Parser(tokens)
    try:
        ast = parser.parse()
        print("\n=== AST (Árbol de Sintaxis Abstracta) ===")
        print(ast)
        print("\n¡Análisis exitoso! El programa es sintácticamente correcto.")
    except SyntaxError as e:
        print(f"Error sintáctico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()