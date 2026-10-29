import os
from langchain_aws import ChatBedrockConverse

def get_model():
    model = ChatBedrockConverse(
        model=os.getenv("BEDROCK_MODEL_ID"),
        region_name=os.getenv("AWS_REGION"),
        temperature=0.3
    )

    return model