"""Validación de GPU — Harmonic Score (mitigación R06/R07)."""
import torch

def main():
    print("=" * 60)
    print("VALIDACION GPU - HARMONIC SCORE")
    print("=" * 60)
    print("PyTorch:", torch.__version__)
    print("CUDA runtime:", torch.version.cuda)
    print("CUDA disponible:", torch.cuda.is_available())

    if not torch.cuda.is_available():
        print("=> Sin GPU: modo CPU (viable para Ciclo 1)")
        return

    props = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info(0)

    print("GPU:", props.name)
    print("VRAM total: %.1f GB" % (props.total_memory / 1024 ** 3))
    print("VRAM libre: %.1f GB" % (free / 1024 ** 3))
    print("Compute capability: %d.%d" % (props.major, props.minor))

    # Prueba de cómputo real en GPU
    x = torch.randn(2048, 2048, device="cuda")
    y = (x @ x).sum()
    torch.cuda.synchronize()
    print("Matmul en GPU OK:", float(y))
    print("=" * 60)

if __name__ == "__main__":
    main()
    