#!/usr/bin/env python3
"""
Seed script to add demo companies for testing
Run: python seed_data.py
"""

import asyncio
import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

DEMO_COMPANIES = [
    {
        "company_name": "Stripe",
        "company_url": "https://stripe.com",
        "extra_urls": ["https://stripe.com/about"]
    },
    {
        "company_name": "Shopify", 
        "company_url": "https://www.shopify.com",
        "extra_urls": ["https://www.shopify.com/about"]
    },
    {
        "company_name": "Notion",
        "company_url": "https://www.notion.so",
        "extra_urls": ["https://www.notion.so/product"]
    },
    {
        "company_name": "Figma",
        "company_url": "https://www.figma.com",
        "extra_urls": ["https://www.figma.com/about/"]
    },
    {
        "company_name": "Airtable",
        "company_url": "https://airtable.com",
        "extra_urls": ["https://airtable.com/product"]
    }
]

def create_prospect(company_data):
    """Create a prospect via API"""
    try:
        print(f"Creating prospect for {company_data['company_name']}...")
        
        response = requests.post(
            f"{API_BASE}/prospects/create",
            json=company_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Created account ID {result['account_id']} in {result['processing_time']:.1f}s")
            return result['account_id']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating {company_data['company_name']}: {str(e)}")
        return None

def generate_profile(account_id, company_name):
    """Generate profile for account"""
    try:
        print(f"Generating profile for {company_name}...")
        
        response = requests.post(
            f"{API_BASE}/accounts/{account_id}/generate_profile",
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            coverage = result.get('provenance_coverage', 0)
            print(f"✅ Profile generated with {coverage:.0%} provenance coverage")
            return True
        else:
            print(f"❌ Profile error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating profile for {company_name}: {str(e)}")
        return False

def generate_assets(account_id, company_name):
    """Generate assets for account"""
    try:
        print(f"Generating assets for {company_name}...")
        
        response = requests.post(
            f"{API_BASE}/accounts/{account_id}/generate_assets",
            json={"persona": "Exec"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Assets generated in {result['processing_time']:.1f}s")
            return True
        else:
            print(f"❌ Assets error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating assets for {company_name}: {str(e)}")
        return False

def main():
    """Main seeding function"""
    print("🌱 Source-to-Sell Demo Data Seeder")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not responding. Make sure the backend is running.")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API. Make sure the backend is running on http://localhost:8000")
        return
    
    print(f"✅ API is running at {API_BASE}")
    print()
    
    successful_accounts = []
    
    # Create prospects
    for company_data in DEMO_COMPANIES:
        account_id = create_prospect(company_data)
        if account_id:
            successful_accounts.append((account_id, company_data['company_name']))
        print()
    
    # Generate profiles and assets for successful accounts
    if successful_accounts:
        print("🔄 Generating profiles and assets...")
        print()
        
        for account_id, company_name in successful_accounts:
            if generate_profile(account_id, company_name):
                generate_assets(account_id, company_name)
            print()
    
    print("=" * 50)
    print(f"✅ Seeding complete! Created {len(successful_accounts)} demo accounts.")
    print(f"🔗 Open the dashboard: {API_BASE}")
    print()
    print("Next steps:")
    print("1. Install the Chrome extension")
    print("2. Visit a company website and capture a prospect")
    print("3. Generate profiles and assets")

if __name__ == "__main__":
    main()