import json
import re

from model import get_model

def validate(draft: dict, source: dict, template: dict, analysed: dict):
    prompt = f"""
    You are a medical report validation assistant.

    Your task is to validate a draft medical report against the original source medical data and the uploaded template structure. 
    Check for factual consistency, completeness, clinical accuracy, and correct field mapping.

    SOURCE MEDICAL DATA:
    {source}

    UPLOADED TEMPLATE STRUCTURE:
    {template}

    TEMPLATE ANALYSED:
    {analysed}

    DRAFT MEDICAL REPORT:
    {draft}

    VALIDATION INSTRUCTIONS:

    1. FACTUAL CONSISTENCY
    - Check whether every clinical statement in the draft is supported by the source medical data.
    - Identify invented, altered, or unsupported clinical information.
    - Determine each field's purpose from its label, question, heading, instructions, and surrounding context.
    - Check that the content directly answers that field's prompt.
    - Flag content that belongs in a different field, even if it is relevant.
    - Flag repeated information unless the template asks for it.
    - Flag answers that are too long for short-answer fields.
    - Ensure that the drafted content does not introduce facts that are not present in the source.

    2. COMPLETENESS
    - Check whether relevant information from the source data has been included in the appropriate template fields.
    - Do not require information that is not relevant to the template or report purpose.

    3. CLINICAL DETAILS
    - Check for omitted information only when it is relevant to the report and belongs
    in a specific template field.
    - Do not require every source detail to appear in the report.
    - Identify the exact field where omitted source-supported information belongs.

    4. MISSING INFORMATION
    - Ensure that missing information has not been presented as a confirmed negative finding.
    - Check that unavailable information has not been fabricated or inferred.
    - Fields without supporting source information should remain unpopulated.

    5. CONTRADICTIONS
    - Identify conflicting statements within the draft.
    - Identify contradictions between the draft and the source medical data.
    - Preserve uncertainty and flag inconsistencies rather than silently resolving them.

    6. UNSUPPORTED CONCLUSIONS
    - Flag diagnoses, clinical interpretations, treatment recommendations, or follow-up instructions that are not explicitly supported by the source data.

    7. FIELD ID VALIDATION
    - Verify that every field_id returned in the draft exists in the uploaded template structure.
    - Identify field IDs that do not exist in the original template.
    - Check whether generated content has been assigned to the appropriate template field based on its label, heading, and surrounding context.
    - Identify content assigned to headings, decorative elements, or instructions instead of fillable fields.
    - Identify cases where information has been placed in an unrelated or incorrect field.
    - Ensure that the original template structure and field IDs have not been modified.
    - Do not invent or correct field IDs.

    8. STRUCTURE AND READABILITY
    - Check whether the draft follows the original template's section order and structure.
    - Ensure that no new template sections or unrelated fields have been introduced.

    9. ANALYSED TEMPLATE VALIDATION
    - Use the analysed template to understand the purpose, meaning, and expected content of each field.
    - Verify that drafted content matches the intended purpose of each field.
    - Use the original extracted template to verify the actual field IDs, original content, and locations.
    - Do not treat the analysed template as the source of truth for field IDs or original template content.
    - If the analysed template and original extraction appear inconsistent, flag the uncertainty rather than guessing.

    OUTPUT REQUIREMENTS:

    Return only a valid JSON object with the following structure:

        "status": "PASS",
        "issues": ,
        "missing_information": 

    The status must be:
    - "PASS" if no material issues are identified.
    - "FAIL" if one or more material issues are identified.

    Each item in the issues list must contain:
    - "category": The issue category.
    - "field_id": The affected template field ID, if applicable; otherwise null.
    - "draft_statement": The relevant draft content.
    - "explanation": A clear explanation of the identified issue.
    - "supporting_source": The relevant supporting source information, if available; otherwise null.

    Each item in the missing_information list must contain:
    - "information": The relevant source information omitted from the draft.
    - "expected_field_id": The appropriate template field ID, if identifiable; otherwise null.
    - "explanation": Why the information should have been included.

    ADDITIONAL RULES:
    - Do not rewrite the report.
    - Do not invent missing facts.
    - Do not silently correct discrepancies.
    - Do not modify the draft.
    - Do not treat missing source information as a negative finding.
    - Do not flag intentionally unpopulated fields as errors when the source does not contain the relevant information.
    - Do not flag harmless wording differences when the clinical meaning is preserved.
    - Return only valid JSON without Markdown code fences or additional commentary.
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

    valid_data = json.loads(content)

    print("Validation done")

    return valid_data
