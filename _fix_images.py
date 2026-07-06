#!/usr/bin/env python3
"""Fix images: use curl for Pexels (bypass proxy), boto3 for R2"""
import json, io, subprocess, os, time
from pathlib import Path
from urllib.parse import quote_plus
import concurrent.futures

ARTICLES_DIR = Path.home() / "site-builds" / "unistay-cn" / "src" / "content" / "articles"
STATE_FILE = Path.home() / "site-builds" / "unistay-cn" / "_bulk_gen_state.json"

CREDS = json.load(open(Path.home() / "Library/CloudStorage/Dropbox-Personal/cowork/cowork-cloud-tools/credentials.json"))
PEXELS_KEY = CREDS["pexels"]["api_key"]
R2_KEY = CREDS["r2"]["access_key_id"]
R2_SECRET = CREDS["r2"]["secret_access_key"]
R2_ENDPOINT = CREDS["r2"]["s3_endpoint"]
R2_BUCKET = CREDS["r2"]["bucket"]
R2_PUBLIC = CREDS["r2"]["public_url"]

import boto3
from botocore.config import Config
s3 = boto3.client('s3', endpoint_url=R2_ENDPOINT, aws_access_key_id=R2_KEY,
                  aws_secret_access_key=R2_SECRET,
                  config=Config(signature_version='s3v4'), region_name='auto')

# Proxy-free env for curl
CURL_ENV = os.environ.copy()
for k in ["http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY","all_proxy","ALL_PROXY"]:
    CURL_ENV.pop(k, None)
CURL_ENV["no_proxy"] = "*"
CURL_ENV["NO_PROXY"] = "*"

state = json.load(open(STATE_FILE))
completed = set(state["completed"])

def get_pexels_image(query):
    for attempt in range(3):
        q = query if attempt == 0 else f"{query.split()[0]} university building"
        q_enc = quote_plus(q)
        result = subprocess.run([
            "curl", "-s", "--max-time", "10",
            "-H", f"Authorization: {PEXELS_KEY}",
            f"https://api.pexels.com/v1/search?query={q_enc}&per_page=5&orientation=landscape&size=large"
        ], capture_output=True, text=True, env=CURL_ENV, timeout=12)
        if result.returncode != 0:
            continue
        try:
            data = json.loads(result.stdout)
            photos = data.get("photos", [])
            if photos:
                src = photos[0]["src"]
                return src.get("large2x") or src.get("large") or src["original"]
        except:
            continue
    return None

def download_image(url):
    result = subprocess.run(["curl", "-sL", "--max-time", "20", "-o", "-", url],
                          capture_output=True, env=CURL_ENV, timeout=25)
    if result.returncode == 0 and len(result.stdout) > 1000:
        return result.stdout
    return None

def upload_to_r2(image_data, slug):
    key = f"unistay/{slug}.jpg"
    s3.upload_fileobj(io.BytesIO(image_data), R2_BUCKET, key,
                      ExtraArgs={'ContentType': 'image/jpeg', 'ACL': 'public-read'})
    return f"{R2_PUBLIC}/{key}"

def process_article(slug):
    filepath = ARTICLES_DIR / f"{slug}.md"
    if not filepath.exists():
        return f"{slug}: file not found"
    
    content = filepath.read_text(encoding="utf-8")
    if "PLACEHOLDER" not in content:
        if "heroImage:" in content and "img.ulec.com.cn" in content:
            return f"{slug}: already has image"
    
    lines = content.split("\n")
    title = ""
    category = ""
    for line in lines[:30]:
        if line.startswith("title:"):
            title = line.split(":",1)[1].strip().strip('"')
        if line.startswith("category:"):
            category = line.split(":",1)[1].strip().strip('"')
    
    search_terms = [category] if category else []
    if title:
        parts = title.replace("：",":").split(":")
        search_terms.insert(0, parts[0])
    
    query = " ".join(search_terms[:2]) + " university campus building"
    
    img_url = get_pexels_image(query)
    if not img_url:
        img_url = get_pexels_image("modern university campus")
    if not img_url:
        return f"{slug}: no image"
    
    img_data = download_image(img_url)
    if not img_data:
        return f"{slug}: download failed"
    
    try:
        r2_url = upload_to_r2(img_data, slug)
    except Exception as e:
        return f"{slug}: R2 error: {e}"
    
    content = content.replace("PLACEHOLDER", r2_url)
    filepath.write_text(content, encoding="utf-8")
    return f"{slug}: OK"

# Run
print(f"Processing {len(completed)} articles...")
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_article, slug): slug for slug in completed}
    for f in concurrent.futures.as_completed(futures):
        slug = futures[f]
        try:
            r = f.result()
            print(r)
            results.append(r)
        except Exception as e:
            print(f"{slug}: {e}")

ok = [r for r in results if ": OK" in r]
print(f"\nDone: {len(ok)} OK / {len(results)} total")
