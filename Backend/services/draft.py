import json
import re

from model import get_model

def create_draft(data: dict, analyzed_data: dict, template: dict, validation: dict = None):
    revision_section = ""
    if validation:
        revision_section = f"""
        PREVIOUS VALIDATION FEEDBACK:
        A previous draft was reviewed and did not pass validation. Address every
        issue below. Correct the listed problems and incorporate the missing
        information where it is supported by the source data. Do not introduce
        facts that are not present in the source.

        {validation}
        """

    prompt = f"""
    You are a medical report drafting assistant.

    Read and understand the source medical data, the original template structure, and the analysed template carefully, then fill each answer field of the template using only what the source directly states.

    SOURCE MEDICAL DATA:
    {data}

    UPLOADED TEMPLATE STRUCTURE (ORIGINAL EXTRACTION):
    {template}

    ANALYSED TEMPLATE (TEMPLATE UNDERSTANDING AGENT OUTPUT):
    {analyzed_data}

    {revision_section}

    INSTRUCTIONS:

    1. Follow the headings and section order of the uploaded template. Do not assume a fixed set of headings.

    2. USE THE ANALYSED DATA:
    - Use the analysed template to understand the purpose and meaning of each section and field.
    - Follow the identified section hierarchy and relationships between fields.
    - Use the identified content types to distinguish narrative sections, questions, short-answer fields, Yes/No fields, and placeholders.
    - Use the identified placeholder meanings to determine what information belongs in each placeholder.
    - Use the original extracted template to verify the actual text and field locations.
    - The analysed template provides interpretation, but the original extracted template remains the source of truth for field IDs and original content.
    - If the analysis conflicts with the original extracted content, do not blindly follow the analysis. Avoid guessing and omit uncertain fields.

    3. FIELD-SPECIFIC MAPPING:
    - Determine what each field asks for using its field label, question, heading, instructions, analysed purpose, and surrounding template context.
    - Put information only in the field that specifically requests it.
    - Do not place content under a related but different field.
    - Keep each answer focused and appropriately concise for that field.
    - Do not combine information intended for separate fields.
    - Do not repeat the same information across fields unless the template explicitly requests it.

    4. Preserve all relevant clinical information, including symptoms, medical history, examination findings, investigations, diagnoses, treatments, medications, dosages, referrals, and follow-up plans when provided.

    5. Do not invent, assume, or infer missing clinical facts, diagnoses, medications, dosages, or test results.

    6. Use objective, neutral, and professional medical language. Improve grammar and readability without changing clinical meaning.

    7. Preserve dates, units, medication names, dosages, and other important details exactly as supplied.

    8. If information for a field or section is missing, do not generate content for that field. Do not interpret missing information as a negative finding.

    9. Preserve uncertainty in the source. Flag inconsistencies rather than silently correcting them.

    10. Do not add unsupported treatment recommendations or clinical conclusions.

    11. Preserve the template's existing sections and order. Do not introduce new sections or remove relevant template sections.

    12. "Yes/no", "frequency", "duration", and "cause" fields may only be filled if the source states the answer explicitly.

    13. SUMMARY AND RECOMMENDATIONS FIELDS:
    - A summary may restate key findings from the source. Do not add new facts.
    - Recommendations may only restate actions the source explicitly states. Add a short reason for each only if the source supports it.
    - Do not add treatment recommendations or clinical conclusions of your own.

    14. FIELD ID MAPPING:
    - Return the exact field_id for each field you populate.
    - Use only field_ids supplied in the original extracted template.
    - Populate only fields intended for an answer, not headings, labels, instructions, decorative elements, or signature/administrative fields.
    - Do not assume an empty element is fillable merely because it is empty.
    - If the template structure does not make a field's purpose clear, omit that field rather than guessing.

    15. PLACEHOLDER REPLACEMENT:
    - Identify placeholders using the analysed template.
    - Replace each placeholder only when the source medical data provides the corresponding information.
    - A paragraph may contain multiple placeholders with different meanings.
    - Return the complete updated paragraph for fields containing inline placeholders.
    - Preserve all surrounding original text.
    - Do not return unresolved placeholder values as if they were completed.

    16. OUTPUT FORMAT:
    - Return only a valid JSON object.
    - Do not wrap the JSON in Markdown code fences.
    - Use each field_id as a JSON key.
    - Use the drafted content as its corresponding string value.
    - Include only fields that should be populated and have supporting information in the source medical data.
    - If multiple pieces of information belong in the same field, combine them into a clearly structured string.
    - Do not return template headings as JSON keys unless they are actual fillable fields with their own field_id.
    - Do not return empty strings or fields without supporting source information.
    - Do not include explanations, additional commentary, or Markdown code fences.
    - Ensure the output is valid JSON with correctly escaped characters.

    17. This is a draft for review by a qualified healthcare professional. Do not claim that it has been clinically verified or approved.

    Generate the report now.
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

    draft_data = json.loads(content)

    return draft_data