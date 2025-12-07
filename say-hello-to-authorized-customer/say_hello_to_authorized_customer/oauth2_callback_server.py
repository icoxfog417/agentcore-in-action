"""OAuth2 callback server for handling authorization code grant flow."""

import json
from fastapi import FastAPI
from bedrock_agentcore.services.identity import IdentityClient


OAUTH2_CALLBACK_SERVER_PORT = 9090


def _is_workshop_studio() -> bool:
    """Check if running in SageMaker Workshop Studio environment."""
    try:
        with open("/opt/ml/metadata/resource-metadata.json", "r") as file:
            json.load(file)
        return True
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def get_oauth2_callback_base_url() -> str:
    """Get the base URL for OAuth provider redirects."""
    if not _is_workshop_studio():
        return f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}"
    
    import boto3
    with open("/opt/ml/metadata/resource-metadata.json", "r") as file:
        data = json.load(file)
        domain_id = data["DomainId"]
        space_name = data["SpaceName"]
    
    sagemaker_client = boto3.client("sagemaker")
    response = sagemaker_client.describe_space(
        DomainId=domain_id, SpaceName=space_name
    )
    return response["Url"] + f"/proxy/{OAUTH2_CALLBACK_SERVER_PORT}"


class OAuth2CallbackServer:
    """OAuth2 callback server for handling authorization code grant flow."""
    
    def __init__(self, region: str):
        """Initialize the OAuth2 callback server."""
        self.region = region
        self.identity_client = IdentityClient(region=region)
        self.user_token_identifier = None
        self.app = FastAPI()
        self._setup_routes()
    
    def _setup_routes(self):
        """Configure FastAPI routes."""
        
        @self.app.post("/userIdentifier/token")
        async def _store_user_token(user_token_identifier_value):
            """Store user token identifier for OAuth session binding."""
            self.user_token_identifier = user_token_identifier_value
        
        @self.app.get("/ping")
        async def _handle_ping():
            """Health check endpoint."""
            return {"status": "success"}
        
        @self.app.get("/oauth2/callback")
        async def _handle_oauth2_callback(session_id: str):
            """Handle OAuth2 callback from provider."""
            self.identity_client.complete_oauth_flow(
                session_id=session_id,
                user_token_identifier=self.user_token_identifier
            )
            return {"status": "success"}


def store_token_in_oauth2_callback_server(identity_client, user_token_identifier):
    """Store user token identifier in the callback server."""
    # This is a simplified version - in practice, this would communicate with the running server
    server = OAuth2CallbackServer(region=identity_client.region)
    server.user_token_identifier = user_token_identifier
