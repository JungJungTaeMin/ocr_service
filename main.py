import base64
import io
import os
from functools import lru_cache

import certifi
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps
from pydantic import BaseModel


class OcrRequest(BaseModel):
    image: str


app = FastAPI(title="YakMap EasyOCR")
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_reader():
    import easyocr

    return easyocr.Reader(
        ["ko", "en"],
        gpu=os.getenv("EASYOCR_GPU", "false").lower() == "true",
        detector=False,
        verbose=False,
    )


def decode_image(image: str) -> Image.Image:
    if "," in image:
        image = image.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image)
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image.") from exc


def prepare_image(image: Image.Image) -> Image.Image:
    max_side = 1600

    if max(image.size) <= max_side:
        return image

    resized = image.copy()
    resized.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return resized


def find_text_lines(image: Image.Image) -> list[list[int]]:
    gray = ImageOps.autocontrast(image.convert("L"))
    width, height = gray.size
    pixels = gray.load()
    minimum_dark_pixels = max(3, width // 200)
    active_rows = []

    for y in range(height):
        dark_pixels = sum(1 for x in range(width) if pixels[x, y] < 205)
        active_rows.append(dark_pixels >= minimum_dark_pixels)

    raw_lines = []
    start = None

    for y, is_active in enumerate(active_rows + [False]):
        if is_active and start is None:
            start = y
        elif not is_active and start is not None:
            if y - start >= 6:
                raw_lines.append([start, y])
            start = None

    merged_lines = []
    max_gap = max(6, height // 150)

    for top, bottom in raw_lines:
        if merged_lines and top - merged_lines[-1][1] <= max_gap:
            merged_lines[-1][1] = bottom
        else:
            merged_lines.append([top, bottom])

    margin = max(5, height // 200)
    boxes = [
        [0, width, max(0, top - margin), min(height, bottom + margin)]
        for top, bottom in merged_lines
        if bottom - top >= 8
    ]

    return boxes[:40] or [[0, width, 0, height]]


@app.get("/")
def root():
    return {"status": "ok", "service": "yakmap-easyocr"}


@app.post("/ocr")
def extract_text(payload: OcrRequest):
    import numpy as np

    image = prepare_image(decode_image(payload.image))
    gray_image = np.asarray(image.convert("L"))
    text_lines = find_text_lines(image)
    reader = get_reader()
    results = reader.recognize(
        gray_image,
        horizontal_list=text_lines,
        free_list=[],
        batch_size=1,
        workers=0,
        detail=1,
        reformat=False,
    )
    items = [
        {
            "text": text,
            "confidence": float(confidence),
        }
        for _, text, confidence in results
    ]
    text = "\n".join(item["text"] for item in items)

    return {
        "medicineName": "",
        "text": text,
        "results": items,
        "source": "easyocr",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
