#!/usr/bin/env python3
"""
unistay.cn 全面铺量 — 80篇学生公寓文章批量生成
Track A (45): 国家 × 住宿关键词
Track B (35): 大学 × 住宿关键词
"""

import json, os, re, sys, time, hashlib, random, uuid, io
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.parse import quote

# ── config ──────────────────────────────────────────────
SITE_DIR = Path.home() / "site-builds" / "unistay-cn"
ARTICLES_DIR = SITE_DIR / "src" / "content" / "articles"
STATE_FILE = SITE_DIR / "_bulk_gen_state.json"

CREDS = json.load(open(Path.home() / "Library/CloudStorage/Dropbox-Personal/cowork/cowork-cloud-tools/credentials.json"))
DS_KEY = CREDS["deepseek"]["api_key"]
DS_ENDPOINT = CREDS["deepseek"]["endpoint"]
DS_MODEL = CREDS["deepseek"]["pro_model"]
PEXELS_KEY = CREDS["pexels"]["api_key"]
R2_KEY = CREDS["r2"]["access_key_id"]
R2_SECRET = CREDS["r2"]["secret_access_key"]
R2_ENDPOINT = CREDS["r2"]["s3_endpoint"]
R2_BUCKET = CREDS["r2"]["bucket"]
R2_PUBLIC = CREDS["r2"]["public_url"]

MAX_WORKERS = 8
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

# ── dedup: read existing article titles ─────────────────
def get_existing_slugs():
    slugs = set()
    for f in ARTICLES_DIR.glob("*.md"):
        name = f.stem
        slugs.add(name.lower().replace(" ", ""))
        # Also read title from frontmatter
        try:
            content = f.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = parts[1]
                    for line in fm.split("\n"):
                        if line.startswith("title:"):
                            t = line.split(":", 1)[1].strip().strip('"').strip("'")
                            slugs.add(t.lower().replace(" ", ""))
        except:
            pass
    return slugs

EXISTING = get_existing_slugs()
print(f"Existing articles: {len(EXISTING)}")

# ── Topic generation ────────────────────────────────────
COUNTRIES = {
    "澳大利亚": ["学生公寓", "PBSA专建学生公寓", "宿舍vs校外租房", "租房合同关键条款", "押金bond退还", "房型对比studio ensuite", "租金水平与预算", "水电网杂费", "找房时间线", "租房避坑防骗", "homestay寄宿", "通勤与选区", "学生公寓品牌怎么选"],
    "英国": ["学生公寓", "PBSA专建学生公寓", "宿舍vs校外租房", "租房合同关键条款", "押金bond退还", "房型对比studio ensuite", "租金水平与预算", "水电网杂费", "找房时间线", "租房避坑防骗", "homestay寄宿", "通勤与选区"],
    "美国": ["学生公寓怎么找", "宿舍vs校外租房", "租房合同关键条款", "押金退还", "房型对比", "租金水平与预算", "水电网杂费", "找房时间线", "租房避坑防骗", "通勤与选区"],
    "加拿大": ["学生公寓怎么找", "宿舍vs校外租房", "租房合同关键条款", "押金退还", "租金水平与预算", "房型对比", "找房时间线"],
    "新西兰": ["学生公寓怎么找", "宿舍vs校外租房", "租金水平与预算", "租房避坑指南"],
    "新加坡": ["学生公寓怎么找", "宿舍vs校外租房", "租金水平与预算", "租房合同注意"],
    "爱尔兰": ["学生公寓怎么找", "宿舍vs校外租房", "租金水平与预算", "租房避坑指南"],
    "欧洲": ["学生公寓怎么找(英授国家)", "宿舍vs校外租房", "租金水平与预算"],
}

UNIVERSITIES = {
    "澳大利亚": ["悉尼大学USYD", "新南威尔士大学UNSW", "莫纳什大学Monash", "昆士兰大学UQ", "澳国立ANU", "墨尔本大学UMelb", "阿德莱德大学", "西澳大学UWA"],
    "英国": ["伦敦大学学院UCL", "伦敦国王学院KCL", "伦敦政治经济学院LSE", "帝国理工IC", "曼彻斯特大学", "爱丁堡大学", "利兹大学", "布里斯托大学", "华威大学", "谢菲尔德大学"],
    "美国": ["纽约大学NYU", "哥伦比亚大学", "加州大学洛杉矶UCLA", "波士顿大学BU"],
    "加拿大": ["多伦多大学UofT", "不列颠哥伦比亚大学UBC", "麦吉尔大学McGill"],
    "香港": ["香港大学", "香港中文大学", "香港科技大学", "香港城市大学"],
    "新西兰": ["奥克兰大学", "奥塔哥大学"],
    "新加坡": ["新加坡国立大学NUS", "南洋理工大学NTU"],
    "爱尔兰": ["都柏林大学UCD", "都柏林圣三一学院Trinity"],
}

UNI_KEYWORDS = ["周边学生公寓推荐区域", "校内宿舍vs校外公寓", "到校通勤时间", "周边租金范围", "找房攻略"]

def dedup_check(title):
    """Check if title is too similar to existing"""
    normalized = title.lower().replace(" ", "").replace("·","").replace("：","").replace(":","")
    for e in EXISTING:
        e_norm = e.replace(" ", "").replace("·","").replace("：","").replace(":","")
        # Check substring overlap
        if normalized in e_norm or e_norm in normalized:
            return True
        # Check high overlap (>70%)
        common = set(normalized) & set(e_norm)
        if len(common) / max(len(normalized), len(e_norm)) > 0.8:
            return True
    return False

def generate_topics():
    topics_a = []
    topics_b = []
    
    # Track A: Country × keyword
    for country, keywords in COUNTRIES.items():
        for kw in keywords:
            title = f"{country}留学生{kw}指南"
            if not dedup_check(title):
                topics_a.append({"title": title, "country": country, "keyword": kw, "track": "A"})
    
    # Track B: University × keyword
    for country, unis in UNIVERSITIES.items():
        for uni in unis:
            for ukw in UNI_KEYWORDS:
                title = f"{uni}{ukw}"
                if not dedup_check(title):
                    topics_b.append({"title": title, "university": uni, "country": country, "keyword": ukw, "track": "B"})
    
    # Select 45 from A, 35 from B
    import random
    random.seed(42)
    random.shuffle(topics_a)
    random.shuffle(topics_b)
    
    selected_a = topics_a[:45]
    selected_b = topics_b[:35]
    
    all_topics = selected_a + selected_b
    random.shuffle(all_topics)
    
    return all_topics, selected_a, selected_b

TOPICS, TOPICS_A, TOPICS_B = generate_topics()
print(f"Generated {len(TOPICS_A)} A-topics + {len(TOPICS_B)} B-topics = {len(TOPICS)} total")

if len(TOPICS) < 80:
    print(f"WARNING: Only {len(TOPICS)} topics generated, need 80!")

# ── LLM call ────────────────────────────────────────────
def call_dspro(system_prompt, user_prompt, temperature=0.7):
    import urllib.request
    data = json.dumps({
        "model": DS_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{DS_ENDPOINT}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DS_KEY}",
        }
    )
    resp = urllib.request.urlopen(req, timeout=180)
    result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]

# ── Image: Pexels search + download ─────────────────────
def get_pexels_image(query, country="", orientation="landscape"):
    search_q = f"{query} {country} student apartment campus"
    url = f"https://api.pexels.com/v1/search?query={quote(search_q)}&per_page=5&orientation={orientation}"
    req = Request(url, headers={"Authorization": PEXELS_KEY})
    resp = json.loads(urlopen(req).read())
    
    if not resp.get("photos"):
        # Fallback: try broader search
        url2 = f"https://api.pexels.com/v1/search?query={quote(query)}&per_page=5&orientation={orientation}"
        req2 = Request(url2, headers={"Authorization": PEXELS_KEY})
        resp2 = json.loads(urlopen(req2).read())
        if not resp2.get("photos"):
            return None, None
        photo = resp2["photos"][0]
    else:
        photo = resp["photos"][0]
    
    img_url = photo["src"]["large2x"] or photo["src"]["large"] or photo["src"]["original"]
    photographer = photo["photographer"]
    photo_url = photo["url"]
    return img_url, photographer

def upload_to_r2(image_data, slug):
    """Upload image to R2 using S3-compatible API"""
    import boto3
    from botocore.config import Config
    
    s3 = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_KEY,
        aws_secret_access_key=R2_SECRET,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )
    
    key = f"unistay/{slug}.jpg"
    s3.upload_fileobj(
        io.BytesIO(image_data),
        R2_BUCKET,
        key,
        ExtraArgs={'ContentType': 'image/jpeg', 'ACL': 'public-read'}
    )
    return f"{R2_PUBLIC}/{key}"

# ── Redline checks ──────────────────────────────────────
def has_markdown_table(text):
    """Check for markdown tables"""
    lines = text.split("\n")
    pipe_lines = 0
    for line in lines:
        if line.strip().startswith("|") and "|" in line[1:]:
            pipe_lines += 1
            if pipe_lines >= 2:
                return True
        else:
            pipe_lines = 0
    return False

def has_brand_names(text):
    """Check for banned brand names (UNILINK etc)"""
    banned = ["UNILINK", "unilink", "Unilink", "优领", "优领教育", "Unilink Education"]
    for b in banned:
        if b in text:
            return True, b
    return False, ""

def has_bad_year_in_title(title):
    """Check title for years before 2026"""
    years = re.findall(r'20\d\d', title)
    for y in years:
        if int(y) < 2026:
            return True, y
    return False, ""

def validate_article(md_text, title):
    """Run all redline checks"""
    errors = []
    
    # 1. Check has table
    if has_markdown_table(md_text):
        errors.append("Contains markdown table")
    
    # 2. Check brand names
    has_brand, brand = has_brand_names(md_text)
    if has_brand:
        errors.append(f"Contains banned brand: {brand}")
    
    # 3. Check title year
    has_year, year = has_bad_year_in_title(title)
    if has_year:
        errors.append(f"Title has year {year} (only 2026/2027 allowed)")
    
    # 4. Check frontmatter starts with ---
    if not md_text.strip().startswith("---"):
        errors.append("Frontmatter doesn't start with ---")
    
    # 5. Check word count (1200-2000 Chinese chars approx)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', md_text))
    if chinese_chars < 800:
        errors.append(f"Too short: {chinese_chars} Chinese chars (min ~1000)")
    
    return errors

# ── Article generation ──────────────────────────────────
SYSTEM_PROMPT = """你是一位资深留学生活编辑，为 unistay.cn（留学生公寓指南网站）写作。遵守以下红线：

## 写作要求
- 字数：1200-2000字，实用攻略风格（lifestyle + 实操）
- 结构：开头痛点/数据 → 分小节实操 → 费用/区域/避坑要点 → 结尾FAQ 3-5条
- 标题：冷静陈述句，含具体数字/时间/学校/城市名
- 数据时效：首选2026年数据，2025可接受，2024及更早禁用（除历史对比节）
- 目标受众：中国大陆留学生及家长

## 红线（绝对禁止）
1. **禁任何留学中介品牌名**（UNILINK/优领/启德/新东方/澳际/IDP等全部禁）——这是独立学生公寓站
2. **禁markdown表格**——对比/排序用有序号列表 1. 2. 3.
3. **标题年份只用2026或2027**——禁2025及更早
4. **禁政治/医美/国内财经敏感话题**
5. **禁感叹号/震惊体/速看体等标题党**

## 输出格式
直接输出markdown文章（含frontmatter），第一行必须是 `---`。
frontmatter必须包含: title, description(SEO描述150-200字), category, publishDate(YYYY-MM-DD), pubDatetime(ISO8601 UTC), modDatetime(ISO8601 UTC), readingTime, heroImage(先填 PLACEHOLDER), ogImage(同heroImage), tags

正文用 ## 二级标题分节，每段≤200字，加粗关键词。正文无表格、无品牌名。

category 用国家/地区名（如"澳大利亚"、"英国"、"美国"等）。pubDatetime 散布在未来1-4个月内（现在是2026年6月），时分秒随机。"""

def generate_one_article(topic, image_url=None):
    """Generate a single article"""
    title = topic["title"]
    track = topic.get("track", "?")
    country = topic.get("country", "")
    keyword = topic.get("keyword", "")
    university = topic.get("university", "")
    
    context = f"国家: {country}" if country else ""
    if university:
        context += f"\n大学: {university}"
    if keyword:
        context += f"\n关键词: {keyword}"
    
    user_prompt = f"""请为 unistay.cn 写一篇留学生公寓指南文章。

标题: {title}
{context}

要求：
- 1200-2000字，实用攻略风格
- 开头痛点+数据开场（用2026年数据）
- 分小节实操讲解
- 费用/区域/避坑要点
- FAQ 3-5条
- category 用国家名（{country if country else '留学住宿'}）
- pubDatetime 散布在2026年6月-10月之间，随机时分秒
- heroImage 填 PLACEHOLDER

直接输出完整markdown（frontmatter从---开始），不要额外解释。"""
    
    for attempt in range(3):
        try:
            response = call_dspro(SYSTEM_PROMPT, user_prompt)
            
            # Clean up response (remove thinking blocks if any)
            if "<｜end▁of▁thinking｜>" in response:
                response = response.split("response", 1)[1] if "response" in response else response
            
            # Ensure it starts with ---
            response = response.strip()
            if not response.startswith("---"):
                # Try to find the first ---
                idx = response.find("---")
                if idx >= 0:
                    response = response[idx:]
                else:
                    print(f"  WARNING: No frontmatter found, attempt {attempt+1}")
                    continue
            
            # Remove trailing explanations
            # Find the last meaningful markdown line
            lines = response.split("\n")
            cut_idx = len(lines)
            for i in range(len(lines)-1, -1, -1):
                if lines[i].strip().startswith("#") or lines[i].strip().startswith("-") or lines[i].strip().startswith(">"):
                    cut_idx = i + 1
                    break
                if lines[i].strip() and not lines[i].strip().startswith("```") and not lines[i].strip().startswith("---"):
                    cut_idx = i + 1
                    break
            if cut_idx < len(lines) - 1:
                response = "\n".join(lines[:cut_idx])
            
            # Validate
            errors = validate_article(response, title)
            if errors:
                if attempt < 2:
                    print(f"  Retry {attempt+1}: {errors}")
                    user_prompt += f"\n\n上次生成有以下问题: {errors}。请重新生成，严格遵守所有红线。"
                    continue
                else:
                    print(f"  FAILED after 3 attempts: {errors}")
                    return None
            
            # Replace PLACEHOLDER with actual image URL
            if image_url:
                response = response.replace("PLACEHOLDER", image_url)
            
            return response
            
        except Exception as e:
            print(f"  Error attempt {attempt+1}: {e}")
            time.sleep(2)
    
    return None

def get_slug_from_title(title):
    """Generate filename slug from title"""
    # Remove special chars, keep Chinese and alphanumeric
    cleaned = re.sub(r'[^\u4e00-\u9fff\w]', '', title)
    if len(cleaned) > 80:
        cleaned = cleaned[:80]
    return cleaned

# ── Main pipeline ───────────────────────────────────────
def process_topic(idx, topic):
    """Process a single topic: image + article generation"""
    title = topic["title"]
    country = topic.get("country", "")
    keyword = topic.get("keyword", "")
    slug = get_slug_from_title(title)
    
    print(f"[{idx+1}/{len(TOPICS)}] {title}")
    
    # 1. Get image
    img_url = None
    try:
        search_q = f"{country} {keyword} student accommodation university campus"
        photo_url, photographer = get_pexels_image(search_q, country)
        if photo_url:
            print(f"  Image: {photo_url[:80]}...")
            # Download image
            img_data = urlopen(Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})).read()
            img_url = upload_to_r2(img_data, slug)
            print(f"  Uploaded to R2: {img_url}")
        else:
            print(f"  No image found")
            # Try broader search
            photo_url, photographer = get_pexels_image(f"{country} university building", "")
            if photo_url:
                img_data = urlopen(Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})).read()
                img_url = upload_to_r2(img_data, slug)
                print(f"  Fallback image uploaded: {img_url}")
    except Exception as e:
        print(f"  Image error: {e}")
    
    # 2. Generate article
    article = generate_one_article(topic, img_url)
    if not article:
        print(f"  FAILED to generate article")
        return None
    
    # 3. Write to file
    filepath = ARTICLES_DIR / f"{slug}.md"
    filepath.write_text(article, encoding="utf-8")
    print(f"  Written: {filepath}")
    
    return {"slug": slug, "file": str(filepath), "image": img_url}

# ── Entry point ─────────────────────────────────────────
def main():
    print(f"=" * 60)
    print(f"unistay.cn Bulk Article Generation - {len(TOPICS)} articles")
    print(f"=" * 60)
    
    # Load state
    completed = set()
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        completed = set(state.get("completed", []))
        print(f"Resuming: {len(completed)} already completed")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for i, topic in enumerate(TOPICS):
            slug = get_slug_from_title(topic["title"])
            if slug in completed:
                print(f"[{i+1}/{len(TOPICS)}] SKIP (completed): {topic['title']}")
                continue
            f = executor.submit(process_topic, i, topic)
            futures[f] = (i, topic, slug)
        
        for f in concurrent.futures.as_completed(futures):
            i, topic, slug = futures[f]
            try:
                result = f.result()
                if result:
                    results.append(result)
                    completed.add(slug)
                    # Save state periodically
                    json.dump({"completed": list(completed), "total": len(TOPICS)}, 
                             open(STATE_FILE, "w"), indent=2)
            except Exception as e:
                print(f"[{i+1}] EXCEPTION: {e}")
    
    print(f"\nDone: {len(results)} articles generated")
    print(f"State saved to {STATE_FILE}")
    
    # Print summary
    for r in results:
        print(f"  {r['slug']}: {r['image'][:60] if r.get('image') else 'NO IMAGE'}")

if __name__ == "__main__":
    main()
