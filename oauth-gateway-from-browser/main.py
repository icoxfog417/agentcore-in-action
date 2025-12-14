"""Demonstration entry point for YouTube OAuth agent"""
import argparse
import json
import os
import sys
import boto3
import uvicorn
from dotenv import load_dotenv
from oauth2_callback_server import OAuth2CallbackServer

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
CONFIG_FILE = "config.json"


def create_cognito_user(user_pool_id, username, password):
    """Create Cognito user with permanent password"""
    cognito_client = boto3.client("cognito-idp", region_name=REGION)
    
    try:
        cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            TemporaryPassword=password,
            MessageAction="SUPPRESS"
        )
        
        cognito_client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True
        )
        
        print(f"✓ Created user: {username}")
    except cognito_client.exceptions.UsernameExistsException:
        print(f"User {username} already exists")


def main():
    parser = argparse.ArgumentParser(description="YouTube OAuth Agent Demo")
    parser.add_argument("--signup", action="store_true", help="Create new Cognito user")
    parser.add_argument("--username", help="Username for signup")
    parser.add_argument("--password", help="Password for signup")
    args = parser.parse_args()
    
    # Load config
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run construct.py first.")
        sys.exit(1)
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    # Handle signup mode
    if args.signup:
        if not args.username or not args.password:
            print("Error: --username and --password required for signup")
            sys.exit(1)
        
        create_cognito_user(config["user_pool_id"], args.username, args.password)
        return
    
    # Start OAuth2 callback server
    print("Starting OAuth2 callback server...")
    print("Open http://localhost:8080 in your browser")
    
    server = OAuth2CallbackServer(region=REGION, config=config)
    uvicorn.run(server.app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
