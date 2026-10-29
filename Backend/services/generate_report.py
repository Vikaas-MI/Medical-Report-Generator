from docx import Document

def populate_template(data: dict, template_path: str, output_path: str):
    document = Document(template_path)

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