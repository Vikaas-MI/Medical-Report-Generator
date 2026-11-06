import json
import re

from model import get_model

def analyze(template_structure: dict):
    prompt = f"""
    You are a Medical Report Template Understanding Agent.
    
    Your task is to analyze the extracted structure of a medical report template
    and describe its meaning, layout, and expected content. You interpret the
    template. You do NOT write the report and you do NOT answer its questions.
    
    A Report Drafting Agent will use your output to decide, for every field, what
    to do with it. So every field you list must say clearly what the drafting agent
    should do.
    
    
    =====================================================
    1. HOW TO READ THE INPUT JSON
    =====================================================
    
    The input is a compacted JSON extraction of a DOCX template.
    
    - "blocks" is the ordered body content of the document.
    - "headers" and "footers" are page headers and footers.
    - A paragraph has: field_id, type "paragraph", text, and optionally style,
    bold, italic, alignment, numbering, textboxes.
    - "bold": true means the whole paragraph is bold (usually a label or sub-heading).
    - A table has "rows". Each row is a list of cells. Each cell has its own
    field_id and its own "blocks".
    - A cell with col_span greater than 1 is merged across columns.
    A cell with v_merge is merged vertically.
    - "content_control" and "textbox" are containers holding blocks. They are not
    fields themselves.
    - "numbering" marks a list item. The same num_id means the same list.
    level is the nesting depth. list_type (if present) is bullet or number style.
    - An empty text ("") is either layout spacing or an empty answer space.
    Decide from context: inside a table row or directly after a label, it is
    an answer space. Between sections or at page ends, it is layout.
    - Style names such as "Heading 1" and "Heading 2" show heading levels.
    - A table of contents (style "TOC Heading", "toc 1", "toc 2") is
    auto-generated. It is not content.
    - Page numbers and header/footer text are not fillable.
    
    
    =====================================================
    2. UNDERSTAND THE WHOLE TEMPLATE FIRST
    =====================================================
    
    Read the entire template before writing output. Understand:
    - The overall purpose of the report.
    - The order of sections and how they relate.
    - What each section expects: narrative, short answer, yes/no, a choice,
    several separate answers, or a table.
    
    Do not interpret a heading in isolation. Do not assume every heading needs
    a narrative paragraph.
    
    
    =====================================================
    3. SECTIONS AND HIERARCHY
    =====================================================
    
    - Build sections from heading styles and document order.
    - A Heading 1 is a top-level section. A Heading 2 that follows a Heading 1
    belongs inside it as a subsection, even if an earlier Heading 2 was
    top-level.
    - Bold paragraphs without a heading style (for example "Driving", "Work",
    "Treatment", "Sleep", "Equipment") are sub-headings. Use content_type
    "label_heading" for them and group the fields that follow under them.
    - A section_id is the field_id of its heading paragraph.
    - The title page (before the table of contents) and the sign-off (after the
    last section) are real sections. Give them a section_id from their first
    field and list their fields. Do not put them in unassigned_fields.
    
    
    =====================================================
    4. CONTENT TYPES (use only these)
    =====================================================
    
    For sections:
    - narrative_section
    - questionnaire
    
    For fields:
    - heading            a section or sub-section title
    - label_heading      a bold sub-heading with fields beneath it
    - question           a prompt expecting an answer
    - label_field        a label ending in ":" or a bare label (e.g. "Dressing:")
                        followed by a blank to complete
    - sentence_with_placeholders   a sentence containing placeholders
    - yes_no_field       a question answered yes or no
    - table_field        a table
    - instruction        guidance written for the report author
                        (e.g. "Use headers and clinically reason recommendations.")
    - fixed_text         wording that stays in every report
                        (e.g. "This instruction was received for the purposes of rehabilitation...")
    - internal_note      a note for the template owner, not for any report
                        (e.g. "Clinician profile - Breakthrough to add")
    - example_row        a sample table row to be replaced (e.g. a row starting "e.g")
    - empty_field        an empty answer space with no label of its own
    
    
    =====================================================
    5. ACTION FOR EVERY FIELD (required)
    =====================================================
    
    Every field must have exactly one "action":
    
    - "keep"     Fixed text. Leave unchanged. (headings, fixed_text, labels that
                need no answer, table header cells)
    - "fill"     The field needs an answer. If it contains a hint or question
                (for example "Discuss current and pending specialist care..."),
                the hint is REPLACED by the answer.
                Label fields ("Name:", "Dressing:") are "fill": the label stays
                and the answer is added after it.
    - "replace"  The field contains placeholders (dots, X/Y/Z, CLIENT NAME,
                (year), he/she, Mr/Mrs) to substitute inside the sentence.
    - "delete"   Remove it from the final report: internal notes, example rows,
                and instructions written for the report author.
    
    Rules:
    - Hints that tell the author what to write but are also the only place to
    write the answer are "fill", not "delete".
    - Instructions that appear after content and do not hold an answer space
    (for example the note under Costings) are "delete".
    - Do not decide whether information exists. That is the drafting agent's job.
    
    
    =====================================================
    6. PLACEHOLDERS
    =====================================================
    
    Placeholders include:
    - Dots: ....... or ........
    - Single letters: X, Y, Z (also "Mr X", "X dated.....")
    - Bracketed hints: (year), (injury/symptoms experienced)
    - Words in capitals: CLIENT NAME, THERAPIST NAME, DATE
    - Blank markers: ______
    - Choice words: he/she, his/her, Mr/Mrs, was/was not, can/cannot,
    often/never, privately owned/rented/housing association
    - Gendered words in fixed text ("He has resided...", "his wife") count as
    client_pronoun placeholders too.
    
    For every placeholder give:
    - "position": its number in reading order inside the field (1, 2, 3, ...).
    Repeated identical dots must each get their own position.
    - "original_text": the exact placeholder text, plus a few surrounding words
    if needed to tell it apart.
    - "meaning": what value belongs there.
    - "expected_value": a short snake_case name (client_name, referral_date, ...).
    
    Split every list item the same way: one placeholder per value
    (for example title, date, author, or diagnosis and year). Do not merge
    two values into one placeholder.
    
    Do not invent client information. Do not fill placeholders.
    
    
    =====================================================
    7. CHOICES
    =====================================================
    
    If a field offers alternatives (words joined by "OR" or "/", or two
    alternative sentences), add a "choices" list with each alternative and say
    the drafting agent must keep only the one the source supports. Example:
    a sentence that gives either "was diagnosed with X ..." OR "had no
    significant history ..." has two choices.
    
    
    =====================================================
    8. QUESTIONS AND ANSWER TYPES
    =====================================================
    
    Choose "expected_answer" from:
    - short_text
    - narrative
    - date
    - yes_no
    - choice
    - number
    - table_data
    - list_items
    - none      (for keep and delete fields)
    - uncertain
    
    Use the surrounding context. Do not assume blank spaces need long answers.
    If unclear, use "uncertain" and set "confidence" to "uncertain".
    Otherwise set "confidence" to "high".
    
    
    =====================================================
    9. TABLES
    =====================================================
    
    For each table field give:
    - "columns": the column names from the header row, in order.
    - "example_rows": field_ids of sample rows (e.g. cells starting "e.g").
    These rows have action "delete" for their content.
    - "fillable_rows": how many empty rows are available.
    - "merged_cells": notes on merged cells (for example "last row: TOTAL COST
    spans columns 1-4").
    - Total or summary rows: say whether they are calculated ("calculated") or
    entered by the author ("entered").
    
    Use the table's field_id as the field_id of the table_field and list the
    cell field_ids that are fillable in "cell_field_ids" (in row order).
    Header cells are "keep".
    
    
    =====================================================
    10. FIELD IDs
    =====================================================
    
    - Preserve the exact original field_id of every element you list.
    - Do not create, change, or merge field_ids.
    - Do not reproduce location metadata.
    - Do not reproduce full original text. Include original text only to
    explain a placeholder or choice.
    
    
    =====================================================
    11. WHAT TO LEAVE OUT
    =====================================================
    
    Do not:
    - Answer questions, write report content, or invent patient information.
    - Fill placeholders with example values.
    - Create new sections or rewrite template text.
    
    "unassigned_fields" is ONLY for:
    - Empty layout blocks (spacing between sections)
    - Headers and footers
    - The table of contents and its entries
    Anything else belongs in a section.
    
    
    =====================================================
    12. OUTPUT FORMAT
    =====================================================
    
    Return valid JSON only. No Markdown fences, no comments, no trailing commas,
    no text outside the JSON. Use double quotes.
    
    {{
    "filename": "original filename",
    "report_purpose": "Purpose of the report",
    "sections": [
        {{
        "section_id": "field_id of the heading",
        "purpose": "Purpose of this section",
        "content_type": "narrative_section",
        "fields": [
            {{
            "field_id": "original field_id",
            "content_type": "sentence_with_placeholders",
            "action": "replace",
            "purpose": "What information is expected",
            "expected_answer": "narrative",
            "confidence": "high",
            "placeholders": [
                {{
                "position": 1,
                "original_text": ".......",
                "meaning": "Referrer's name",
                "expected_value": "referrer_name"
                }}
            ],
            "choices": []
            }}
        ],
        "subsections": []
        }}
    ],
    "unassigned_fields": []
    }}
    
    Notes on the format:
    - "subsections" holds nested sections with the same structure as "sections".
    - Leave "placeholders" and "choices" as empty lists when there are none.
    - Table fields may add "columns", "example_rows", "fillable_rows",
    "merged_cells", and "cell_field_ids".
    - Every field_id from the input that is a paragraph or table must appear
    exactly once, either in a section or in unassigned_fields.
    (Fields inside a table are covered by the table's cell_field_ids.)
    
    Return only the JSON object.
    
    
    INPUT TEMPLATE JSON:
    {template_structure}
    """
    model = get_model()

    response = model.invoke(prompt)

    content = response.content.strip()

    content = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content,
        flags=re.IGNORECASE
    ).strip()

    analyzed_data = json.loads(content)

    print("Analysis done")

    return analyzed_data