"""
Módulo parser: Analizador sintáctico para el lenguaje Smart Home.
Recibe una lista de tokens (del lexer) y verifica que sigan la gramática.
Construye un AST (Árbol de Sintaxis Abstracta) como tuplas anidadas.
"""

# ------------------------------------------------------------------
# Clase Parser: se encarga de recorrer los tokens y reconocer estructuras
# ------------------------------------------------------------------
class Parser:
    def __init__(self, tokens):
        """
        Constructor: guarda la lista de tokens y posiciona el puntero al inicio.
        """
        self.tokens = tokens    # lista de objetos Token
        self.pos = 0            # índice del token actual

    # --------------------------------------------------------------
    # Métodos auxiliares para navegar por la lista de tokens
    # --------------------------------------------------------------
    def token_actual(self):
        """
        Retorna el token en la posición actual, o None si ya no hay más tokens.
        """
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consumir(self, tipo_esperado):
        """
        Verifica que el token actual sea del tipo esperado.
        Si es correcto, avanza al siguiente token y retorna el token consumido.
        Si no, lanza un error sintáctico con información de línea/columna.
        """
        token = self.token_actual()
        if token is None:
            # Fin de archivo inesperado
            raise SyntaxError(
                f"Error sintáctico: se esperaba '{tipo_esperado}' pero llegó fin de archivo"
            )
        if token.tipo == tipo_esperado:
            self.pos += 1       # avanzamos
            return token
        else:
            # Error: el token actual no es el que esperábamos
            raise SyntaxError(
                f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                f"se esperaba '{tipo_esperado}', se encontró '{token.tipo}' (valor: {token.valor})"
            )

    # --------------------------------------------------------------
    # Métodos de análisis para cada regla gramatical
    # --------------------------------------------------------------

    def parse_asignacion(self):
        """
        Regla gramatical:
        asignacion ::= IDENT DOT IDENT ASSIGN (ON|OFF|NUMBER)
        (por ahora solo acepta esos valores simples; luego se ampliará)
        Retorna una tupla que representa el nodo AST: ('assign', dispositivo, atributo, valor)
        """
        # 1) Leemos el identificador del dispositivo
        token_dispositivo = self.consumir("IDENT")
        dispositivo = token_dispositivo.valor

        # 2) Consumimos el punto
        self.consumir("DOT")

        # 3) Leemos el identificador del atributo
        token_atributo = self.consumir("IDENT")
        atributo = token_atributo.valor

        # 4) Consumimos el signo igual
        self.consumir("ASSIGN")

        # 5) El valor puede ser ON, OFF o un número (por ahora)
        token_valor = self.token_actual()
        if token_valor.tipo in ("ON", "OFF", "NUMBER"):
            valor = token_valor.valor
            self.pos += 1   # consumimos el valor
        else:
            raise SyntaxError(
                f"Error sintáctico: se esperaba ON, OFF o NUMBER, "
                f"pero se encontró {token_valor.tipo} en línea {token_valor.linea}"
            )

        # Retornamos una representación simple del AST (luego se cambiará por clases)
        return ("assign", dispositivo, atributo, valor)

    def parse(self):
        """
        Punto de entrada principal.
        Por ahora, asumimos que el programa es una sola asignación.
        Luego se extenderá para manejar múltiples instrucciones.
        """
        ast = self.parse_asignacion()

        # Después de la asignación, no debe haber más tokens (fin de archivo)
        if self.token_actual() is not None:
            token_extra = self.token_actual()
            raise SyntaxError(
                f"Error sintáctico: tokens extra después de la instrucción "
                f"en línea {token_extra.linea}, columna {token_extra.columna}"
            )
        return ast