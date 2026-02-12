import requests
import json
from packaging import version

CURRENT_VERSION = "1.3.0"
GITHUB_REPO = "bbqqvv/AnonymNotes"

def check_for_updates():
    """
    Check GitHub for latest release.
    Returns: (has_update: bool, latest_version: str, download_url: str, error: str)
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 404:
             return False, CURRENT_VERSION, "", "Release not found (Repo private or no releases?)"
        
        if response.status_code != 200:
            return False, CURRENT_VERSION, "", f"API Error: {response.status_code}"
        
        data = response.json()
        latest_version = data.get("tag_name", "").lstrip("v")
        download_url = data.get("html_url", "")
        
        if not latest_version:
            return False, CURRENT_VERSION, "", "No version found"
        
        # Compare versions
        has_update = version.parse(latest_version) > version.parse(CURRENT_VERSION)
        
        return has_update, latest_version, download_url, ""
        
    except Exception as e:
        return False, CURRENT_VERSION, "", str(e)
