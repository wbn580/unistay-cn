/**
 * UniStay 优住 — 展示格式化工具
 */
import type { CityT, PropertyLite } from './data';

export const SITE = {
  name: 'UniStay 优住',
  shortName: '优住',
  url: 'https://unistay.cn',
  imgBase: 'https://img.unistay.cn',
  heroImage: 'https://img.unistay.cn/housing/unistay-hero-litwindow-2026-2100x1382.jpg',
  disclaimer: '信息仅供参考，价格与房态以运营方实时为准。',
} as const;

const CURRENCY_SYMBOL: Record<string, string> = {
  GBP: '£',
  USD: '$',
  AUD: 'A$',
  CAD: 'C$',
  NZD: 'NZ$',
  SGD: 'S$',
  EUR: '€',
  AED: 'AED ',
};

export function cur(code: string): string {
  return CURRENCY_SYMBOL[code] ?? `${code} `;
}

export function fmtNum(n: number): string {
  return n.toLocaleString('en-US');
}

/** 计价周期：weekly → 周，monthly → 月 */
export function durUnit(duration: string | null | undefined): string {
  return duration === 'weekly' ? '周' : duration === 'monthly' ? '月' : '期';
}

/** 价格短句：£199/周起 */
export function priceFrom(p: {
  currency: string;
  min_price: number | null;
  price_duration?: string;
}): string | null {
  if (!p.min_price) return null;
  return `${cur(p.currency)}${fmtNum(p.min_price)}/${durUnit(p.price_duration)}起`;
}

/** 价格区间：£491–653/周 */
export function priceRange(p: {
  currency: string;
  min_price: number | null;
  max_price?: number | null;
  price_duration?: string;
}): string | null {
  if (!p.min_price) return null;
  const s = cur(p.currency);
  const u = durUnit(p.price_duration);
  if (p.max_price && p.max_price !== p.min_price) {
    return `${s}${fmtNum(p.min_price)}–${fmtNum(p.max_price)}/${u}`;
  }
  return `${s}${fmtNum(p.min_price)}/${u}`;
}

/** 城市显示名：有中文名 →「伦敦 London」；无 → 英文名 */
export function cityDisplay(c: Pick<CityT, 'name' | 'name_zh'>): string {
  return c.name_zh ? `${c.name_zh} ${c.name}` : c.name;
}
/** 城市短名（H1/正文用）：优先中文 */
export function cityShort(c: Pick<CityT, 'name' | 'name_zh'>): string {
  return c.name_zh || c.name;
}

/** 房型代码 → 中文标签 */
const UNIT_LABEL: Record<string, string> = {
  studio: 'Studio 单间公寓',
  ensuite: 'Ensuite 独卫套间',
  non_ensuite: '标准间（共用卫浴）',
  shared_room: '合住房',
  private_room: '独立房间',
  apartment: '整租公寓',
  independent_house: '独栋房源',
  branded_independent_house: '品牌独栋',
  '1b': '一室',
  '2b': '两室',
  '3b': '三室',
  '4b': '四室',
  '5b': '五室',
  '6b': '六室',
  '7b': '七室',
  '8b': '八室',
  greater_8b: '八室以上',
};
export function unitLabel(code: string): string {
  return UNIT_LABEL[code] ?? code;
}

/** 评分维度 → 中文标签（渲染白名单 · 按重要度排序） */
export const DIM_ORDER: Array<[string, string]> = [
  ['location', '位置'],
  ['value_for_money', '性价比'],
  ['staff', '员工服务'],
  ['cleaning', '清洁'],
  ['safety_security', '安全'],
  ['internet', '网络'],
  ['amenities', '设施'],
  ['social', '社交氛围'],
  ['community', '社区'],
  ['management', '管理'],
  ['room_experience', '房间体验'],
  ['study_environment', '学习环境'],
];

export function pickDims(
  dims: Record<string, number> | null | undefined,
  max = 8
): Array<{ key: string; label: string; value: number }> {
  if (!dims) return [];
  const out: Array<{ key: string; label: string; value: number }> = [];
  for (const [key, label] of DIM_ORDER) {
    const v = dims[key];
    if (typeof v === 'number' && v > 0) out.push({ key, label, value: v });
    if (out.length >= max) break;
  }
  return out;
}

/** desc 里混着 &amp;nbsp; 这类实体，展示前清一遍 */
export function cleanDesc(s: string | null | undefined): string {
  if (!s) return '';
  return s
    .replace(/&amp;/g, '&')
    .replace(/&nbsp;/g, ' ')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

/** available_from "13-07-2026" → 2026年7月13日 */
export function fmtAvail(s: string | null | undefined): string | null {
  if (!s) return null;
  const m = s.match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (!m) return s;
  return `${m[3]}年${Number(m[2])}月${Number(m[1])}日`;
}

/** 房源图 URL（image 为空返回 null，由占位组件接管） */
export function propImg(image: string | null | undefined): string | null {
  return image ? `${SITE.imgBase}/${image}` : null;
}

/** 星星串：4 → ★★★★☆ */
export function stars(rating: number): string {
  const r = Math.round(rating);
  return '★'.repeat(Math.max(0, Math.min(5, r))) + '☆'.repeat(Math.max(0, 5 - r));
}

/** 评论截断 */
export function clip(s: string, n: number): string {
  return s.length > n ? s.slice(0, n).trimEnd() + '…' : s;
}

/** 城市页可比性排序：有价+有评优先，再按评论数 */
export function sortForListing(a: PropertyLite, b: PropertyLite): number {
  const ar = typeof a.rating === 'number' ? a.rating : 0;
  const br = typeof b.rating === 'number' ? b.rating : 0;
  const ag = a.g_reviews ?? 0;
  const bg = b.g_reviews ?? 0;
  if ((bg > 0 ? 1 : 0) !== (ag > 0 ? 1 : 0)) return (bg > 0 ? 1 : 0) - (ag > 0 ? 1 : 0);
  if (br !== ar) return br - ar;
  return bg - ag;
}
