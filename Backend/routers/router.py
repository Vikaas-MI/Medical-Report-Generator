import os

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse

from workflow import graph
from services.extractor import extract_template

router = APIRouter()

UPLOADS_DIR = "uploads"


async def _save_upload(file: UploadFile, destination: str) -> None:
    content = await file.read()
    with open(destination, "wb") as f:
        f.write(content)


@router.post("/generate-report")
async def generate_report(template: UploadFile = File(...), support: UploadFile = File(...)):
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Save both uploads to the uploads directory first.
    template_path = os.path.join(UPLOADS_DIR, "template.docx")
    support_path = os.path.join(UPLOADS_DIR, "support.docx")

    await _save_upload(template, template_path)
    await _save_upload(support, support_path)

    template_extracted = extract_template(template_path)
    support_file_extracted = extract_template(support_path)

    print(template_extracted)

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
