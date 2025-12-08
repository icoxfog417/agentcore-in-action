"""Minimal test: Gateway authorization with Cognito OAuth"""
import json
import time
import boto3
import pytest
import requests


@pytest.fixture(scope="module")
def aws_clients():
    region = "us-east-1"
    return {
        "cognito": boto3.client("cognito-idp", region_name=region),
        "control": boto3.client("bedrock-agentcore-control", region_name=region),
        "iam": boto3.client("iam", region_name=region),
        "region": region
    }


@pytest.fixture(scope="module")
def cognito_oauth_setup(aws_clients):
    """Create Cognito with OAuth flows enabled"""
    cognito = aws_clients["cognito"]
    
    # Create user pool
    pool = cognito.create_user_pool(
        PoolName=f"test-oauth-{int(time.time())}",
        Policies={"PasswordPolicy": {"MinimumLength": 8}}
    )
    pool_id = pool["UserPool"]["Id"]
    
    # Create domain for OAuth
    domain_prefix = f"test-oauth-{int(time.time())}"
    cognito.create_user_pool_domain(
        Domain=domain_prefix,
        UserPoolId=pool_id
    )
    
    # Create resource server with scope
    cognito.create_resource_server(
        UserPoolId=pool_id,
        Identifier="test-resource",
        Name="Test Resource",
        Scopes=[{"ScopeName": "test-scope", "ScopeDescription": "Test scope"}]
    )
    
    # Create app client with OAuth
    client = cognito.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="test-oauth-client",
        GenerateSecret=False,
        AllowedOAuthFlows=["code"],
        AllowedOAuthFlowsUserPoolClient=True,
        AllowedOAuthScopes=["openid", "test-resource/test-scope"],
        CallbackURLs=[f"http://localhost:{p}/callback" for p in range(8080, 8090)],  # Allow ports 8080-8089
        SupportedIdentityProviders=["COGNITO"]
    )
    client_id = client["UserPoolClient"]["ClientId"]
    
    # Create user
    cognito.admin_create_user(
        UserPoolId=pool_id,
        Username="testuser",
        TemporaryPassword="TempPass123!",
        MessageAction="SUPPRESS"
    )
    cognito.admin_set_user_password(
        UserPoolId=pool_id,
        Username="testuser",
        Password="TestPass123!",
        Permanent=True
    )
    
    discovery_url = f"https://cognito-idp.{aws_clients['region']}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
    
    yield {
        "pool_id": pool_id,
        "client_id": client_id,
        "discovery_url": discovery_url,
        "domain_prefix": domain_prefix
    }
    
    # Cleanup
    cognito.delete_user_pool_domain(Domain=domain_prefix, UserPoolId=pool_id)
    cognito.delete_user_pool(UserPoolId=pool_id)


@pytest.fixture(scope="module")
def gateway_with_scope(aws_clients, cognito_oauth_setup):
    """Create gateway requiring scope"""
    iam = aws_clients["iam"]
    control = aws_clients["control"]
    
    # Create role
    role = iam.create_role(
        RoleName=f"test-oauth-gw-{int(time.time())}",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole"}]
        })
    )
    role_arn = role["Role"]["Arn"]
    
    # Create gateway with scope requirement
    gw = control.create_gateway(
        name=f"test-oauth-gw-{int(time.time())}",
        protocolType="MCP",
        protocolConfiguration={"mcp": {"supportedVersions": ["2025-11-25"], "searchType": "SEMANTIC"}},
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration={
            "customJWTAuthorizer": {
                "discoveryUrl": cognito_oauth_setup["discovery_url"],
                "allowedClients": [cognito_oauth_setup["client_id"]],
                "allowedScopes": ["test-resource/test-scope"]
            }
        },
        roleArn=role_arn,
        exceptionLevel="DEBUG"
    )
    gateway_id = gw["gatewayId"]
    gateway_url = gw["gatewayUrl"]
    
    # Wait for ready
    while control.get_gateway(gatewayIdentifier=gateway_id)["status"] != "READY":
        time.sleep(5)
    
    yield {"gateway_id": gateway_id, "gateway_url": gateway_url, "role_arn": role_arn}
    
    # Cleanup
    control.delete_gateway(gatewayIdentifier=gateway_id)
    time.sleep(2)
    iam.delete_role(RoleName=role_arn.split("/")[-1])


def test_oauth_flow_info(aws_clients, cognito_oauth_setup, gateway_with_scope):
    """Display OAuth flow information for manual testing"""
    region = aws_clients["region"]
    domain = cognito_oauth_setup["domain_prefix"]
    client_id = cognito_oauth_setup["client_id"]
    
    auth_url = (
        f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri=http://localhost:8080/callback"
        f"&scope=openid+test-resource/test-scope"
    )
    
    token_url = f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/token"
    
    print(f"\n{'='*60}")
    print("OAuth Flow Setup Complete")
    print(f"{'='*60}")
    print(f"\nGateway URL: {gateway_with_scope['gateway_url']}")
    print(f"\n1. Open this URL in browser:")
    print(f"   {auth_url}")
    print(f"\n2. Login with:")
    print(f"   Username: testuser")
    print(f"   Password: TestPass123!")
    print(f"\n3. After redirect, extract 'code' from URL")
    print(f"\n4. Exchange code for token:")
    print(f"   POST {token_url}")
    print(f"   Body: grant_type=authorization_code&client_id={client_id}&code=CODE&redirect_uri=http://localhost:8080/callback")
    print(f"\n5. Use id_token to call gateway")
    print(f"{'='*60}\n")


@pytest.fixture(scope="module")
def gateway_no_scope(aws_clients, cognito_oauth_setup):
    """Create gateway without scope requirement"""
    iam = aws_clients["iam"]
    control = aws_clients["control"]
    
    # Create role
    role = iam.create_role(
        RoleName=f"test-oauth-noscope-{int(time.time())}",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole"}]
        })
    )
    role_arn = role["Role"]["Arn"]
    
    # Create gateway without scope requirement
    gw = control.create_gateway(
        name=f"test-oauth-noscope-{int(time.time())}",
        protocolType="MCP",
        protocolConfiguration={"mcp": {"supportedVersions": ["2025-11-25"], "searchType": "SEMANTIC"}},
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration={
            "customJWTAuthorizer": {
                "discoveryUrl": cognito_oauth_setup["discovery_url"],
                "allowedClients": [cognito_oauth_setup["client_id"]]
            }
        },
        roleArn=role_arn,
        exceptionLevel="DEBUG"
    )
    gateway_id = gw["gatewayId"]
    gateway_url = gw["gatewayUrl"]
    
    # Wait for ready
    while control.get_gateway(gatewayIdentifier=gateway_id)["status"] != "READY":
        time.sleep(5)
    
    yield {"gateway_id": gateway_id, "gateway_url": gateway_url, "role_arn": role_arn}
    
    # Cleanup
    control.delete_gateway(gatewayIdentifier=gateway_id)
    time.sleep(2)
    iam.delete_role(RoleName=role_arn.split("/")[-1])


def get_oauth_token_automated(cognito_setup, region, scopes):
    """Helper to get OAuth token via automated browser"""
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    auth_code = {"code": None}
    
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                auth_code["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Success!</h1></body></html>")
        def log_message(self, format, *args):
            pass
    
    for port in range(8080, 8090):
        try:
            server = HTTPServer(("localhost", port), CallbackHandler)
            break
        except OSError:
            continue
    
    callback_url = f"http://localhost:{port}/callback"
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    
    domain = cognito_setup["domain_prefix"]
    client_id = cognito_setup["client_id"]
    scope_str = "+".join(scopes)
    
    auth_url = (
        f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={callback_url}"
        f"&scope={scope_str}"
    )
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
    
    service = Service(executable_path="/snap/chromium/current/usr/lib/chromium-browser/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(auth_url)
        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.send_keys("testuser")
        driver.find_element(By.NAME, "password").send_keys("TestPass123!")
        driver.find_element(By.NAME, "signInSubmitButton").click()
        WebDriverWait(driver, 20).until(lambda d: "localhost" in d.current_url)
    finally:
        driver.quit()
    
    server_thread.join(timeout=5)
    server.server_close()
    
    if not auth_code["code"]:
        return None
    
    token_url = f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/token"
    token_response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": auth_code["code"],
            "redirect_uri": callback_url
        }
    )
    
    if token_response.status_code == 200:
        return token_response.json()["access_token"]
    return None


def test_gateway_with_oauth_token(aws_clients, cognito_oauth_setup, gateway_no_scope):
    """Test gateway without scope requirement using automated OAuth"""
    access_token = get_oauth_token_automated(cognito_oauth_setup, aws_clients["region"], ["openid"])
    
    assert access_token, "Failed to get OAuth token"
    
    response = requests.post(
        gateway_no_scope["gateway_url"],
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "MCP-Protocol-Version": "2025-11-25"
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    
    print(f"\n[No Scope Required] Status: {response.status_code}")
    print(f"[No Scope Required] Response:\n{json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200


def test_gateway_with_oauth_token_with_scope(aws_clients, cognito_oauth_setup, gateway_with_scope):
    """Test gateway with scope requirement using automated OAuth"""
    access_token = get_oauth_token_automated(cognito_oauth_setup, aws_clients["region"], ["openid", "test-resource/test-scope"])
    
    assert access_token, "Failed to get OAuth token"
    
    response = requests.post(
        gateway_with_scope["gateway_url"],
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "MCP-Protocol-Version": "2025-11-25"
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    
    print(f"\n[With Scope] Status: {response.status_code}")
    print(f"[With Scope] Response:\n{json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200


def test_gateway_with_automated_oauth(aws_clients, cognito_oauth_setup, gateway_with_scope):
    """Test gateway with fully automated browser OAuth flow"""
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    
    # Storage for auth code
    auth_code = {"code": None}
    
    # Callback server
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                auth_code["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Success!</h1></body></html>")
        
        def log_message(self, format, *args):
            pass
    
    # Start callback server on port from allowed range
    for port in range(8080, 8090):
        try:
            server = HTTPServer(("localhost", port), CallbackHandler)
            break
        except OSError:
            continue
    else:
        pytest.fail("No available port in range 8080-8089")
    
    callback_url = f"http://localhost:{port}/callback"
    
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    
    # Build authorization URL
    region = aws_clients["region"]
    domain = cognito_oauth_setup["domain_prefix"]
    client_id = cognito_oauth_setup["client_id"]
    
    auth_url = (
        f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={callback_url}"
        f"&scope=openid+test-resource/test-scope"
    )
    
    # Automate browser login
    from selenium.webdriver.chrome.service import Service
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
    
    service = Service(executable_path="/snap/chromium/current/usr/lib/chromium-browser/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(auth_url)
        
        # Debug: print page source
        print(f"\n[DEBUG] Page title: {driver.title}")
        print(f"[DEBUG] Current URL: {driver.current_url}")
        
        # Wait for and fill username
        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.send_keys("testuser")
        
        # Fill password
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys("TestPass123!")
        
        # Submit form
        submit_button = driver.find_element(By.NAME, "signInSubmitButton")
        submit_button.click()
        
        # Wait for redirect to callback
        WebDriverWait(driver, 20).until(lambda d: "localhost" in d.current_url)
        
    finally:
        driver.quit()
    
    server_thread.join(timeout=5)
    server.server_close()
    
    assert auth_code["code"], "No authorization code received"
    
    # Exchange code for token
    token_url = f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/token"
    token_response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": auth_code["code"],
            "redirect_uri": callback_url
        }
    )
    
    assert token_response.status_code == 200, f"Token exchange failed: {token_response.text}"
    
    tokens = token_response.json()
    access_token = tokens["access_token"]
    
    # Debug: decode token to see claims
    import base64
    parts = access_token.split(".")
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    decoded = json.loads(base64.b64decode(payload))
    print(f"\n[Access Token Claims]:\n{json.dumps(decoded, indent=2)}")
    
    # Test gateway
    response = requests.post(
        gateway_with_scope["gateway_url"],
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "MCP-Protocol-Version": "2025-11-25"
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    
    print(f"\n[Gateway] Status: {response.status_code}")
    print(f"[Gateway] Response:\n{json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
