from pathlib import Path
import os

from docx import Document
from docx.oxml.ns import qn


BASE_DIR = Path(__file__).resolve().parent.parent


class _ElementMapper:
    """Re-walk the document the same way the extractor did and map every
    field_id to the live XML element it refers to.

    The extractor (services/extractor.py) assigns field_ids using three shared
    counters (block, table, textbox) that are incremented in document-traversal
    order. To stay in sync, this mapper mirrors that exact traversal order over
    the same ``Document`` so the generated field_ids match one-for-one.
    """

    def __init__(self):
        self.counters = {"block": 0, "table": 0, "textbox": 0}
        # field_id -> {"kind": ..., "element": <xml>}
        self.paragraphs = {}   # block_{n}       -> <w:p>
        self.cells = {}        # table_{t}_row_{r}_cell_{c} -> <w:tc>
        self.textboxes = {}    # textbox_{n}     -> <w:txbxContent>

    def _next(self, kind):
        index = self.counters[kind]
        self.counters[kind] += 1
        return index

    def walk_container(self, container):
        for element in container:
            tag = element.tag

            if tag == qn("w:p"):
                self._walk_paragraph(element)

            elif tag == qn("w:tbl"):
                self._walk_table(element)

            elif tag == qn("w:sdt"):
                sdt_content = element.find(qn("w:sdtContent"))
                if sdt_content is not None:
                    self.walk_container(sdt_content)

            elif tag == qn("w:customXml"):
                self.walk_container(element)

    def _walk_paragraph(self, element):
        # Matches extract_paragraph: assign a block id, then walk inline
        # content (which may contain textboxes) in the same order.
        block_index = self._next("block")
        self.paragraphs[f"block_{block_index}"] = element
        self._walk_inline(element)

    def _walk_inline(self, element):
        # Mirrors extract_inline_content: only textboxes consume a counter.
        def walk_inline(node):
            if node.tag == qn("w:txbxContent"):
                textbox_index = self._next("textbox")
                self.textboxes[f"textbox_{textbox_index}"] = node
                # Mirror extract_textbox -> walk_container: the textbox's
                # inner paragraphs/tables consume block/table counters too.
                self.walk_container(node)
                return
            if node.tag in {qn("w:pPr"), qn("w:rPr")}:
                return
            for child in node:
                walk_inline(child)

        for child in element:
            walk_inline(child)

    def _walk_table(self, element):
        table_index = self._next("table")
        table_id = f"table_{table_index}"

        table_rows = [c for c in element if c.tag == qn("w:tr")]
        for row_index, row in enumerate(table_rows):
            table_cells = [c for c in row if c.tag == qn("w:tc")]
            for cell_index, cell in enumerate(table_cells):
                field_id = (
                    f"{table_id}_row_{row_index}_cell_{cell_index}"
                )
                self.cells[field_id] = cell
                # Recurse so nested blocks/tables/textboxes keep counter sync.
                self.walk_container(cell)

    def build(self, document):
        # 1. Main document body (extract_template order)
        self.walk_container(document.element.body)

        # 2. Headers and footers (extract_headers_footers order)
        for section in document.sections:
            parts = [
                section.header,
                section.footer,
                section.first_page_header,
                section.first_page_footer,
                section.even_page_header,
                section.even_page_footer,
            ]
            for part in parts:
                self.walk_container(part._element)

        return self


def _set_paragraph_element_text(paragraph_element, content: str) -> None:
    """Write ``content`` into a <w:p> element, preserving its first run's
    formatting and clearing any remaining runs/text."""
    runs = paragraph_element.findall(qn("w:r"))

    if runs:
        text_nodes = runs[0].findall(qn("w:t"))
        if text_nodes:
            text_nodes[0].text = content
            text_nodes[0].set(qn("xml:space"), "preserve")
            for node in text_nodes[1:]:
                node.text = ""
        else:
            _append_text_run(runs[0], content)
        # Clear text in all remaining runs.
        for run in runs[1:]:
            for node in run.findall(qn("w:t")):
                node.text = ""
    else:
        new_run = paragraph_element.makeelement(qn("w:r"), {})
        paragraph_element.append(new_run)
        _append_text_run(new_run, content)


def _append_text_run(run_element, content: str) -> None:
    text_node = run_element.makeelement(qn("w:t"), {})
    text_node.set(qn("xml:space"), "preserve")
    text_node.text = content
    run_element.append(text_node)


def _set_cell_text(cell_element, content: str) -> None:
    """Write ``content`` into the first paragraph of a table cell, clearing
    any additional paragraphs."""
    paragraphs = cell_element.findall(qn("w:p"))

    if not paragraphs:
        new_p = cell_element.makeelement(qn("w:p"), {})
        cell_element.append(new_p)
        paragraphs = [new_p]

    _set_paragraph_element_text(paragraphs[0], content)
    for extra in paragraphs[1:]:
        for run in extra.findall(qn("w:r")):
            for node in run.findall(qn("w:t")):
                node.text = ""


def _set_textbox_text(textbox_element, content: str) -> None:
    """Write ``content`` into a textbox, one line per paragraph."""
    paragraphs = list(textbox_element.iter(qn("w:p")))
    if not paragraphs:
        return

    lines = content.split("\n")
    for para_index, paragraph in enumerate(paragraphs):
        line = lines[para_index] if para_index < len(lines) else ""
        _set_paragraph_element_text(paragraph, line)


def populate_template(data: dict, template_structure: dict | None = None):
    """Populate the template with drafted content keyed by field_id.

    ``template_structure`` is accepted for backwards compatibility with the
    workflow but is no longer required: field locations are resolved by
    re-walking the live document so they always match the extractor's IDs.
    """
    template_path = BASE_DIR / "uploads" / "template.docx"
    output_path = BASE_DIR / "reports" / "report.docx"

    document = Document(template_path)

    mapper = _ElementMapper().build(document)

    for field_id, content in data.items():
        if content is None:
            continue
        content = str(content)

        if field_id in mapper.paragraphs:
            _set_paragraph_element_text(mapper.paragraphs[field_id], content)
        elif field_id in mapper.cells:
            _set_cell_text(mapper.cells[field_id], content)
        elif field_id in mapper.textboxes:
            _set_textbox_text(mapper.textboxes[field_id], content)
        # Unknown field_ids (LLM may emit stray keys) are skipped silently.

    os.makedirs(output_path.parent, exist_ok=True)
    document.save(output_path)

    return str(output_path)
