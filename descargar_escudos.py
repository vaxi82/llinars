"""
Descarga todos los escudos (de equipo local y visitante) que aparecen en
partidos.json y los deja en la carpeta escudos/, además de generar un
escudos.zip listo para subir al repo o descomprimir donde haga falta.

Uso:
    pip install requests
    python descargar_escudos.py

Requisitos:
    - Ejecutarlo en una máquina con acceso normal a internet (tu ordenador).
    - Tener partidos.json en el mismo directorio que este script (o pasar
      la ruta como primer argumento).

Reutiliza la misma lógica de nombrado de archivo que scraper.py
(_nombre_seguro) para que los nombres coincidan si más adelante el propio
scraper.py también descarga escudos.
"""

import json
import os
import re
import sys
import zipfile

import requests

ESCUDOS_DIR = "escudos"
ZIP_SALIDA = "escudos.zip"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
    "Referer": "https://www.fcf.cat/ca/competicio",
}


def nombre_seguro(nombre):
    """Misma lógica que scraper.py: nombre de archivo local a partir de la URL."""
    nombre = str(nombre or "").split("?")[0]
    nombre = os.path.basename(nombre)
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", nombre)
    return nombre or "escudo.png"


def cargar_partidos(ruta_json):
    with open(ruta_json, "r", encoding="utf-8") as f:
        return json.load(f)


def urls_unicas(partidos):
    urls = {}
    for p in partidos:
        for campo, nombre_equipo in (
            ("escudo_local", "equipo_local"),
            ("escudo_visitante", "equipo_visitante"),
        ):
            url = p.get(campo)
            equipo = p.get(nombre_equipo, "?")
            if url:
                urls.setdefault(url, equipo)
    return urls


def descargar(url):
    ruta_local = os.path.join(ESCUDOS_DIR, nombre_seguro(url))

    if os.path.isfile(ruta_local) and os.path.getsize(ruta_local) > 0:
        print(f"  ya existe: {ruta_local}")
        return True

    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        content_type = res.headers.get("Content-Type", "").lower()
        es_imagen = "image" in content_type or url.lower().endswith(
            (".png", ".jpg", ".jpeg", ".webp", ".svg")
        )
        if res.status_code == 200 and res.content and es_imagen:
            with open(ruta_local, "wb") as f:
                f.write(res.content)
            print(f"  OK: {ruta_local} ({len(res.content)} bytes)")
            return True
        print(f"  FALLO ({res.status_code}, content-type={content_type}): {url}")
    except Exception as e:
        print(f"  ERROR: {url} -> {e}")
    return False


def main():
    ruta_json = sys.argv[1] if len(sys.argv) > 1 else "partidos.json"
    if not os.path.isfile(ruta_json):
        print(f"No encuentro {ruta_json}. Pásalo como argumento si está en otra ruta.")
        sys.exit(1)

    partidos = cargar_partidos(ruta_json)
    urls = urls_unicas(partidos)

    print(f"Encontrados {len(urls)} escudos distintos en {ruta_json}\n")

    os.makedirs(ESCUDOS_DIR, exist_ok=True)

    ok, fallidos = [], []
    for url, equipo in sorted(urls.items(), key=lambda x: x[1]):
        print(f"{equipo}")
        if descargar(url):
            ok.append(url)
        else:
            fallidos.append((equipo, url))

    print(f"\nDescargados/disponibles: {len(ok)}/{len(urls)}")
    if fallidos:
        print("No se pudieron obtener:")
        for equipo, url in fallidos:
            print(f"  - {equipo}: {url}")

    # Empaquetar TODO lo que haya en escudos/ (incluye los que ya tuvieras)
    with zipfile.ZipFile(ZIP_SALIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in sorted(os.listdir(ESCUDOS_DIR)):
            fpath = os.path.join(ESCUDOS_DIR, fname)
            if os.path.isfile(fpath):
                z.write(fpath, arcname=f"escudos/{fname}")

    print(f"\nListo: {ZIP_SALIDA} generado con el contenido de {ESCUDOS_DIR}/")


if __name__ == "__main__":
    main()
