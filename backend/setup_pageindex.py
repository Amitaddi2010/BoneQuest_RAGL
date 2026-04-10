"""
Download and install PageIndex library into backend/lib/PageIndex/
Run this script once: python setup_pageindex.py
"""
import os
import urllib.request
import ssl

# Bypass SSL verification for corporate/proxy environments
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE_URL = "https://raw.githubusercontent.com/VectifyAI/PageIndex/main/pageindex/"
FILES = [
    "__init__.py",
    "client.py",
    "config.yaml",
    "page_index.py",
    "page_index_md.py",
    "retrieve.py",
    "utils.py",
]

TARGET_DIR = os.path.join(os.path.dirname(__file__), "lib", "PageIndex", "pageindex")
os.makedirs(TARGET_DIR, exist_ok=True)

print(f"Downloading PageIndex files to: {TARGET_DIR}")
for fname in FILES:
    url = BASE_URL + fname
    target = os.path.join(TARGET_DIR, fname)
    print(f"  Downloading {fname}...", end=" ", flush=True)
    try:
        urllib.request.urlretrieve(url, target, context=ctx)
        print("✓")
    except Exception as e:
        # Try without SSL context
        try:
            urllib.request.urlretrieve(url, target)
            print("✓")
        except Exception as e2:
            print(f"✗ ({e2})")

print("\nDone! PageIndex is now available at lib/PageIndex/pageindex/")
print("You can now restart the server: python main.py")
