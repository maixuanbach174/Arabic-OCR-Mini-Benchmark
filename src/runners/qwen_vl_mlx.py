import re
import tempfile
import time
from pathlib import Path

import mlx.core as mx
from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template
from PIL import Image

FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def clean_output(text):
    """Strip markdown code fences the model sometimes wraps its answer in."""
    return FENCE.sub("", text.strip()).strip()


class Runner:
    def __init__(self, sys_cfg, cfg):
        self.max_new_tokens = sys_cfg["max_new_tokens"]
        self.max_pixels = sys_cfg.get("max_pixels")
        self.model, self.processor = load(sys_cfg["model_id"])
        self.prompt = apply_chat_template(self.processor, self.model.config, cfg["prompt"], num_images=1)
        self._tmp = tempfile.TemporaryDirectory()

    def _maybe_resize(self, image_path):
        img = Image.open(image_path)
        w, h = img.size
        if not self.max_pixels or w * h <= self.max_pixels:
            return image_path
        scale = (self.max_pixels / (w * h)) ** 0.5
        out = Path(self._tmp.name) / Path(image_path).name
        img.convert("RGB").resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS).save(out)
        return str(out)

    def predict(self, image_path):
        start = time.perf_counter()
        result = generate(self.model, self.processor, self.prompt, image=[self._maybe_resize(image_path)],
                          max_tokens=self.max_new_tokens, temperature=0.0, verbose=False)
        latency = time.perf_counter() - start
        return {"text": clean_output(result.text), "raw_output": result.text, "latency_s": latency,
                "generation_tokens": result.generation_tokens, "finish_reason": result.finish_reason}

    def peak_accelerator_gb(self):
        return mx.get_peak_memory() / 1e9
