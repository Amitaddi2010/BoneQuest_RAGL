import urllib.request
import json
import time

def check(url):
    print(f"Checking {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read().decode('utf-8')
            print(f"[{r.status}] {body}")
    except Exception as e:
        print(f"Error: {e}")

check("https://bonequest-ragl.onrender.com/api/health")
check("https://bone-quest-ragl-3xko.vercel.app/api/health")
