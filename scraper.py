import requests
import json
import sys
from datetime import datetime


# ============================================================
# CONFIGURACIÓN
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

CLUB = "LLINARS"

ESCUDO_CLUB = "https://www.fcf.cat/img/escudos/club_08027.png"

BASE_ESCUDOS = "https://www.fcf.cat/img/escudos/"

CAMPO_CASA = "Camp Municipal de Llinars del Vallès"

ARCHIVO_SALIDA = "partidos.json"


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.fcf.cat/"
}


# ============================================================
# ESCUDOS
# ============================================================

def escudo_url(valor):

    if not valor:
        return ESCUDO_CLUB

    valor = str(valor).strip()

    if not valor:
        return ESCUDO_CLUB

    if valor.startswith("http://") or valor.startswith("https://"):
        return valor

    return BASE_ESCUDOS + valor


# ============================================================
# FECHA
# ============================================================

def parse_fecha(valor):

    if not valor:
        return None

    valor = str(valor).strip()

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M"
    ]

    for formato in formatos:
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


# ============================================================
# ¿ES PARTIDO DEL LLINARS?
# ============================================================

def es_partido_llinars(partido):

    codigo_casa = str(
        partido.get("CODEQUIPO_CASA", "")
    )

    codigo_fuera = str(
        partido.get("CODEQUIPO_FUERA", "")
    )

    # Descansos
    if codigo_casa == "-1":
        return False

    if codigo_fuera == "-1":
        return False

    local = str(
        partido.get("NOMBRE_CASA", "") or ""
    ).upper()

    visitante = str(
        partido.get("NOMBRE_FUERA", "") or ""
    ).upper()

    return (
        CLUB in local
        or
        CLUB in visitante
    )


# ============================================================
# EXTRAER PARTIDOS
# ============================================================

def extraer_partidos(
    data,
    jugador,
    categoria,
    url_web
):

    resultados = []

    if not isinstance(data, dict):
        return resultados

    for clave_jornada, lista in data.items():

        if not isinstance(lista, list):
            continue

        for partido in lista:

            if not isinstance(partido, dict):
                continue

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
            ).replace("\n", " ").strip()

            visitante = str(
                partido.get(
                    "NOMBRE_FUERA",
                    ""
                ) or ""
            ).replace("\n", " ").strip()

            # -----------------------------------------------
            # Fecha/hora
            # -----------------------------------------------

            comienzo = partido.get(
                "COMIENZO1"
            )

            fecha_dt = parse_fecha(
                comienzo
            )

            if fecha_dt:

                fecha = fecha_dt.strftime(
                    "%Y-%m-%d"
                )

                hora = fecha_dt.strftime(
                    "%H:%M"
                )

            else:

                fecha = ""
                hora = ""

            # -----------------------------------------------
            # Local / visitante
            # -----------------------------------------------

            es_local = (
                CLUB in local.upper()
            )

            # -----------------------------------------------
            # Campo
            # -----------------------------------------------

            campo = partido.get(
                "CAMPO"
            )

            if not campo:

                if es_local:
                    campo = CAMPO_CASA
                else:
                    campo = f"Campo de {local}"

            campo = str(
                campo
            ).replace("\n", " ").strip()

            # -----------------------------------------------
            # Jornada
            # -----------------------------------------------

            jornada = str(
                partido.get(
                    "JORNADA",
                    clave_jornada
                )
            )

            # -----------------------------------------------
            # Crear objeto
            # -----------------------------------------------

            resultado = {
                "jugador": jugador,
                "categoria": categoria,
                "jornada": jornada,

                "equipo_local": local,
                "equipo_visitante": visitante,

                "escudo_local": escudo_url(
                    partido.get("ESCUDO_CASA")
                ),

                "escudo_visitante": escudo_url(
                    partido.get("ESCUDO_FUERA")
                ),

                "es_local": es_local,

                "fecha": fecha,
                "hora": hora,

                "campo": campo,

                "url": url_web
            }

            resultados.append(
                resultado
            )

    return resultados


# ============================================================
# ORDENAR
# ============================================================

def clave_orden(partido):

    fecha = partido.get(
        "fecha",
        ""
    )

    hora = partido.get(
        "hora",
        "00:00"
    )

    try:

        return datetime.strptime(
            f"{fecha} {hora}",
            "%Y-%m-%d %H:%M"
        )

    except ValueError:

        return datetime.max


# ============================================================
# MAIN
# ============================================================

def main():

    todos = []

    errores = []

    print()
    print("=" * 70)
    print("        SCRAPER FCF - LLINARS")
    print("=" * 70)
    print()

    print(
        "Ejecutado:",
        datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    print()

    # ========================================================
    # ERIK / BIEL
    # ========================================================

    for config in JUGADORES:

        jugador = config["jugador"]

        print("-" * 70)
        print(
            f"Consultando {jugador}..."
        )
        print("-" * 70)

        try:

            respuesta = requests.get(
                config["api"],
                headers=HEADERS,
                timeout=30
            )

            print(
                "HTTP:",
                respuesta.status_code
            )

            if respuesta.status_code != 200:

                errores.append(
                    f"{jugador}: HTTP "
                    f"{respuesta.status_code}"
                )

                print(
                    "ERROR HTTP"
                )

                continue

            try:

                data = respuesta.json()

            except Exception as e:

                errores.append(
                    f"{jugador}: JSON inválido: {e}"
                )

                print(
                    "ERROR: respuesta no JSON"
                )

                continue

            encontrados = extraer_partidos(
                data,
                jugador,
                config["categoria"],
                config["url_web"]
            )

            print(
                "Partidos encontrados:",
                len(encontrados)
            )

            # -----------------------------------------------
            # Mostrar todos los partidos encontrados
            # -----------------------------------------------

            for partido in encontrados:

                print(
                    f"  ✓ "
                    f"{partido['fecha']} "
                    f"{partido['hora']} | "
                    f"{partido['equipo_local']} "
                    f"vs "
                    f"{partido['equipo_visitante']} | "
                    f"J{partido['jornada']}"
                )

            todos.extend(
                encontrados
            )

        except Exception as e:

            errores.append(
                f"{jugador}: {e}"
            )

            print(
                "ERROR:",
                e
            )

        print()


    # ========================================================
    # ELIMINAR DUPLICADOS
    # ========================================================

    unicos = {}

    for partido in todos:

        clave = (
            partido["jugador"],
            partido["fecha"],
            partido["hora"],
            partido["equipo_local"],
            partido["equipo_visitante"]
        )

        unicos[clave] = partido


    todos = list(
        unicos.values()
    )


    # ========================================================
    # ORDENAR
    # ========================================================

    todos.sort(
        key=clave_orden
    )


    # ========================================================
    # GUARDAR
    # ========================================================

    try:

        with open(
            ARCHIVO_SALIDA,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                todos,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            "ERROR guardando partidos.json:",
            e
        )

        sys.exit(1)


    # ========================================================
    # RESUMEN
    # ========================================================

    print("=" * 70)
    print(
        f"OK: {len(todos)} partidos guardados"
    )
    print(
        f"Archivo: {ARCHIVO_SALIDA}"
    )
    print("=" * 70)

    print()

    # Contadores
    erik = sum(
        1 for p in todos
        if p["jugador"] == "Erik"
    )

    biel = sum(
        1 for p in todos
        if p["jugador"] == "Biel"
    )

    print(
        f"Erik: {erik} partidos"
    )

    print(
        f"Biel: {biel} partidos"
    )

    print()

    if errores:

        print("AVISOS:")

        for error in errores:
            print(
                " -",
                error
            )

    print()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()