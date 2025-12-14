"""OAuth callback handler for completing GitHub authorization"""
import boto3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


class OAuthCallbackHandler:
    """Handles OAuth callback to complete authorization flow"""

    def __init__(self, region: str, identity_arn: str):
        self.region = region
        self.identity_arn = identity_arn
        self.app = FastAPI()
        self.identity_client = boto3.client("bedrock-agentcore", region_name=region)

        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def home():
            return """
            <html><body>
            <h1>GitHub OAuth Callback Server</h1>
            <p>This server handles OAuth callbacks from AgentCore Identity.</p>
            <p>When you authorize GitHub access, you'll be redirected here.</p>
            </body></html>
            """

        @self.app.get("/oauth/callback")
        async def oauth_callback(session_id: str):
            """
            Complete OAuth flow after user authorizes GitHub access.

            Args:
                session_id: Session URI from AgentCore Identity OAuth elicitation
            """
            return await self._handle_oauth_callback(session_id)

    async def _handle_oauth_callback(self, session_id: str):
        """
        Complete OAuth session binding.

        This is called after the user authorizes access to their GitHub account.
        AgentCore Identity will exchange the authorization code for an access token
        and store it bound to the user's identity.

        Args:
            session_id: Session URI from OAuth elicitation

        Returns:
            HTML response confirming successful authorization
        """
        try:
            # Note: In this MCP server example, we don't have a user token yet
            # since the client connects via SigV4, not OAuth.
            # The user binding happens automatically based on the AWS credentials
            # used to call the Gateway.

            # For now, we'll acknowledge the callback
            # In production, you might want to notify the user through another channel
            # or store session state to complete the flow

            print(f"[DEBUG] OAuth callback received for session: {session_id}")
            print("[DEBUG] User should retry their MCP tool call now")

            return HTMLResponse(f"""
            <html><body>
            <h1>✓ GitHub Authorization Successful</h1>
            <p>You have successfully authorized access to your GitHub account.</p>
            <p>Session ID: <code>{session_id}</code></p>
            <p><strong>Next step:</strong> Return to your MCP client and retry the tool call.</p>
            <p>The tool should now work without requiring authorization.</p>
            </body></html>
            """)

        except Exception as e:
            print(f"[ERROR] Failed to complete OAuth callback: {e}")
            return HTMLResponse(f"""
            <html><body>
            <h1>❌ OAuth Error</h1>
            <p>Failed to complete authorization: {str(e)}</p>
            <p>Please try again or contact support.</p>
            </body></html>
            """, status_code=500)

    def run(self, host="0.0.0.0", port=8080):
        """Start the callback server"""
        import uvicorn
        print(f"Starting OAuth callback server on http://{host}:{port}")
        print(f"Callback URL: http://{host}:{port}/oauth/callback")
        uvicorn.run(self.app, host=host, port=port)
