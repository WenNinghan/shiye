"""Isolated PaddleOCR formula worker using a JSON-lines protocol on stdout."""

import argparse
import importlib.metadata
import json
import os
import sys
import time
import traceback
from pathlib import Path


PROTOCOL = sys.stdout
sys.stdout = sys.stderr  # Keep Paddle download/progress logs away from the protocol.

if getattr(sys, "frozen", False):
    # A distributed offline model pack must never download models behind the
    # user's back. Missing assets produce an actionable error instead.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    def offline_audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise OSError("离线公式包禁止网络访问；请重新导入完整模型包")
    sys.addaudithook(offline_audit)


def emit(payload):
    PROTOCOL.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    PROTOCOL.flush()


def flatten_box(value):
    while isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], (list, tuple)):
        value = value[0]
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    return [float(v) for v in value]


def box_overlap(a, b):
    inter = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1e-6, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / min(area_a, area_b)


class Engine:
    def __init__(self, model, device):
        self.model_name = model
        self.device = device
        self.pipeline = None
        self.recognizer = None

    def load_pipeline(self):
        if self.pipeline is None:
            from paddleocr import FormulaRecognitionPipeline

            options = dict(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_layout_detection=True,
                layout_detection_model_name="PP-DocLayout_plus-L",
                formula_recognition_model_name=self.model_name,
                device=self.device,
            )
            if self.device == "cpu":
                options["enable_mkldnn"] = False
            self.pipeline = FormulaRecognitionPipeline(**options)
        return self.pipeline

    def load_recognizer(self):
        if self.recognizer is None:
            from paddleocr import FormulaRecognition

            self.recognizer = FormulaRecognition(model_name=self.model_name, device=self.device)
        return self.recognizer

    def status(self):
        cache = Path(os.environ.get("PADDLE_PDX_CACHE_HOME", Path.home() / ".paddlex"))
        return {
            "paddleocr_version": importlib.metadata.version("paddleocr"),
            "paddlepaddle_version": importlib.metadata.version("paddlepaddle"),
            "model_cached": (cache / "official_models" / self.model_name).is_dir(),
            "loaded": self.pipeline is not None or self.recognizer is not None,
        }

    def recognize(self, path, bbox):
        import numpy as np
        from PIL import Image

        with Image.open(path) as image:
            image = image.convert("RGB")
            width, height = image.size
            x0, y0, x1, y1 = bbox
            crop = np.asarray(image.crop((int(x0 * width), int(y0 * height), max(int(x0 * width) + 1, int(x1 * width)), max(int(y0 * height) + 1, int(y1 * height)))))
            started = time.monotonic()
            output = list(self.load_recognizer().predict(crop))
        latex = output[0].json["res"].get("rec_formula", "") if output else ""
        return {"latex": str(latex), "elapsed_ms": round((time.monotonic() - started) * 1000)}

    def scan(self, path, min_score):
        started = time.monotonic()
        output = list(
            self.load_pipeline().predict(
                path,
                use_layout_detection=True,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                layout_threshold=float(min_score),
            )
        )
        if not output:
            return {"formulas": [], "elapsed_ms": round((time.monotonic() - started) * 1000)}
        data = output[0].json["res"]
        detected = [
            box for box in data.get("layout_det_res", {}).get("boxes", [])
            if str(box.get("label", "")).lower() == "formula" and float(box.get("score", 0)) >= min_score
        ]
        formulas = []
        for item in data.get("formula_res_list", []):
            bbox = flatten_box(item.get("dt_polys"))
            if not bbox:
                continue
            match = max(detected, key=lambda box: box_overlap(bbox, flatten_box(box.get("coordinate")) or [0, 0, 0, 0]), default={})
            formulas.append(
                {
                    "latex": str(item.get("rec_formula", "")),
                    "bbox": bbox,
                    "confidence": float(match.get("score")) if match.get("score") is not None else None,
                }
            )
        return {"formulas": formulas, "elapsed_ms": round((time.monotonic() - started) * 1000)}


def serve(args):
    engine = Engine(args.model, args.device)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            action = request.get("action")
            if action == "status":
                result = engine.status()
            elif action == "warm":
                started = time.monotonic()
                engine.load_pipeline()
                result = {**engine.status(), "elapsed_ms": round((time.monotonic() - started) * 1000)}
            elif action == "recognize":
                path = Path(request["path"])
                bbox = [float(value) for value in request["bbox"]]
                if not path.is_file() or len(bbox) != 4 or not (0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1):
                    raise ValueError("invalid formula image or bounding box")
                result = engine.recognize(str(path), bbox)
            elif action == "scan":
                path = Path(request["path"])
                if not path.is_file():
                    raise ValueError("formula image does not exist")
                result = engine.scan(str(path), float(request.get("min_score", 0.5)))
            else:
                raise ValueError("未知公式任务")
            emit({"id": request.get("id"), "ok": True, "result": result})
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            emit({"id": request.get("id") if "request" in locals() else None, "ok": False, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--model", default="PP-FormulaNet_plus-M")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    if args.serve:
        serve(args)
    elif args.warm:
        engine = Engine(args.model, args.device)
        engine.load_pipeline()
        emit({"ok": True, "result": engine.status()})
    else:
        parser.error("use --serve or --warm")


if __name__ == "__main__":
    main()
