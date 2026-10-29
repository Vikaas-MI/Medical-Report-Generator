import json

from model import get_model

def create_draft(data: dict, template: dict):
    prompt = f"""
        You are a medical report drafting assistant.

        Generate a clear, professional, and clinically neutral medical report
        using the source medical data and the structure of the uploaded template.

        SOURCE MEDICAL DATA:
        {data}

        UPLOADED TEMPLATE STRUCTURE:
        {template}

        Instructions:

        1. Follow the headings and section order of the uploaded template.
        Do not assume a fixed set of headings.

        2. Map the relevant source medical information to the appropriate
        sections of the template.

        3. Preserve all relevant clinical information, including symptoms,
        medical history, examination findings, investigations, diagnoses,
        treatments, and follow-up plans when provided.

        4. Do not invent, assume, or infer missing clinical facts, diagnoses,
        medications, dosages, or test results.

        5. Use objective, neutral, and professional medical language.
        Improve grammar and readability without changing clinical meaning.

        6. Preserve dates, units, medication names, dosages, and other
        important details exactly as supplied.

        7. If information for a section is missing, leave it blank or mark
        it as "Not provided" where appropriate. Never interpret missing
        information as a negative finding.

        8. Preserve uncertainty in the source. Flag inconsistencies rather
        than silently correcting them.

        9. Do not add unsupported treatment recommendations or clinical
        conclusions.

        10. Preserve the template's existing headings and order. Do not
            introduce unnecessary sections or remove relevant template sections.

        11. Return the report content mapped to the template sections.
            Do not return JSON, explanations, or additional commentary.

        12. This is a draft for review by a qualified healthcare professional.
            Do not claim that it has been clinically verified.

        OUTPUT FORMAT:
            Return only a valid JSON object.
            Use each template heading as a key and its drafted content as the value.
            Include only headings that exist in the uploaded template.
            Do not wrap the JSON in Markdown code fences.

        Example key - value pairs:
                "Patient Details": "Patient Name: John Smith",
                "Clinical History": "Lower back pain for three days.",
                "Assessment": "Not provided"
            
        Generate the report now.
        """

    model = get_model()

    response = model.invoke(prompt)
    draft_data = json.loads(response.content)

    return draft_data