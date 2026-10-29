from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse

from workflow import graph
from services.extractor import docx_text_extract

router = APIRouter()

@router.post("/generate-report")
async def generate_report(template: UploadFile = File(...), support: UploadFile = File(...)):
    template_extracted = await docx_text_extract(template)
    support_file_extracted = await docx_text_extract(support)

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
