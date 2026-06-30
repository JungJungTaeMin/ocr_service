# YakMap EasyOCR Service

YakMap OCR을 EasyOCR로 돌리기 위한 별도 서버입니다.

## 실행

```bash
cd easyocr-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

macOS에서 EasyOCR 모델 다운로드 중 `CERTIFICATE_VERIFY_FAILED`가 뜨면 아래 명령을 먼저 실행하세요.

```bash
"/Applications/Python 3.13/Install Certificates.command"
```

그래도 안 되면 가상환경 안에서 인증서 패키지를 다시 설치합니다.

```bash
pip install --upgrade certifi
```

## YakMap 연결

Vercel 환경변수에 아래 값을 추가합니다.

```text
EASY_OCR_API_ENDPOINT=https://배포한-easyocr-서버주소/ocr
```

YakMap의 `/api/ocr`는 `EASY_OCR_API_ENDPOINT`를 가장 먼저 호출합니다.

## 참고

EasyOCR은 PyTorch 모델을 내려받기 때문에 Vercel Node 함수 안에 직접 넣기 어렵습니다.
Render, Railway, Fly.io 같은 파이썬 서버 환경에 이 폴더를 배포해서 연결하는 방식을 사용하세요.

## Render 배포

1. Render에서 `New` → `Web Service`
2. GitHub 저장소 연결
3. Root Directory: `easyocr-service`
4. Environment: `Docker`
5. Instance Type: 테스트 목적이면 Free 선택
6. Deploy

배포 후 주소가 `https://yakmap-easyocr.onrender.com`라면 Vercel 환경변수는 아래처럼 넣습니다.

```text
EASY_OCR_API_ENDPOINT=https://yakmap-easyocr.onrender.com/ocr
```
