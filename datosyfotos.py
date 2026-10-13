#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
descargar_datos_y_fotos.py
1. Lee o descarga las candidaturas oficiales del IEES.
2. Filtra estrictamente propietarios (Opción A).
3. Descarga todas las fotos y logos a carpetas locales ('fotos/' y 'logos/').
4. Genera un nuevo 'candidatos.json' con rutas locales para evitar problemas de CORS.
"""

import os
import json
import re
import urllib.request
import unicodedata
from urllib.parse import urlparse

# Archivo origen y carpetas de destino
ARCHIVO_ENTRADA = 'candidatos.json'
ARCHIVO_SALIDA = 'candidatos.json'
CARPETA_FOTOS = 'fotos'
CARPETA_LOGOS = 'logos'

# Encabezado para evitar que el servidor del IEES bloquee la descarga de fotos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def normalizar(texto):
    """Elimina tildes y caracteres especiales para comparar cadenas limpiamente."""
    if not texto:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(texto))
    sin_tildes = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return sin_tildes.upper().strip()


def es_propietario(c):
    """Filtro Opción A: Verifica si es titular descartando suplencias."""
    calidad = normalizar(c.get('calidad') or c.get('tipo_candidatura') or c.get('tipo_formula') or '')
    if 'SUPLENTE' in calidad:
        return False

    cargo = normalizar(c.get('cargo') or '')
    if 'SUPLENTE' in cargo:
        return False

    return True


def sanear_url(url):
    """Limpia barras invertidas de URLs escapadas en JSON."""
    if not url:
        return ''
    return str(url).replace('\\/', '/').strip()


def descargar_archivo(url, ruta_destino):
    """Descarga una imagen desde una URL remota guardándola localmente."""
    if not url or 'placehold.co' in url:
        return False

    if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 0:
        return True  # Ya fue descargada previamente

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as respuesta:
            contenido = respuesta.read()
            if len(contenido) > 500:  # Validar que no sea una respuesta vacía o error 404 en html
                with open(ruta_destino, 'wb') as f:
                    f.write(contenido)
                return True
    except Exception as e:
        print(f"    [!] No se pudo descargar {url}: {e}")
        return False


def main():
    # Crear carpetas si no existen
    os.makedirs(CARPETA_FOTOS, exist_ok=True)
    os.makedirs(CARPETA_LOGOS, exist_ok=True)

    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"[ERROR] No se encontró '{ARCHIVO_ENTRADA}' en el directorio actual.")
        return

    print(f"[*] Leyendo '{ARCHIVO_ENTRADA}'...")
    with open(ARCHIVO_ENTRADA, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    print(f"[*] Total de registros encontrados: {len(datos)}")

    # 1. Filtrar únicamente a titulares/propietarios (Opción A)
    candidatos_filtrados = []
    claves_vistas = set()

    for c in datos:
        if not es_propietario(c):
            continue

        nombre_prop = normalizar(c.get('nombre_propietario', ''))
        partido = normalizar(c.get('partido_siglas') or c.get('partido') or '')
        localidad = normalizar(c.get('localidad') or '')
        clave = f"{nombre_prop}_{partido}_{localidad}"

        if clave in claves_vistas:
            continue

        claves_vistas.add(clave)
        candidatos_filtrados.append(c)

    print(f"[*] Titulares únicos seleccionados: {len(candidatos_filtrados)}")
    print("[*] Iniciando descarga de fotografías y logotipos...")

    total = len(candidatos_filtrados)
    descargadas_fotos = 0
    descargados_logos = 0

    for i, c in enumerate(candidatos_filtrados, 1):
        cid = c.get('id', i)
        nombre = normalizar(c.get('nombre_propietario', f'candidato_{cid}'))
        slug = re.sub(r'[^A-Z0-9]+', '_', nombre).strip('_')

        # Procesar Fotografía
        url_foto = sanear_url(c.get('fotografia', ''))
        if url_foto:
            ext = os.path.splitext(urlparse(url_foto).path)[1]
            if not ext or len(ext) > 5:
                ext = '.jpg'
            
            nombre_archivo_foto = f"candidato_{cid}_{slug[:30]}{ext}"
            ruta_local_foto = os.path.join(CARPETA_FOTOS, nombre_archivo_foto)

            if descargar_archivo(url_foto, ruta_local_foto):
                # Cambiar URL remota por la ruta relativa local para el HTML
                c['fotografia'] = f"{CARPETA_FOTOS}/{nombre_archivo_foto}"
                descargadas_fotos += 1

        # Procesar Logo del Partido
        url_logo = sanear_url(c.get('logo', ''))
        if url_logo:
            ext_l = os.path.splitext(urlparse(url_logo).path)[1]
            if not ext_l or len(ext_l) > 5:
                ext_l = '.png'

            siglas = normalizar(c.get('partido_siglas') or c.get('partido') or 'partido')
            slug_logo = re.sub(r'[^A-Z0-9]+', '_', siglas).strip('_')
            nombre_archivo_logo = f"logo_{slug_logo}{ext_l}"
            ruta_local_logo = os.path.join(CARPETA_LOGOS, nombre_archivo_logo)

            if descargar_archivo(url_logo, ruta_local_logo):
                c['logo'] = f"{CARPETA_LOGOS}/{nombre_archivo_logo}"
                descargados_logos += 1

        if i % 25 == 0 or i == total:
            print(f"    Progreso: {i}/{total} candidatos procesados...")

    # Guardar candidatos.json actualizado con rutas locales
    print(f"[*] Guardando archivo actualizado en '{ARCHIVO_SALIDA}'...")
    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(candidatos_filtrados, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("PROCESO TERMINADO CON ÉXITO:")
    print(f" - Titulares guardados: {len(candidatos_filtrados)}")
    print(f" - Fotos listas en la carpeta '{CARPETA_FOTOS}/': {descargadas_fotos}")
    print(f" - Logos listos en la carpeta '{CARPETA_LOGOS}/': {descargados_logos}")
    print(f" - Archivo '{ARCHIVO_SALIDA}' actualizado con enlaces locales.")
    print("=" * 50)


if __name__ == '__main__':
    main()