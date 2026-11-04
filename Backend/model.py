
import os
import boto3

from dotenv import load_dotenv
from botocore.config import Config
from langchain_aws import ChatBedrockConverse

load_dotenv()


def get_model():

    bedrock_config = Config(
        connect_timeout=10,
        read_timeout=300,
        retries={
            "max_attempts": 3,
            "mode": "standard"
        }
    )

    bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION"),
        config=bedrock_config
    )

    model = ChatBedrockConverse(
        client=bedrock_client,
        model_id=os.getenv("BEDROCK_MODEL_ID"),
        temperature=0.3,
        max_tokens=16384,
    )

    return model
