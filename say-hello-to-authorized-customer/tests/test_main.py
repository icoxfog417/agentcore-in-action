"""Test suite for Say Hello to Authorized Customer example."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestConfiguration:
    """Tests for configuration loading and validation."""

    def test_load_env_variables(self):
        """Verify all required environment variables load correctly."""
        with patch.dict(os.environ, {
            'AWS_REGION': 'us-east-1',
            'GOOGLE_CLIENT_ID': 'test-client-id',
            'GOOGLE_CLIENT_SECRET': 'test-secret',
            'CALLBACK_URL': 'http://localhost:9090/oauth2/callback'
        }):
            from say_hello_to_authorized_customer.config import load_config
            config = load_config()
            assert config['region'] == 'us-east-1'
            assert config['google_client_id'] == 'test-client-id'
            assert config['google_client_secret'] == 'test-secret'
            assert config['callback_url'] == 'http://localhost:9090/oauth2/callback'

    def test_missing_required_env_variables(self):
        """Graceful handling when required env vars are missing."""
        with patch.dict(os.environ, {}, clear=True):
            from say_hello_to_authorized_customer.config import load_config
            with pytest.raises(ValueError, match="Missing required environment variable"):
                load_config()


class TestOAuth2CallbackServer:
    """Tests for OAuth2 callback server functionality."""

    def test_callback_server_initialization(self):
        """Server initializes with correct region and endpoints."""
        from say_hello_to_authorized_customer.oauth2_callback_server import OAuth2CallbackServer
        server = OAuth2CallbackServer(region='us-east-1')
        assert server.region == 'us-east-1'
        assert server.app is not None
        assert server.identity_client is not None

    def test_get_oauth2_callback_base_url_localhost(self):
        """Returns correct localhost URL in local environment."""
        from say_hello_to_authorized_customer.oauth2_callback_server import get_oauth2_callback_base_url
        with patch('say_hello_to_authorized_customer.oauth2_callback_server._is_workshop_studio', return_value=False):
            url = get_oauth2_callback_base_url()
            assert url == 'http://localhost:9090'

    def test_store_user_token_identifier(self):
        """User token identifier is stored correctly."""
        from say_hello_to_authorized_customer.oauth2_callback_server import store_token_in_oauth2_callback_server
        mock_identity_client = Mock()
        mock_user_token = Mock()
        mock_server = Mock()
        
        with patch('say_hello_to_authorized_customer.oauth2_callback_server.OAuth2CallbackServer') as MockServer:
            MockServer.return_value = mock_server
            store_token_in_oauth2_callback_server(mock_identity_client, mock_user_token)
            assert mock_server.user_token_identifier == mock_user_token

    def test_ping_endpoint(self):
        """Health check endpoint returns success."""
        from say_hello_to_authorized_customer.oauth2_callback_server import OAuth2CallbackServer
        from fastapi.testclient import TestClient
        
        server = OAuth2CallbackServer(region='us-east-1')
        client = TestClient(server.app)
        response = client.get('/ping')
        assert response.status_code == 200
        assert response.json() == {'status': 'success'}


class TestGatewayConfiguration:
    """Tests for AgentCore Gateway configuration."""

    def test_create_gateway_with_oauth(self):
        """Gateway is created with correct OAuth configuration."""
        from say_hello_to_authorized_customer.gateway_config import create_gateway
        
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            mock_client.create_gateway.return_value = {
                'gatewayArn': 'arn:aws:bedrock:us-east-1:123456789012:gateway/test-gateway'
            }
            
            gateway_arn = create_gateway(
                name='test-gateway',
                google_client_id='test-client-id',
                google_client_secret='test-secret',
                callback_url='http://localhost:9090/oauth2/callback',
                region='us-east-1'
            )
            
            assert gateway_arn.startswith('arn:aws:bedrock')
            mock_client.create_gateway.assert_called_once()

    def test_gateway_oauth_scopes(self):
        """Gateway has correct OAuth scopes (profile, openid)."""
        from say_hello_to_authorized_customer.gateway_config import create_gateway
        
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            mock_client.create_gateway.return_value = {
                'gatewayArn': 'arn:aws:bedrock:us-east-1:123456789012:gateway/test-gateway'
            }
            
            create_gateway(
                name='test-gateway',
                google_client_id='test-client-id',
                google_client_secret='test-secret',
                callback_url='http://localhost:9090/oauth2/callback',
                region='us-east-1'
            )
            
            call_args = mock_client.create_gateway.call_args
            # Verify OAuth scopes are in the configuration
            assert 'profile' in str(call_args)
            assert 'openid' in str(call_args)

    def test_delete_gateway(self):
        """Gateway cleanup works correctly."""
        from say_hello_to_authorized_customer.gateway_config import delete_gateway
        
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            delete_gateway(
                gateway_arn='arn:aws:bedrock:us-east-1:123456789012:gateway/test-gateway',
                region='us-east-1'
            )
            
            mock_client.delete_gateway.assert_called_once()


class TestIdentityConfiguration:
    """Tests for AgentCore Identity configuration."""

    def test_create_workload_identity(self):
        """Workload identity is created with callback URL."""
        from say_hello_to_authorized_customer.identity_config import create_workload_identity
        
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            mock_client.create_workload_identity.return_value = {
                'workloadIdentityArn': 'arn:aws:bedrock:us-east-1:123456789012:workload-identity/test-identity'
            }
            
            identity_arn = create_workload_identity(
                name='test-identity',
                callback_url='http://localhost:9090/oauth2/callback',
                region='us-east-1'
            )
            
            assert identity_arn.startswith('arn:aws:bedrock')
            mock_client.create_workload_identity.assert_called_once()

    def test_get_user_token_identifier_from_jwt(self):
        """User identifier is extracted from JWT sub claim."""
        from say_hello_to_authorized_customer.identity_config import get_user_token_identifier
        
        # Mock JWT token with sub claim
        mock_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIn0.test'
        
        with patch('jwt.decode', return_value={'sub': 'user123'}):
            user_identifier = get_user_token_identifier(mock_token)
            assert user_identifier is not None

    def test_delete_workload_identity(self):
        """Identity cleanup works correctly."""
        from say_hello_to_authorized_customer.identity_config import delete_workload_identity
        
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            delete_workload_identity(
                identity_arn='arn:aws:bedrock:us-east-1:123456789012:workload-identity/test-identity',
                region='us-east-1'
            )
            
            mock_client.delete_workload_identity.assert_called_once()


class TestAgentImplementation:
    """Tests for agent implementation and behavior."""

    def test_create_agent_with_gateway(self):
        """Agent is created with Gateway tools."""
        # This test verifies the function exists and has correct signature
        # Actual agent creation requires strands_agents which is runtime dependency
        from say_hello_to_authorized_customer.agent import create_agent
        import inspect
        
        sig = inspect.signature(create_agent)
        assert 'gateway_arn' in sig.parameters
        assert 'region' in sig.parameters

    def test_detect_elicitation_response(self):
        """Agent detects elicitation URL from Gateway response."""
        from say_hello_to_authorized_customer.agent import detect_elicitation
        
        mock_response = {
            'type': 'elicitation',
            'url': 'https://accounts.google.com/o/oauth2/auth?...'
        }
        
        is_elicitation, url = detect_elicitation(mock_response)
        assert is_elicitation is True
        assert url.startswith('https://accounts.google.com')

    def test_greet_user_with_profile_name(self):
        """Agent formats greeting with user's profile name."""
        from say_hello_to_authorized_customer.agent import format_greeting
        
        profile_data = {
            'names': [{'displayName': 'John Doe'}]
        }
        
        greeting = format_greeting(profile_data)
        assert 'John Doe' in greeting
        assert 'Hello' in greeting
