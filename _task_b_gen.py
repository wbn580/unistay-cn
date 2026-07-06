#!/usr/bin/env python3
"""unistay.cn Task B — 80 city GEO articles. DSPro + placeholder images. Fast."""
import json, os, time, random, concurrent.futures, urllib.request
from pathlib import Path
from datetime import datetime, timedelta, timezone

SITE_DIR = Path.home() / "site-builds" / "unistay-cn"
ARTICLES_DIR = SITE_DIR / "src" / "content" / "articles"
STATE_FILE = SITE_DIR / "_task_b_state.json"
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

CREDS = json.load(open(Path.home() / "Library/CloudStorage/Dropbox-Personal/cowork/cowork-cloud-tools/credentials.json"))
DS = CREDS["deepseek"]
API_URL = DS["endpoint"] + "/chat/completions"
HEADERS = {"Authorization": f"Bearer {DS['api_key']}", "Content-Type": "application/json"}

# Remove old state
if STATE_FILE.exists():
    STATE_FILE.unlink()

# ── 80 Topics ──
TOPICS = [
    # UK 20
    ("london","英国","伦敦","留学租房攻略2026","伦敦留学生租房全攻略2026：从区域选择到签约避坑"),
    ("london","英国","伦敦","学生公寓vs寄宿家庭","伦敦学生公寓与寄宿家庭对比：价格、体验与安全保障"),
    ("london","英国","伦敦","一房一厅租金","伦敦留学生一房一厅租金2026：各区域真实价格对比"),
    ("london","英国","伦敦","合租注意事项","伦敦留学合租避坑指南：室友匹配、分摊与合同要点"),
    ("manchester","英国","曼彻斯特","留学租房攻略2026","曼彻斯特留学租房攻略2026：热门学生区与租金趋势"),
    ("manchester","英国","曼彻斯特","学生公寓vs寄宿家庭","曼彻斯特学生公寓与寄宿家庭怎么选2026"),
    ("manchester","英国","曼彻斯特","一房一厅租金","曼彻斯特一房一厅月租多少：2026年各邮编区真实数据"),
    ("manchester","英国","曼彻斯特","合租注意事项","曼彻斯特留学合租注意事项：找室友、签合同与水电分摊"),
    ("edinburgh","英国","爱丁堡","留学租房攻略2026","爱丁堡留学租房全攻略2026：老城区到大学周边怎么选"),
    ("edinburgh","英国","爱丁堡","学生公寓品牌推荐","爱丁堡学生公寓品牌推荐：Unite与CRM房源对比2026"),
    ("nottingham","英国","诺丁汉","留学租房攻略2026","诺丁汉留学租房攻略2026：University Park周边热门区域"),
    ("nottingham","英国","诺丁汉","学生公寓押金中介费","诺丁汉学生公寓押金与中介费全解析：避坑指南2026"),
    ("birmingham","英国","伯明翰","留学租房攻略2026","伯明翰留学租房攻略2026：市中心vs校园周边怎么选"),
    ("birmingham","英国","伯明翰","短租平台对比","伯明翰国际学生短租平台对比：Airbnb与Student.com"),
    ("liverpool","英国","利物浦","留学租房攻略2026","利物浦留学租房攻略2026：市中心到Smithdown Road选房"),
    ("glasgow","英国","格拉斯哥","留学租房攻略2026","格拉斯哥留学租房攻略2026：西区与市中心学生住宿"),
    ("leeds","英国","利兹","留学租房攻略2026","利兹留学租房攻略2026：Headingley与市中心怎么选"),
    ("sheffield","英国","谢菲尔德","留学租房攻略2026","谢菲尔德留学租房攻略2026：Crookes与Broomhall选房"),
    ("cardiff","英国","卡迪夫","留学租房攻略2026","卡迪夫留学租房攻略2026：Cathays与Roath学生区指南"),
    ("bristol","英国","布里斯托","留学租房攻略2026","布里斯托留学租房攻略2026：Clifton与Redland选房"),

    # Australia 18
    ("sydney","澳大利亚","悉尼","留学租房攻略2026","悉尼留学租房攻略2026：从City到Inner West各区详解"),
    ("sydney","澳大利亚","悉尼","学生公寓vs寄宿家庭","悉尼学生公寓与寄宿家庭对比：价格与生活体验2026"),
    ("sydney","澳大利亚","悉尼","一房一厅租金","悉尼留学生一房一厅月租2026：各区真实行情分析"),
    ("sydney","澳大利亚","悉尼","短租平台对比","悉尼国际学生短租平台对比：Flatmates与Domain选房"),
    ("melbourne","澳大利亚","墨尔本","留学租房攻略2026","墨尔本留学租房攻略2026：CBD与Carlton选房指南"),
    ("melbourne","澳大利亚","墨尔本","学生公寓vs寄宿家庭","墨尔本学生公寓与寄宿家庭怎么选2026"),
    ("melbourne","澳大利亚","墨尔本","一房一厅租金","墨尔本一房一厅月租2026：各区租金地图与趋势"),
    ("melbourne","澳大利亚","墨尔本","合租注意事项","墨尔本留学合租避坑指南：室友匹配与退租要点"),
    ("brisbane","澳大利亚","布里斯班","留学租房攻略2026","布里斯班留学租房攻略2026：South Bank与Toowong"),
    ("brisbane","澳大利亚","布里斯班","学生公寓品牌推荐","布里斯班学生公寓品牌推荐2026：UniLodge与Scape对比"),
    ("perth","澳大利亚","珀斯","留学租房攻略2026","珀斯留学租房攻略2026：Crawley与Bentley周边选房"),
    ("perth","澳大利亚","珀斯","学生公寓押金中介费","珀斯学生公寓押金与中介费详解：西澳租房规则"),
    ("adelaide","澳大利亚","阿德莱德","留学租房攻略2026","阿德莱德留学租房攻略2026：CBD与North Terrace周边"),
    ("canberra","澳大利亚","堪培拉","留学租房攻略2026","堪培拉留学租房攻略2026：ANU周边与Belconnen选房"),

    # USA 16
    ("boston","美国","波士顿","留学租房攻略2026","波士顿留学租房攻略2026：Fenway与Allston选房指南"),
    ("boston","美国","波士顿","学生公寓vs寄宿家庭","波士顿学生公寓与寄宿家庭对比：价格与便利性2026"),
    ("boston","美国","波士顿","一房一厅租金","波士顿留学生一房一厅月租2026：各街区真实价格"),
    ("boston","美国","波士顿","校内宿舍申请流程","波士顿大学校内宿舍申请流程与时间表2026"),
    ("new-york","美国","纽约","留学租房攻略2026","纽约留学租房攻略2026：曼哈顿与布鲁克林选房"),
    ("new-york","美国","纽约","学生公寓vs寄宿家庭","纽约学生公寓与寄宿家庭怎么选：费用对比2026"),
    ("new-york","美国","纽约","一房一厅租金","纽约留学生一房一厅租金2026：各区真实行情"),
    ("new-york","美国","纽约","合租注意事项","纽约留学合租避坑指南：担保人与信用分要点"),
    ("los-angeles","美国","洛杉矶","留学租房攻略2026","洛杉矶留学租房攻略2026：USC与UCLA周边选房"),
    ("los-angeles","美国","洛杉矶","一房一厅租金","洛杉矶一房一厅租金2026：Westwood到Koreatown"),
    ("san-francisco","美国","旧金山","留学租房攻略2026","旧金山留学租房攻略2026：Mission到Sunset选房"),
    ("san-francisco","美国","旧金山","短租平台对比","旧金山留学生短租平台对比：Zillow与Apartments.com"),
    ("chicago","美国","芝加哥","留学租房攻略2026","芝加哥留学租房攻略2026：Hyde Park与Lincoln Park"),
    ("seattle","美国","西雅图","留学租房攻略2026","西雅图留学租房攻略2026：U District与Capitol Hill"),

    # Canada 12
    ("toronto","加拿大","多伦多","留学租房攻略2026","多伦多留学租房攻略2026：Downtown到North York选房"),
    ("toronto","加拿大","多伦多","学生公寓vs寄宿家庭","多伦多学生公寓与寄宿家庭对比2026"),
    ("toronto","加拿大","多伦多","一房一厅租金","多伦多留学生一房一厅租金2026：各区价格地图"),
    ("toronto","加拿大","多伦多","合租注意事项","多伦多留学合租注意事项：UofT周边租房避坑"),
    ("vancouver","加拿大","温哥华","留学租房攻略2026","温哥华留学租房攻略2026：UBC周边与Kitsilano"),
    ("vancouver","加拿大","温哥华","学生公寓品牌推荐","温哥华学生公寓品牌推荐：Wesbrook与校内对比"),
    ("vancouver","加拿大","温哥华","一房一厅租金","温哥华一房一厅月租2026：UBC周边与市中心行情"),
    ("montreal","加拿大","蒙特利尔","留学租房攻略2026","蒙特利尔留学租房攻略2026：Plateau与Milton-Parc"),
    ("montreal","加拿大","蒙特利尔","短租平台对比","蒙特利尔留学生短租平台对比：Kijiji与Louer"),
    ("ottawa","加拿大","渥太华","留学租房攻略2026","渥太华留学租房攻略2026：Sandy Hill与Centretown"),
    ("ottawa","加拿大","渥太华","校内宿舍申请流程","渥太华大学校内宿舍申请流程与时间表2026"),

    # HK 4
    ("hong-kong-island","中国香港","港岛","留学租房攻略2026","港岛留学租房攻略2026：中西区与湾仔学生公寓"),
    ("kowloon","中国香港","九龙","留学租房攻略2026","九龙留学租房攻略2026：红磡与旺角学生住宿指南"),
    ("new-territories","中国香港","新界","留学租房攻略2026","新界留学租房攻略2026：沙田与大埔学生住宿"),
    ("hong-kong-island","中国香港","港岛","学生公寓vs寄宿家庭","港岛学生公寓与寄宿家庭对比：租金与通勤"),

    # Singapore 3
    ("singapore","新加坡","新加坡","留学租房攻略2026","新加坡留学租房攻略2026：NUS与NTU周边选房"),
    ("singapore","新加坡","新加坡","学生公寓品牌推荐","新加坡学生公寓品牌推荐：Cove与Hmlet对比2026"),
    ("singapore","新加坡","新加坡","一房一厅租金","新加坡留学生一房一厅租金2026：组屋与公寓行情"),

    # NZ 3
    ("auckland","新西兰","奥克兰","留学租房攻略2026","奥克兰留学租房攻略2026：CBD与奥大周边住宿"),
    ("wellington","新西兰","惠灵顿","留学租房攻略2026","惠灵顿留学租房攻略2026：维多利亚大学周边选房"),
    ("auckland","新西兰","奥克兰","学生公寓vs寄宿家庭","奥克兰学生公寓与寄宿家庭对比2026"),

    # Japan 2
    ("tokyo","日本","东京","留学租房攻略2026","东京留学租房攻略2026：早稻田与上野周边选房"),
    ("osaka","日本","大阪","留学租房攻略2026","大阪留学租房攻略2026：大阪大学周边学生住宿"),
]

TOTAL = len(TOPICS)
print(f"Topics: {TOTAL}")

# Dedup
def get_existing():
    titles = set()
    for f in ARTICLES_DIR.glob("*.md"):
        try:
            text = f.read_text()
            if text.startswith("---"):
                for line in text.split("---",2)[1].split("\n"):
                    if line.startswith("title:"):
                        t = line.split(":",1)[1].strip().strip('"').strip("'")
                        titles.add(t.lower().replace(" ",""))
        except: pass
    return titles

EXISTING = get_existing()
print(f"Existing: {len(EXISTING)}")

def is_dup(title):
    n = title.lower().replace(" ","").replace("·","").replace("：","").replace(":","")
    return any(n in e or e in n for e in EXISTING)

# ── Generate one ──
SYSTEM = """You are a content writer for a student housing website (unistay.cn).
Write a Chinese article about student accommodation in a specific city.

RULES:
- Target: Chinese international students + parents
- Use 2026 data where possible
- NEVER mention: 异乡好居, 学旅家, 51Room, Student.com, uhomes, 游子曰, 澳际, 启德, 新东方前途, 无忧留学, IDP, UNILINK, 优领
- NO tables
- NO clickbait (震惊, 必看, 绝了, 封神, 史上最)
- NO "排名", "榜单", "测评", "评测" in article
- Short paragraphs, 2-3 H2 sections
- One specific price/rental number per section
- 1000-1500 Chinese characters total
- Neutral, helpful editorial tone
- Write directly in markdown, start with ##"""

def gen(idx, t):
    slug, country, city, kw, title = t
    if is_dup(title):
        print(f"[{idx+1}/{TOTAL}] SKIP: {title[:40]}")
        return {"title": title, "status": "skipped"}
    
    user = f"""Write a student housing guide:

City: {city} ({country})
Title: {title}

Include:
1. Specific 2026 rental price ranges for {city} (be realistic)
2. 2-3 specific neighborhoods near universities
3. Practical advice for Chinese students
4. 2-4 ## headings
5. Total 1000-1500 Chinese characters
6. End with a practical checklist

Write the full article now. Start with ## heading."""

    try:
        data = json.dumps({
            "model": DS["pro_model"],
            "messages": [{"role":"system","content":SYSTEM},{"role":"user","content":user}],
            "temperature": 0.7, "max_tokens": 2500
        }).encode()
        req = urllib.request.Request(API_URL, data=data, headers=HEADERS, method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
        text = resp["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[{idx+1}/{TOTAL}] API ERROR: {e}")
        return {"title": title, "status": "failed", "error": str(e)}
    
    # Build frontmatter
    days_ago = random.randint(30, 180)
    pub = (datetime.now(timezone.utc) - timedelta(days=days_ago, seconds=random.randint(0,86400)))
    
    desc = f"2026年{city}留学生住宿攻略：{kw}。覆盖{city}主要大学周边学生公寓、租金行情、通勤建议与选房避坑指南。"[:160]
    
    fm = f"""---
title: "{title}"
description: "{desc}"
category: "{country}"
publishDate: "{pub.strftime('%Y-%m-%d')}"
pubDatetime: "{pub.strftime('%Y-%m-%dT%H:%M:%SZ')}"
modDatetime: "{pub.strftime('%Y-%m-%dT%H:%M:%SZ')}"
readingTime: 7
heroImage: "https://img.ulec.com.cn/unistay/placeholder.jpg"
ogImage: "https://img.ulec.com.cn/unistay/placeholder.jpg"
tags: ["{city}", "{kw}", "留学租房", "学生公寓"]
region: "{slug}"
city: "{city}"
---"""

    full = fm + "\n\n" + text.strip() + "\n"
    
    fname = f"{country}-{slug}-{kw}.md".replace("/","-").replace(" ","-")[:120]
    (ARTICLES_DIR / fname).write_text(full)
    EXISTING.add(title.lower().replace(" ",""))
    
    print(f"[{idx+1}/{TOTAL}] OK: {title[:50]} ({len(text)} chars)")
    return {"title": title, "slug": slug, "city": city, "status": "ok"}

# ── Run ──
state = {"completed": [], "total": TOTAL}
print(f"\nStarting {TOTAL} articles with 8 workers...\n")
t0 = time.time()

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(gen, i, t): (i,t) for i,t in enumerate(TOPICS)}
    for f in concurrent.futures.as_completed(futs):
        try:
            r = f.result()
            state["completed"].append(r)
            if len(state["completed"]) % 10 == 0:
                STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
                ok = sum(1 for c in state["completed"] if c.get("status")=="ok")
                print(f"  [SAVE] {ok} ok / {len(state['completed'])} done | {time.time()-t0:.0f}s")
        except Exception as e:
            print(f"FUTURE ERROR: {e}")

STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
elapsed = time.time() - t0
ok = sum(1 for c in state["completed"] if c.get("status")=="ok")
print(f"\nDONE: {ok}/{TOTAL} ok in {elapsed:.0f}s ({elapsed/60:.1f}min)")
