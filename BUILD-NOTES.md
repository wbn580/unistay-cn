# UniStay 优住 平台化重做 · BUILD NOTES（2026-07-07）

## 本次改动（覆盖旧「海外住宿观察」指南皮）
- **品牌**：UniStay 优住 · 墨青 #22485A + 杏金 #C9873B + 系统黑体栈；SSOT `unistay-cn-brand/`（favicon=亮灯四格窗，五件套已入 public/）
- **设计系统**：src/styles/global.css 重写（--color-* token + .us-* 组件类：条目卡/评分条/chip/按钮/scroll-reveal）
- **BaseLayout/BaseHead/Header/Footer**：全部重写（修掉遗留 git 冲突标记 ×2 处：BaseLayout + about.astro）；widget 三件套 chat.unistay.cn（住宿小助手 · #22485A/#C9873B）
- **首页**：平台首页（亮灯窗 hero + 信任数字 + 三步 + 12 国 + 热门城市 + top 公寓 + 真实评论中英对照提要 + 8 校快链 + 指南 + FAQ JSON-LD）
- **新数据路由**：
  - /zhusu/ · /zhusu/[country]/ ×12 · /chengshi/[country]/[city]/ ×228
  - /fangyuan/[slug]/ ×3246（编辑速评数据驱动逐页差异化 + 分维度评分条 + 英文原评 + LodgingBusiness/FAQ JSON-LD）
  - /daxue/ · /daxue/[slug]/ ×703 · /guides/（409 篇索引）· category/[category] 重写（原页 hardcode 2 类且 lang 过滤 bug 致空列表）
- **保留**：409 篇文章 URL（/{id}/）不变
- **public/_headers**：HTML no-cache + assets immutable（§7.B）

## 待 Mac 侧执行
1. `npm install`（无新依赖，保险起见）
2. 房源图转存（同 findstay 一个脚本，key 共用）：`housing_rehost_images.py`
3. `npm run build`（注意 build 含 astro check + pagefind）→ sanity/盗链 gate → 截图（桌面+手机：首页/城市/房源页）
4. `npx wrangler deploy`（Workers Static Assets · wrangler.toml 已有 [assets]）
5. unistay.cn 未接腾讯 CDN（未备案）；如后续备案接 CDN 记得 purge 流程

## 已知风险 / 后续
- 评论原文为英文（真实性优先），中文速评已补；后续可派 Hermes 批量生成更细的中文摘译
- name_zh 只覆盖 ~100 主要城市，其余显示英文名（数据层可后补）

## ⚠️ wizard_cities.json 计价周期约束（2026-07-10）
AI 找房向导按每套房源真实 price_duration 显示单位（周/月）。
重新生成 public/wizard_cities.json 时**必须**：每套房源 props 带 `u`（"weekly"/"monthly"，join 自 src/data/properties/*.json 的 price_duration）+ 每城市带 `du`（该城主导周期）。
缺 `u`/`du` 会导致卡片单位回退不准 / 周月混用失真。各国惯例不同（US/CA/EU 多月租，AU/UK 周租，IE 混合），不可按国家一刀切。
