from pathlib import Path
import os

from docx import Document
from docx.oxml.ns import qn


BASE_DIR = Path(__file__).resolve().parent.parent


def _build_field_locations(template_structure: dict) -> dict:
    """Map every field_id in the extracted template to its location.

    The extractor produces paragraphs, tables, headers, footers, and
    textboxes. The draft may populate any of these, so every field_id must
    be locatable here.
    """
    field_locations = {}

    # Main document paragraphs
    for paragraph in template_structure.get("paragraphs", []):
        field_locations[paragraph["field_id"]] = paragraph["location"]

    # Main document tables
    for table in template_structure.get("tables", []):
        for row in table.get("rows", []):
            for cell in row:
                field_locations[cell["field_id"]] = cell["location"]

    # Header / footer paragraphs
    for part_name in ("headers", "footers"):
        for part in template_structure.get(part_name, []):
            section_index = part.get("section", 0)
            for paragraph in part.get("paragraphs", []):
                field_locations[paragraph["field_id"]] = {
                    "type": "header_footer_paragraph",
                    "part": part_name[:-1],  # "header" / "footer"
                    "section": section_index,
                }

    # Textboxes (document, headers, footers)
    for textbox in template_structure.get("textboxes", []):
        field_locations[textbox["field_id"]] = textbox["location"]

    return field_locations


def _set_paragraph_text(paragraph, content: str) -> None:
    """Replace a paragraph's text in place while preserving its first run.

    The draft returns the complete, placeholder-resolved text for a field,
    so the original text is overwritten rather than appended to.
    """
    if paragraph.runs:
        paragraph.runs[0].text = content
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(content)


def _iter_textbox_paragraphs(xml_part, textbox_index: int):
    """Yield the <w:p> elements of a specific textbox within an xml part."""
    for index, textbox in enumerate(xml_part.iter(qn("w:txbxContent"))):
        if index == textbox_index:
            return list(textbox.iter(qn("w:p")))
    return []


def populate_template(data: dict, template_structure: dict):
    template_path = BASE_DIR / "uploads" / "template.docx"
    output_path = BASE_DIR / "reports" / "report.docx"

    document = Document(template_path)

    field_locations = _build_field_locations(template_structure)

    for field_id, content in data.items():
        if field_id not in field_locations:
            # The draft is LLM-generated; skip unknown field IDs rather than
            # aborting the whole report.
            continue

        location = field_locations[field_id]
        location_type = location.get("type")

        if location_type == "paragraph":
            paragraph = document.paragraphs[location["index"]]
            _set_paragraph_text(paragraph, content)

        elif location_type == "table_cell":
            table = document.tables[location["table"]]
            cell = table.rows[location["row"]].cells[location["cell"]]
            cell.text = content

        elif location_type == "header_footer_paragraph":
            section = document.sections[location["section"]]
            part = (
                section.header
                if location["part"] == "header"
                else section.footer
            )
            # field_id format: "{part}_{section}_paragraph_{index}"
            paragraph_index = int(field_id.rsplit("_", 1)[-1])
            if 0 <= paragraph_index < len(part.paragraphs):
                _set_paragraph_text(part.paragraphs[paragraph_index], content)

        elif location_type == "textbox":
            xml_part = _resolve_textbox_part(document, location.get("part"))
            if xml_part is None:
                continue

            paragraphs = _iter_textbox_paragraphs(
                xml_part, location["textbox_index"]
            )
            _set_textbox_text(paragraphs, content)

    os.makedirs(output_path.parent, exist_ok=True)
    document.save(output_path)

    return str(output_path)


def _resolve_textbox_part(document, part: str | None):
    """Return the xml element that contains a textbox for the given part."""
    if not part or part == "document":
        return document.element.body

    if part.startswith("header_section_"):
        section_index = int(part.rsplit("_", 1)[-1])
        return document.sections[section_index].header._element

    if part.startswith("footer_section_"):
        section_index = int(part.rsplit("_", 1)[-1])
        return document.sections[section_index].footer._element

    return None


def _set_textbox_text(paragraphs, content: str) -> None:
    """Write content into the first paragraph of a textbox, clearing the rest."""
    if not paragraphs:
        return

    lines = content.split("\n")

    for para_index, paragraph in enumerate(paragraphs):
        text_nodes = list(paragraph.iter(qn("w:t")))
        line = lines[para_index] if para_index < len(lines) else ""

        if text_nodes:
            text_nodes[0].text = line
            for node in text_nodes[1:]:
                node.text = ""
