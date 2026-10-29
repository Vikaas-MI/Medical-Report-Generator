from fastapi import APIRouter, UploadFile, File

from services.report_service import generate_report

router = APIRouter()

@router.post("/generate-report")
async def generate_report(file: UploadFile = File(...)):
    result = await generate_report(file)
    return result
