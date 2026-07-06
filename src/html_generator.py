# =============================================================================
# Generador de HTML del dashboard SMART HOME
# =============================================================================
# Esta es la idea general: el parser (parser.py) analiza el código .smart y
# nos devuelve una lista con dos cosas adentro: [sensores, dispositivos].
# Este archivo agarra esa data "cruda" (tokens) y arma un HTML lindo para
# mostrar en el navegador. O sea: parser = entiende el lenguaje, este
# archivo = lo dibuja en pantalla.
# =============================================================================


def generar_html(data):
    """Esta función recibe `data` (lo que devuelve parsear()) y devuelve un
    string con el HTML entero armado. No escribe nada a disco todavía, solo
    arma el texto. Eso lo hace la otra función de abajo (guardar_html)."""

    # Si el parser no nos dio nada (None, lista vacía, etc.) no tiene sentido
    # seguir: cortamos acá y devolvemos None para avisar "no hay nada que
    # mostrar". Esto es lo que faltaba antes en gui.py: nadie chequeaba esto.
    if not data:
        return None

    # data viene como [sensores, dispositivos] (una lista con 2 elementos,
    # cada uno es a su vez una lista de tokens). Los separamos para
    # trabajarlos más cómodo.
    sensores = data[0]
    dispositivos = data[1]

    # --- Sensores -------------------------------------------------------
    # Los tokens de sensores vienen "mezclados": un token de tipo SENSOR
    # (el nombre, ej "sensor_luz") seguido del token con su valor
    # (ej "300lux"). Por eso recorremos con índice `i`: cuando encontramos
    # un SENSOR, sabemos que el valor está en la posición siguiente (i+1).
    sensores_html = ""
    for i in range(0, len(sensores)):
        if sensores[i].tipo == "SENSOR":
            # armamos un <h2>nombre: valor</h2> por cada sensor encontrado
            sensores_html += f"<h2>{sensores[i].valor}: {sensores[i + 1].valor}</h2>\n"

    # --- Dispositivos: agrupar tokens (nombre, atributo, valor) de a tres --
    # Acá es un poco más compleja la cosa. En el .smart, cada línea de
    # dispositivo tiene esta forma:
    #     foco_living.brillo = 70%
    #     (nombre) (atributo)  (valor)
    # y eso se traduce a 3 tokens seguidos: DISPOSITIVO, ATRIBUTO, VALOR.
    # Como un mismo dispositivo (ej "foco_living") puede aparecer varias
    # veces con distintos atributos (estado, brillo, color...), armamos un
    # diccionario para agruparlos todos bajo el mismo nombre:
    #
    #   dispositivos_dict = {
    #       "foco_living": {"estado": Token(ON), "brillo": Token(70%), ...},
    #       "aire_living": {...},
    #   }
    dispositivos_dict = {}
    i = 0
    while i < len(dispositivos):
        if dispositivos[i].tipo == "DISPOSITIVO":
            nombre = dispositivos[i].valor        # ej "foco_living"
            atributo = dispositivos[i + 1].valor   # ej "brillo"
            valor = dispositivos[i + 2]            # el token completo con el valor (ej Token(70%))

            # si es la primera vez que vemos este dispositivo, le creamos
            # su diccionario interno vacío
            if nombre not in dispositivos_dict:
                dispositivos_dict[nombre] = {}

            # guardamos el atributo con su valor
            dispositivos_dict[nombre][atributo] = valor

            # avanzamos de a 3 porque ya consumimos DISPOSITIVO + ATRIBUTO + VALOR
            i += 3
        else:
            # por las dudas aparezca algún token raro que no es DISPOSITIVO,
            # no nos quedamos trabados: avanzamos de a 1 nomás
            i += 1

    # Ahora que ya tenemos todo prolijo en el diccionario, armamos el HTML:
    # una "caja" (<div class="cajadis">) por cada dispositivo, con una lista
    # de sus atributos adentro.
    dispositivos_html = ""
    for nombre, atributos in dispositivos_dict.items():
        dispositivos_html += '<div class="cajadis">\n'
        dispositivos_html += f'    <h1>{nombre}</h1>\n'
        dispositivos_html += '    <ul>\n'

        for atributo, valor in atributos.items():
            # caso especial: si el valor es un email, en vez de mostrarlo
            # como texto plano hacemos un link "mailto:" para que se pueda
            # clickear y mandar un mail directamente
            if valor.tipo == "EMAIL":
                usuario = valor.valor.split("@")[0]  # la parte antes de la @, para el texto del link
                dispositivos_html += (
                    f'<li>{atributo}: <a href="mailto:{valor.valor}">Contactar a {usuario}</a></li>\n'
                )
            else:
                # cualquier otro valor (ON/OFF, porcentaje, temperatura, etc.)
                # se muestra tal cual, como texto
                dispositivos_html += f'<li>{atributo}: {valor.valor}</li>\n'

        dispositivos_html += '    </ul>\n'
        dispositivos_html += '</div>\n'

    # --- Plantilla HTML ---------------------------------------------------
    # Esto es un f-string gigante: básicamente un HTML normal, pero como es
    # un f-string, todo lo que está entre {} se reemplaza por variables de
    # Python. OJO: como el HTML/CSS también usa llaves { } (para el CSS),
    # hay que escaparlas duplicándolas ({{ y }}) para que Python no las
    # confunda con una variable. Por eso ves cosas como "body {{ ... }}" en
    # vez de "body { ... }": eso, una vez que Python arma el string final,
    # se convierte en "body { ... }" normal.
    #
    # Las dos variables reales que se insertan acá son {sensores_html} y
    # {dispositivos_html}, que ya armamos arriba.
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>SMART-HOME Dashboard</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: #f4f6f8;
                color: #2b2b2b;
                margin: 0;
                padding: 30px;
            }}
            .contenedor {{
                max-width: 800px;
                margin: 0 auto;
            }}
            h1.titulo-principal {{
                text-align: center;
                color: #2c3e50;
            }}
            /* .caja y .cajadis mantienen exactamente el borde de 1px
               y el padding de 20px que pide la consigna; el resto
               de las propiedades son estética adicional. */
            .caja {{
                border: 1px solid green;
                padding: 20px;
                border-radius: 6px;
                background-color: #eafaf1;
                margin-bottom: 25px;
            }}
            .caja h2 {{
                color: #1e8449;
                margin: 8px 0;
            }}
            .cajadis {{
                border: 1px solid gray;
                padding: 20px;
                border-radius: 6px;
                background-color: #ffffff;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }}
            .cajadis h1 {{
                color: #34495e;
                margin-top: 0;
                font-size: 1.3em;
                border-bottom: 1px solid #ecf0f1;
                padding-bottom: 8px;
            }}
            .cajadis ul {{
                list-style: none;
                padding-left: 0;
            }}
            .cajadis li {{
                padding: 4px 0;
            }}
            .cajadis a {{
                color: #2980b9;
                text-decoration: none;
            }}
            .cajadis a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="contenedor">
            <h1 class="titulo-principal">Estado de la Smart Home</h1>
            <h1>Lista de Sensores</h1>
            <div class="caja">
                {sensores_html}
            </div>
            <h1>Lista de Actuadores</h1>
            {dispositivos_html}
        </div>
    </body>
    </html>
    """

    # devolvemos el HTML armado como string; todavía no se guardó en
    # ningún lado, eso lo hace guardar_html()
    return html


def guardar_html(data, ruta_salida):
    """Esta es la función "de mas alto nivel" que en general vas a llamar
    desde afuera (desde main.py o gui.py). Hace dos cosas:
      1) le pide a generar_html() que arme el string del HTML
      2) si salió bien, lo escribe físicamente en un archivo

    Devuelve True si se guardó el archivo, o False si no había data válida
    (por ejemplo si el parser rechazó el script y no generó nada)."""

    html = generar_html(data)

    # si generar_html nos devolvió None, no hay nada para guardar: avisamos
    # con False para que quien nos llamó sepa que no se generó ningún .html
    if html is None:
        return False

    # "w" = abrir en modo escritura (si el archivo ya existe, lo pisa)
    # encoding="utf-8" para que no explote con tildes, ñ, °C, etc.
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)

    return True