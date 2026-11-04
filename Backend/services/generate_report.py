from docx import Document
from pathlib import Path
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def populate_template(data: dict, template_structure: dict):

    template_path = BASE_DIR / "uploads" / "template.docx"
    output_path = BASE_DIR / "reports" / "report.docx"

    document = Document(template_path)

    # Create a lookup dictionary using field IDs
    field_locations = {}

    for paragraph in template_structure["paragraphs"]:
        field_locations[paragraph["field_id"]] = paragraph["location"]

    for table in template_structure["tables"]:
        for row in table["rows"]:
            for cell in row:
                field_locations[cell["field_id"]] = cell["location"]

    # Populate the fields returned by the LLM
    for field_id, content in data.items():

        if field_id not in field_locations:
            raise ValueError(f"Unknown field ID: {field_id}")

        location = field_locations[field_id]

        if location["type"] == "paragraph":

            paragraph = document.paragraphs[location["index"]]

            new_paragraph = OxmlElement("w:p")
            paragraph._p.addnext(new_paragraph)

            new_para = Paragraph(new_paragraph, paragraph._parent)
            new_para.add_run(content)

        elif location["type"] == "table_cell":

            table = document.tables[location["table"]]

            cell = table.rows[location["row"]].cells[location["cell"]]

            cell.text = content

    # Ensure the output directory exists
    os.makedirs(output_path.parent, exist_ok=True)

    document.save(output_path)

    return str(output_path)