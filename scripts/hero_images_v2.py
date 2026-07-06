#!/usr/bin/env python3
"""unistay-cn 配图脚本 v2 — Pexels only (User-Agent fixed), retry no-image articles"""
import json, re, os, sys, time, hashlib, hmac, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt

ARTICLES_DIR = Path('/Users/benwu/site-builds/unistay-cn/src/content/articles')
CRED_PATH = Path('/Users/benwu/cowork/cowork-cloud-tools/credentials.json')
MAX_WORKERS = 3

creds = json.loads(CRED_PATH.read_text())
PEXELS_KEY = creds['pexels']['api_key']
R2 = creds['r2']
UA = 'unistay-cn-bot/1.0 (macOS)'

def sha256_hex(data): return hashlib.sha256(data).hexdigest()
def sign(key, msg): return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
def get_signing_key(secret, date, region, service):
    k = sign(("AWS4"+secret).encode(), date)
    k = sign(k, region); k = sign(k, service)
    return sign(k, "aws4_request")

def r2_upload(body, object_key, content_type):
    ep = R2['s3_endpoint']; bucket = R2['bucket']
    url = f"{ep}/{bucket}/{urllib.parse.quote(object_key, safe='/-_.')}"
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc; path = parsed.path or "/"
    now = dt.datetime.now(dt.timezone.utc)
    amz = now.strftime("%Y%m%dT%H%M%SZ"); ds = now.strftime("%Y%m%d")
    ph = sha256_hex(body)
    hdrs = {"host":host,"x-amz-date":amz,"x-amz-content-sha256":ph,"content-type":content_type,"content-length":str(len(body))}
    sk = sorted(hdrs); ch = "".join(f"{k}:{hdrs[k]}\n" for k in sk); sh = ";".join(sk)
    cr = f"PUT\n{path}\n\n{ch}\n{sh}\n{ph}"
    cs = f"{ds}/auto/s3/aws4_request"
    sts = f"AWS4-HMAC-SHA256\n{amz}\n{cs}\n{sha256_hex(cr.encode())}"
    sgk = get_signing_key(R2['secret_access_key'], ds, "auto", "s3")
    sig = hmac.new(sgk, sts.encode(), hashlib.sha256).hexdigest()
    hdrs["authorization"] = f"AWS4-HMAC-SHA256 Credential={R2['access_key_id']}/{cs}, SignedHeaders={sh}, Signature={sig}"
    req = urllib.request.Request(url, data=body, method="PUT")
    for k,v in hdrs.items(): req.add_header(k,v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status in (200,201,204):
                base = R2.get("public_url","").rstrip('/')
                if not base.startswith("http"): base = "https://"+base
                return f"{base}/{object_key}"
    except Exception as e:
        print(f"  R2 err: {e}", flush=True)
    return None

def pexels_search(query, per_page=5):
    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={per_page}&orientation=landscape&size=large"
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("photos",[])
    except Exception as e:
        return []

def download_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(), r.headers.get("Content-Type","image/jpeg")
    except:
        return None

# Keyword extraction from Chinese + English titles
def extract_keywords(title):
    kw = []
    title_lower = title.lower()
    
    # Country detection
    countries = {
        'australia': ['australia','sydney','melbourne','brisbane','adelaide','perth','gold coast','澳洲','澳大利亚','悉尼','墨尔本','布里斯班','阿德莱德','珀斯'],
        'uk': ['uk','london','manchester','birmingham','leeds','edinburgh','glasgow','liverpool','英国','伦敦','曼彻斯特','伯明翰','利兹','爱丁堡'],
        'usa': ['usa','new york','los angeles','boston','chicago','san francisco','美国','纽约','洛杉矶','波士顿','芝加哥'],
        'canada': ['canada','toronto','vancouver','montreal','加拿大','多伦多','温哥华'],
        'hong kong': ['hong kong','hung hom','香港','红磡'],
        'new zealand': ['new zealand','auckland','新西兰'],
        'singapore': ['singapore','新加坡'],
        'japan': ['japan','tokyo','osaka','日本'],
        'korea': ['korea','seoul','韩国'],
        'ireland': ['ireland','dublin','爱尔兰'],
        'europe': ['europe','germany','france','netherlands','italy','spain','欧洲'],
    }
    
    location = None
    for loc, keywords in countries.items():
        for k in keywords:
            if k in title_lower:
                location = loc
                break
        if location: break
    
    # Type detection
    types = {
        'student accommodation': ['student accommodation','学生公寓','student housing','pbsa'],
        'dormitory': ['dormitory','宿舍','dorm'],
        'apartment': ['apartment','公寓','flat','租房'],
        'studio': ['studio'],
        'shared': ['shared','合租','share house'],
        'homestay': ['homestay','寄宿'],
        'interior': ['interior','房型','room type','室内'],
        'building': ['building exterior','建筑','外观','facade'],
    }
    
    typ = None
    for t, keywords in types.items():
        for k in keywords:
            if k in title_lower:
                typ = t
                break
        if typ: break
    
    # Build search queries
    if location and typ:
        kw.append(f"{location} {typ} modern")
    if location:
        kw.append(f"{location} modern student housing exterior")
        kw.append(f"{location} university campus accommodation")
    if typ:
        kw.append(f"modern {typ} building")
    kw.append("modern student accommodation building exterior")
    kw.append("university campus housing modern")
    return kw

used_indices = {}

def process_article(fp):
    bn = fp.name
    try:
        content = fp.read_text(encoding='utf-8')
    except:
        return {'file':bn,'status':'error','error':'read'}
    
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m: return {'file':bn,'status':'error','error':'no fm'}
    fm_text = m.group(1); body_text = content[m.end():]
    
    if 'heroImage:' in fm_text and 'heroImage: ""' not in fm_text:
        return {'file':bn,'status':'skip'}
    
    # If previously had empty heroImage (hello-world case), we still want to fill it
    # Actually check if heroImage has a real URL
    him = re.search(r'heroImage:\s*"(.+?)"', fm_text)
    if him and him.group(1) and him.group(1).startswith('http'):
        return {'file':bn,'status':'skip'}
    
    tm = re.search(r'title:\s*"?(.+?)"?\s*$', fm_text, re.MULTILINE)
    if not tm: return {'file':bn,'status':'error','error':'no title'}
    title = tm.group(1)
    
    terms = extract_keywords(title)
    
    for term in terms:
        photos = pexels_search(term)
        if not photos: continue
        
        idx = used_indices.get(term, 0)
        if idx >= len(photos): continue
        photo = photos[idx]
        used_indices[term] = idx + 1
        
        img_url = photo['src'].get('large2x') or photo['src'].get('large') or photo['src'].get('original')
        if not img_url: continue
        
        result = download_image(img_url)
        if result:
            img_bytes, ct = result
            time.sleep(0.3)
            
            ext = 'jpg'
            if ct and 'png' in ct: ext = 'png'
            elif ct and 'webp' in ct: ext = 'webp'
            
            slug = re.sub(r'[^a-zA-Z0-9-]','-',bn.replace('.md','').lower())[:50].strip('-')
            if not slug: slug = hashlib.md5(bn.encode()).hexdigest()[:12]
            
            ok = f"unistay/{slug}-{dt.datetime.now().year}.{ext}"
            purl = r2_upload(img_bytes, ok, ct)
            if not purl: return {'file':bn,'status':'error','error':'r2'}
            
            # Patch frontmatter
            lines = fm_text.split('\n')
            nl = []; ha = False; od = False
            for line in lines:
                nl.append(line)
                if not ha and (line.startswith('tags:') or line.startswith('readingTime:') or line.startswith('modDatetime:')):
                    nl.append(f'heroImage: "{purl}"')
                    ha = True
                if not od and line.startswith('ogImage:'):
                    nl[-1] = f'ogImage: "{purl}"'
                    od = True
            if not ha: nl.append(f'heroImage: "{purl}"')
            if not od: nl.append(f'ogImage: "{purl}"')
            
            nfm = '\n'.join(nl)
            nc = f'---\n{nfm}\n---{body_text}'
            if not nc.startswith('---'): return {'file':bn,'status':'error','error':'fm corrupt'}
            fp.write_text(nc, encoding='utf-8')
            return {'file':bn,'status':'ok','url':purl,'term':term}
    
    return {'file':bn,'status':'no_image','terms':terms[:3]}

def main():
    af = []
    for pat in ['*.md','en/*.md']:
        af.extend(ARTICLES_DIR.glob(pat))
    af = [f for f in af if f.name != 'hello-world.md']
    
    # Only process files that DON'T have heroImage
    need_img = []
    for f in af:
        try:
            c = f.read_text(encoding='utf-8')
            if 'heroImage:' not in c or 'heroImage: ""' in c:
                need_img.append(f)
        except:
            need_img.append(f)
    
    print(f"Need images: {len(need_img)}/{len(af)}", flush=True)
    
    ok=0; sk=0; er=0; ni=0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_article, f): f for f in need_img}
        for i, fut in enumerate(as_completed(futures)):
            r = fut.result()
            s = r['status']
            ic = {'ok':'V','skip':'-','error':'X','no_image':'o'}.get(s,'?')
            msg = f"[{i+1}/{len(need_img)}] {ic} {r['file'][:55]}"
            if s=='ok': ok+=1; msg+=f" -> {r.get('url','')[:45]}"
            elif s=='skip': sk+=1
            elif s=='no_image': ni+=1
            else: er+=1; msg+=f" ({r.get('error','')})"
            print(msg, flush=True)
    
    print(f"\nDone: {ok} ok, {sk} skip, {ni} no-img, {er} err", flush=True)

if __name__ == '__main__':
    main()
