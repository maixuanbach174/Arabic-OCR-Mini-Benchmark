import subprocess
import time


class Runner:
    def __init__(self, sys_cfg, cfg):
        self.args = ["-l", sys_cfg.get("lang", "ara"), "--psm", str(sys_cfg.get("psm", 7))]
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()
        if sys_cfg.get("lang", "ara") not in langs:
            raise RuntimeError("Tesseract 'ara' traineddata missing: brew install tesseract-lang")

    def predict(self, image_path):
        start = time.perf_counter()
        out = subprocess.run(["tesseract", image_path, "stdout", *self.args],
                             capture_output=True, text=True, check=True).stdout
        return {"text": " ".join(out.split()), "latency_s": time.perf_counter() - start}
