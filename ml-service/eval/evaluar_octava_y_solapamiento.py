"""
evaluar_octava_y_solapamiento.py
Evalúa específicamente errores de octava y duplicados en solapamiento.
"""
import os
import sys
import json
from music21 import converter, note
import numpy as np

def extraer_notas(ruta_xml):
    """Extrae notas de un MusicXML."""
    try:
        score = converter.parse(ruta_xml)
        notas = []
        for n in score.flatten().notes:
            if isinstance(n, note.Note):
                notas.append({
                    'pitch': int(n.pitch.midi),
                    'octave': int(n.pitch.midi) // 12 - 1,
                    'onset': float(n.offset),
                    'offset': float(n.offset + n.duration.quarterLength),
                    'nombre': n.pitch.nameWithOctave
                })
        return sorted(notas, key=lambda x: x['onset'])
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def detectar_duplicados_solapamiento(notas, umbral=0.307):
    """Detecta notas duplicadas en zonas de solapamiento."""
    duplicados = []
    for i, nota in enumerate(notas):
        for j in range(i+1, len(notas)):
            otra = notas[j]
            time_diff = abs(nota['onset'] - otra['onset'])
            if time_diff < umbral and nota['pitch'] == otra['pitch']:
                duplicados.append({
                    'nota1': nota['nombre'],
                    'nota2': otra['nombre'],
                    'time_diff': time_diff,
                    'onset1': nota['onset'],
                    'onset2': otra['onset']
                })
    return duplicados

def detectar_errores_octava(notas_ref, notas_gen, tolerancia=0.05):
    """Detecta notas con error de octava."""
    errores_octava = []
    for ref in notas_ref:
        for gen in notas_gen:
            if abs(ref['onset'] - gen['onset']) < tolerancia:
                diff_octavas = abs(ref['octave'] - gen['octave'])
                if diff_octavas > 0:
                    errores_octava.append({
                        'ref': ref['nombre'],
                        'gen': gen['nombre'],
                        'diff_octavas': diff_octavas,
                        'onset': ref['onset']
                    })
    return errores_octava

def main():
    if len(sys.argv) < 3:
        print("Uso: python evaluar_octava_y_solapamiento.py <ref.xml> <gen.xml>")
        sys.exit(1)

    ruta_ref = sys.argv[1]
    ruta_gen = sys.argv[2]

    print("="*70)
    print("🔍 EVALUACIÓN DE OCTAVA Y SOLAPAMIENTO")
    print("="*70)

    notas_ref = extraer_notas(ruta_ref)
    notas_gen = extraer_notas(ruta_gen)

    print(f"\n📄 Notas en Referencia: {len(notas_ref)}")
    print(f"🤖 Notas Generadas: {len(notas_gen)}")

    # Detectar duplicados
    duplicados = detectar_duplicados_solapamiento(notas_gen)
    print(f"\n⚠️  Notas duplicadas en solapamiento: {len(duplicados)}")
    if duplicados:
        print("   Ejemplos:")
        for d in duplicados[:5]:
            print(f"   - {d['nota1']} y {d['nota2']} (diff: {d['time_diff']:.3f}s)")

    # Detectar errores de octava
    errores_octava = detectar_errores_octava(notas_ref, notas_gen)
    print(f"\n🎵 Errores de octava: {len(errores_octava)}")
    if errores_octava:
        print("   Ejemplos:")
        for e in errores_octava[:5]:
            print(f"   - Ref: {e['ref']} → Gen: {e['gen']} (diff: {e['diff_octavas']} octavas)")

    # Guardar resultados
    resultados = {
        'archivo_referencia': os.path.basename(ruta_ref),
        'archivo_generado': os.path.basename(ruta_gen),
        'notas_referencia': len(notas_ref),
        'notas_generadas': len(notas_gen),
        'duplicados_solapamiento': len(duplicados),
        'errores_octava': len(errores_octava),
        'ejemplos_duplicados': duplicados[:10],
        'ejemplos_octava': errores_octava[:10]
    }

    with open('resultados_octava_solapamiento.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados guardados en 'resultados_octava_solapamiento.json'")
    print("="*70)

if __name__ == "__main__":
    main()