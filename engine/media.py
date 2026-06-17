# engine/media.py
"""
Extraction pour IMAGES et VIDEOS, avant envoi a l'IA.
Image : OCR (Tesseract) si texte, sinon description vision (llava via Ollama).
Video : transcription (faster-whisper) + descriptions d'images cles (llava).
Degradation gracieuse + diagnostics detailles.
"""
import base64
import io
import os
import shutil

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    import pillow_avif  # support AVIF (si installe)
except ImportError:
    pass

try:
    from PIL import Image
    import pytesseract
    _HAS_OCR = True
except ImportError:
    _HAS_OCR = False

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

try:
    from faster_whisper import WhisperModel
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False

OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "llava"          # ou "llama3.2-vision"
WHISPER_SIZE = "base"           # "medium" = plus precis, plus lent
OCR_MIN_CHARS = 20
MAX_KEYFRAMES = 3

# --- Resolution du binaire Tesseract (independant du PATH) -------------------
if _HAS_OCR:
    _tess = shutil.which("tesseract")
    if not _tess:
        for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                     r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
            if os.path.exists(cand):
                _tess = cand
                break
    if _tess:
        pytesseract.pytesseract.tesseract_cmd = _tess


# --- Vision (llava via Ollama) ---------------------------------------------
def _describe_image_b64(b64, prompt="Decris cette image en detail, en francais."):
    if not _HAS_REQUESTS:
        return None, "requests manquant"
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": VISION_MODEL, "prompt": prompt,
            "images": [b64], "stream": False,
        }, timeout=180)
        if r.status_code != 200:
            # Ollama met la vraie raison dans le corps
            try:
                detail = r.json().get("error", r.text[:300])
            except Exception:
                detail = r.text[:300]
            return None, f"{r.status_code} - {detail}"
        return r.json().get("response", "").strip(), None
    except requests.exceptions.ConnectionError:
        return None, "Ollama injoignable (ollama serve)"
    except Exception as e:
        return None, str(e)


def _to_jpeg_b64(path):
    """Convertit toute image lisible par Pillow en JPEG base64 (format sur)."""
    if not _HAS_OCR:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode(), None
    try:
        img = Image.open(path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode(), None
    except Exception as e:
        return None, str(e)


# --- OCR --------------------------------------------------------------------
def _ocr(path):
    if not _HAS_OCR:
        return None, "pytesseract/Pillow manquant"
    try:
        img = Image.open(path)
        try:
            txt = pytesseract.image_to_string(img, lang="fra+eng")
        except Exception:
            txt = pytesseract.image_to_string(img)
        return txt.strip(), None
    except pytesseract.TesseractNotFoundError:
        return None, "Binaire Tesseract introuvable (installe-le + PATH)"
    except Exception as e:
        return None, str(e)


def extract_image(path):
    warnings = []
    text, err = _ocr(path)
    if err:
        warnings.append(f"OCR indisponible : {err}")
    if text and len(text) >= OCR_MIN_CHARS:
        return text, "image-ocr", warnings

    b64, conv_err = _to_jpeg_b64(path)
    if b64:
        desc, err2 = _describe_image_b64(b64)
        if desc:
            return desc, "image-vision", warnings
        if err2:
            warnings.append(f"Vision indisponible : {err2}")
    elif conv_err:
        warnings.append(f"Image illisible : {conv_err}")

    if text:
        return text, "image-ocr", warnings
    return "", "image-failed", warnings


# --- Video ------------------------------------------------------------------
def _transcribe(path):
    if not _HAS_WHISPER:
        return None, "faster-whisper manquant"
    try:
        model = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(path)
        return " ".join(s.text for s in segments).strip(), None
    except Exception as e:
        return None, str(e)


def _keyframe_descriptions(path, n=MAX_KEYFRAMES):
    if not _HAS_CV2:
        return [], "opencv manquant"
    descs = []
    try:
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        if total <= 0:
            cap.release()
            return [], "video illisible"
        idxs = [int(total * i / (n + 1)) for i in range(1, n + 1)]
        for k, idx in enumerate(idxs):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            ok2, buf = cv2.imencode(".jpg", frame)
            if not ok2:
                continue
            b64 = base64.b64encode(buf.tobytes()).decode()
            desc, _ = _describe_image_b64(
                b64, prompt="Decris brievement cette scene, en francais.")
            if desc:
                descs.append(f"[{k+1}] {desc}")
        cap.release()
        return descs, None
    except Exception as e:
        return descs, str(e)


def extract_video(path):
    warnings, parts = [], []
    transcript, err = _transcribe(path)
    if transcript:
        parts.append("TRANSCRIPTION AUDIO :\n" + transcript)
    elif err:
        warnings.append(f"Transcription indisponible : {err}")
    frames, err2 = _keyframe_descriptions(path)
    if frames:
        parts.append("SCENES CLES :\n" + "\n".join(frames))
    elif err2:
        warnings.append(f"Images cles indisponibles : {err2}")
    text = "\n\n".join(parts).strip()
    return text, ("video" if text else "video-failed"), warnings


if __name__ == "__main__":
    print("Dependances detectees :")
    print(f"  OCR (pytesseract/PIL) : {_HAS_OCR}")
    if _HAS_OCR:
        print(f"  Binaire Tesseract     : {pytesseract.pytesseract.tesseract_cmd}")
    print(f"  OpenCV (images cles)  : {_HAS_CV2}")
    print(f"  faster-whisper        : {_HAS_WHISPER}")
    print(f"  requests (vision)     : {_HAS_REQUESTS}")
