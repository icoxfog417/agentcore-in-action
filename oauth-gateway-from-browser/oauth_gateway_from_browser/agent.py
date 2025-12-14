"""Agent logic for Gateway tool calls with OAuth"""
import requests


def call_gateway_tool(gateway_url, bearer_token, tool_name, arguments, return_url=None, force_auth=False):
    """Make raw JSON-RPC call to Gateway with OAuth configuration"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
        "MCP-Protocol-Version": "2025-11-25"
    }
    
    params = {
        "name": tool_name,
        "arguments": arguments
    }
    
    # Only add _meta if return_url is provided (for retry after OAuth)
    if return_url:
        params["_meta"] = {
            "aws.bedrock-agentcore.gateway/credentialProviderConfiguration": {
                "oauthCredentialProvider": {
                    "returnUrl": return_url,
                    "forceAuthentication": force_auth
                }
            }
        }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": params
    }
    
    print(f"\n[DEBUG] Request to: {gateway_url}")
    print(f"[DEBUG] Headers: {headers}")
    print(f"[DEBUG] Payload: {payload}")
    
    response = requests.post(gateway_url, headers=headers, json=payload)
    
    # Debug: print response
    print(f"Status: {response.status_code}")
    print(f"Response text: {response.text[:500]}")
    
    if response.status_code != 200:
        return {"error": {"code": -1, "message": f"HTTP {response.status_code}: {response.text}"}}
    
    try:
        return response.json()
    except Exception as e:
        return {"error": {"code": -1, "message": f"JSON decode error: {str(e)}, Response: {response.text[:200]}"}}


def greet_user(gateway_url, bearer_token, return_url=None):
    """Execute greeting flow with YouTube data"""
    # Get channel info (without _meta to trigger OAuth elicitation)
    channel_result = call_gateway_tool(
        gateway_url, bearer_token,
        "YouTubeTarget___getChannels",
        {"part": "snippet", "mine": True}
    )
    
    # Check for OAuth elicitation
    if "error" in channel_result:
        error_code = channel_result["error"].get("code")
        error_data = channel_result["error"].get("data", {})
        
        print(f"[DEBUG] Error code: {error_code}")
        print(f"[DEBUG] Error data: {error_data}")
        
        if error_code == -32042 and "elicitations" in error_data:
            # OAuth elicitation response
            elicitation = error_data["elicitations"][0]
            return {
                "status": "oauth_required",
                "auth_url": elicitation["url"],
                "elicitation_id": elicitation["elicitationId"]
            }
        else:
            # Other error
            return {
                "status": "error",
                "message": channel_result["error"].get("message", "Unknown error"),
                "details": str(channel_result["error"])
            }
    
    # Get subscriptions (no return_url needed - session already bound)
    subs_result = call_gateway_tool(
        gateway_url, bearer_token,
        "YouTubeTarget___getSubscriptions",
        {"part": "snippet", "mine": True, "maxResults": 1}
    )
    
    if "error" in subs_result:
        return {
            "status": "error",
            "message": subs_result["error"].get("message", "Unknown error")
        }
    
    # Parse JSON responses
    import json
    channel_data = json.loads(channel_result["result"]["content"][0]["text"])
    channel_name = channel_data["items"][0]["snippet"]["title"]
    
    subs_data = json.loads(subs_result["result"]["content"][0]["text"])
    subscription_title = subs_data["items"][0]["snippet"]["title"]
    
    return {
        "status": "success",
        "greeting": f"Hello {channel_name}! You subscribe to {subscription_title} that has fantastic videos!"
    }
