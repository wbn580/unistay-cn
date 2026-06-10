#!/usr/bin/env python3
"""
Batch hero image fetcher for unistay-cn articles.
Uses Pexels API → downloads → uploads to R2 → updates frontmatter.
"""
import json, os, sys, time, re, hashlib, io, random
import requests
import boto3
from pathlib import Path

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "src" / "content" / "articles"
CREDS_PATH = os.path.expanduser("~/Library/CloudStorage/Dropbox-Personal/cowork/cowork-cloud-tools/credentials.json")
CATALOG_PATH = os.path.expanduser("~/Library/CloudStorage/Dropbox-Personal/cowork/cowork-cloud-tools/r2-image-catalog.json")

# Load creds
creds = json.load(open(CREDS_PATH))
PEXELS_KEY = creds["pexels"]["api_key"]
R2 = creds["r2"]

s3 = boto3.client(
    "s3",
    endpoint_url=R2["endpoint"],
    aws_access_key_id=R2["access_key_id"],
    aws_secret_access_key=R2["secret_access_key"],
)
BUCKET = R2["bucket"]
PUBLIC_URL = R2["public_url"]  # https://img.ulec.com.cn

# City/theme keyword mapping for English search queries
CITY_MAP = {
    "悉尼": "Sydney", "墨尔本": "Melbourne", "布里斯班": "Brisbane",
    "伦敦": "London", "曼彻斯特": "Manchester", "伯明翰": "Birmingham",
    "爱丁堡": "Edinburgh", "格拉斯哥": "Glasgow", "利兹": "Leeds",
    "纽约": "New York", "洛杉矶": "Los Angeles", "波士顿": "Boston",
    "多伦多": "Toronto", "温哥华": "Vancouver", "蒙特利尔": "Montreal",
    "奥克兰": "Auckland", "惠灵顿": "Wellington", "基督城": "Christchurch",
    "新加坡": "Singapore", "香港": "Hong Kong", "东京": "Tokyo",
    "首尔": "Seoul", "都柏林": "Dublin", "巴黎": "Paris",
    "柏林": "Berlin", "阿姆斯特丹": "Amsterdam",
    "堪培拉": "Canberra", "珀斯": "Perth", "阿德莱德": "Adelaide",
    "黄金海岸": "Gold Coast", "霍巴特": "Hobart", "达尔文": "Darwin",
}
THEME_MAP = {
    "学生公寓": "student apartment", "合租": "shared apartment",
    "studio": "studio apartment", "en-suite": "ensuite room",
    "租房": "rental apartment", "宿舍": "dormitory",
    "寄宿家庭": "homestay", "长租": "long term rental",
    "短租": "short term rental", "押金": "apartment deposit",
    "合同": "rental contract", "退租": "moving out",
    "找房": "apartment hunting", "租金": "apartment rent",
    "房型": "room type", "预算": "budget apartment",
    "安全": "safe neighborhood", "交通": "commute apartment",
    "续租": "lease renewal", "转租": "sublet apartment",
    "水电网": "utilities apartment", "室友": "roommate",
    "独立空间": "private room", "性价比": "affordable housing",
    "高端": "luxury apartment", "校内": "campus housing",
    "校外": "off campus housing", "PBSA": "PBSA student accommodation",
}

def extract_keywords(title: str) -> str:
    """Extract English search keywords from Chinese title."""
    parts = []
    # Check cities
    for cn, en in CITY_MAP.items():
        if cn in title:
            parts.append(en)
    # Check themes
    for cn, en in THEME_MAP.items():
        if cn.lower() in title.lower():
            parts.append(en)
    # If no matches, use generic housing terms based on content hints
    if not parts:
        if "留学" in title or "海外" in title or "国际" in title:
            parts.append("international student housing")
        else:
            parts.append("student accommodation building")
    # Add "interior" for variety if only city
    if len(parts) == 1:
        parts.append("building exterior")
    query = " ".join(parts[:3])
    return query

def search_pexels(query: str, used_ids: set) -> dict | None:
    """Search Pexels, skip already-used photo IDs."""
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 15, "orientation": "landscape", "size": "large"},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"  Pexels API error: {r.status_code} {r.text[:100]}")
            return None
        data = r.json()
        photos = [p for p in data.get("photos", []) if p["id"] not in used_ids]
        if not photos:
            print(f"  No unused photos for '{query}', retrying without dedup")
            photos = data.get("photos", [])
        if not photos:
            return None
        # Pick a random one from top results for variety
        return random.choice(photos[:min(8, len(photos))])
    except Exception as e:
        print(f"  Pexels error: {e}")
        return None

def download_image(url: str) -> bytes | None:
    """Download image bytes."""
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        print(f"  Download error: {e}")
    return None

def upload_to_r2(data: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Upload to R2, return public URL."""
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
    return f"{PUBLIC_URL}/{key}"

def patch_frontmatter(filepath: Path, hero_url: str):
    """Add heroImage and ogImage to frontmatter (after tags line)."""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # Find end of frontmatter (second ---)
    fm_end = None
    dash_count = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            dash_count += 1
            if dash_count == 2:
                fm_end = i
                break
    
    if fm_end is None:
        print(f"  WARNING: no frontmatter end found in {filepath.name}")
        return False
    
    # Find where to insert (before the closing ---)
    new_lines = lines[:fm_end] + [
        f"heroImage: \"{hero_url}\"",
        f"ogImage: \"{hero_url}\"",
    ] + lines[fm_end:]
    
    filepath.write_text("\n".join(new_lines), encoding="utf-8")
    return True

def load_catalog() -> dict:
    """Load or create image catalog."""
    if os.path.exists(CATALOG_PATH):
        try:
            return json.load(open(CATALOG_PATH))
        except:
            pass
    return {"images": {}, "used_pexels_ids": []}

def save_catalog(cat: dict):
    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    tmp = CATALOG_PATH + ".tmp"
    json.dump(cat, open(tmp, "w"), indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG_PATH)

def main():
    catalog = load_catalog()
    used_ids = set(catalog.get("used_pexels_ids", []))
    
    # Find all .md files without heroImage
    articles = []
    for md in sorted(ARTICLES_DIR.glob("*.md")):
        if md.name.endswith(".bak"):
            continue
        content = md.read_text(encoding="utf-8")
        if "heroImage:" in content:
            continue
        # Extract title
        m = re.search(r'^title:\s*"([^"]*)"', content, re.MULTILINE)
        title = m.group(1) if m else md.stem
        articles.append((md, title))
    
    total = len(articles)
    print(f"=== Processing {total} articles without heroImage ===")
    
    success = 0
    fail = 0
    rate_limit_wait = 1.5  # seconds between Pexels API calls
    
    for i, (filepath, title) in enumerate(articles):
        print(f"\n[{i+1}/{total}] {filepath.name}")
        print(f"  Title: {title[:80]}...")
        
        # Generate search query
        query = extract_keywords(title)
        print(f"  Query: {query}")
        
        # Search Pexels
        time.sleep(rate_limit_wait)
        photo = search_pexels(query, used_ids)
        if not photo:
            print(f"  FAILED: No photo found")
            fail += 1
            continue
        
        photo_id = photo["id"]
        img_url = photo["src"]["large"]  # 940x650
        photographer = photo["photographer"]
        print(f"  Photo: {photo_id} by {photographer}")
        
        # Download
        img_data = download_image(img_url)
        if not img_data:
            print(f"  FAILED: Download error")
            fail += 1
            continue
        
        # Generate R2 key
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', title[:60].lower()).strip('-')
        if not slug:
            slug = f"article-{i}"
        ext = ".jpg"
        r2_key = f"unistay/{slug}-{photo_id}{ext}"
        
        # Upload
        try:
            r2_url = upload_to_r2(img_data, r2_key)
            print(f"  Uploaded: {r2_url}")
        except Exception as e:
            print(f"  FAILED: R2 upload error: {e}")
            fail += 1
            continue
        
        # Patch frontmatter
        if patch_frontmatter(filepath, r2_url):
            used_ids.add(photo_id)
            success += 1
            print(f"  OK: heroImage + ogImage added")
        else:
            print(f"  WARNING: frontmatter patch failed")
            fail += 1
        
        # Save catalog every 10 articles
        if success % 10 == 0:
            catalog["used_pexels_ids"] = sorted(used_ids)
            save_catalog(catalog)
    
    # Final save
    catalog["used_pexels_ids"] = sorted(used_ids)
    save_catalog(catalog)
    
    print(f"\n=== DONE: {success} success, {fail} failed, {total} total ===")
    
    # Verify: check first line of all md files
    print("\n=== Verifying frontmatter (first line must be ---) ===")
    broken = []
    for md in sorted(ARTICLES_DIR.glob("*.md")):
        if md.name.endswith(".bak"):
            continue
        first = md.read_text(encoding="utf-8")[:10]
        if not first.startswith("---"):
            broken.append(md.name)
    if broken:
        print(f"BROKEN FILES ({len(broken)}):")
        for b in broken:
            print(f"  {b}")
    else:
        print("All files OK")

if __name__ == "__main__":
    main()
