"""OAuth2 callback server for Cognito and YouTube flows"""
import boto3
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from bedrock_agentcore.services.identity import UserTokenIdentifier


class OAuth2CallbackServer:
    def __init__(self, region, config):
        self.region = region
        self.config = config
        self.app = FastAPI()
        self.access_token = None
        self.identity_client = boto3.client("bedrock-agentcore", region_name=region)
        
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def home():
            domain_prefix = f"youtube-gw-{self.config['user_pool_id'].lower().replace('_', '-')[:20]}"
            cognito_url = (
                f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/authorize"
                f"?client_id={self.config['cognito_client_id']}"
                f"&response_type=code"
                f"&redirect_uri=http://localhost:8080/cognito/callback"
            )
            return f"""
            <html><body>
            <h1>YouTube Agent Demo</h1>
            <a href="{cognito_url}">Login with Cognito</a>
            </body></html>
            """
        
        @self.app.get("/test-gateway")
        async def test_gateway():
            """Test Gateway with list tools"""
            if not self.access_token:
                return {"error": "Not authenticated. Login first."}
            
            # Try listing tools
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "MCP-Protocol-Version": "2025-11-25"
            }
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            response = requests.post(self.config["gateway_url"], headers=headers, json=payload)
            return {
                "status_code": response.status_code,
                "response": response.text[:500]
            }
        
        @self.app.get("/cognito/callback")
        async def cognito_callback(code: str):
            return await self._handle_cognito_callback(code)
        
        @self.app.get("/oauth2/callback")
        async def oauth2_callback(session_id: str):
            return await self._handle_youtube_callback(session_id)
    
    async def _handle_cognito_callback(self, code):
        """Exchange Cognito auth code for access token"""
        domain_prefix = f"youtube-gw-{self.config['user_pool_id'].lower().replace('_', '-')[:20]}"
        token_url = f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token"
        
        response = requests.post(token_url, data={
            "grant_type": "authorization_code",
            "client_id": self.config["cognito_client_id"],
            "code": code,
            "redirect_uri": "http://localhost:8080/cognito/callback"
        })
        
        token_response = response.json()
        self.access_token = token_response["access_token"]
        
        # Save token to file for testing
        with open("/tmp/access_token.txt", "w") as f:
            f.write(self.access_token)
        print(f"✓ Access token saved to /tmp/access_token.txt")
        print(f"✓ Token (first 50 chars): {self.access_token[:50]}...")
        
        # Trigger OAuth elicitation
        from say_hello_to_authorized_customer.agent import greet_user
        result = greet_user(self.config["gateway_url"], self.access_token, "http://localhost:8080/oauth2/callback")
        
        if result["status"] == "oauth_required":
            return HTMLResponse(f"""
            <html><body>
            <h1>Authorize YouTube Access</h1>
            <a href="{result['auth_url']}">Click here to authorize</a>
            </body></html>
            """)
        
        if result["status"] == "error":
            return HTMLResponse(f"""
            <html><body>
            <h1>Error</h1>
            <p>{result['message']}</p>
            <pre>Check server logs for details</pre>
            </body></html>
            """)
        
        return HTMLResponse(f"<html><body><h1>{result['greeting']}</h1></body></html>")
    
    async def _handle_youtube_callback(self, session_id):
        """Complete YouTube OAuth and retry Gateway call"""
        print(f"[DEBUG] Completing OAuth session binding for session: {session_id}")
        
        self.identity_client.complete_resource_token_auth(
            sessionUri=session_id,
            userIdentifier={"userToken": self.access_token}
        )
        
        print("[DEBUG] Session binding complete, retrying tool call...")
        
        # Retry greeting (without _meta - session is already bound)
        from say_hello_to_authorized_customer.agent import greet_user
        result = greet_user(self.config["gateway_url"], self.access_token)
        
        print(f"[DEBUG] Result: {result}")
        
        if result["status"] == "success":
            return HTMLResponse(f"<html><body><h1>{result['greeting']}</h1></body></html>")
        else:
            return HTMLResponse(f"<html><body><h1>Error</h1><p>{result.get('message', 'Unknown error')}</p><pre>{result}</pre></body></html>")
