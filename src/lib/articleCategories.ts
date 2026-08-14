export const CANONICAL_ARTICLE_CATEGORIES = [
  "房源点评",
  "大学住宿",
  "城市指南",
  "国家总览",
  "租房攻略",
  "落地准备",
  "入住准备",
  "账单与入住",
] as const;

const canonicalCategorySet = new Set<string>(CANONICAL_ARTICLE_CATEGORIES);

export function isCanonicalArticleCategory(value: string | undefined): value is string {
  return Boolean(value && canonicalCategorySet.has(value));
}
