import base64
import json
import uuid
from pathlib import Path

import boto3
import streamlit as st
import yaml
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Path to the AgentCore deploy config, anchored on this file so it resolves
# regardless of where Streamlit is launched from.
AGENTCORE_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "Backend" / ".bedrock_agentcore.yaml"
)


class AgentConfigError(RuntimeError):
    """Raised when the deployed agent's config cannot be resolved."""


class AgentInvokeError(RuntimeError):
    """Raised when the agent returns an unexpected (error-shaped) response."""


def load_agent_config(config_path: Path = AGENTCORE_CONFIG_PATH) -> tuple[str, str]:
    """Read the deployed agent ARN and region from .bedrock_agentcore.yaml.

    Uses ``default_agent`` to pick the active agent block, then returns its
    ``bedrock_agentcore.agent_arn`` and ``aws.region``. Raises AgentConfigError
    with an actionable message if the file is missing or the agent is not yet
    deployed (ARN is null).
    """
    if not config_path.exists():
        raise AgentConfigError(
            f"Deploy config not found at {config_path}. "
            "Deploy the agent first with `agentcore deploy`."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    default_agent = config.get("default_agent")
    agents = config.get("agents") or {}
    agent = agents.get(default_agent) or {}

    arn = (agent.get("bedrock_agentcore") or {}).get("agent_arn")
    region = (agent.get("aws") or {}).get("region")

    if not arn:
        raise AgentConfigError(
            "Agent ARN is empty in the deploy config — the agent has not been "
            "deployed yet. Run `agentcore deploy`."
        )
    if not region:
        raise AgentConfigError("AWS region is missing from the deploy config.")

    return arn, region


def invoke_agent(
    template_bytes: bytes,
    support_bytes: bytes,
    arn: str,
    region: str,
) -> dict:
    """Invoke the deployed AgentCore agent with two .docx files.

    Base64-encodes the uploads into the JSON payload, calls InvokeAgentRuntime
    (using the default AWS credential chain), concatenates the streamed response
    chunks, parses the JSON, and returns the decoded report plus metadata.
    """
    payload = json.dumps({
        "template_b64": base64.b64encode(template_bytes).decode("ascii"),
        "support_b64": base64.b64encode(support_bytes).decode("ascii"),
    }).encode()

    client = boto3.client("bedrock-agentcore", region_name=region)

    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=str(uuid.uuid4()),
        payload=payload,
        qualifier="DEFAULT",
    )

    chunks = [chunk.decode("utf-8") for chunk in response.get("response", [])]
    body = json.loads("".join(chunks))

    report_b64 = body.get("report_b64")
    if not report_b64:
        raise AgentInvokeError(
            f"Agent did not return a report. Response: {body}"
        )

    return {
        "report_bytes": base64.b64decode(report_b64),
        "validation": body.get("validation"),
        "revision_count": body.get("revision_count"),
    }


st.set_page_config(page_title="Medical Report Generator", page_icon="🩺")

st.title("🩺 Medical Report Generator")
st.caption(
    "Upload a report template and the supporting medical data. "
    "The deployed agent drafts, validates, and generates a formatted report."
)

with st.form("report_form"):
    template_file = st.file_uploader(
        "Template document (.docx)",
        type=["docx"],
        help="A Word document whose headings define the report structure.",
    )
    support_file = st.file_uploader(
        "Supporting medical data (.docx)",
        type=["docx"],
        help="A Word document containing the source clinical information.",
    )

    submitted = st.form_submit_button("Generate report")

if submitted:
    if template_file is None or support_file is None:
        st.warning("Please upload both the template and the supporting document.")
    else:
        with st.spinner("Generating report. This may take a moment..."):
            try:
                arn, region = load_agent_config()
                result = invoke_agent(
                    template_file.getvalue(),
                    support_file.getvalue(),
                    arn,
                    region,
                )
            except AgentConfigError as exc:
                st.error(str(exc))
            except NoCredentialsError:
                st.error(
                    "No AWS credentials found. Configure them with `aws configure`, "
                    "environment variables, or an SSO profile, then try again."
                )
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "ClientError")
                message = exc.response.get("Error", {}).get("Message", str(exc))
                if code in ("AccessDeniedException", "UnauthorizedException"):
                    st.error(
                        "Access denied. Your AWS identity needs "
                        "`bedrock-agentcore:InvokeAgentRuntime` on this agent.\n\n"
                        f"{message}"
                    )
                elif code in ("ResourceNotFoundException", "ValidationException"):
                    st.error(
                        "The deployed agent could not be found. It may have been "
                        "deleted or the config is stale.\n\n"
                        f"{code}: {message}"
                    )
                else:
                    st.error(f"AWS error ({code}): {message}")
            except (BotoCoreError, AgentInvokeError) as exc:
                st.error(f"Request failed: {exc}")
            else:
                st.success("Report generated successfully.")

                validation = result.get("validation") or {}
                status = validation.get("status")
                revision_count = result.get("revision_count")
                if status:
                    detail = f"Validation: {status}"
                    if revision_count is not None:
                        detail += f"  •  Revisions: {revision_count}"
                    st.info(detail)
                    issues = validation.get("issues") or []
                    missing = validation.get("missing_information") or []
                    if issues or missing:
                        with st.expander("Validation details"):
                            st.json({"issues": issues, "missing_information": missing})

                st.download_button(
                    label="Download report.docx",
                    data=result["report_bytes"],
                    file_name="report.docx",
                    mime=DOCX_MIME,
                )
