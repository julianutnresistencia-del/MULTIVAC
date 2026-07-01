# =============================================================================
# SMART HOME — Suite de tests del lexer
# =============================================================================
# Cómo correr:
#   cd al directorio donde está este archivo (junto a lexer.py)
#   pip install pytest --break-system-packages   (si hace falta)
#   pytest test_lexer.py -v
#
# Organización:
#   1. Tests "unitarios" -> una línea, un tipo de token, casos límite de rango.
#   2. Tests de "frases" -> combinaciones reales como aparecen en un script.
#   3. Test de regresión -> el ejemplo COMPLETO del PDF de la cátedra,
#      línea por línea, no debe arrojar NINGÚN error léxico.
#
# IMPORTANTE: estos tests reflejan el comportamiento DESEADO según el
# enunciado, no el comportamiento actual del lexer. Al día de creación de
# este archivo, varios tests fallan: eso es información, no un bug del test.
# A medida que corrijan el lexer, más tests deberían pasar a verde.
# =============================================================================

import os
import pytest
from lexer import motor_lexer


def tipos(tokens):
    """Lista de tipos de token, para asserts cortos."""
    return [t.tipo for t in tokens]


def valores(tokens):
    """Lista de valores de token SIN espacios accidentales, para detectar
    el bug de 'espacio pegado adelante' de forma explícita."""
    return [t.valor for t in tokens]


def sin_errores(entrada):
    """Helper: corre el lexer y arma un mensaje de fallo legible."""
    tokens, errores = motor_lexer(entrada)
    msg = "\n".join(str(e) for e in errores)
    assert not errores, f"Errores léxicos inesperados en {entrada!r}:\n{msg}"
    return tokens


# -----------------------------------------------------------------------------
# 1. PALABRAS RESERVADAS — case-insensitive
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("palabra", [
    "when", "WHEN", "When",
    "if", "IF", "then", "THEN", "else", "ELSE",
    "do", "DO", "end", "END", "every", "EVERY",
    "and", "AND", "or", "OR", "not", "NOT",
])
def test_reservadas_case_insensitive(palabra):
    tokens = sin_errores(palabra)
    assert len(tokens) == 1
    assert tokens[0].tipo == "RESERVADA"


def test_reservada_no_pega_espacio():
    """El valor del token no debe arrastrar espacios en blanco."""
    tokens = sin_errores("WHEN")
    assert tokens[0].valor == "WHEN"  # sin espacios adelante/atrás


def test_palabras_consecutivas_no_arrastran_espacio():
    tokens = sin_errores("WHEN DO")
    assert valores(tokens) == ["WHEN", "DO"], (
        "Cada token debe tener su valor limpio, sin el espacio "
        "separador incluido en el string"
    )


# -----------------------------------------------------------------------------
# 2. BOOLEANOS
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("valor", ["TRUE", "FALSE", "true", "false", "True", "False"])
def test_booleano_sensor_case_insensitive(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "BOOLEANO_SENSOR"


@pytest.mark.parametrize("valor", ["ON", "OFF", "on", "off", "On", "Off"])
def test_booleano_dispositivo_case_insensitive(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "BOOLEANO_DISPOSITIVO"


# -----------------------------------------------------------------------------
# 3. NUMÉRICOS CON UNIDAD
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("valor", ["0%", "50%", "100%"])
def test_porcentaje_rango_valido(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "PORCENTAJE"


@pytest.mark.parametrize("valor", ["101%", "150%"])
def test_porcentaje_fuera_de_rango(valor):
    _, errores = motor_lexer(valor)
    assert errores, f"{valor!r} debería generar error de rango"


@pytest.mark.parametrize("valor", ["25°C", "-5°C", "0°C", "25°c", "-5°c"])
def test_temperatura_case_insensitive(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "TEMPERATURA"


@pytest.mark.parametrize("valor", ["10s", "5m", "1h", "10S", "5M", "1H"])
def test_tiempo_valido_case_insensitive(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "TIEMPO"


@pytest.mark.parametrize("valor", ["600lux", "0lux", "1000lux"])
def test_iluminancia_valida(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "LUZ"


def test_hora_formato_valido():
    tokens = sin_errores("22:00")
    assert tokens[0].tipo == "HORA"


def test_hora_formato_valido_2():
    tokens = sin_errores("06:00")
    assert tokens[0].tipo == "HORA"


@pytest.mark.parametrize("valor", ["24:00", "23:60", "25:99"])
def test_hora_fuera_de_rango_da_error(valor):
    _, errores = motor_lexer(valor)
    assert errores, f"{valor!r} debería ser una hora inválida"


def test_fecha_formato_valido():
    tokens = sin_errores("21/04/2026")
    assert tokens[0].tipo == "FECHA"


# -----------------------------------------------------------------------------
# 4. EMAIL — siguiendo la sección 4 del PDF (letras, dígitos, _, ., +, -)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("valor", [
    "felipe@smart-home.com.ar",
    "bomberos@smart-home.com.ar",
    "felipe@smarthome.com",
    "user.name@dominio.com",
    "user_name@dominio.com",
    "user+tag@dominio.io",
])
def test_email_valido(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "EMAIL"


@pytest.mark.parametrize("valor", [
    "sin-arroba.com",
    "@sindominio.com",
])
def test_email_invalido_da_error(valor):
    _, errores = motor_lexer(valor)
    assert errores, f"{valor!r} debería ser inválido"


# -----------------------------------------------------------------------------
# 5. TEXTO ENTRE COMILLAS
# -----------------------------------------------------------------------------
def test_texto_simple():
    tokens = sin_errores('"hola mundo"')
    assert tokens[0].tipo == "TEXTO"
    assert tokens[0].valor == "hola mundo"


def test_texto_con_coma():
    tokens = sin_errores('"Son las 22hs, hora de dormir"')
    assert tokens[0].tipo == "TEXTO"
    assert tokens[0].valor == "Son las 22hs, hora de dormir"


def test_texto_con_punto_final():
    tokens = sin_errores('"PELIGRO. HUMO DETECTADO"')
    assert tokens[0].tipo == "TEXTO"


# -----------------------------------------------------------------------------
# 6. SENSORES Y DISPOSITIVOS — identificadores
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("valor", [
    "sensor_temp", "sensor_humedad", "sensor_luz",
    "sensor_movimiento", "sensor_humo",
])
def test_sensores_validos(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "SENSOR"


def test_sensor_con_sufijo_libre():
    """El PDF no exige que el sufijo del sensor sea exactamente uno de la
    lista fija; en el ejemplo aparece 'sensor_temp_int'. Validar con el
    grupo si el lexer debe ser flexible acá."""
    tokens, errores = motor_lexer("sensor_temp_int")
    # Este test documenta una decisión de diseño pendiente -> ver informe.
    assert tokens or errores  # solo que no explote


@pytest.mark.parametrize("valor", [
    "foco_entrada", "foco_patio", "aire_acondicionado",
    "persiana_sala", "persiana_comedor", "cerradura_principal",
    "altavoz_comedor",
])
def test_dispositivos_validos(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "DISPOSITIVO"


@pytest.mark.parametrize("valor", ["reloj", "alarma"])
def test_dispositivos_sin_sufijo(valor):
    """reloj y alarma se usan SIN guion bajo + sufijo en el ejemplo
    oficial (reloj.hora, alarma.estado)."""
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "DISPOSITIVO"


# -----------------------------------------------------------------------------
# 7. NOTACIÓN DE PUNTO dispositivo.atributo
# -----------------------------------------------------------------------------
# Decisión de diseño del grupo: el lexer emite TRES tokens separados
# (DISPOSITIVO, PUNTO, ATRIBUTO) en vez de un solo token compuesto. Esto
# permite que el parser distinga el "Sujeto" (dispositivo) de su
# "Característica" (atributo) sin tener que volver a parsear strings.
@pytest.mark.parametrize("entrada,disp,attr", [
    ("foco_entrada.estado", "foco_entrada", "estado"),
    ("aire_acondicionado.temp_objetivo", "aire_acondicionado", "temp_objetivo"),
    ("reloj.hora", "reloj", "hora"),
    ("alarma.estado", "alarma", "estado"),
    ("altavoz_comedor.mensaje", "altavoz_comedor", "mensaje"),
    ("altavoz_comedor.email", "altavoz_comedor", "email"),
])
def test_notacion_punto_emite_tres_tokens(entrada, disp, attr):
    tokens = sin_errores(entrada)
    assert len(tokens) == 3, f"Se esperaban 3 tokens, se obtuvieron {len(tokens)}: {tokens}"
    assert tipos(tokens) == ["DISPOSITIVO", "PUNTO", "ATRIBUTO"]
    assert tokens[0].valor == disp
    assert tokens[1].valor == "."
    assert tokens[2].valor == attr


# -----------------------------------------------------------------------------
# 7b. VALORES DISCRETOS sin comillas (.color, .modo)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("valor", [
    "blanco", "rojo", "azul", "blue",
    "FRIO", "CALOR", "VENT", "frio", "calor", "vent",
])
def test_valor_discreto_reconocido(valor):
    tokens = sin_errores(valor)
    assert tokens[0].tipo == "VALOR_DISCRETO"


# -----------------------------------------------------------------------------
# 8. COMENTARIOS
# -----------------------------------------------------------------------------
def test_comentario_simple():
    tokens = sin_errores("// esto es un comentario")
    assert tokens[0].tipo == "COMENTARIO"


def test_comentario_con_caracteres_especiales():
    tokens = sin_errores('// 50% de luz a 22°C y "comillas" y user@mail.com')
    assert tokens[0].tipo == "COMENTARIO"


# -----------------------------------------------------------------------------
# 9. OPERADORES
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("op", ["==", "!=", ">", "<", ">=", "<=", "="])
def test_operadores(op):
    tokens = sin_errores(op)
    assert tokens[0].tipo == "OPERADOR"


def test_operador_sin_espacios():
    tokens = sin_errores("sensor_luz<250lux")
    assert valores(tokens) == ["sensor_luz", "<", "250lux"]


def test_operador_con_espacios_no_arrastra_espacio():
    tokens = sin_errores("sensor_luz < 250lux")
    assert valores(tokens) == ["sensor_luz", "<", "250lux"], (
        "Ninguno de los tokens debería incluir el espacio separador"
    )


# -----------------------------------------------------------------------------
# 10. FRASES — líneas reales tal como aparecen en el ejemplo del PDF
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("linea", [
    "WHEN sensor_luz < 250lux DO",
    "foco_entrada.estado = ON",
    "foco_entrada.brillo = 80%",
    "foco_patio.color = blue",
    "WHEN sensor_movimiento == TRUE DO",
    "IF sensor_temp_int > 26°C THEN",
    "aire_acondicionado.modo = FRIO",
    "aire_acondicionado.temp_objetivo = 22°C",
    "EVERY 30m DO",
    "IF reloj.hora > 22:00 AND alarma.estado == OFF THEN",
    "persiana_sala.posicion = 0%",
    'altavoz_comedor.mensaje = "Son las 22hs, hora de dormir"',
    "altavoz_comedor.email = felipe@smart-home.com.ar",
    "IF sensor_humo == TRUE AND aire_acondicionado.estado == OFF THEN",
    "persiana_comedor.posicion =100%",
    'altavoz_comedor.mensaje = "PELIGRO. HUMO DETECTADO"',
    "altavoz_comedor.email = bomberos@smart-home.com.ar",
])
def test_lineas_del_ejemplo_oficial_sin_errores(linea):
    sin_errores(linea)


# -----------------------------------------------------------------------------
# 11. REGRESIÓN — el archivo .smart completo del PDF, de punta a punta
# -----------------------------------------------------------------------------
def test_archivo_ejemplo_completo_sin_errores():
    ruta = os.path.join(os.path.dirname(__file__), "ejemplos", "basico.smart")
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    tokens, errores = motor_lexer(contenido)
    if errores:
        detalle = "\n".join(str(e) for e in errores)
        pytest.fail(f"El ejemplo oficial del PDF generó {len(errores)} error(es):\n{detalle}")
