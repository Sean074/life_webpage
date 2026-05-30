import io
import random
from pathlib import Path

from PIL import Image, ImageOps

from app.models import gallery as gallery_model

IMAGES_ROOT = Path(__file__).parent.parent.parent / "data" / "images"
THUMB_SIZE = (400, 400)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
CATEGORIES = ["drawings", "paintings", "photography"]
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_DIMENSION = 10_000


def image_url(category: str, filename: str) -> str:
    return f"/art/{category}/{filename}"


def thumb_url(category: str, filename: str) -> str:
    return f"/art/thumbs/{category}/{filename}"


_TRANSPOSE = {
    90: Image.Transpose.ROTATE_270,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_90,
}


def _make_thumb(src_path: Path, thumb_path: Path, rotation: int = 0):
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize(THUMB_SIZE, Image.LANCZOS)
        if rotation in _TRANSPOSE:
            img = img.transpose(_TRANSPOSE[rotation])
        img.save(thumb_path, quality=85, optimize=True)


def save_image(file_bytes: bytes, original_filename: str, category: str, title: str) -> int:
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")

    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB limit.")

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img_width, img_height = img.size
            fmt = img.format
            img = ImageOps.exif_transpose(img)
            buf = io.BytesIO()
            save_kwargs: dict = {"format": fmt}
            if fmt in ("JPEG", "WEBP"):
                save_kwargs["quality"] = 95
            img.save(buf, **save_kwargs)
            clean_bytes = buf.getvalue()
    except Exception:
        raise ValueError("File is not a valid image.")

    if img_width > MAX_IMAGE_DIMENSION or img_height > MAX_IMAGE_DIMENSION:
        raise ValueError(f"Image dimensions must not exceed {MAX_IMAGE_DIMENSION} px per side.")

    cat_dir = IMAGES_ROOT / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(original_filename).stem
    safe_stem = "".join(c if c.isalnum() or c in "-_." else "_" for c in stem)
    filename = f"{safe_stem}{ext}"

    dest = cat_dir / filename
    counter = 1
    while dest.exists():
        filename = f"{safe_stem}_{counter}{ext}"
        dest = cat_dir / filename
        counter += 1

    dest.write_bytes(clean_bytes)

    thumb_path = IMAGES_ROOT / "thumbs" / category / filename
    _make_thumb(dest, thumb_path)

    return gallery_model.insert_image(category, filename, title.strip())


def get_all_images() -> list[dict]:
    images = gallery_model.get_all_images()
    for img in images:
        img["url"] = image_url(img["category"], img["filename"])
        img["thumb"] = thumb_url(img["category"], img["filename"])
    return images


def get_images_by_category(category: str) -> list[dict]:
    images = gallery_model.get_images_by_category(category)
    for img in images:
        img["url"] = image_url(img["category"], img["filename"])
        img["thumb"] = thumb_url(img["category"], img["filename"])
    return images


def rotate_image(image_id: int, direction: str):
    img = gallery_model.get_image(image_id)
    if not img:
        return
    delta = 90 if direction == "cw" else -90
    new_rotation = (img.get("rotation", 0) + delta) % 360
    gallery_model.update_rotation(image_id, new_rotation)
    src = IMAGES_ROOT / img["category"] / img["filename"]
    thumb = IMAGES_ROOT / "thumbs" / img["category"] / img["filename"]
    if src.exists():
        _make_thumb(src, thumb, rotation=new_rotation)


def remove_image(image_id: int):
    img = gallery_model.get_image(image_id)
    if not img:
        return
    src = IMAGES_ROOT / img["category"] / img["filename"]
    thumb = IMAGES_ROOT / "thumbs" / img["category"] / img["filename"]
    if src.exists():
        src.unlink()
    if thumb.exists():
        thumb.unlink()
    gallery_model.delete_image(image_id)


def random_gallery_thumbs(n: int = 3) -> list[dict]:
    images = get_all_images()
    return random.sample(images, min(n, len(images)))


def generate_missing_thumbs():
    for img in gallery_model.get_all_images():
        src = IMAGES_ROOT / img["category"] / img["filename"]
        thumb = IMAGES_ROOT / "thumbs" / img["category"] / img["filename"]
        if src.exists() and not thumb.exists():
            _make_thumb(src, thumb)
