# eval/exp_midwindow.py
import sys, torch, numpy as np, librosa
from pathlib import Path
ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML)); sys.path.insert(0, str(ML / "models" / "amt" / "src"))
import settings as config
from utils.audio import slice_padded_array
from pipeline.model_stage import RealModel

model = RealModel.get().model
tm = model.task_manager
SEG = config.MODEL_AUDIO["window"]

y, sr = librosa.load(str(ML / "storage/tests/v1/andersen-24-etudes-op15-no5.mp3"), sr=16000, mono=True)
x = np.clip(y / (np.max(np.abs(y)) + 1e-8), -1, 1) * 0.95
segs = slice_padded_array(x.reshape(1, -1), SEG, SEG, pad=True).astype(np.float32)

@torch.no_grad()
def decode_one(idx):
    t = torch.from_numpy(segs[idx:idx+1]).unsqueeze(1).to(config.DEVICE)
    preds = model.inference(t, None)
    arr = preds.detach().cpu().numpy()          # (1, C, L)
    total_ev = 0
    for c in range(arr.shape[1]):
        tok = [int(v) for v in arr[0, c]]
        out = tm.detokenize(tok)                # (note_events, tie_events, ...)
        total_ev += len(out[0])
    return idx, total_ev, [int(v) for v in arr[0, 0]][:12]

for i in (0, 2, 10, 30, 50):
    idx, n_ev, head = decode_one(i)
    print(f"ventana {idx:02d} (llamada fresca): eventos={n_ev} tokens={head}")