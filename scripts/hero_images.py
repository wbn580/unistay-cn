     1|     1|#!/usr/bin/env python3
     2|     2|"""
     3|     3|unistay-cn 配图脚本：读取所有文章 → Pexels/Pixabay 搜图 → 下载 → 上传 R2 → 写 heroImage+ogImage
     4|     4|"""
     5|     5|import json, re, os, sys, time, hashlib, hmac, urllib.request, urllib.parse, urllib.error, mimetypes
     6|     6|from pathlib import Path
     7|     7|from concurrent.futures import ThreadPoolExecutor, as_completed
     8|     8|import datetime as dt
     9|     9|
    10|    10|# ── Config ──────────────────────────────────────────────────
    11|    11|ARTICLES_DIR = Path('/Users/benwu/site-builds/unistay-cn/src/content/articles')
    12|    12|CRED_PATH = Path('/Users/benwu/cowork/cowork-cloud-tools/credentials.json')
    13|    13|MAX_WORKERS = 4
    14|    14|
    15|    15|creds = json.loads(CRED_PATH.read_text())
    16|    16|PEXELS_KEY = creds['pexels']['api_key']
    17|    17|PIXABAY_KEY = creds['pixabay']['api_key']
    18|    18|R2 = creds['r2']
    19|    19|
    20|    20|# ── R2 Upload ────────────────────────────────────────────────
    21|    21|def sha256_hex(data: bytes) -> str:
    22|    22|    return hashlib.sha256(data).hexdigest()
    23|    23|
    24|    24|def sign(key: bytes, msg: str) -> bytes:
    25|    25|    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    26|    26|
    27|    27|def get_signing_key(secret: str, date: str, region: str, service: str) -> bytes:
    28|    28|    k_date = sign(("AWS4" + secret).encode("utf-8"), date)
    29|    29|    k_region = sign(k_date, region)
    30|    30|    k_service = sign(k_region, service)
    31|    31|    return sign(k_service, "aws4_request")
    32|    32|
    33|    33|def r2_upload(body: bytes, object_key: str, content_type: str):
    34|    34|    endpoint = R2['s3_endpoint']
    35|    35|    bucket = R2['bucket']
    36|    36|    url = f"{endpoint}/{bucket}/{urllib.parse.quote(object_key, safe='/-_.')}"
    37|    37|    
    38|    38|    parsed = urllib.parse.urlparse(url)
    39|    39|    host = parsed.netloc
    40|    40|    path = parsed.path or "/"
    41|    41|    
    42|    42|    now = dt.datetime.now(dt.timezone.utc)
    43|    43|    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    44|    44|    date_stamp = now.strftime("%Y%m%d")
    45|    45|    payload_hash = sha256_hex(body)
    46|    46|    
    47|    47|    headers = {
    48|    48|        "host": host, "x-amz-date": amz_date,
    49|    49|        "x-amz-content-sha256": payload_hash,
    50|    50|        "content-type": content_type,
    51|    51|        "content-length": str(len(body)),
    52|    52|    }
    53|    53|    
    54|    54|    sorted_keys = sorted(headers.keys())
    55|    55|    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted_keys)
    56|    56|    signed_headers = ";".join(sorted_keys)
    57|    57|    
    58|    58|    canonical_request = f"PUT\n{path}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    59|    59|    credential_scope = f"{date_stamp}/auto/s3/aws4_request"
    60|    60|    string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{sha256_hex(canonical_request.encode())}"
    61|    61|    
    62|    62|    signing_key = get_signing_key(R2['secret_access_key'], date_stamp, "auto", "s3")
    63|    63|    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    64|    64|    
    65|    65|    auth = (
    66|    66|        f"AWS4-HMAC-SHA256 Credential={R2['access_key_id']}/{credential_scope}, "
    67|    67|        f"SignedHeaders={signed_headers}, Signature={signature}"
    68|    68|    )
    69|    69|    headers["authorization"] = auth
    70|    70|    
    71|    71|    req = urllib.request.Request(url, data=body, method="PUT")
    72|    72|    for k, v in headers.items():
    73|    73|        req.add_header(k, v)
    74|    74|    
    75|    75|    try:
    76|    76|        with urllib.request.urlopen(req, timeout=30) as resp:
    77|    77|            if resp.status in (200, 201, 204):
    78|    78|                base = R2.get("public_url", "").rstrip('/')
    79|    79|                if not base.startswith("http"):
    80|    80|                    base = "https://" + base
    81|    81|                return f"{base}/{object_key}"
    82|    82|    except Exception as e:
    83|    83|        print(f"  R2 upload error: {e}", flush=True)
    84|    84|    return None
    85|    85|
    86|    86|# ── Pexels API ──────────────────────────────────────────────
    87|    87|def pexels_search(query: str, per_page: int = 5):
    88|    88|    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={per_page}&orientation=landscape&size=large"
    89|    89|    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY, "User-Agent": "unistay-cn-bot/1.0"})
    90|    90|    try:
    91|    91|        with urllib.request.urlopen(req, timeout=15) as resp:
    92|    92|            data = json.loads(resp.read())
    93|    93|            return data.get("photos", [])
    94|    94|    except Exception as e:
    95|    95|        print(f"  Pexels error '{query}': {e}", flush=True)
    96|    96|        return []
    97|    97|
    98|    98|# ── Pixabay API ─────────────────────────────────────────────
    99|    99|def pixabay_search(query: str, per_page: int = 5):
   100|   100|    url = f"https://pixabay.com/api/?key=***&q={urllib.parse.quote(query)}&per_page=3&orientation=horizontal&safesearch=true&image_type=photo"
   101|   101|    try:
   102|   102|        with urllib.request.urlopen(url, timeout=15) as resp:
   103|   103|            data = json.loads(resp.read())
   104|   104|            return data.get("hits", [])
   105|   105|    except Exception as e:
   106|   106|        print(f"  Pixabay error '{query}': {e}", flush=True)
   107|   107|        return []
   108|   108|
   109|   109|# ── Download image ──────────────────────────────────────────
   110|   110|def download_image(url: str):
   111|   111|    try:
   112|   112|        req = urllib.request.Request(url, headers={"User-Agent": "unistay-cn-bot/1.0"})
   113|   113|        with urllib.request.urlopen(req, timeout=20) as resp:
   114|   114|            ct = resp.headers.get("Content-Type", "image/jpeg")
   115|   115|            return resp.read(), ct
   116|   116|    except Exception as e:
   117|   117|        print(f"  Download error: {e}", flush=True)
   118|   118|        return None
   119|   119|
   120|   120|# ── Generate search terms from Chinese title ─────────────────
   121|   121|COUNTRY_MAP = {
   122|   122|    '澳洲': 'australia', '澳大利亚': 'australia', '悉尼': 'sydney',
   123|   123|    '墨尔本': 'melbourne', '布里斯班': 'brisbane', '阿德莱德': 'adelaide',
   124|   124|    '珀斯': 'perth', '黄金海岸': 'gold coast',
   125|   125|    '英国': 'uk', '伦敦': 'london', '曼彻斯特': 'manchester',
   126|   126|    '伯明翰': 'birmingham', '利兹': 'leeds', '爱丁堡': 'edinburgh',
   127|   127|    '格拉斯哥': 'glasgow', '利物浦': 'liverpool',
   128|   128|    '美国': 'usa', '纽约': 'new york', '洛杉矶': 'los angeles',
   129|   129|    '波士顿': 'boston', '芝加哥': 'chicago', '旧金山': 'san francisco',
   130|   130|    '加拿大': 'canada', '多伦多': 'toronto', '温哥华': 'vancouver',
   131|   131|    '蒙特利尔': 'montreal',
   132|   132|    '香港': 'hong kong', '红磡': 'hung hom',
   133|   133|    '新西兰': 'new zealand', '奥克兰': 'auckland',
   134|   134|    '新加坡': 'singapore',
   135|   135|    '日本': 'japan', '东京': 'tokyo', '大阪': 'osaka',
   136|   136|    '韩国': 'korea', '首尔': 'seoul',
   137|   137|    '爱尔兰': 'ireland', '都柏林': 'dublin',
   138|   138|    '欧洲': 'europe', '德国': 'germany', '法国': 'france',
   139|   139|    '荷兰': 'netherlands', '意大利': 'italy', '西班牙': 'spain',
   140|   140|}
   141|   141|
   142|   142|TYPE_KEYWORDS = {
   143|   143|    '学生公寓': 'student accommodation building modern',
   144|   144|    '宿舍': 'student dormitory exterior',
   145|   145|    '租房': 'rental apartment modern',
   146|   146|    '合租': 'shared apartment living room',
   147|   147|    '寄宿': 'homestay family house',
   148|   148|    '短租': 'short term rental apartment',
   149|   149|    '长租': 'long term rental housing',
   150|   150|    '品牌公寓': 'premium student housing building',
   151|   151|    '房型': 'apartment interior bright',
   152|   152|    '合同': 'rental contract keys apartment',
   153|   153|    '押金': 'deposit refund apartment keys',
   154|   154|    '安全': 'secure apartment building entrance',
   155|   155|    '预算': 'student budget planning desk',
   156|   156|    '费用': 'student budget calculator desk',
   157|   157|    '牌照': 'building exterior modern',
   158|   158|    'Studio': 'studio apartment interior',
   159|   159|}
   160|   160|
   161|   161|def generate_search_terms(title: str):
   162|   162|    terms = []
   163|   163|    location = None
   164|   164|    for cn, en in COUNTRY_MAP.items():
   165|   165|        if cn in title:
   166|   166|            location = en
   167|   167|            break
   168|   168|    
   169|   169|    typ = None
   170|   170|    for cn, en in TYPE_KEYWORDS.items():
   171|   171|        if cn in title:
   172|   172|            typ = en
   173|   173|            break
   174|   174|    
   175|   175|    if location and typ:
   176|   176|        terms.append(f"{location} {typ}")
   177|   177|    if location:
   178|   178|        terms.append(f"{location} student housing exterior modern")
   179|   179|        terms.append(f"{location} university accommodation")
   180|   180|    if typ:
   181|   181|        terms.append(typ)
   182|   182|    
   183|   183|    terms.append("modern student accommodation building")
   184|   184|    terms.append("university campus apartment exterior")
   185|   185|    return terms
   186|   186|
   187|   187|# ── Process single article ──────────────────────────────────
   188|   188|used_indices = {}
   189|   189|
   190|   190|def process_article(filepath: Path):
   191|   191|    basename = filepath.name
   192|   192|    try:
   193|   193|        content = filepath.read_text(encoding='utf-8')
   194|   194|    except Exception as e:
   195|   195|        return {'file': basename, 'status': 'error', 'error': f'read: {e}'}
   196|   196|    
   197|   197|    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
   198|   198|    if not m:
   199|   199|        return {'file': basename, 'status': 'error', 'error': 'no frontmatter'}
   200|   200|    
   201|   201|    fm_text = m.group(1)
   202|   202|    body_text = content[m.end():]
   203|   203|    
   204|   204|    if 'heroImage:' in fm_text:
   205|   205|        return {'file': basename, 'status': 'skip', 'reason': 'has heroImage'}
   206|   206|    
   207|   207|    title_match = re.search(r'title:\s*"?(.+?)"?\s*$', fm_text, re.MULTILINE)
   208|   208|    if not title_match:
   209|   209|        return {'file': basename, 'status': 'error', 'error': 'no title'}
   210|   210|    title = title_match.group(1)
   211|   211|    
   212|   212|    search_terms = generate_search_terms(title)
   213|   213|    
   214|   214|    image_bytes = None
   215|   215|    image_ct = None
   216|   216|    source_attr = ""
   217|   217|    used_term = ""
   218|   218|    
   219|   219|    for term in search_terms:
   220|   220|        photos = pexels_search(term)
   221|   221|        if not photos:
   222|   222|            photos = pixabay_search(term)
   223|   223|        if not photos:
   224|   224|            continue
   225|   225|        
   226|   226|        idx = used_indices.get(term, 0)
   227|   227|        if idx >= len(photos):
   228|   228|            continue
   229|   229|        
   230|   230|        photo = photos[idx]
   231|   231|        used_indices[term] = idx + 1
   232|   232|        used_term = term
   233|   233|        
   234|   234|        if 'src' in photo:
   235|   235|            img_url = photo['src'].get('large2x') or photo['src'].get('large') or photo['src'].get('original')
   236|   236|            source_attr = f"Pexels/{photo.get('photographer','')}"
   237|   237|        else:
   238|   238|            img_url = photo.get('largeImageURL') or photo.get('webformatURL')
   239|   239|            source_attr = f"Pixabay/{photo.get('user','')}"
   240|   240|        
   241|   241|        if not img_url:
   242|   242|            continue
   243|   243|        
   244|   244|        result = download_image(img_url)
   245|   245|        if result:
   246|   246|            image_bytes, image_ct = result
   247|   247|            time.sleep(0.3)
   248|   248|            break
   249|   249|    
   250|   250|    if not image_bytes:
   251|   251|        return {'file': basename, 'status': 'no_image', 'terms': search_terms[:3]}
   252|   252|    
   253|   253|    ext = 'jpg'
   254|   254|    if image_ct and 'png' in image_ct:
   255|   255|        ext = 'png'
   256|   256|    elif image_ct and 'webp' in image_ct:
   257|   257|        ext = 'webp'
   258|   258|    
   259|   259|    safe_slug = re.sub(r'[^a-zA-Z0-9-]', '-', basename.replace('.md','').lower())[:50].strip('-')
   260|   260|    if not safe_slug:
   261|   261|        safe_slug = hashlib.md5(basename.encode()).hexdigest()[:12]
   262|   262|    
   263|   263|    object_key = f"unistay/{safe_slug}-{dt.datetime.now().year}.{ext}"
   264|   264|    public_url = r2_upload(image_bytes, object_key, image_ct)
   265|   265|    if not public_url:
   266|   266|        return {'file': basename, 'status': 'error', 'error': 'r2 upload failed'}
   267|   267|    
   268|   268|    # Patch frontmatter - add heroImage + ogImage
   269|   269|    lines = fm_text.split('\n')
   270|   270|    new_lines = []
   271|   271|    hero_added = False
   272|   272|    og_done = False
   273|   273|    
   274|   274|    for line in lines:
   275|   275|        new_lines.append(line)
   276|   276|        if not hero_added and (line.startswith('tags:') or line.startswith('readingTime:')):
   277|   277|            new_lines.append(f'heroImage: "{public_url}"')
   278|   278|            hero_added = True
   279|   279|        if not og_done and line.startswith('ogImage:'):
   280|   280|            new_lines[-1] = f'ogImage: "{public_url}"'
   281|   281|            og_done = True
   282|   282|    
   283|   283|    if not hero_added:
   284|   284|        new_lines.append(f'heroImage: "{public_url}"')
   285|   285|    if not og_done:
   286|   286|        new_lines.append(f'ogImage: "{public_url}"')
   287|   287|    
   288|   288|    new_fm = '\n'.join(new_lines)
   289|   289|    new_content = f'---\n{new_fm}\n---{body_text}'
   290|   290|    
   291|   291|    if not new_content.startswith('---'):
   292|   292|        return {'file': basename, 'status': 'error', 'error': 'fm corruption'}
   293|   293|    
   294|   294|    filepath.write_text(new_content, encoding='utf-8')
   295|   295|    
   296|   296|    return {
   297|   297|        'file': basename, 'status': 'ok', 'url': public_url,
   298|   298|        'term': used_term, 'source': source_attr,
   299|   299|    }
   300|   300|
   301|   301|# ── Main ─────────────────────────────────────────────────────
   302|   302|def main():
   303|   303|    all_files = []
   304|   304|    for pat in ['*.md', 'en/*.md']:
   305|   305|        all_files.extend(ARTICLES_DIR.glob(pat))
   306|   306|    all_files = [f for f in all_files if f.name != 'hello-world.md']
   307|   307|    
   308|   308|    print(f"Total: {len(all_files)} articles", flush=True)
   309|   309|    
   310|   310|    ok = skip = err = noimg = 0
   311|   311|    
   312|   312|    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
   313|   313|        futures = {executor.submit(process_article, f): f for f in all_files}
   314|   314|        for i, future in enumerate(as_completed(futures)):
   315|   315|            r = future.result()
   316|   316|            s = r['status']
   317|   317|            icon = {'ok':'V', 'skip':'-', 'error':'X', 'no_image':'o'}.get(s, '?')
   318|   318|            msg = f"[{i+1}/{len(all_files)}] {icon} {r['file'][:55]}"
   319|   319|            if s == 'ok':
   320|   320|                ok += 1
   321|   321|                msg += f" -> {r.get('url','')[:45]}"
   322|   322|            elif s == 'skip': skip += 1
   323|   323|            elif s == 'no_image': noimg += 1
   324|   324|            else: err += 1; msg += f" ({r.get('error','')})"
   325|   325|            print(msg, flush=True)
   326|   326|    
   327|   327|    print(f"\nDone: {ok} ok, {skip} skip, {noimg} no-img, {err} err", flush=True)
   328|   328|
   329|   329|if __name__ == '__main__':
   330|   330|    main()
   331|   331|