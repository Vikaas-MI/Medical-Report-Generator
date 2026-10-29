from fastapi import APIRouter

router = APIRouter()

@router.post("/generate-report")
async def generate_report():
    return {"message": "Report generated"}