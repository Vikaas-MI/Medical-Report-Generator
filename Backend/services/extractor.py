
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph



class ExtractionContext:

    def __init__(self, document):
        self.document = document

        self.counters = {
            "block": 0,
            "table": 0,
            "textbox": 0,
        }

    def next_id(self, element_type):
        index = self.counters[element_type]
        self.counters[element_type] += 1

        return index


def get_formatting(paragraph):

    runs = []

    for run in paragraph.runs:
        runs.append({
            "text": run.text,
            "bold": run.bold,
            "italic": run.italic,
            "underline": run.underline,
            "font_name": run.font.name,
            "font_size": (
                run.font.size.pt if run.font.size else None
            ),
        })

    return {
        "style": paragraph.style.name if paragraph.style else None,
        "alignment": (
            str(paragraph.alignment)
            if paragraph.alignment is not None else None
        ),
        "runs": runs,
    }



def get_numbering(element):

    p_pr = element.find(qn("w:pPr"))

    if p_pr is None:
        return None

    num_pr = p_pr.find(qn("w:numPr"))

    if num_pr is None:
        return None

    num_id = num_pr.find(qn("w:numId"))
    ilvl = num_pr.find(qn("w:ilvl"))

    return {
        "num_id": (
            num_id.get(qn("w:val")) if num_id is not None else None
        ),
        "level": (
            ilvl.get(qn("w:val")) if ilvl is not None else None
        ),
    }



def extract_textbox(element, location, context):

    textbox_index = context.next_id("textbox")

    textbox_location = {
        **location,
        "textbox_index": textbox_index,
    }

    return {
        "field_id": f"textbox_{textbox_index}",
        "type": "textbox",
        "location": textbox_location,
        "blocks": walk_container(
            element,
            textbox_location,
            context,
        ),
    }



def extract_inline_content(element, location, context):

    content = []

    def walk_inline(node):

        tag = node.tag

        # Normal text
        if tag == qn("w:t"):
            if node.text:
                content.append({
                    "type": "text",
                    "text": node.text,
                })
            return

        # Tab
        if tag == qn("w:tab"):
            content.append({
                "type": "tab",
            })
            return

        # Line, page or column break
        if tag == qn("w:br"):

            break_type = node.get(qn("w:type"), "textWrapping")

            if break_type == "page":
                element_type = "page_break"
            elif break_type == "column":
                element_type = "column_break"
            else:
                element_type = "line_break"

            content.append({
                "type": element_type,
            })
            return

        # Rendered page break
        if tag == qn("w:lastRenderedPageBreak"):
            content.append({
                "type": "page_break",
            })
            return

        # Textbox inside paragraph
        if tag == qn("w:txbxContent"):

            content.append(
                extract_textbox(
                    node,
                    location,
                    context,
                )
            )
            return

        # Ignore formatting properties
        if tag in {
            qn("w:pPr"),
            qn("w:rPr"),
        }:
            return

        # Continue checking nested elements
        for child in node:
            walk_inline(child)

    for child in element:
        walk_inline(child)

    return content



def extract_paragraph(element, location, context):

    paragraph = Paragraph(
        element,
        context.document,
    )

    block_index = context.next_id("block")

    field_id = f"block_{block_index}"

    content = extract_inline_content(
        element,
        location,
        context,
    )

    p_pr = element.find(qn("w:pPr"))

    has_section_break = (
        p_pr is not None
        and p_pr.find(qn("w:sectPr")) is not None
    )

    return {
        "field_id": field_id,
        "type": "paragraph",
        "text": paragraph.text.strip(),
        "content": content,
        "location": location,
        "formatting": get_formatting(paragraph),
        "numbering": get_numbering(element),
        "section_break_after": has_section_break,
    }


def extract_table(element, location, context):

    table_index = context.next_id("table")

    table_id = f"table_{table_index}"

    rows = []

    # Direct table rows only
    table_rows = [
        child for child in element
        if child.tag == qn("w:tr")
    ]

    for row_index, row in enumerate(table_rows):

        cells = []

        # Direct cells only
        table_cells = [
            child for child in row
            if child.tag == qn("w:tc")
        ]

        for cell_index, cell in enumerate(table_cells):

            cell_location = {
                **location,
                "row": row_index,
                "cell": cell_index,
            }

            cells.append({
                "field_id": (
                    f"{table_id}_row_{row_index}_cell_{cell_index}"
                ),
                "type": "table_cell",
                "location": cell_location,
                "blocks": walk_container(
                    cell,
                    cell_location,
                    context,
                ),
            })

        rows.append(cells)

    return {
        "field_id": table_id,
        "type": "table",
        "location": location,
        "rows": rows,
    }


# ==================================================
# 8. UNIFIED RECURSIVE EXTRACTION LOOP
# ==================================================

def walk_container(container, parent_location, context):

    blocks = []

    for index, element in enumerate(container):

        location = {
            **parent_location,
            "block_index": index,
        }

        # Paragraph
        if element.tag == qn("w:p"):

            blocks.append(
                extract_paragraph(
                    element,
                    location,
                    context,
                )
            )

        # Table
        elif element.tag == qn("w:tbl"):

            blocks.append(
                extract_table(
                    element,
                    location,
                    context,
                )
            )

        # Content controls
        elif element.tag == qn("w:sdt"):

            sdt_content = element.find(qn("w:sdtContent"))

            if sdt_content is not None:

                blocks.append({
                    "field_id": f"content_control_{index}",
                    "type": "content_control",
                    "location": location,
                    "blocks": walk_container(
                        sdt_content,
                        location,
                        context,
                    ),
                })

        # Custom XML wrapper
        elif element.tag == qn("w:customXml"):

            blocks.extend(
                walk_container(
                    element,
                    location,
                    context,
                )
            )

    return blocks


def extract_headers_footers(document, context):

    headers = []
    footers = []

    for section_index, section in enumerate(document.sections):

        parts = [
            ("header", section.header),
            ("footer", section.footer),
            ("first_page_header", section.first_page_header),
            ("first_page_footer", section.first_page_footer),
            ("even_page_header", section.even_page_header),
            ("even_page_footer", section.even_page_footer),
        ]

        for part_name, part in parts:

            part_location = {
                "part": part_name,
                "section": section_index,
            }

            part_blocks = walk_container(
                part._element,
                part_location,
                context,
            )

            part_data = {
                "section": section_index,
                "blocks": part_blocks,
                "is_linked_to_previous": part.is_linked_to_previous,
            }

            if "header" in part_name:
                headers.append({
                    "type": part_name,
                    **part_data,
                })
            else:
                footers.append({
                    "type": part_name,
                    **part_data,
                })

    return headers, footers



def extract_template(file_path: str | Path) -> dict:

    document = Document(file_path)

    context = ExtractionContext(document)

    # Main document
    blocks = walk_container(
        document.element.body,
        {"part": "document"},
        context,
    )

    # Headers and footers
    headers, footers = extract_headers_footers(
        document,
        context,
    )

    # Sections
    sections = []

    for index, section in enumerate(document.sections):

        sections.append({
            "section_index": index,
            "start_type": str(section.start_type),
            "different_first_page": (
                section.different_first_page_header_footer
            ),
        })

    return {
        "filename": Path(file_path).name,
        "blocks": blocks,
        "headers": headers,
        "footers": footers,
        "sections": sections,
    }
