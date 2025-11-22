import sys, requests

REPO = "RokctAI/rpanel"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

try:
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    tag = data.get("tag_name")
    if not tag:
        sys.stderr.write("No tag_name found in release data\n")
        sys.exit(1)
    print(tag)
except Exception as e:
    sys.stderr.write(f"Failed to fetch latest release: {e}\n")
    sys.exit(1)
