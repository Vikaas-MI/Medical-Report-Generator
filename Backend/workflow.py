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

    #Genrator Node
    output_path: str


def draft_report(state: ReportState):
    draft = create_draft(state["supporting_text"], state["template_structure"])

    return {"report_draft":draft}

def validate_report(state: ReportState):
    validation = validate(state["report_draft"], state["supporting_text"])

    return {"validation":validation}

def generate_docx(state: ReportState):
    output_path = populate_template(state["report_draft"])

    return {"output_path": output_path}


builder = StateGraph(ReportState)

builder.add_node("draft", draft_report)
builder.add_node("validate", validate_report)
builder.add_node("generate", generate_docx)


builder.add_edge(START, "draft")
builder.add_edge("draft", "validate")
builder.add_edge("validate", "generate")
builder.add_edge("generate", END)


graph = builder.compile()