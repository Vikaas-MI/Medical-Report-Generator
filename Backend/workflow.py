from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Any

from services.draft import create_draft
from services.generate_report import populate_template
from services.validator import validate
from services.extractor import docx_text_extract


class ReportState(TypedDict, total=False):

    template_structure: dict[str, Any]
    supporting_text: dict[str, Any]

    #Draft Node
    report_draft: dict[str, Any]

    #Validator Node
    validation: dict[str, Any]
    revision_count: int

    #Genrator Node
    output_path: str


# Maximum number of redraft attempts before giving up and generating anyway.
MAX_REVISIONS = 2


def draft_report(state: ReportState):
    # On the first pass there is no validation; on a redraft, pass the feedback.
    draft = create_draft(
        state["supporting_text"],
        state["template_structure"],
        state.get("validation"),
    )

    return {
        "report_draft": draft,
        "revision_count": state.get("revision_count", 0) + 1,
    }

def validate_report(state: ReportState):
    validation = validate(state["report_draft"], state["supporting_text"])

    return {"validation": validation}

def generate_docx(state: ReportState):
    output_path = populate_template(state["report_draft"])

    return {"output_path": output_path}


def route_after_validation(state: ReportState) -> str:
    validation = state.get("validation") or {}

    if validation.get("status") == "FAIL" and state.get("revision_count", 0) < MAX_REVISIONS:
        return "draft"

    return "generate"


builder = StateGraph(ReportState)

builder.add_node("draft", draft_report)
builder.add_node("validate", validate_report)
builder.add_node("generate", generate_docx)


builder.add_edge(START, "draft")
builder.add_edge("draft", "validate")
builder.add_conditional_edges(
    "validate",
    route_after_validation,
    {"draft": "draft", "generate": "generate"},
)
builder.add_edge("generate", END)


graph = builder.compile()