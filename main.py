import base64
import io
import os

import certifi
import easyocr
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel


class OcrRequest(BaseModel):
    image: str


app = FastAPI(title="YakMap EasyOCR")
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
reader = easyocr.Reader(["ko", "en"], gpu=os.getenv("EASYOCR_GPU", "false").lower() == "true")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def decode_image(image: str) -> Image.Image:
    if "," in image:
        image = image.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image)
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image.") from exc


@app.get("/")
def root():
    return {"status": "ok", "service": "yakmap-easyocr"}


@app.post("/ocr")
def extract_text(payload: OcrRequest):
    image = decode_image(payload.image)
    results = reader.readtext(image)
    items = [
        {
            "text": text,
            "confidence": confidence,
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
