#!/usr/bin/env python3
"""Test script to verify API configuration status endpoint"""

import os
import requests
import json

# Get API URL and key from environment
API_URL = os.getenv('VITE_API_URL', 'http://localhost:8088')
API_KEY = os.getenv('API_KEY', 'not-secure-api-key')

# Test the configuration status endpoint
print(f"Testing configuration status endpoint at {API_URL}/settings/status")
print(f"Using API key: {API_KEY[:4]}...{API_KEY[-4:] if len(API_KEY) > 8 else ''}")

headers = {'X-API-Key': API_KEY}

try:
    response = requests.get(f"{API_URL}/settings/status", headers=headers)
    response.raise_for_status()
    
    data = response.json()
    print(f"\nConfiguration Status:")
    print(f"  Configured: {data.get('configured', False)}")
    print(f"  Has API Credentials: {data.get('has_api_credentials', False)}")
    
    # Also check providers
    print("\nChecking providers...")
    response = requests.get(f"{API_URL}/settings/providers", headers=headers)
    response.raise_for_status()
    
    providers_data = response.json()
    print(f"Current Provider: {providers_data.get('current_provider')}")
    print("\nAvailable Providers:")
    for provider in providers_data.get('providers', []):
        status = "✓" if provider['available'] else "✗"
        print(f"  {status} {provider['name']} ({provider['provider']})")
        if provider['available']:
            print(f"    - Credentials: {provider.get('credentials', {})}")
    
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Response: {e.response.text}")