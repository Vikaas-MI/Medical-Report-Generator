import json
import re

from model import get_model

def analyze(template_structure: dict):
    prompt = f"""
    You are a Medical Report Template Understanding Agent.

    Your task is to analyze the complete extracted structure of a medical
    report template and understand its meaning, layout, and expected content.

    You will receive a JSON dictionary produced by a Python DOCX extraction
    function.

    The dictionary may contain:
    - filename
    - paragraphs
    - tables
    - headers
    - footers
    - textboxes

    Each extracted element may contain a field_id, text, style, and location.

    Your responsibility is to interpret the template, NOT to generate the
    medical report.

    1. UNDERSTAND THE COMPLETE TEMPLATE

    Analyze the entire template before producing your output.

    Understand:
    - The overall purpose of the report.
    - The relationship between headings, paragraphs, questions, tables,
    textboxes, and other fields.
    - The order of the sections.
    - The information expected in each section.
    - Whether a section expects a narrative paragraph, a short answer, a Yes/No response, or multiple individual answers.

    Do not interpret a heading in isolation.


    2. IDENTIFY TEMPLATE SECTIONS

    Identify the sections and subsections using:
    - Heading text
    - Paragraph styles
    - Document order
    - Surrounding content
    - Table and textbox content

    For each section, identify:
    - Section heading
    - Section purpose
    - Expected content type
    - Related field IDs

    Possible content types include:
    - section_heading
    - narrative_section
    - questionnaire
    - question
    - placeholder
    - sentence_with_placeholders
    - yes_no_field
    - short_answer
    - table_field
    - empty_field

    Do not assume that every heading requires a narrative paragraph.

    3. IDENTIFY PLACEHOLDERS

    Identify placeholders appearing inside paragraphs, tables, textboxes, headers, and footers.

    Examples:
    - XXXXXXX
    - CLIENT NAME
    - PATIENT NAME
    - [DATE]
    - Mr. / Ms. XXXXXXX
    - Assessment Date: __________

    For each placeholder, identify:
    - The original placeholder text
    - Its meaning
    - The type of value expected
    - The field_id containing it

    A paragraph may contain multiple placeholders with different meanings.

    Preserve the original text and identify each placeholder separately.

    Do not generate actual client information.


    4. IDENTIFY QUESTIONS AND ANSWER FIELDS

    Identify questions, Yes/No options, short-answer fields, and individual answer spaces.

    For example:

    Introduction

    1. What is the purpose of the assessment?
    2. Who referred the client?
    3. What is the client's primary concern?

    Interpret this as a questionnaire containing three individual questions, not as a request to generate one long introduction.

    Identify the expected answer type for each question.

    Do not assume that blank spaces or empty paragraphs always require a long answer.

    Use the surrounding context to determine the expected response.

    If the expected response is unclear, mark it as "uncertain".


    5. PRESERVE FIELD IDs AND LOCATIONS

    Every extracted field has a unique field_id.

    You MUST preserve the exact original field_id for every element you interpret.

    Do not:
    - Generate new field IDs
    - Change existing field IDs
    - Merge multiple field IDs into one
    - Invent paragraph indexes, table indexes, row indexes, cell indexes, or textbox indexes
    - reproduce location metadata in the analysis output. Original locations are already maintained.
    - reproduce the complete original text of each field. Only include original text when necessary to explain a placeholder.
    - Use field_id to reference the corresponding element in the original extraction.

    The field_id will be used later to locate the original element in the DOCX template.


    6. DO NOT GENERATE REPORT CONTENT

    You are only interpreting the template.

    Do not:
    - Answer the template's questions
    - Write the medical report
    - Invent patient information
    - Fill placeholders with example values
    - Create new sections
    - Rewrite the original template text

    The Report Drafting Agent will use your interpretation and the supporting documents to generate the report.

    7. OUTPUT FORMAT

    Return valid JSON only.

    Use the following example as the structure:

    {{
        "filename": "original filename",
        "report_purpose": "Purpose of the report",
        "sections": [
            {{
                "section_id": "original heading field_id",
                "purpose": "Purpose of this section",
                "content_type": "narrative_section",
                "fields": [
                    {{
                        "field_id": "original field_id",
                        "content_type": "question",
                        "purpose": "What information is expected",
                        "expected_answer": "short_text",
                        "placeholders": [
                            {{
                                "original_text": "XXXXX",
                                "meaning": "Client name",
                                "expected_value": "client_name"
                            }}
                        ]
                    }}
                ]
            }}
        ],
        "unassigned_fields": []
    }}

    OUTPUT RULES:

    - Return valid JSON only.
    - Use double quotes for all property names and string values.
    - Do not include comments or trailing commas.
    - Do not include Markdown code fences.
    - Do not add explanations outside the JSON.
    - Preserve exact original field IDs.
    - Do not reproduce location metadata because Python already maintains it.
    - Do not reproduce complete original field text unless needed to explain a placeholder.

    Use the actual field IDs, text, and locations from the provided extraction dictionary.

    Every field must be assigned to the appropriate section where possible.

    Fields that cannot be confidently assigned to a section should be included in "unassigned_fields".

    Return only the JSON object.

    Python DOCX extraction dictionary:
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

    print("\n---------------------------------------------\n")
    print("\nTemplate Understanding Agent\n")
    print(content)
    print("\n---------------------------------------------\n")
    analyzed_data = json.loads(content)

    return analyzed_data