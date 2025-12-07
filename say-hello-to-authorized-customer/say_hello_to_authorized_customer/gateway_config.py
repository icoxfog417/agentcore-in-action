"""AgentCore Gateway configuration and management."""

import boto3


def create_gateway(
    name: str,
    google_client_id: str,
    google_client_secret: str,
    callback_url: str,
    region: str
) -> str:
    """Create AgentCore Gateway with Google OAuth target."""
    client = boto3.client('bedrock-agentcore', region_name=region)
    
    response = client.create_gateway(
        gatewayName=name,
        mcpVersion='2025-11-25',
        targets=[{
            'targetType': 'OPENAPI',
            'openApiTarget': {
                'baseUrl': 'https://people.googleapis.com',
                'outboundAuthentication': {
                    'oauth2': {
                        'authorizationCodeGrant': {
                            'clientId': google_client_id,
                            'clientSecret': google_client_secret,
                            'authorizationEndpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
                            'tokenEndpoint': 'https://oauth2.googleapis.com/token',
                            'scopes': ['profile', 'openid']
                        }
                    }
                }
            }
        }]
    )
    
    return response['gatewayArn']


def delete_gateway(gateway_arn: str, region: str):
    """Delete AgentCore Gateway."""
    client = boto3.client('bedrock-agentcore', region_name=region)
    client.delete_gateway(gatewayIdentifier=gateway_arn)
