#!/usr/bin/env python3
"""
Download GitHub Actions workflows from top 100 repositories.

This script downloads all .yml and .yaml files from the .github/workflows directory
of each repository in the top-100-repos-filtered.json file and saves them in a flat
directory structure with the naming convention: author_repo_filename
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_API_BASE = "https://api.github.com"
REPOS_JSON_PATH = "scripts/top-100-repos-filtered.json"
OUTPUT_DIR = "scripts/top-100-workflows"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

if not GITHUB_TOKEN:
    print("Error: GH_TOKEN environment variable is required")
    sys.exit(1)

# Headers for GitHub API requests
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "validate-actions-workflow-downloader"
}


def load_repositories() -> List[Dict]:
    """Load the list of repositories from JSON file."""
    repos_file = Path(REPOS_JSON_PATH)
    if not repos_file.exists():
        print(f"Error: Repository file {REPOS_JSON_PATH} not found")
        sys.exit(1)
    
    with open(repos_file, 'r') as f:
        return json.load(f)


def create_output_directory():
    """Create the output directory if it doesn't exist."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be filesystem-safe."""
    # Replace problematic characters
    sanitized = filename.replace("/", "_").replace("\\", "_").replace(":", "_")
    sanitized = sanitized.replace("<", "_").replace(">", "_").replace("|", "_")
    sanitized = sanitized.replace("?", "_").replace("*", "_").replace('"', "_")
    return sanitized


def get_workflow_files(owner: str, repo: str) -> List[Dict]:
    """Get list of workflow files from a repository's .github/workflows directory."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/.github/workflows"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 404:
            print(f"  No .github/workflows directory found in {owner}/{repo}")
            return []
        
        if response.status_code != 200:
            print(f"  Error fetching workflow list from {owner}/{repo}: {response.status_code}")
            if response.status_code == 403:
                print(f"  Rate limit or permissions issue: {response.json().get('message', '')}")
            return []
        
        files = response.json()
        workflow_files = [
            f for f in files 
            if f['type'] == 'file' and f['name'].endswith(('.yml', '.yaml'))
        ]
        
        return workflow_files
    
    except requests.RequestException as e:
        print(f"  Request error for {owner}/{repo}: {e}")
        return []


def download_workflow_file(owner: str, repo: str, file_info: Dict, output_dir: Path) -> bool:
    """Download a single workflow file."""
    filename = file_info['name']
    download_url = file_info['download_url']
    
    # Create output filename: author_repo_filename
    sanitized_owner = sanitize_filename(owner)
    sanitized_repo = sanitize_filename(repo)
    sanitized_filename = sanitize_filename(filename)
    output_filename = f"{sanitized_owner}_{sanitized_repo}_{sanitized_filename}"
    output_path = output_dir / output_filename
    
    try:
        response = requests.get(download_url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"    Error downloading {filename}: {response.status_code}")
            return False
        
        # Write the file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"    Downloaded: {output_filename}")
        return True
    
    except requests.RequestException as e:
        print(f"    Request error downloading {filename}: {e}")
        return False
    except Exception as e:
        print(f"    Error writing {filename}: {e}")
        return False


def check_rate_limit():
    """Check current rate limit status."""
    url = f"{GITHUB_API_BASE}/rate_limit"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            rate_limit = response.json()
            core = rate_limit['resources']['core']
            remaining = core['remaining']
            reset_time = core['reset']
            
            print(f"Rate limit: {remaining} requests remaining")
            
            if remaining < 10:
                wait_time = reset_time - int(time.time()) + 1
                print(f"Rate limit low, waiting {wait_time} seconds...")
                time.sleep(wait_time)
                
    except Exception as e:
        print(f"Could not check rate limit: {e}")


def main():
    """Main function to download all workflow files."""
    print("Loading repositories...")
    repositories = load_repositories()
    print(f"Found {len(repositories)} repositories")
    
    print("Creating output directory...")
    output_dir = create_output_directory()
    print(f"Output directory: {output_dir.absolute()}")
    
    total_files = 0
    successful_downloads = 0
    
    for i, repo_info in enumerate(repositories, 1):
        owner = repo_info['owner']
        repo = repo_info['repo']
        
        print(f"\n[{i}/{len(repositories)}] Processing {owner}/{repo}")
        
        # Check rate limit every 10 repositories
        if i % 10 == 0:
            check_rate_limit()
        
        # Get workflow files
        workflow_files = get_workflow_files(owner, repo)
        
        if not workflow_files:
            continue
        
        print(f"  Found {len(workflow_files)} workflow files")
        total_files += len(workflow_files)
        
        # Download each workflow file
        for file_info in workflow_files:
            if download_workflow_file(owner, repo, file_info, output_dir):
                successful_downloads += 1
            
            # Small delay to be respectful to the API
            time.sleep(0.1)
    
    print(f"\n=== Download Summary ===")
    print(f"Total workflow files found: {total_files}")
    print(f"Successfully downloaded: {successful_downloads}")
    print(f"Failed downloads: {total_files - successful_downloads}")
    print(f"Output directory: {output_dir.absolute()}")
    
    if successful_downloads > 0:
        print(f"\nFiles saved with naming convention: author_repo_filename")
        print("Example: facebook_react_ci.yml")


if __name__ == "__main__":
    main()