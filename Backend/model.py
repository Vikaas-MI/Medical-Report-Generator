import os
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

load_dotenv()

def get_model():
    model = ChatBedrockConverse(
        model=os.getenv("BEDROCK_MODEL_ID"),
        region_name=os.getenv("AWS_REGION"),
        temperature=0.3
    )

    return model