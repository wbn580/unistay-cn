/**
 * Build-time region classifier for unistay.cn articles.
 * Classifies by title + body keywords WITHOUT modifying frontmatter.
 */

export interface RegionInfo {
  slug: string;       // URL-safe slug e.g. "australia"
  name: string;       // Display name e.g. "澳大利亚"
  nameEn: string;     // English name e.g. "Australia"
}

export const REGIONS: RegionInfo[] = [
  { slug: "australia",    name: "澳大利亚", nameEn: "Australia" },
  { slug: "uk",           name: "英国",     nameEn: "UK" },
  { slug: "usa",          name: "美国",     nameEn: "USA" },
  { slug: "canada",       name: "加拿大",   nameEn: "Canada" },
  { slug: "hongkong",     name: "香港",     nameEn: "Hong Kong" },
  { slug: "newzealand",   name: "新西兰",   nameEn: "New Zealand" },
  { slug: "singapore",    name: "新加坡",   nameEn: "Singapore" },
  { slug: "ireland",      name: "爱尔兰",   nameEn: "Ireland" },
  { slug: "europe",       name: "欧洲",     nameEn: "Europe" },
  { slug: "other",        name: "其他",     nameEn: "Other" },
];

// Keyword → region slug mapping. Order matters: more specific first.
const REGION_RULES: [string[], string][] = [
  // Australia
  [["澳大利亚","澳洲","australia","悉尼","墨尔本","布里斯班","珀斯","阿德莱德","堪培拉",
    "黄金海岸","霍巴特","达尔文","unsw","usyd","monash","anu","uq","uts","rmit",
    "deakin","griffith","qut","uwa","unisa","flinders","latrobe","jcu","curtin",
    "new south wales","victoria university","卧龙岗","纽卡斯尔","sydney","melbourne",
    "brisbane","perth","adelaide","canberra","gold coast","hobart","darwin",
    "cairns","geelong","wollongong","newcastle"], "australia"],

  // UK
  [["英国","uk","united kingdom","伦敦","曼彻斯特","曼城","伯明翰","利兹","爱丁堡",
    "格拉斯哥","谢菲尔德","布里斯托","诺丁汉","利物浦","南安普顿","纽卡斯尔",
    "卡迪夫","考文垂","贝尔法斯特","ucl","kcl","lse","帝国理工","imperial college",
    "london","manchester","birmingham","leeds","edinburgh","glasgow","sheffield",
    "bristol","nottingham","liverpool","southampton","cardiff","cambridge","oxford",
    "coventry","belfast","exeter","york","durham","leicester","reading","aberdeen",
    "st andrews","warwick","bath","拉夫堡","埃克塞特"], "uk"],

  // USA
  [["美国","us","usa","united states","america","纽约","洛杉矶","波士顿","旧金山",
    "芝加哥","西雅图","华盛顿","费城","nyu","哥大","columbia university","ucla",
    "usc","berkeley","stanford","mit","harvard","yale","princeton","cornell",
    "michigan","uiuc","purdue","texas","new york","los angeles","boston",
    "san francisco","chicago","seattle","philadelphia","austin","miami",
    "san diego","atlanta","pittsburgh","portland"], "usa"],

  // Canada
  [["加拿大","canada","多伦多","温哥华","蒙特利尔","渥太华","卡尔加里","埃德蒙顿",
    "uoft","ubc","mcgill","mcmaster","waterloo","queens","western university",
    "toronto","vancouver","montreal","ottawa","calgary","edmonton","halifax",
    "victoria","winnipeg","saskatchewan"], "canada"],

  // Hong Kong
  [["香港","hk","hong kong","港大","中大","科大","城大","理大","浸大","嶺大",
    "hong kong university","cuhk","hkust","cityu","polyu","hku","hkbaptistu",
    "lingnan","红磡","旺角","九龙","沙田","大埔","港岛","将军澳","坑口",
    "尖沙咀","铜锣湾","中环","西环","湾仔","油麻地"], "hongkong"],

  // New Zealand
  [["新西兰","new zealand","奥克兰","惠灵顿","基督城","但尼丁","哈密尔顿",
    "奥塔哥","auckland","wellington","christchurch","dunedin","hamilton",
    "otago","massey","waikato","canterbury","lincoln"], "newzealand"],

  // Singapore
  [["新加坡","singapore","nus","ntu","smu","sutd","sit","suss",
    "新加坡国立","南洋理工","新加坡管理"], "singapore"],

  // Ireland
  [["爱尔兰","ireland","都柏林","dublin","ucd","trinity","tcd","ucc","nuig",
    "dcu","galway","cork","limerick","waterford"], "ireland"],

  // Europe (non-UK/IE)
  [["荷兰","德国","法国","西班牙","意大利","瑞典","瑞士","比利时","奥地利",
    "芬兰","挪威","丹麦","波兰","葡萄牙","捷克","匈牙利","希腊",
    "阿姆斯特丹","慕尼黑","柏林","巴黎","巴塞罗那","马德里","米兰","罗马",
    "斯德哥尔摩","苏黎世","哥本哈根","维也纳","赫尔辛基","奥斯陆",
    "netherlands","germany","france","spain","italy","sweden","switzerland",
    "belgium","austria","finland","norway","denmark","poland","portugal",
    "amsterdam","munich","berlin","paris","barcelona","madrid","milan","rome",
    "stockholm","zurich","copenhagen","vienna","helsinki","oslo",
    "eth zurich","epfl","tu delft","kth","lund","erasmus","bologna"], "europe"],
];

export function classifyRegion(title: string, body: string, tags: string[]): string {
  const text = (title + " " + body + " " + (tags || []).join(" ")).toLowerCase();

  for (const [keywords, slug] of REGION_RULES) {
    for (const kw of keywords) {
      if (text.includes(kw.toLowerCase())) {
        return slug;
      }
    }
  }

  return "other";
}

export function getRegionBySlug(slug: string): RegionInfo | undefined {
  return REGIONS.find(r => r.slug === slug);
}

/** Get region display info + article count for each region */
export function getRegionStats(articles: Array<{ data: { title: string; tags?: string[] }; body: string }>): Array<RegionInfo & { count: number }> {
  const counts: Record<string, number> = {};
  for (const a of articles) {
    const region = classifyRegion(a.data.title, a.body, a.data.tags || []);
    counts[region] = (counts[region] || 0) + 1;
  }

  return REGIONS.map(r => ({ ...r, count: counts[r.slug] || 0 }));
}
