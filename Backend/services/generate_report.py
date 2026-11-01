import os
from pathlib import Path
from docx import Document

BASE_DIR = Path(__file__).resolve().parent.parent

def populate_template(data: dict):

    print("Before template path")
    #template_path = "uploads/template.docx"
    template_path = BASE_DIR / "uploads" / "template.docx"
    print("After template path")
    output_path = os.path.join("reports", "report.docx")
    document = Document(template_path)
    print("After template path 2")
    print("Template path:", template_path)
    print("File exists:", template_path.exists())

    for i, paragraph in enumerate(document.paragraphs):
        heading = paragraph.text.strip()

        if heading in data:
            content = data[heading]

            for next_paragraph in document.paragraphs[i + 1:]:
                if next_paragraph.text.strip() in data:
                    next_paragraph.insert_paragraph_before(content)
                    break
            else:
                document.add_paragraph(content)

    document.save(output_path)
    return output_path