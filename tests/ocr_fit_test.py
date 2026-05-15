import torch
import sys

def run_test():
    print("--- Hardware Fit Test ---")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    
    if cuda_available:
        try:
            device_props = torch.cuda.get_device_properties(0)
            vram_gb = device_props.total_memory / 1e9
            print(f"GPU: {device_props.name}")
            print(f"VRAM: {vram_gb:.2f} GB")
            
            if vram_gb < 8:
                print("WARNING: VRAM is less than 8GB. Heavy models may fail.")
            else:
                print("VRAM is sufficient for most 7B models (quantized) and specialized OCR.")
        except Exception as e:
            print(f"Error getting GPU properties: {e}")
    else:
        print("No CUDA device found. Falling back to CPU for OCR.")

if __name__ == "__main__":
    run_test()
