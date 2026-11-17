import time

import easyocr


def order_rtl(results):
    """Group EasyOCR boxes into lines (top to bottom), then order each line right to left."""
    boxes = []
    for bbox, text, _conf in results:
        xs, ys = [p[0] for p in bbox], [p[1] for p in bbox]
        boxes.append({"x": (min(xs) + max(xs)) / 2, "y": (min(ys) + max(ys)) / 2,
                      "h": max(ys) - min(ys), "text": text})
    boxes.sort(key=lambda b: b["y"])
    lines = []
    for b in boxes:
        if lines and abs(b["y"] - lines[-1][-1]["y"]) < 0.5 * max(b["h"], lines[-1][-1]["h"]):
            lines[-1].append(b)
        else:
            lines.append([b])
    return "\n".join(" ".join(b["text"] for b in sorted(line, key=lambda b: -b["x"])) for line in lines)


class Runner:
    def __init__(self, sys_cfg, cfg):
        self.reader = easyocr.Reader([sys_cfg.get("lang", "ar")], gpu=sys_cfg.get("gpu", False), verbose=False)

    def predict(self, image_path):
        start = time.perf_counter()
        results = self.reader.readtext(image_path, detail=1)
        return {"text": order_rtl(results), "latency_s": time.perf_counter() - start}
