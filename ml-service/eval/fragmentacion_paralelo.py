"""
Estrategia: Procesar N fragmentos de 8 segundos en paralelo,
cada uno como "inicio de pieza" (ventana 1), con solape y fusión.
"""

import numpy as np
import torch
from pathlib import Path

def transcribe_fragmentado_paralelo(audio_path, 
                                     horizon_seg=8.0,  # segundos por fragmento
                                     overlap_frac=0.25, # 25% solape
                                     batch_size=4):     # fragmentos en paralelo
    """
    Divide el audio en fragmentos de horizonte fiable,
    los procesa en paralelo en GPU, y fusiona los resultados.
    
    Args:
        audio_path: ruta al MP3/WAV
        horizon_seg: duración de cada fragmento (default: 8s = 4 ventanas)
        overlap_frac: fracción de solape entre fragmentos (default: 25%)
        batch_size: cuántos fragmentos procesar simultáneamente en GPU
    """
    import librosa
    from pipeline.model_stage import RealModel
    
    # 1. Cargar audio
    y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    duracion_total = len(y) / sr
    
    # 2. Calcular parámetros de segmentación
    hop_seg = horizon_seg * (1 - overlap_frac)  # salto entre fragmentos
    hop_samples = int(hop_seg * sr)
    horizon_samples = int(horizon_seg * sr)
    
    # 3. Generar índices de fragmentos
    fragmentos = []
    for start in range(0, len(y), hop_samples):
        end = min(start + horizon_samples, len(y))
        fragmentos.append((start, end))
    
    print(f"Audio: {duracion_total:.1f}s | Fragmentos: {len(fragmentos)} | "
          f"Horizonte: {horizon_seg}s | Solape: {overlap_frac*100}%")
    
    # 4. Procesar fragmentos en batches paralelos
    model = RealModel.get().model
    todas_las_notas = []
    
    for batch_start in range(0, len(fragmentos), batch_size):
        batch_end = min(batch_start + batch_size, len(fragmentos))
        batch_frags = fragmentos[batch_start:batch_end]
        
        print(f"Procesando fragmentos {batch_start+1}-{batch_end} de {len(fragmentos)}...")
        
        # Preparar batch de audio segments
        batch_audio = []
        for start, end in batch_frags:
            seg = y[start:end]
            # Pad si es más corto que horizon_samples
            if len(seg) < horizon_samples:
                seg = np.pad(seg, (0, horizon_samples - len(seg)))
            batch_audio.append(seg)
        
        batch_tensor = torch.from_numpy(
            np.stack(batch_audio).astype(np.float32)
        ).unsqueeze(1).to(model.device)  # (batch, 1, samples)
        
        # Inferencia paralela: cada fragmento como "inicio de pieza"
        with torch.no_grad():
            # inference_file procesa cada elemento del batch independientemente
            preds_list, _ = model.inference_file(bsz=batch_size, audio_segments=batch_tensor)
        
        # Decodificar cada fragmento del batch
        for i, (start_sample, end_sample) in enumerate(batch_frags):
            t0_seg = start_sample / sr  # tiempo absoluto del fragmento
            
            # preds_list[i] tiene shape (n_ventanas_en_fragmento, n_canales, seq_len)
            preds_frag = preds_list[i]
            
            notas_frag = decode_fragmento(preds_frag, t0_seg)
            todas_las_notas.extend(notas_frag)
    
    # 5. Fusionar notas duplicadas en zonas de solape
    notas_finales = fusionar_notas_solape(todas_las_notas, overlap_seg=horizon_seg*overlap_frac)
    
    print(f"Notas totales: {len(todas_las_notas)} -> {len(notas_finales)} (post-fusión)")
    return notas_finales


def decode_fragmento(preds_frag, t0_seg):
    """Decodifica las predicciones de un fragmento y las desplaza a tiempo absoluto."""
    from pipeline.model_stage import RealModel
    model = RealModel.get().model
    
    notas = []
    SEG_SEC = 2.048
    
    # preds_frag es una lista de arrays, uno por ventana
    for i, pred in enumerate(preds_frag):
        t0_ventana = t0_seg + i * SEG_SEC
        
        # Decodificar cada canal
        for c in range(pred.shape[0]):
            tok = [int(t) for t in pred[c]]
            out = model.task_manager.detokenize(tok)
            note_events, tie_events = out[0], out[1]
            
            # Desplazar a tiempo absoluto
            for ev in list(note_events) + list(tie_events):
                if hasattr(ev, 'onset') and ev.onset is not None:
                    ev.onset += t0_ventana
                if hasattr(ev, 'offset') and ev.offset is not None:
                    ev.offset += t0_ventana
            
            # Convertir a notas
            try:
                from utils.event2note import note_event2note
                seg_notes, _ = note_event2note(note_events, tie_events)
                notas.extend(seg_notes)
            except:
                continue
    
    return notas


def fusionar_notas_solape(notas, overlap_seg, delta_merge=0.05):
    """
    Elimina duplicados en zonas de solape y fusiona notas cortadas.
    
    Criterios:
    - Duplicado: mismo pitch y |onset_A - onset_B| < 50ms
    - Fusión: mismo pitch y (offset_A - onset_B) < delta_merge
    """
    if not notas:
        return notas
    
    notas.sort(key=lambda n: n.onset)
    fusionadas = [notas[0]]
    
    for nota in notas[1:]:
        prev = fusionadas[-1]
        
        # ¿Es duplicado en solape?
        if (nota.pitch == prev.pitch and 
            abs(nota.onset - prev.onset) < 0.05):
            # Conservar la de mayor duración
            if (nota.offset - nota.onset) > (prev.offset - prev.onset):
                fusionadas[-1] = nota
            continue
        
        # ¿Es nota cortada que debe fusionarse?
        if (nota.pitch == prev.pitch and 
            (nota.onset - prev.offset) < delta_merge):
            prev.offset = max(prev.offset, nota.offset)
            continue
        
        fusionadas.append(nota)
    
    return fusionadas