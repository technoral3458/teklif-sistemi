import os
import base64
import uuid
from PIL import Image
import streamlit as st
from config import IMAGES_DIR, ALLOWED_IMAGE_TYPES, MAX_IMAGE_MB


def save_uploaded_image(uploaded_file, prefix: str = "img") -> str | None:
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_TYPES:
        st.error(f"Desteklenmeyen format: {ext}")
        return None
    if uploaded_file.size > MAX_IMAGE_MB * 1024 * 1024:
        st.error(f"Görsel {MAX_IMAGE_MB}MB'dan büyük olamaz.")
        return None
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(IMAGES_DIR, filename)
    try:
        img = Image.open(uploaded_file)
        img.thumbnail((1200, 1200), Image.LANCZOS)
        img.save(path, optimize=True, quality=85)
        return path
    except Exception as e:
        st.error(f"Görsel kaydedilemedi: {e}")
        return None


def get_image_base64(path: str) -> str:
    if not path:
        return ""
    if str(path).startswith("http"):
        return path
    candidates = [path, os.path.join(IMAGES_DIR, os.path.basename(path))]
    for p in candidates:
        if os.path.isfile(p):
            try:
                ext = os.path.splitext(p)[1].lstrip(".").lower()
                if ext == "jpg":
                    ext = "jpeg"
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f"data:image/{ext};base64,{b64}"
            except Exception:
                pass
    return ""


def image_tag(path: str, width: int = 120, css_class: str = "") -> str:
    src = get_image_base64(path)
    if not src:
        return ""
    cls = f' class="{css_class}"' if css_class else ""
    return f'<img src="{src}" width="{width}"{cls} style="border-radius:6px;object-fit:contain;">'


def delete_image(path: str):
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass
