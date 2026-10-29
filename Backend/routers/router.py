import os
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse

from workflow import graph
from services.extractor import docx_text_extract

router = APIRouter()

UPLOADS_DIR = "uploads"

@router.post("/generate-report")
async def generate_report(template: UploadFile = File(...), support: UploadFile = File(...)):
    template_extracted = await docx_text_extract(template)
    support_file_extracted = await docx_text_extract(support)

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    template_path = os.path.join(UPLOADS_DIR, "template.docx")

    template_bytes = await template.read()
    with open(template_path, "wb") as f:
        f.write(template_bytes)

    await template.seek(0)

    result = graph.invoke({
        "template_structure": template_extracted,
        "supporting_text": support_file_extracted,
    })

    path = result["output_path"]

    return FileResponse(
        path=path,
        filename="report.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
