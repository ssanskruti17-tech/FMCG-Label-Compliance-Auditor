from fastapi import APIRouter, UploadFile, File
from typing import Optional
from api.models.response_models import ParsedProductResponse
from api.services.ocr_service import process_images

router = APIRouter(prefix="/ocr", tags=["OCR Extraction"])

@router.post("/extract", response_model=ParsedProductResponse)
async def extract_product_data(
    front_image: Optional[UploadFile] = File(default=None),
    back_image: Optional[UploadFile] = File(default=None)
):
    front_bytes = None
    if front_image:
        front_bytes = await front_image.read()
        
    back_bytes = None
    if back_image:
        back_bytes = await back_image.read()
        
    product_data = process_images(front_bytes, back_bytes)
    return product_data
