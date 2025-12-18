# Debugging Step 6: Cognito → AgentCore Callback

## The Problem

At step 6, when Cognito redirects to AgentCore's callback endpoint, the URL is missing `code` and `state` parameters:

```
Expected: https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback?code=XXX&state=YYY
Actual:   https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback  (no params)
```

## Root Causes

### 1. **Redirect URI Mismatch** (Most Likely)

When AgentCore Identity initiates the OAuth flow, it sends a `redirect_uri` parameter to Cognito:

```
Cognito Hosted UI URL:
https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/authorize?
  client_id={CLIENT_ID}&
  redirect_uri=https://bedrock-agentcore.{region}.amazonaws.com/identities/oauth2/callback&
  response_type=code&
  scope=openid+email+profile&
  state={STATE}
```

**If the `redirect_uri` in this URL doesn't EXACTLY match what's in Cognito's `CallbackURLs` configuration, Cognito will:**
- Reject the authorization request, OR
- Redirect without parameters

**Check:**
1. Cognito's registered callback URL (from CloudFormation)
2. The redirect_uri AgentCore is using (from browser network logs)

### 2. **Region Mismatch**

The callback URL format is:
```
https://bedrock-agentcore.{REGION}.amazonaws.com/identities/oauth2/callback
```

**If regions don't match:**
- CloudFormation uses: `${AWS::Region}` → might be `us-east-1`
- AgentCore provider uses: `{REGION}` from .env → might be different
- Python script uses: `os.environ.get("AWS_REGION")` → might be different

**All three must use the SAME region!**

### 3. **Cognito User Pool Client Issue**

The Cognito client might have been updated manually or have stale configuration.

**Required settings:**
```yaml
CallbackURLs:
  - https://bedrock-agentcore.{REGION}.amazonaws.com/identities/oauth2/callback
AllowedOAuthFlows: [code]
AllowedOAuthScopes: [openid, email, profile]
AllowedOAuthFlowsUserPoolClient: true
```

### 4. **AgentCore Provider Configuration**

The inbound OAuth provider (created in construct.py) might not be correctly configured for USER_FEDERATION flow.

Check: The provider must use `credentialProviderVendor="CognitoOauth2"`

## Diagnostic Steps

### Step 1: Capture the actual redirect URL

When you run `main.py` and the error occurs:

1. Open browser DevTools (F12) → **Network tab**
2. Enable "Preserve log"
3. Run `main.py`
4. Look for the redirect chain:

```
Request #1: AgentCore → Cognito Hosted UI
  URL: https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/authorize
  Check query params:
    - redirect_uri: ??? (COPY THIS VALUE)
    - client_id: ???
    - scope: ???

Request #2: Cognito → Google
  URL: https://accounts.google.com/o/oauth2/v2/auth
  Check query params:
    - redirect_uri: https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/idpresponse
    - (This should have code and state when returning)

Request #3: Google → Cognito (after sign-in)
  URL: https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/idpresponse?code=XXX&state=YYY
  ✅ Verify code and state are present

Request #4: Cognito → AgentCore ⚠️ ERROR HERE
  URL: https://bedrock-agentcore.{region}.amazonaws.com/identities/oauth2/callback
  ❌ Check if code and state are present
```

### Step 2: Compare redirect_uri values

From Request #1, compare the `redirect_uri` parameter with your Cognito configuration:

```bash
# Get Cognito's registered callback URLs
aws cognito-idp describe-user-pool-client \
  --user-pool-id {POOL_ID} \
  --client-id {CLIENT_ID} \
  --region {REGION} \
  --query 'UserPoolClient.CallbackURLs'
```

**They must match EXACTLY (including trailing slashes, protocol, etc.)**

### Step 3: Check for region consistency

```bash
# Check all regions match
echo "Region in .env:" && grep AWS_REGION .env
echo "Region in config.json:" && python3 -c "import json; print(json.load(open('config.json'))['region'])"
echo "Region in CloudFormation:" && aws cloudformation describe-stacks --stack-name mcp-oauth-gateway-infra --query 'Stacks[0].Parameters[?ParameterKey==`StackName`].ParameterValue' --output text
```

### Step 4: Verify Cognito configuration

```bash
# Get full Cognito client config
aws cognito-idp describe-user-pool-client \
  --user-pool-id {POOL_ID} \
  --client-id {CLIENT_ID} \
  --region {REGION} \
  --output json
```

Check:
- `CallbackURLs` includes AgentCore callback
- `AllowedOAuthFlows` includes "code"
- `AllowedOAuthScopes` includes ["openid", "email", "profile"]
- `AllowedOAuthFlowsUserPoolClient` is `true`

## Possible Solutions

### Solution 1: Update Cognito Callback URL

If the callback URL is wrong:

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id {POOL_ID} \
  --client-id {CLIENT_ID} \
  --region {REGION} \
  --callback-urls "https://bedrock-agentcore.{REGION}.amazonaws.com/identities/oauth2/callback" \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email profile \
  --allowed-o-auth-flows-user-pool-client
```

### Solution 2: Recreate AgentCore Provider

If the provider configuration is wrong:

```bash
# Delete and recreate
aws bedrock-agentcore-control delete-oauth2-credential-provider \
  --name mcp-oauth-gateway-inbound-cognito \
  --region {REGION}

# Then run construct.py again
uv run python construct.py
```

### Solution 3: Fix Region Mismatch

Ensure all configs use the same region:

1. `.env`: `AWS_REGION=us-east-1`
2. `construct.py`: Uses `REGION` from .env
3. `main.py`: Uses `config["region"]` from config.json
4. CloudFormation: Uses `${AWS::Region}` (matches deployment region)

### Solution 4: Browser Cache

Clear browser cookies for:
- `*.amazoncognito.com`
- `*.amazonaws.com`
- `accounts.google.com`

## Expected Behavior

When working correctly, Request #4 should look like:

```
URL: https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback?code=7b2e9f3a...&state=abc123...
```

The `@requires_access_token` decorator will then:
1. Exchange the code for a Cognito JWT
2. Return the JWT to your `run_agent` function
3. You should see: `✓ Authenticated (token length: 1234)`
