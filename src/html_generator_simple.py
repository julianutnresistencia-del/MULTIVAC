# =============================================================================
# Generador de HTML del dashboard SMART HOME — versión "a la letra del enunciado"
# =============================================================================
# Esta versión NO tiene nada de diseño extra (fuentes, sombras, colores lindos,
# hover, etc.). Solo hace exactamente lo que pide la consigna de "5. Traducción
# a HTML":
#
#   - nombre de archivo: igual al fuente pero con extensión .htm/.html (eso ya
#     lo resuelve quien llama a guardar_html, pasándole la ruta correcta)
#   - un <div> con borde 1px verde y padding 20px para los sensores
#   - cada sensor: nombre y valor (con unidad) encerrados en <h2>
#   - cada actuador: un <div> con borde 1px gris y padding 20px
#   - nombre del actuador encerrado en <h1>
#   - atributos del actuador: lista <ul> con un <li> por atributo
#   - valores EMAIL: <a href="mailto:...">Contactar a <usuario></a>
# =============================================================================


def generar_html(data):
    """Arma el HTML a partir de `data` = [sensores, dispositivos] (lo que
    devuelve parser.parsear()). Devuelve el string HTML, o None si no hay
    data válida."""
    if not data:
        return None

    sensores = data[0]
    dispositivos = data[1]

    # --- Sensores: <h2>nombre: valor</h2> por cada uno -------------------
    sensores_html = ""
    for i in range(0, len(sensores)):
        if sensores[i].tipo == "SENSOR":
            sensores_html += f"<h2>{sensores[i].valor}: {sensores[i + 1].valor}</h2>\n"

    # --- Actuadores: agrupar tokens (nombre, atributo, valor) de a tres ---
    # Los tokens vienen de a tres seguidos: DISPOSITIVO, ATRIBUTO, VALOR.
    # Un mismo actuador puede aparecer varias veces (una por atributo), así
    # que los agrupamos en un diccionario para juntar todos sus atributos
    # antes de armar su <div>.
    dispositivos_dict = {}
    i = 0
    while i < len(dispositivos):
        if dispositivos[i].tipo == "DISPOSITIVO":
            nombre = dispositivos[i].valor
            atributo = dispositivos[i + 1].valor
            valor = dispositivos[i + 2]

            if nombre not in dispositivos_dict:
                dispositivos_dict[nombre] = {}
            dispositivos_dict[nombre][atributo] = valor

            i += 3
        else:
            i += 1

    # --- Un <div> por actuador, con <h1> + <ul><li>...</li></ul> ----------
    dispositivos_html = ""
    for nombre, atributos in dispositivos_dict.items():
        dispositivos_html += '<div style="border: 1px solid gray; padding: 20px;">\n'
        dispositivos_html += f'<h1>{nombre}</h1>\n'
        dispositivos_html += '<ul>\n'

        for atributo, valor in atributos.items():
            if valor.tipo == "EMAIL":
                usuario = valor.valor.split("@")[0]
                dispositivos_html += (
                    f'<li>{atributo}: <a href="mailto:{valor.valor}">Contactar a {usuario}</a></li>\n'
                )
            else:
                dispositivos_html += f'<li>{atributo}: {valor.valor}</li>\n'

        dispositivos_html += '</ul>\n'
        dispositivos_html += '</div>\n'

    # --- HTML final: sin CSS de diseño --------------------
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>SMART-HOME Dashboard</title>
</head>
<body>

<div style="border: 1px solid green; padding: 20px;">
{sensores_html}
</div>

{dispositivos_html}

</body>
</html>
"""

    return html


def guardar_html(data, ruta_salida):
    """Genera el HTML con generar_html() y lo escribe en `ruta_salida`.
    Devuelve True si se escribió el archivo, False si no había data válida."""
    html = generar_html(data)
    if html is None:
        return False

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)
    return True