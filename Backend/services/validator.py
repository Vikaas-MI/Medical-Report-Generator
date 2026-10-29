import json

from model import get_model
from services.draft import create_draft

def validate(draft: str, source: str):
    prompt = f"""
    You are a medical report validation assistant. Your task is to validate a draft medical report against the original source data for completeness, factual consistency, and clinical accuracy.

    Source Data:
    {source}

    Draft Medical Report:
    {draft}

    Validation Instructions:

    1. Factual consistency: Check whether the statements in the draft are supported by the source data. Identify invented, altered, or unsupported clinical information.
    2. Completeness: Check whether relevant information from the source data such as including symptoms, medical history, examination findings, investigations, diagnoses, medications, and follow-up plans, has been omitted.
    3. Clinical details: Verify that medication names, dosages, units, dates, measurements, and test results match the source data. Flag discrepancies without guessing the correct values.
    4. Missing information: Ensure that missing information has not been presented as a confirmed negative finding. Check that missing details are appropriately identified or left blank according to the report requirements.
    5. Contradictions: Identify conflicting statements within the report or between the report and the source data.
    6. Structure and readability: Check whether the report is organized, clear, professional, and free of significant grammatical errors.
    7. Unsupported conclusions: Flag diagnoses, clinical interpretations, treatment recommendations, or follow-up instructions that are not explicitly supported by the source data.

    Output Requirements:

    Return only a valid JSON object containing:

    - status: "PASS" if no material issues are identified; otherwise "FAIL".
    - issues: A list of identified issues. For each issue, include its category, the relevant draft statement, an explanation, and the supporting source information when available.
    - missing_information: A list of important source details omitted from the draft.

    Do not rewrite the report, invent missing facts, or silently correct discrepancies. Return only the validation result in valid JSON format.

    """
    model = get_model()

    response = model.invoke(prompt)
    draft_data = json.loads(response.content)

    return draft_data
