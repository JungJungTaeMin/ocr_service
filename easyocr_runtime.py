import json
import math
import os

import numpy as np
from PIL import Image, ImageOps


class EasyOcrRuntime:
    def __init__(self):
        import torch

        torch.set_grad_enabled(False)
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.backends.mkldnn.enabled = False

        model_path = os.getenv("EASYOCR_RUNTIME_MODEL", "/app/korean_easyocr.pt")
        config_path = os.getenv("EASYOCR_RUNTIME_CONFIG", "/app/korean_easyocr.json")

        with open(config_path, encoding="utf-8") as config_file:
            self.characters = ["[blank]"] + list(json.load(config_file)["characters"])

        self.torch = torch
        self.model = torch.jit.load(model_path, map_location="cpu").eval()

    def _prepare_line(self, image):
        torch = self.torch
        source = image.convert("L") if isinstance(image, Image.Image) else Image.fromarray(image).convert("L")
        width, height = source.size
        target_height = 64
        target_width = max(16, min(1200, math.ceil(target_height * width / max(1, height))))
        resized = source.resize((target_width, target_height), Image.Resampling.BICUBIC)
        pixels = np.asarray(resized, dtype=np.float32)
        pixels = (pixels / 255.0 - 0.5) / 0.5
        return torch.from_numpy(pixels).unsqueeze(0).unsqueeze(0)

    def _decode(self, predictions):
        probabilities = predictions.softmax(2)
        confidence_by_step, indices = probabilities.max(2)
        indices = indices[0].cpu().tolist()
        confidence_by_step = confidence_by_step[0].cpu().tolist()
        decoded = []
        selected_confidences = []
        previous = None

        for index, confidence in zip(indices, confidence_by_step):
            if index != 0 and index != previous and index < len(self.characters):
                decoded.append(self.characters[index])
                selected_confidences.append(max(float(confidence), 1e-8))
            previous = index

        if not selected_confidences:
            return "", 0.0

        confidence = math.exp(
            sum(math.log(value) for value in selected_confidences)
            / len(selected_confidences)
        )
        return "".join(decoded).strip(), confidence

    def recognize(self, gray_image: np.ndarray, boxes: list[list[int]]):
        torch = self.torch
        results = []

        for left, right, top, bottom in boxes:
            line_image = gray_image[top:bottom, left:right]

            if line_image.size == 0:
                continue

            tensor = self._prepare_line(ImageOps.autocontrast(Image.fromarray(line_image)))
            dummy_text = torch.zeros((1, max(1, tensor.shape[-1] // 10 + 1)), dtype=torch.long)

            with torch.inference_mode():
                predictions = self.model(tensor, dummy_text)

            text, confidence = self._decode(predictions)

            if text:
                results.append(([left, right, top, bottom], text, confidence))

        return results
