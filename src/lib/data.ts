/**
 * UniStay 优住 — 构建期数据加载层
 * 用 fs 读 src/data/*.json（避免让 TS 对 1MB 级 JSON 做字面量类型推断，
 * 也避免 Vite 把大 JSON 打进模块图），模块级缓存，只在构建期执行。
 */
import { readFileSync } from 'node:fs';

export interface CountryT {
  name: string;
  zh: string;
  slug: string;
  cc: string;
  currency: string;
  property_count: number;
  city_count: number;
  university_count: number;
}

export interface CityUniRef {
  slug: string;
  name: string;
  rank: number;
}

export interface CityT {
  slug: string;
  country: string;
  country_name: string;
  country_zh: string;
  cc: string;
  name: string;
  name_zh?: string;
  property_count: number;
  min_price: number | null;
  currency: string;
  universities: CityUniRef[];
}

export interface ReviewT {
  author: string;
  rating: number;
  text: string;
  source?: string;
  time?: string;
}

export interface PropertyLite {
  slug: string;
  name: string;
  country: string;
  country_zh: string;
  cc: string;
  city: string;
  city_slug: string;
  currency: string;
  min_price: number | null;
  price_duration: string;
  rating: number | boolean | null;
  g_reviews: number | null;
  image: string | null;
}

export interface PropertyFull extends PropertyLite {
  id: string;
  source: string;
  country_name: string;
  address: string | null;
  max_price: number | null;
  deposit: string | number | null;
  unit_types: string[];
  tags: string[];
  min_lease: number | string | null;
  available_from: string | null;
  rating_dims: Record<string, number> | null;
  g_rating: number | null;
  reviews: ReviewT[];
  desc?: string | null;
}

export interface UniversityT {
  slug: string;
  name: string;
  rank: number;
  country: string;
  country_zh: string;
  address: string | null;
  website: string | null;
  g_rating: number | null;
  g_reviews: number | null;
  city_key: string | null;
  reviews?: ReviewT[];
}

export interface StatsT {
  properties: number;
  cities: number;
  countries: number;
  universities: number;
  review_snippets: number;
  google_reviews_total: number;
  built?: string;
}

function load<T>(rel: string): T {
  const url = new URL(`../data/${rel}`, import.meta.url);
  return JSON.parse(readFileSync(url, 'utf-8')) as T;
}

let _stats: StatsT | null = null;
let _countries: CountryT[] | null = null;
let _cities: CityT[] | null = null;
let _pindex: PropertyLite[] | null = null;
let _unis: UniversityT[] | null = null;
const _propsByCountry = new Map<string, PropertyFull[]>();

export function getStats(): StatsT {
  return (_stats ??= load<StatsT>('stats.json'));
}
export function getCountries(): CountryT[] {
  return (_countries ??= load<CountryT[]>('countries.json'));
}
export function getCities(): CityT[] {
  return (_cities ??= load<CityT[]>('cities.json'));
}
export function getPropertyIndex(): PropertyLite[] {
  return (_pindex ??= load<PropertyLite[]>('properties_index.json'));
}
export function getUniversities(): UniversityT[] {
  return (_unis ??= load<UniversityT[]>('universities.json'));
}
export function getCountryProperties(countrySlug: string): PropertyFull[] {
  if (!_propsByCountry.has(countrySlug)) {
    _propsByCountry.set(countrySlug, load<PropertyFull[]>(`properties/${countrySlug}.json`));
  }
  return _propsByCountry.get(countrySlug)!;
}
export function getAllProperties(): PropertyFull[] {
  return getCountries().flatMap((c) => getCountryProperties(c.slug));
}

/** 数值型评分守卫：数据里 rating 存在 true/false 脏值，只认 number */
export function numRating(v: unknown): number | null {
  return typeof v === 'number' && v > 0 && v <= 5 ? v : null;
}

/** 城市查找：country slug + city slug */
export function findCity(country: string, city: string): CityT | undefined {
  return getCities().find((c) => c.country === country && c.slug === city);
}
