**Median CER (normalized), lower is better**

| System | Printed (PATS) | Handwritten (KHATT) | Historical (HistoryAr) |
|---|---:|---:|---:|
| Qwen2.5-VL-3B (MLX) | 2.3% | 31.5% | 38.9% |
| Tesseract 5 (ara) | 2.3% | 50.0% | 100.0% |
| EasyOCR (ar) | 4.5% | 44.1% | 39.0% |

**Full results** (CER/WER as %, n = samples scored)

| System | Subset | n | CER raw (median / mean) | CER norm (median / mean) | WER norm (median / mean) | Halluc. rate | Empty output | Latency s/img (mean) | Peak mem GB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5-VL-3B (MLX) | Printed (PATS) | 100 | 3.5% / 12.2% | 2.3% / 7.2% | 7.7% / 12.3% | 1.0% | 0.0% | 3.42 | 8.25 |
| Tesseract 5 (ara) | Printed (PATS) | 100 | 3.2% / 11.6% | 2.3% / 11.0% | 9.2% / 25.8% | 0.0% | 6.0% | 0.05 | 0.06 |
| EasyOCR (ar) | Printed (PATS) | 100 | 4.8% / 7.1% | 4.5% / 6.2% | 17.2% / 23.1% | 0.0% | 0.0% | 0.63 | 6.61 |
| Qwen2.5-VL-3B (MLX) | Handwritten (KHATT) | 100 | 54.5% / 67.2% | 31.5% / 45.0% | 78.4% / 82.3% | 3.0% | 0.0% | 6.52 | 8.25 |
| Tesseract 5 (ara) | Handwritten (KHATT) | 100 | 52.5% / 60.1% | 50.0% / 58.4% | 100.0% / 106.3% | 0.0% | 23.0% | 0.05 | 0.06 |
| EasyOCR (ar) | Handwritten (KHATT) | 100 | 46.1% / 45.4% | 44.1% / 43.5% | 100.0% / 104.8% | 0.0% | 0.0% | 1.22 | 6.61 |
| Qwen2.5-VL-3B (MLX) | Historical (HistoryAr) | 100 | 66.4% / 185.0% | 38.9% / 157.5% | 86.2% / 187.3% | 10.0% | 0.0% | 6.23 | 8.25 |
| Tesseract 5 (ara) | Historical (HistoryAr) | 100 | 100.0% / 80.8% | 100.0% / 79.5% | 100.0% / 102.4% | 0.0% | 51.0% | 0.13 | 0.06 |
| EasyOCR (ar) | Historical (HistoryAr) | 100 | 49.7% / 54.0% | 39.0% / 47.0% | 100.0% / 95.5% | 0.0% | 9.0% | 0.91 | 6.61 |
