import requests
import json
import sys
import os
import re
from datetime import datetime, date

# ============================================================
# CONFIGURACIÓN — API REAL DE LA FCF
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
# CLUB
# ============================================================

CLUB = "LLINARS"

ESCUDO_CLUB_URL = "https://www.fcf.cat/img/escudos/club_08027.png"
ESCUDO_CLUB_LOCAL = "escudos/club_08027.png"

CAMPO_CASA = "Camp Municipal de Llinars del Vallès"

# Los campos ESCUDO_CASA / ESCUDO_FUERA de la API
# suelen contener solamente el nombre del fichero.
BASE_ESCUDOS = "https://www.fcf.cat/img/escudos/"

ESCUDOS_DIR = "escudos"

# ============================================================
# HTTP
# ============================================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
    "Referer": "https://www.fcf.cat/ca/competicio",
}

# Caché durante la ejecución.
# URL remota -> ruta que se utilizará en partidos.json
_cache_escudos = {}


# ============================================================
# UTILIDADES DE ESCUDOS
# ============================================================

def _nombre_seguro(nombre):
    """
    Convierte el nombre del fichero de la FCF en un nombre seguro.
    Ejemplo:
        00100_0001223430_LLINARS.png
    """
    nombre = str(nombre or "").split("?")[0]
    nombre = os.path.basename(nombre)
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", nombre)

    if not nombre:
        return "escudo.png"

    return nombre


def construir_url_escudo(valor):
    """
    Convierte el valor ESCUDO_CASA / ESCUDO_FUERA de la API
    en una URL completa.
    """

    if not valor:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    if valor.startswith("http://") or valor.startswith("https://"):
        return valor

    return BASE_ESCUDOS + valor.lstrip("/")


def descargar_escudo(url_remota):
    """
    Intenta descargar un escudo y guardarlo en /escudos.

    IMPORTANTE:
    Si la FCF bloquea la descarga desde GitHub Actions,
    NO utilizamos el escudo de Llinars como sustituto.

    En ese caso devolvemos la URL remota de la FCF.
    El navegador podrá intentar cargarla directamente.

    Si posteriormente la descarga funciona, el archivo queda
    guardado en GitHub y se utilizará localmente.
    """

    if not url_remota:
        return ESCUDO_CLUB_LOCAL

    # Ya procesado durante esta ejecución.
    if url_remota in _cache_escudos:
        return _cache_escudos[url_remota]

    nombre = _nombre_seguro(url_remota)
    ruta_local = os.path.join(ESCUDOS_DIR, nombre)

    # --------------------------------------------------------
    # 1. Si ya existe en GitHub, utilizarlo.
    # --------------------------------------------------------

    if os.path.isfile(ruta_local) and os.path.getsize(ruta_local) > 0:
        ruta_relativa = ruta_local.replace("\\", "/")
        _cache_escudos[url_remota] = ruta_relativa

        print(f"ESCUDO OK (local): {ruta_relativa}")

        return ruta_relativa

    # --------------------------------------------------------
    # 2. Intentar descargarlo.
    # --------------------------------------------------------

    try:
        print(f"Descargando escudo: {url_remota}")

        res = requests.get(
            url_remota,
            headers=headers,
            timeout=20
        )

        content_type = res.headers.get("Content-Type", "").lower()

        if (
            res.status_code == 200
            and res.content
            and (
                "image" in content_type
                or url_remota.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg"))
            )
        ):
            os.makedirs(ESCUDOS_DIR, exist_ok=True)

            with open(ruta_local, "wb") as f:
                f.write(res.content)

            ruta_relativa = ruta_local.replace("\\", "/")

            _cache_escudos[url_remota] = ruta_relativa

            print(f"ESCUDO GUARDADO: {ruta_relativa}")

            return ruta_relativa

        print(
            f"AVISO: no se pudo descargar {url_remota} "
            f"(HTTP {res.status_code}, Content-Type: {content_type})"
        )

    except Exception as e:
        print(f"AVISO: error descargando {url_remota}: {e}")

    # --------------------------------------------------------
    # 3. FALLBACK:
    #    Utilizar directamente la URL de la FCF.
    #
    #    NO utilizar el escudo de Llinars.
    # --------------------------------------------------------

    print(f"FALLBACK URL REMOTA: {url_remota}")

    _cache_escudos[url_remota] = url_remota

    return url_remota


def escudo_url(valor):
    """
    Recibe ESCUDO_CASA / ESCUDO_FUERA de la API
    y devuelve:

      escudos/xxx.png

    si se ha podido guardar localmente,

    o:

      https://www.fcf.cat/img/escudos/xxx.png

    si la FCF bloquea la descarga.
    """

    url_remota = construir_url_escudo(valor)

    if not url_remota:
        return ESCUDO_CLUB_LOCAL

    return descargar_escudo(url_remota)


# ============================================================
# FECHAS
# ============================================================

def parse_comienzo(txt):
    """
    COMIENZO1 viene normalmente como:

        YYYY-MM-DD HH:MM:SS

    Devuelve:

        (date, HH:MM)
    """

    if not txt:
        return None, ""

    txt = str(txt).strip()

    try:
        dt = datetime.strptime(
            txt,
            "%Y-%m-%d %H:%M:%S"
        )

        return dt.date(), dt.strftime("%H:%M")

    except ValueError:
        pass

    try:
        dt = datetime.fromisoformat(txt)

        return dt.date(), dt.strftime("%H:%M")

    except ValueError:
        return None, ""


# ============================================================
# FILTRO DE PARTIDOS
# ============================================================

def es_partido_llinars(partido):
    """
    Conservamos únicamente partidos donde participa Llinars.
    """

    # Descansos
    if partido.get("CODEQUIPO_CASA") == "-1":
        return False

    if partido.get("CODEQUIPO_FUERA") == "-1":
        return False

    loc = partido.get("NOMBRE_CASA", "") or ""
    vis = partido.get("NOMBRE_FUERA", "") or ""

    return CLUB in (loc + " " + vis).upper()


# ============================================================
# EXTRAER PARTIDOS
# ============================================================

def extrae_partidos(data, jugador, categoria, url_web):

    acumulados = []

    for jornada, partidos in data.items():

        if not isinstance(partidos, list):
            continue

        for p in partidos:

            if not isinstance(p, dict):
                continue

            if not es_partido_llinars(p):
                continue

            loc = p.get("NOMBRE_CASA", "") or ""
            vis = p.get("NOMBRE_FUERA", "") or ""

            es_local = CLUB in loc.upper()

            f_date, hora = parse_comienzo(
                p.get("COMIENZO1")
            )

            # ------------------------------------------------
            # ESCUDOS
            # ------------------------------------------------

            escudo_local = escudo_url(
                p.get("ESCUDO_CASA")
            )

            escudo_visitante = escudo_url(
                p.get("ESCUDO_FUERA")
            )

            acumulados.append({

                "jugador": jugador,

                "categoria": categoria,

                "jornada": jornada,

                "equipo_local": loc,

                "equipo_visitante": vis,

                "escudo_local": escudo_local,

                "escudo_visitante": escudo_visitante,

                "es_local": es_local,

                "fecha": (
                    f_date.isoformat()
                    if f_date
                    else "Fecha por determinar"
                ),

                "hora": hora,

                "campo": (
                    p.get("CAMPO")
                    or (
                        CAMPO_CASA
                        if es_local
                        else f"Campo de {vis}"
                    )
                ),

                "url": url_web,

                "_fecha_date": f_date,
            })

    return acumulados


# ============================================================
# MAIN
# ============================================================

def main():

    hoy = date.today()

    partidos = []

    errores = []

    # --------------------------------------------------------
    # Asegurar que existe la carpeta de escudos.
    # --------------------------------------------------------

    os.makedirs(ESCUDOS_DIR, exist_ok=True)

    # --------------------------------------------------------
    # Procesar todos los jugadores/equipos.
    # --------------------------------------------------------

    for eq in JUGADORES:

        print()
        print("=" * 70)
        print(
            f"Procesando {eq['jugador']} "
            f"({eq['categoria']})"
        )
        print("=" * 70)

        try:

            res = requests.get(
                eq["api"],
                headers=headers,
                timeout=25
            )

            if res.status_code != 200:

                errores.append(
                    f"{eq['jugador']}: HTTP {res.status_code}"
                )

                continue

            data = res.json()

            if not isinstance(data, dict):

                errores.append(
                    f"{eq['jugador']}: formato inesperado "
                    f"({type(data)})"
                )

                continue

            encontrados = extrae_partidos(
                data,
                eq["jugador"],
                eq["categoria"],
                eq["url_web"]
            )

            # ------------------------------------------------
            # Solo partidos futuros.
            # ------------------------------------------------

            futuros = [
                p
                for p in encontrados
                if (
                    p["_fecha_date"]
                    and p["_fecha_date"] >= hoy
                )
            ]

            futuros.sort(
                key=lambda p: p["_fecha_date"]
            )

            # Si no quedan futuros,
            # conservamos el último partido disponible.
            if not futuros and encontrados:

                con_fecha = [
                    p
                    for p in encontrados
                    if p["_fecha_date"]
                ]

                con_fecha.sort(
                    key=lambda p: p["_fecha_date"]
                )

                futuros = con_fecha[-1:]

            if not futuros:

                muestra = json.dumps(
                    data,
                    ensure_ascii=False
                )[:1500]

                print(
                    f"DIAGNÓSTICO {eq['jugador']} "
                    f"— estructura recibida:"
                )

                print(muestra)

                errores.append(
                    f"{eq['jugador']}: la API respondió "
                    f"pero no hay partidos de {CLUB}"
                )

            partidos.extend(futuros)

        except Exception as e:

            errores.append(
                f"{eq['jugador']}: {e}"
            )

    # --------------------------------------------------------
    # Eliminar campo interno.
    # --------------------------------------------------------

    for p in partidos:

        p.pop("_fecha_date", None)

    # --------------------------------------------------------
    # No generar JSON vacío.
    # --------------------------------------------------------

    if not partidos:

        print()
        print(
            "ERROR — no se pudo extraer "
            "ningún partido real:"
        )

        for e in errores:
            print("  -", e)

        sys.exit(1)

    # --------------------------------------------------------
    # Guardar JSON.
    # --------------------------------------------------------

    with open(
        "partidos.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            partidos,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Resumen.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        f"OK: {len(partidos)} partidos guardados"
    )
    print("=" * 70)

    for p in partidos:

        print(
            f"- {p['jugador']}: "
            f"{p['equipo_local']} vs "
            f"{p['equipo_visitante']} | "
            f"{p['fecha']} "
            f"{p['hora']} | "
            f"J{p['jornada']}"
        )

        print(
            f"  Escudo local: "
            f"{p['escudo_local']}"
        )

        print(
            f"  Escudo visitante: "
            f"{p['escudo_visitante']}"
        )

    # --------------------------------------------------------
    # Mostrar errores aunque haya partidos.
    # --------------------------------------------------------

    if errores:

        print()
        print("AVISOS:")

        for e in errores:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
