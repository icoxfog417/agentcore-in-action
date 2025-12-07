"""AgentCore Identity configuration and management."""

import boto3
import jwt
from bedrock_agentcore.services.identity import UserTokenIdentifier


def create_workload_identity(name: str, callback_url: str, region: str) -> str:
    """Create AgentCore workload identity with OAuth return URL."""
    client = boto3.client('bedrock-agentcore', region_name=region)
    
    response = client.create_workload_identity(
        workloadIdentityName=name,
        allowedResourceOauth2ReturnUrls=[callback_url]
    )
    
    return response['workloadIdentityArn']


def get_user_token_identifier(id_token: str) -> UserTokenIdentifier:
    """Extract user identifier from JWT token."""
    decoded = jwt.decode(id_token, options={"verify_signature": False})
    return UserTokenIdentifier(user_token=decoded['sub'])


def delete_workload_identity(identity_arn: str, region: str):
    """Delete AgentCore workload identity."""
    client = boto3.client('bedrock-agentcore', region_name=region)
    client.delete_workload_identity(workloadIdentityIdentifier=identity_arn)
