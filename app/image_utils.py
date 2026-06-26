import base64
import io 
from fastapi import UploadFile, HTTPException
from PIL import Image

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
MAX_SIZE_BYTES = 4 * 1024 * 1024
MAX_WIDTH = 800

def compress_image(contents: bytes) -> bytes:
    img = Image.open(io.BytesIO(contents))

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((MAX_WIDTH, new_height), Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=78, optimize=True)
    return output.getvalue()

async def validate_and_encode_image(file: UploadFile) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: jpeg, jpg, png, gif, webp"
        )
    
    contents = await file.read()

    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds 4MB limit")
    
    compressed = compress_image(contents)
    encoded = base64.b64encode(compressed).decode("utf-8")

    return f"data:image/jpeg;base64,{encoded}"