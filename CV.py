import json
import re

ARCHIVO_CANDIDATOS = "candidatos.json"
ARCHIVO_HISTORIAL = "historial_partidos.json"

# Partidos con presencia histórica formal en Sinaloa
PARTIDOS_DETECTABLES = {
    "PRI": ["PRI", "REVOLUCIONARIO INSTITUCIONAL"],
    "PAN": ["PAN", "ACCION NACIONAL", "ACCIÓN NACIONAL"],
    "PRD": ["PRD", "REVOLUCION DEMOCRATICA", "REVOLUCIÓN DEMOCRÁTICA"],
    "MORENA": ["MORENA", "MOVIMIENTO REGENERACION NACIONAL", "MOVIMIENTO REGENERACIÓN NACIONAL"],
    "PAS": ["PAS", "PARTIDO SINALOENSE"],
    "MC": ["MC", "MOVIMIENTO CIUDADANO"],
    "PT": ["PT", "PARTIDO DEL TRABAJO"],
    "PVEM": ["PVEM", "VERDE ECOLOGISTA", "PARTIDO VERDE"]
}

def extraer_anios(texto):
    """Extrae años de 4 dígitos entre 1980 y 2026."""
    return re.findall(r"\b(19[89]\d|20[0-2]\d)\b", texto)

def analizar():
    try:
        with open(ARCHIVO_CANDIDATOS, "r", encoding="utf-8") as f:
            candidatos = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró '{ARCHIVO_CANDIDATOS}'.")
        return

    historial_generado = {}

    for c in candidatos:
        c_id = str(c.get("id"))
        nombre = c.get("nombre_propietario", "")
        partido_actual = (c.get("partido_siglas") or c.get("partido") or "").upper()
        
        # Analizamos EXCLUSIVAMENTE lo que el candidato escribió en su registro oficial
        texto_cv = f"{c.get('trayectoria', '')} {c.get('historia_profesional', '')}".upper()
        
        eventos = []
        partidos_previos = set()

        # Detección estricta dentro del texto del CV
        for siglas, variantes in PARTIDOS_DETECTABLES.items():
            # Si el partido no forma parte de su postulación o coalición actual
            if siglas not in partido_actual:
                for variante in variantes:
                    patron = rf"\b{re.escape(variante)}\b"
                    coincidencia = re.search(patron, texto_cv)
                    if coincidencia:
                        inicio = max(0, coincidencia.start() - 35)
                        fin = min(len(texto_cv), coincidencia.end() + 35)
                        fragmento = texto_cv[inicio:fin]
                        anios = extraer_anios(fragmento)
                        periodo = f"Aprox. {anios[0]}" if anios else "Mención en CV"

                        partidos_previos.add(siglas)
                        eventos.append({
                            "partido": siglas,
                            "periodo": periodo,
                            "nota": f"Mención en CV oficial: \"...{fragmento.strip()}...\""
                        })
                        break

        # Postulación actual ante el IEES
        eventos.append({
            "partido": c.get("partido_siglas") or c.get("partido") or "Actual",
            "periodo": "Elección Actual",
            "nota": "Postulación oficial registrada en el IEES"
        })

        historial_generado[c_id] = {
            "nombre": nombre,
            "total_cambios": len(partidos_previos),
            "historial": eventos
        }

    # Sobrescribir limpiamente el archivo
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial_generado, f, ensure_ascii=False, indent=2)

    total_con_cambios = sum(1 for v in historial_generado.values() if v["total_cambios"] > 0)
    print("=" * 60)
    print("Revisión exclusiva de CV finalizada con éxito.")
    print(f"Total de registros analizados: {len(historial_generado)}")
    print(f"Candidatos con mención explícita a otro partido en su CV: {total_con_cambios}")
    print(f"Archivo guardado: '{ARCHIVO_HISTORIAL}'")
    print("=" * 60)

if __name__ == "__main__":
    analizar()