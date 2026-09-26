import requests
import json
import sys
from datetime import datetime, date


# ============================================================
# CONFIGURACIÓN DE JUGADORES
# ============================================================

JUGADORES = [
    {
        "jugador": "Erik",
        "categoria": "Infantil A",
        "api": "https://www.fcf.cat/api/competition/partidos?grupId=58162479",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58162474&grupId=58162479"
    },
    {
        "jugador": "Biel",
        "categoria": "Benjamí B",
        "api": "https://www.fcf.cat/api/competition/partidos?grupId=60364101",
        "url_web": "https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308235&competicioId=58162174&grupId=60364101"
    }
]


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

CLUB = "LLINARS"

ESCUDO_CLUB = "https://www.fcf.cat/img/escudos/club_08027.png"

BASE_ESCUDOS = "https://www.fcf.cat/img/escudos/"

CAMPO_CASA = "Camp Municipal de Llinars del Vallès"

# Este es el archivo que generará scraper.py
ARCHIVO_SALIDA = "partidos.json"


# ============================================================
# HEADERS
# ============================================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.fcf.cat/ca/competicio",
}


# ============================================================
# ESCUDOS
# ============================================================

def escudo_url(nombre_fichero):
    """
    Convierte el nombre del escudo de la FCF
    en una URL completa.
    """

    if not nombre_fichero:
        return ESCUDO_CLUB

    nombre_fichero = str(nombre_fichero).strip()

    if not nombre_fichero:
        return ESCUDO_CLUB

    if nombre_fichero.startswith("http://") or \
       nombre_fichero.startswith("https://"):

        return nombre_fichero

    return BASE_ESCUDOS + nombre_fichero


# ============================================================
# FECHA Y HORA
# ============================================================

def parse_comienzo(txt):
    """
    Convierte:

        2026-10-04 10:15:00

    en:

        datetime completo
        fecha
        hora
    """

    if not txt:
        return None, None, ""

    txt = str(txt).strip()

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for formato in formatos:

        try:

            dt = datetime.strptime(
                txt,
                formato
            )

            return (
                dt,
                dt.date(),
                dt.strftime("%H:%M")
            )

        except ValueError:
            pass


    # Intento adicional
    try:

        dt = datetime.fromisoformat(txt)

        return (
            dt,
            dt.date(),
            dt.strftime("%H:%M")
        )

    except ValueError:

        return None, None, ""


# ============================================================
# COMPROBAR PARTIDO DEL LLINARS
# ============================================================

def es_partido_llinars(partido):

    # -1 significa descanso / sin partido
    if partido.get("CODEQUIPO_CASA") == "-1":
        return False

    if partido.get("CODEQUIPO_FUERA") == "-1":
        return False


    local = str(
        partido.get("NOMBRE_CASA", "") or ""
    )

    visitante = str(
        partido.get("NOMBRE_FUERA", "") or ""
    )


    texto = (
        local +
        " " +
        visitante
    ).upper()


    return CLUB in texto


# ============================================================
# EXTRAER PARTIDOS
# ============================================================

def extrae_partidos(
    data,
    jugador,
    categoria,
    url_web
):

    acumulados = []


    if not isinstance(data, dict):
        return acumulados


    for jornada, partidos in data.items():

        if not isinstance(partidos, list):
            continue


        for partido in partidos:

            if not isinstance(partido, dict):
                continue


            # -----------------------------------------------
            # Solo partidos del Llinars
            # -----------------------------------------------

            if not es_partido_llinars(partido):
                continue


            # -----------------------------------------------
            # Equipos
            # -----------------------------------------------

            local = str(
                partido.get(
                    "NOMBRE_CASA",
                    ""
                ) or ""
            ).strip()


            visitante = str(
                partido.get(
                    "NOMBRE_FUERA",
                    ""
                ) or ""
            ).strip()


            # -----------------------------------------------
            # Local / visitante
            # -----------------------------------------------

            es_local = (
                CLUB in local.upper()
            )


            # -----------------------------------------------
            # Fecha
            # -----------------------------------------------

            fecha_datetime, fecha_date, hora = \
                parse_comienzo(
                    partido.get("COMIENZO1")
                )


            # -----------------------------------------------
            # Campo
            # -----------------------------------------------

            campo = (
                partido.get("CAMPO")
                or (
                    CAMPO_CASA
                    if es_local
                    else f"Campo de {local}"
                )
            )


            campo = str(
                campo
            ).strip()


            # -----------------------------------------------
            # Crear registro
            # -----------------------------------------------

            registro = {

                "jugador": jugador,

                "categoria": categoria,

                "jornada": str(
                    partido.get(
                        "JORNADA",
                        jornada
                    )
                ),

                "equipo_local": local,

                "equipo_visitante": visitante,

                "escudo_local": escudo_url(
                    partido.get(
                        "ESCUDO_CASA"
                    )
                ),

                "escudo_visitante": escudo_url(
                    partido.get(
                        "ESCUDO_FUERA"
                    )
                ),

                "es_local": es_local,

                # SIEMPRE YYYY-MM-DD
                "fecha": (
                    fecha_date.isoformat()
                    if fecha_date
                    else ""
                ),

                "hora": hora,

                "campo": campo,

                "url": url_web,

                # Campo interno
                "_datetime": fecha_datetime
            }


            acumulados.append(
                registro
            )


    return acumulados


# ============================================================
# FILTRAR PARTIDOS FUTUROS
# ============================================================

def filtrar_futuros(partidos):

    ahora = datetime.now()

    hoy = date.today()

    futuros = []


    for partido in partidos:

        dt = partido.get(
            "_datetime"
        )

        fecha = partido.get(
            "fecha"
        )


        # -----------------------------------------------
        # Tenemos fecha + hora
        # -----------------------------------------------

        if dt is not None:

            if dt >= ahora:

                futuros.append(
                    partido
                )

            continue


        # -----------------------------------------------
        # Solo tenemos fecha
        # -----------------------------------------------

        if fecha:

            try:

                fecha_obj = date.fromisoformat(
                    fecha
                )

                if fecha_obj >= hoy:

                    futuros.append(
                        partido
                    )

            except ValueError:
                pass


    return futuros


# ============================================================
# ORDENAR PARTIDOS
# ============================================================

def clave_orden(partido):

    dt = partido.get(
        "_datetime"
    )


    if dt is not None:
        return dt


    fecha = partido.get(
        "fecha"
    )


    if fecha:

        try:

            return datetime.combine(
                date.fromisoformat(
                    fecha
                ),
                datetime.min.time()
            )

        except ValueError:
            pass


    return datetime.max


# ============================================================
# MAIN
# ============================================================

def main():

    partidos_totales = []

    errores = []


    print()
    print("=" * 65)
    print("        SCRAPER FCF - CALENDARIO LLINARS")
    print("=" * 65)
    print()


    ahora = datetime.now()

    print(
        "Fecha/hora de ejecución:",
        ahora.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    print()


    # ========================================================
    # CONSULTAR CADA JUGADOR
    # ========================================================

    for jugador_config in JUGADORES:

        jugador = jugador_config["jugador"]

        categoria = jugador_config["categoria"]

        api = jugador_config["api"]

        url_web = jugador_config["url_web"]


        print("-" * 65)

        print(
            f"CONSULTANDO: {jugador} "
            f"({categoria})"
        )

        print("-" * 65)


        try:

            respuesta = requests.get(
                api,
                headers=headers,
                timeout=25
            )


            # -----------------------------------------------
            # HTTP
            # -----------------------------------------------

            if respuesta.status_code != 200:

                mensaje = (
                    f"{jugador}: HTTP "
                    f"{respuesta.status_code}"
                )

                errores.append(
                    mensaje
                )

                print(
                    "❌ ERROR:",
                    mensaje
                )

                continue


            # -----------------------------------------------
            # JSON
            # -----------------------------------------------

            try:

                data = respuesta.json()

            except ValueError:

                mensaje = (
                    f"{jugador}: "
                    f"la respuesta no es JSON válido"
                )

                errores.append(
                    mensaje
                )

                print(
                    "❌ ERROR:",
                    mensaje
                )

                continue


            if not isinstance(data, dict):

                mensaje = (
                    f"{jugador}: formato inesperado "
                    f"({type(data).__name__})"
                )

                errores.append(
                    mensaje
                )

                print(
                    "❌ ERROR:",
                    mensaje
                )

                continue


            # -----------------------------------------------
            # EXTRAER
            # -----------------------------------------------

            encontrados = extrae_partidos(
                data,
                jugador,
                categoria,
                url_web
            )


            print(
                "Partidos del Llinars encontrados:",
                len(encontrados)
            )


            # -----------------------------------------------
            # FUTUROS
            # -----------------------------------------------

            futuros = filtrar_futuros(
                encontrados
            )


            futuros.sort(
                key=clave_orden
            )


            print(
                "Partidos futuros:",
                len(futuros)
            )


            # -----------------------------------------------
            # MOSTRAR PARTIDOS
            # -----------------------------------------------

            if futuros:

                print()

                for partido in futuros:

                    print(
                        f"  ✓ "
                        f"{partido['fecha']} "
                        f"{partido['hora']} | "
                        f"{partido['equipo_local']} "
                        f"vs "
                        f"{partido['equipo_visitante']} "
                        f"| J{partido['jornada']}"
                    )

            else:

                print()

                if encontrados:

                    print(
                        f"⚠ {jugador}: "
                        f"se encontraron partidos, "
                        f"pero ninguno es futuro."
                    )

                else:

                    mensaje = (
                        f"{jugador}: la API respondió "
                        f"pero no se encontraron "
                        f"partidos del {CLUB}"
                    )

                    errores.append(
                        mensaje
                    )

                    print(
                        "❌ ERROR:",
                        mensaje
                    )


            # -----------------------------------------------
            # Añadir
            # -----------------------------------------------

            partidos_totales.extend(
                futuros
            )


        except requests.RequestException as e:

            mensaje = (
                f"{jugador}: "
                f"error de conexión: {e}"
            )

            errores.append(
                mensaje
            )

            print(
                "❌ ERROR:",
                mensaje
            )


        except Exception as e:

            mensaje = (
                f"{jugador}: "
                f"error inesperado: {e}"
            )

            errores.append(
                mensaje
            )

            print(
                "❌ ERROR:",
                mensaje
            )


    # ========================================================
    # ORDEN GLOBAL
    # ========================================================

    partidos_totales.sort(
        key=clave_orden
    )


    # ========================================================
    # ELIMINAR CAMPOS INTERNOS
    # ========================================================

    for partido in partidos_totales:

        partido.pop(
            "_datetime",
            None
        )


    # ========================================================
    # SIN PARTIDOS
    # ========================================================

    if not partidos_totales:

        print()
        print("=" * 65)
        print(
            "❌ ERROR: NO SE HA ENCONTRADO "
            "NINGÚN PARTIDO FUTURO"
        )
        print("=" * 65)
        print()

        for error in errores:

            print(
                "  -",
                error
            )

        print()

        sys.exit(1)


    # ========================================================
    # GUARDAR JSON
    # ========================================================

    try:

        with open(
            ARCHIVO_SALIDA,
            "w",
            encoding="utf-8"
        ) as archivo:

            json.dump(
                partidos_totales,
                archivo,
                ensure_ascii=False,
                indent=2
            )


    except OSError as e:

        print()
        print(
            "❌ ERROR escribiendo",
            ARCHIVO_SALIDA
        )

        print(e)

        sys.exit(1)


    # ========================================================
    # RESUMEN FINAL
    # ========================================================

    print()
    print("=" * 65)
    print(
        f"✓ OK: {len(partidos_totales)} "
        f"partidos guardados en "
        f"{ARCHIVO_SALIDA}"
    )
    print("=" * 65)
    print()


    print("PRÓXIMOS PARTIDOS")
    print()


    for partido in partidos_totales:

        print(
            f"  {partido['fecha']} "
            f"{partido['hora']} | "
            f"{partido['jugador']} | "
            f"{partido['equipo_local']} "
            f"vs "
            f"{partido['equipo_visitante']}"
        )


    # ========================================================
    # AVISOS
    # ========================================================

    if errores:

        print()
        print("AVISOS:")
        print()

        for error in errores:

            print(
                "  ⚠",
                error
            )


    print()
    print(
        "Archivo generado:",
        ARCHIVO_SALIDA
    )

    print()


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    main()
