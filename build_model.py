import json
import os

import easyocr
import torch


def main():
    reader = easyocr.Reader(
        ["ko", "en"],
        gpu=False,
        detector=False,
        verbose=False,
    )
    model = reader.recognizer.eval()
    example_image = torch.zeros((1, 1, 64, 320), dtype=torch.float32)
    example_text = torch.zeros((1, 33), dtype=torch.long)

    with torch.inference_mode():
        traced_model = torch.jit.trace(
            model,
            (example_image, example_text),
            strict=False,
        )
        traced_model = torch.jit.freeze(traced_model)

    torch.jit.save(traced_model, os.getenv("EASYOCR_RUNTIME_MODEL", "/app/korean_easyocr.pt"))

    with open(
        os.getenv("EASYOCR_RUNTIME_CONFIG", "/app/korean_easyocr.json"),
        "w",
        encoding="utf-8",
    ) as config_file:
        json.dump({"characters": reader.character}, config_file, ensure_ascii=False)


if __name__ == "__main__":
    main()
