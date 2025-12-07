"""Agent implementation for greeting users."""


def create_agent(gateway_arn: str, region: str):
    """Create agent with Gateway tools."""
    from strands_agents import Agent
    
    agent = Agent(
        name="GreetingAgent",
        tools=[gateway_arn],
        region=region
    )
    return agent


def detect_elicitation(response: dict) -> tuple[bool, str]:
    """Detect elicitation URL from Gateway response."""
    if response.get('type') == 'elicitation':
        return True, response.get('url', '')
    return False, ''


def format_greeting(profile_data: dict) -> str:
    """Format greeting message with user's profile name."""
    name = profile_data.get('names', [{}])[0].get('displayName', 'User')
    return f"Hello, {name}!"
