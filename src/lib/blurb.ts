/**
 * UniStay 优住 — 「编辑速评」生成器
 * 由房源真实字段驱动（价格 / 房型 / 评分维度 / 谷歌评价数 / 租期），
 * 用 slug 哈希在多套措辞池间轮换，保证逐页差异化，不套同一句模板。
 * 口吻：住隔壁的学长学姐——给数、给判断，不吹不催。
 */
import type { PropertyFull } from './data';
import { numRating } from './data';
import { cur, durUnit, fmtNum, unitLabel, DIM_ORDER } from './format';

function hash(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}
function pick<T>(arr: T[], seed: number, salt: number): T {
  return arr[(seed + salt * 7) % arr.length];
}

const DIM_ZH = new Map(DIM_ORDER);

export function editorBlurb(p: PropertyFull, cityZh: string): string {
  const seed = hash(p.slug);
  const parts: string[] = [];
  const u = durUnit(p.price_duration);

  // ① 价格事实
  if (p.min_price) {
    const priceStr =
      p.max_price && p.max_price !== p.min_price
        ? `${cur(p.currency)}${fmtNum(p.min_price)}到${fmtNum(p.max_price)}一${u}`
        : `${cur(p.currency)}${fmtNum(p.min_price)}一${u}`;
    parts.push(
      pick(
        [
          `先看钱：${priceStr}`,
          `价格摆在这：${priceStr}`,
          `${cityZh}这套的报价是${priceStr}`,
          `账面价${priceStr}`,
          `租金${priceStr}`,
        ],
        seed,
        1
      ) + pick(['，', '；'], seed, 2)
    );
  } else {
    parts.push(
      pick(
        [`这套暂未公开报价，`, `价格要询后才知道，`, `报价没挂出来，`],
        seed,
        1
      )
    );
  }

  // ② 房型 / 租期
  const units = (p.unit_types || []).slice(0, 3).map(unitLabel);
  if (units.length) {
    parts.push(
      pick(
        [
          `房型有${units.join('、')}。`,
          `能选的房型是${units.join('、')}。`,
          `${units.join('、')}都有。`,
        ],
        seed,
        3
      )
    );
  } else if (p.min_lease) {
    parts.push(`最短${p.min_lease}${u === '周' ? '周' : '个月'}起租。`);
  }

  // ③ 口碑：优先评分维度，其次谷歌评价
  const dims = p.rating_dims;
  if (dims) {
    const entries = Object.entries(dims)
      .filter(([k, v]) => typeof v === 'number' && DIM_ZH.has(k))
      .sort((a, b) => b[1] - a[1]);
    if (entries.length >= 2) {
      const [topK, topV] = entries[0];
      const [lowK, lowV] = entries[entries.length - 1];
      const topZh = DIM_ZH.get(topK);
      const lowZh = DIM_ZH.get(lowK);
      if (topV >= 4.2 && lowV < 3.8 && topK !== lowK) {
        parts.push(
          pick(
            [
              `住客给${topZh}打了${topV}分，但${lowZh}只有${lowV}分，介意的先掂量。`,
              `${topZh}是强项（${topV}分），${lowZh}偏弱（${lowV}分），看你在乎哪头。`,
              `${topZh}评分${topV}算能打，${lowZh}${lowV}分是短板。`,
            ],
            seed,
            4
          )
        );
      } else if (topV >= 4.2) {
        parts.push(
          pick(
            [`分项评分里${topZh}最高，${topV}分。`, `住客最认${topZh}，给到${topV}分。`],
            seed,
            5
          )
        );
      } else {
        parts.push(`分项评分整体一般（最高${topZh}${topV}分），建议把评价细读一遍。`);
      }
    }
  } else if (p.g_reviews && p.g_rating) {
    parts.push(
      p.g_rating >= 4.0
        ? pick(
            [
              `谷歌上${fmtNum(p.g_reviews)}条评价给到${p.g_rating}分，口碑站得住。`,
              `${fmtNum(p.g_reviews)}条谷歌评价、均分${p.g_rating}，可以作数。`,
            ],
            seed,
            6
          )
        : `谷歌${fmtNum(p.g_reviews)}条评价均分${p.g_rating}，口碑一般，别只看图片下单。`
    );
  } else if (p.g_reviews) {
    const r = numRating(p.rating);
    parts.push(
      r && r < 3
        ? `平台评分只有${r}分（${fmtNum(p.g_reviews)}条评价），下手前务必把差评看完。`
        : `有${fmtNum(p.g_reviews)}条公开评价，值得翻一翻再定。`
    );
  }

  // ④ 收尾建议
  parts.push(
    pick(
      [
        '价格以运营方实时报价为准，拿不准就让小助手帮你对比同城几家。',
        '报价随房态浮动，签约前让小助手再帮你核一遍当周价格。',
        '以运营方实时报价为准，同预算下建议多比两家再签。',
      ],
      seed,
      8
    )
  );

  return parts.join('');
}
