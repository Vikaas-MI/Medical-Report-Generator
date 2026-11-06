"""AgentCore Runtime entrypoint for the Medical Report Generator.

This module wraps the existing LangGraph workflow (``workflow.graph``) so it can
be hosted on Amazon Bedrock AgentCore Runtime. AgentCore communicates with JSON
payloads over ``POST /invocations`` (plus a ``GET /ping`` health check) on port
8080; the ``BedrockAgentCoreApp`` + ``@app.entrypoint`` decorator provides that
HTTP contract automatically.

Input/output files are exchanged as base64 strings inside the JSON payload
(both input .docx files are expected to be < 10MB, well within the AgentCore
payload limit).

Request payload:
    {
        "template_b64": "<base64 of the template .docx>",
        "support_b64":  "<base64 of the supporting .docx>"
    }

Response payload:
    {
        "report_b64": "<base64 of the generated report .docx>",
        "validation": { ... },   # validation metadata from the workflow (if any)
        "revision_count": <int>  # number of draft revisions performed
    }

The existing on-disk file contract (uploads/template.docx, uploads/support.docx,
reports/report.docx) is preserved so the extractor, workflow and generator run
unchanged.
"""

import base64
import binascii
import os
from pathlib import Path

from bedrock_agentcore import BedrockAgentCoreApp

from workflow import graph
from services.extractor import extract_template

# Anchor all paths on the Backend directory, the same way generate_report.py
# does, so behaviour is identical regardless of the process working directory.
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATE_PATH = UPLOADS_DIR / "template.docx"
SUPPORT_PATH = UPLOADS_DIR / "support.docx"

app = BedrockAgentCoreApp()


class PayloadError(ValueError):
    """Raised when the incoming payload is missing or malformed."""


def _decode_to_file(payload: dict, key: str, destination: Path) -> None:
    """Base64-decode ``payload[key]`` and write the bytes to ``destination``."""
    value = payload.get(key)

    if not value:
        raise PayloadError(f"Missing required field '{key}' in payload.")

    if not isinstance(value, str):
        raise PayloadError(f"Field '{key}' must be a base64 string.")

    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PayloadError(f"Field '{key}' is not valid base64: {exc}") from exc

    if not data:
        raise PayloadError(f"Field '{key}' decoded to empty content.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


@app.entrypoint
def invoke(payload: dict) -> dict:
    """AgentCore entrypoint: generate a medical report from two base64 .docx files."""
    if not isinstance(payload, dict):
        raise PayloadError("Payload must be a JSON object.")

    # 1. Materialise the uploaded documents to the paths the workflow expects.
    _decode_to_file(payload, "template_b64", TEMPLATE_PATH)
    _decode_to_file(payload, "support_b64", SUPPORT_PATH)

    # 2. Extract structure from both documents (same as the FastAPI router).
    template_extracted = extract_template(TEMPLATE_PATH)
    support_extracted = extract_template(SUPPORT_PATH)

    # 3. Run the report-generation workflow.
    result = graph.invoke({
        "template_structure": template_extracted,
        "supporting_text": support_extracted,
    })

    # 4. Read the generated report and return it base64-encoded.
    output_path = Path(result["output_path"])
    report_bytes = output_path.read_bytes()

    return {
        "report_b64": base64.b64encode(report_bytes).decode("ascii"),
        "validation": result.get("validation"),
        "revision_count": result.get("revision_count"),
    }


if __name__ == "__main__":
    app.run()
