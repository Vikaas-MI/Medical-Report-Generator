from pathlib import Path
from docx import Document
from docx.oxml.ns import qn


def _paragraph_text(paragraph):
    return paragraph.text.strip()

def _extract_textboxes(xml_part, part_name):
        """Extract text from text boxes in a document part's XML."""
        textboxes = []

        for textbox_index, textbox in enumerate(
            xml_part.iter(qn("w:txbxContent"))
        ):
            paragraphs = []

            for paragraph in textbox.iter(qn("w:p")):
                text = "".join(
                    node.text or ""
                    for node in paragraph.iter(qn("w:t"))
                ).strip()

                if text:
                    paragraphs.append(text)

            if paragraphs:
                textboxes.append({
                    "field_id": f"{part_name}_textbox_{textbox_index}",
                    "text": "\n".join(paragraphs),
                    "location": {
                        "type": "textbox",
                        "part": part_name,
                        "textbox_index": textbox_index,
                    },
                })

        return textboxes


def extract_template(file_path: str | Path) -> dict:
        document = Document(file_path)

        result = {
            "filename": Path(file_path).name,
            "paragraphs": [],
            "tables": [],
            "headers": [],
            "footers": [],
            "textboxes": [],
        }

        # Main document paragraphs
        for index, paragraph in enumerate(document.paragraphs):
            text = _paragraph_text(paragraph)

            if text:
                result["paragraphs"].append({
                    "field_id": f"paragraph_{index}",
                    "text": text,
                    "style": paragraph.style.name,
                    "location": {
                        "type": "paragraph",
                        "index": index,
                    },
                })

        # Tables in the main document
        for table_index, table in enumerate(document.tables):
            table_data = {
                "table_id": f"table_{table_index}",
                "rows": [],
            }

            for row_index, row in enumerate(table.rows):
                row_data = []

                for cell_index, cell in enumerate(row.cells):
                    row_data.append({
                        "field_id": (
                            f"table_{table_index}_row_{row_index}_cell_{cell_index}"
                        ),
                        "text": cell.text.strip(),
                        "location": {
                            "type": "table_cell",
                            "table": table_index,
                            "row": row_index,
                            "cell": cell_index,
                        },
                    })

                table_data["rows"].append(row_data)

            result["tables"].append(table_data)

        # Headers and footers, including their paragraphs and tables
        for section_index, section in enumerate(document.sections):
            for part_name, part in (
                ("header", section.header),
                ("footer", section.footer),
            ):
                part_data = {
                    "section": section_index,
                    "paragraphs": [],
                    "tables": [],
                }

                for paragraph_index, paragraph in enumerate(part.paragraphs):
                    text = _paragraph_text(paragraph)

                    if text:
                        part_data["paragraphs"].append({
                            "field_id": (
                                f"{part_name}_{section_index}_paragraph_{paragraph_index}"
                            ),
                            "text": text,
                        })

                for table_index, table in enumerate(part.tables):
                    rows = []

                    for row_index, row in enumerate(table.rows):
                        rows.append([
                            cell.text.strip()
                            for cell in row.cells
                        ])

                    part_data["tables"].append({
                        "table_index": table_index,
                        "rows": rows,
                    })

                result[f"{part_name}s"].append(part_data)

        # Text boxes in the main document, headers, and footers
        result["textboxes"].extend(
            _extract_textboxes(document.element.body, "document")
        )

        for section_index, section in enumerate(document.sections):
            result["textboxes"].extend(
                _extract_textboxes(
                    section.header._element,
                    f"header_section_{section_index}",
                )
            )
            result["textboxes"].extend(
                _extract_textboxes(
                    section.footer._element,
                    f"footer_section_{section_index}",
                )
            )

        return result



    