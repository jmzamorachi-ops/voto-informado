import os
import json
import urllib.request

# Endpoint estático del IEES alojado en CloudFront / S3
URL_CANDIDATOS = "https://conoceles-sinaloa.mx/jsons/CANDIDATOS.json"
ARCHIVO_SALIDA = "candidatos.json"

def descargar_candidatos():
    print(f"Descargando datos desde {URL_CANDIDATOS}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(URL_CANDIDATOS, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            contenido = response.read().decode("utf-8")
            data = json.loads(contenido)
            
            with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            print(f"Descarga exitosa. Se guardaron {len(data)} registros en '{ARCHIVO_SALIDA}'.")
    except Exception as e:
        print(f"Error al descargar los datos: {e}")

if __name__ == "__main__":
    descargar_candidatos()