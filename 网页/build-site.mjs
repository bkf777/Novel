#!/usr/bin/env node
/**
 * 《注销通知》项目文档站构建脚本
 * Markdown -> 自包含静态站（侧边导航 / 目录 / 全文搜索 / 纸墨双主题 / 阅读进度）
 *
 * 用法：node build-site.mjs
 * 依赖：marked（安装在上级 .build-deps/，不污染源码目录）
 * 源文档：../手稿/（正文与设定） + ./00-站点总览.md（站点首页）
 */
import { readFileSync, writeFileSync, readdirSync, statSync, rmSync, mkdirSync } from 'node:fs';
import { dirname, join, relative, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { marked } = require('/Users/ezreal/projects/小说创作/.build-deps/node_modules/marked');

const ROOT = dirname(fileURLToPath(import.meta.url));   // .../小说创作/网页
const PROJECT = dirname(ROOT);                            // .../小说创作
const OUT = join(ROOT, 'site-dist');

/** 页面清单：顺序即侧边栏顺序。src 相对 PROJECT */
const PAGES = [
  {
    src: '网页/00-站点总览.md', url: 'index.html', nav: '项目总览', section: 'overview',
    title: '《注销通知》· 项目总览',
    hero: {
      kicker: '科幻 / 伦理悬疑 / 家庭救赎',
      title: '注销通知',
      sub: '人死后，生前预录的记忆权重在网里再「活」三天；三天后想多留，烧掉的每一秒算力，都要从活人的脑波里硬抽——而最便宜、最隐蔽的抽血方式，是抽死者的亲生骨肉。',
      stats: [['24', '章全书'], ['9', '天主线'], ['3,521', '字（第一章）']],
    },
  },
  { src: 'gen:progress', url: 'progress.html', nav: '章节进度', section: 'overview', title: '《注销通知》· 章节进度表' },
  { src: '手稿/第01章-注销通知.md', url: 'ch01.html', nav: '第一章 注销通知', section: 'text', title: '第一章 注销通知' },
  {
    src: '手稿/00-世界观设定.md', url: 'worldbuilding.html', nav: '世界观设定', section: 'bible',
    title: '《注销通知》世界观设定',
    banner: {
      tone: 'warn',
      text: '设定口径提示：本页 §2「回声消散、椅子变空」是早期表述，与定稿第一章「她坐在那儿，眼睛还睁着」并存、尚未统一。影像改编暂按定稿第一章执行，本站如实呈现两版口径。',
    },
  },
  { src: '手稿/00-人物档案.md', url: 'characters.html', nav: '人物档案', section: 'bible', title: '人物档案 · 《注销通知》' },
  { src: '手稿/01-大纲.md', url: 'outline.html', nav: '全书大纲', section: 'bible', title: '《注销通知》全书大纲' },
  { src: '手稿/03-文风基准.md', url: 'style.html', nav: '文风基准', section: 'bible', title: '《注销通知》文风基准' },
  { src: '手稿/视频化/第01章-短剧版.md', url: 'shortdrama.html', nav: '竖屏短剧版', section: 'adapt', title: '《注销通知》第一章 · 竖屏短剧版（2 集）' },
  { src: '手稿/视频化/第01章-快节奏改编.md', url: 'adaptation.html', nav: '快节奏改编版', section: 'adapt', title: '第一章 注销通知（快节奏改编版 · 视频向）' },
  { src: '手稿/视频化/第01章-H3提示词.md', url: 'h3-prompts.html', nav: 'H3 视频提示词', section: 'adapt', title: '《注销通知》第一章 · 竖屏短剧版 H3 视频提示词' },
];

const SECTIONS = [
  { id: 'overview', label: '项目总览' },
  { id: 'text', label: '正文' },
  { id: 'bible', label: '设定与档案' },
  { id: 'adapt', label: '影像改编' },
];

/** 源文件相对路径 -> 站点 URL 映射 */
const URL_MAP = new Map(PAGES.filter((p) => !p.src.startsWith('gen:')).map((p) => [p.src, p.url]));

// ---------------------------------------------------------------- utils
const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** 稳定 slug：中文保留，去掉标点空白 */
function slugify(text, fallback) {
  const s = String(text)
    .trim()
    .replace(/[\s\u3000]+/g, '-')
    .replace(/[《》【】（）()：:，,。.、\/·—\-!！?？"'`]/g, '')
    .replace(/-{2,}/g, '-')
    .replace(/^-|-$/g, '');
  return s || `sec-${fallback}`;
}

function stripTags(html) {
  return String(html)
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim();
}

/** 把 Markdown 里的 file:/// 绝对链接 / 裸 .md 链接改写为站内相对链接 */
function rewriteLinks(md) {
  const base = PROJECT.endsWith('/') ? PROJECT : PROJECT + '/';
  return md.replace(/\]\(([^)]+)\)/g, (whole, href) => {
    let path = href.trim();
    let frag = '';
    const hashIdx = path.indexOf('#');
    if (hashIdx >= 0 && !path.startsWith('http')) {
      frag = path.slice(hashIdx);
      path = path.slice(0, hashIdx);
    }
    if (!path) return whole;
    let rel = null;
    if (path.startsWith('file://')) {
      const p = decodeURIComponent(path.replace(/^file:\/\//, ''));
      if (p.startsWith(base)) rel = p.slice(base.length);
    } else if (!/^(https?:|mailto:|#)/.test(path)) {
      rel = path.replace(/^\.\//, '');
      if (rel.startsWith('/')) rel = rel.slice(1);
    }
    const target = rel && URL_MAP.get(rel);
    if (!target) return whole;
    return `](${encodeURI(target)}${frag})`;
  });
}

// ---------------------------------------------------------------- markdown -> html
function renderMarkdown(md, pageUrl) {
  const headings = [];
  const usedIds = new Set();

  const renderer = new marked.Renderer();
  renderer.heading = function ({ tokens, depth }) {
    const text = this.parser.parseInline(tokens);
    const plain = stripTags(text);
    let id = slugify(plain, headings.length);
    let n = 2;
    while (usedIds.has(id)) id = `${id}-${n++}`;
    usedIds.add(id);
    if (depth >= 2 && depth <= 3) headings.push({ depth, text: plain, id });
    return `<h${depth} id="${esc(id)}">${text}</h${depth}>\n`;
  };

  // 链接：新窗口打开 + 安全 rel
  const defaultLink = renderer.link.bind(renderer);
  renderer.link = function ({ href, title, tokens }) {
    const text = this.parser.parseInline(tokens);
    const ext = /^https?:/i.test(href);
    return `<a href="${esc(href)}"${title ? ` title="${esc(title)}"` : ''}${
      ext ? ' target="_blank" rel="noopener noreferrer"' : ''
    }>${text}</a>`;
  };
  void defaultLink;

  const html = marked.parse(rewriteLinks(md), {
    renderer,
    gfm: true,
    breaks: false,
    headerIds: false,
    mangle: false,
  });

  return { html, headings, pageUrl };
}

// ---------------------------------------------------------------- 章节进度页（由 02-写作计划.json 生成）
function renderProgressPage() {
  const plan = JSON.parse(readFileSync(join(PROJECT, '手稿', '02-写作计划.json'), 'utf8'));
  const chapters = plan.chapters || [];
  const done = chapters.filter((c) => c.status === 'completed');
  const days = plan.timeline?.chapterDays || {};

  const rows = chapters
    .map((c) => {
      const day = c.day || days[String(c.chapterNumber)] || '—';
      const isDone = c.status === 'completed';
      const wc = c.wordCount != null ? `${c.wordCount.toLocaleString('en-US')} 字` : '—';
      return `<tr${isDone ? ' class="row-done"' : ''}>
        <td class="c-no">${c.chapterNumber}</td>
        <td class="c-title">${esc(c.title || '（未定）')}</td>
        <td class="c-day">${esc(day)}</td>
        <td class="c-status">${isDone ? '<span class="badge done">已定稿</span>' : '<span class="badge todo">未动笔</span>'}</td>
        <td class="c-wc">${esc(wc)}</td>
      </tr>`;
    })
    .join('\n');

  const html = `<h1 id="章节进度表">章节进度表</h1>
<p>《注销通知》全书共 <strong>${plan.totalChapters}</strong> 章。主线窗口 <strong>${esc(plan.timeline?.mainWindow || '')}</strong>，结局延展至 10-30；当前已完成 <strong>${done.length}</strong> 章。</p>
<table>
  <thead><tr><th>章</th><th>标题</th><th>日程</th><th>状态</th><th>字数</th></tr></thead>
  <tbody>
${rows}
  </tbody>
</table>
<h2 id="全书时钟">全书时钟</h2>
<p>${(plan.timeline?.clocks || []).map((c) => `<strong>${esc(c.name)}</strong>（${esc(c.length)}，归零于 ${esc(c.zeroAt)}）`).join('；')}。</p>
<h2 id="写作红线">写作红线</h2>
<ul>
${(plan.redLines || []).map((r) => `  <li>${esc(r)}</li>`).join('\n')}
</ul>`;

  const headings = [
    { depth: 2, text: '章节进度表', id: '章节进度表' },
    { depth: 2, text: '全书时钟', id: '全书时钟' },
    { depth: 2, text: '写作红线', id: '写作红线' },
  ];
  return { html, headings };
}

// ---------------------------------------------------------------- layout
function renderSidebar(page) {
  return SECTIONS.map((sec) => {
    const items = PAGES.filter((p) => p.section === sec.id)
      .map((p) => {
        const active = p.url === page.url ? ' class="active"' : '';
        const cur = p.url === page.url ? ' aria-current="page"' : '';
        return `<li><a href="${encodeURI(p.url)}"${active}${cur}><span class="dot"></span>${esc(p.nav)}</a></li>`;
      })
      .join('\n        ');
    return `<div class="nav-group">
      <div class="nav-group-title">${esc(sec.label)}</div>
      <ul>
        ${items}
      </ul>
    </div>`;
  }).join('\n    ');
}

function renderToc(headings) {
  if (!headings.length) return '';
  const items = headings
    .map((h) => `<li class="lv${h.depth}"><a href="#${encodeURIComponent(h.id)}">${esc(h.text)}</a></li>`)
    .join('\n            ');
  return `<nav class="toc" id="toc" aria-label="本页目录">
      <div class="toc-title">本页目录</div>
      <ul>
            ${items}
      </ul>
    </nav>`;
}

function renderBanner(banner) {
  if (!banner) return '';
  return `<div class="notice notice-${esc(banner.tone || 'info')}">
    <span class="notice-tag">口径提示</span>
    <span class="notice-body">${banner.text}</span>
  </div>`;
}

function renderHero(hero) {
  if (!hero) return '';
  const stats = (hero.stats || [])
    .map(([v, l]) => `<div><b>${esc(v)}</b><span>${esc(l)}</span></div>`)
    .join('\n          ');
  return `<div class="hero">
        <div class="hero-kicker">${esc(hero.kicker)}</div>
        <h1 class="hero-title">${esc(hero.title)}</h1>
        <div class="hero-sub">${esc(hero.sub)}</div>
        <div class="hero-stats">
          ${stats}
        </div>
      </div>`;
}

function renderPage({ page, bodyHtml, headings }) {
  const idx = PAGES.findIndex((p) => p.url === page.url);
  const prev = idx > 0 ? PAGES[idx - 1] : null;
  const next = idx < PAGES.length - 1 ? PAGES[idx + 1] : null;
  const prevNext =
    prev || next
      ? `<nav class="prevnext">
        ${prev ? `<a class="pn prev" href="${encodeURI(prev.url)}"><span>← 上一篇</span><strong>${esc(prev.nav)}</strong></a>` : '<span></span>'}
        ${next ? `<a class="pn next" href="${encodeURI(next.url)}"><span>下一篇 →</span><strong>${esc(next.nav)}</strong></a>` : '<span></span>'}
      </nav>`
      : '';

  return `<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(page.title)} · 注销通知</title>
<meta name="description" content="《注销通知》科幻长篇：正文、世界观设定、人物档案、24 章大纲与影像改编稿">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23fbfaf7'/%3E%3Crect x='5' y='5' width='54' height='54' rx='9' fill='none' stroke='%23b03a2e' stroke-width='3'/%3E%3Ctext x='32' y='45' font-size='34' text-anchor='middle' fill='%232b2a27' font-family='serif'%3E%E6%B3%A8%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="progress" id="progress"></div>
<header class="topbar">
  <button class="icon-btn menu-btn" id="menuBtn" aria-label="打开目录">
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/></svg>
  </button>
  <a class="brand" href="index.html">
    <span class="brand-mark">注</span>
    <span class="brand-text"><strong>注销通知</strong><em>科幻 / 伦理悬疑 / 家庭救赎</em></span>
  </a>
  <div class="topbar-actions">
    <button class="icon-btn" id="searchBtn" aria-label="搜索">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" fill="none"/><path d="M20 20l-3.5-3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      <span class="btn-label">搜索</span>
    </button>
    <button class="icon-btn" id="themeBtn" aria-label="切换主题">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M21 13a8.5 8.5 0 11-10-10 7 7 0 0010 10z" fill="currentColor"/></svg>
    </button>
  </div>
</header>

<div class="layout">
  <aside class="sidebar" id="sidebar">
    ${renderSidebar(page)}
    <div class="sidebar-foot">
      <div>24 章 · 主线 9 天</div>
      <div>第一章已定稿</div>
    </div>
  </aside>
  <div class="scrim" id="scrim"></div>

  <main class="main">
    <article class="doc">
      ${renderHero(page.hero)}
      ${renderBanner(page.banner)}
      ${bodyHtml}
    </article>
    ${prevNext}
    <footer class="site-foot">《注销通知》项目内容站 · 正文与设定以定稿手稿为准</footer>
  </main>

  ${renderToc(headings)}
</div>

<div class="search-modal" id="searchModal" hidden>
  <div class="search-box">
    <div class="search-input-row">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" fill="none"/><path d="M20 20l-3.5-3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      <input id="searchInput" type="search" placeholder="搜索全文：人物、机制、章节、文风红线…" autocomplete="off">
      <button class="icon-btn" id="searchClose" aria-label="关闭">Esc</button>
    </div>
    <div class="search-results" id="searchResults"></div>
  </div>
</div>

<button class="totop" id="toTop" aria-label="回到顶部">↑</button>
<script src="assets/app.js"></script>
</body>
</html>
`;
}

// ---------------------------------------------------------------- build
function main() {
  try {
    rmSync(OUT, { recursive: true, force: true });
  } catch {}
  mkdirSync(join(OUT, 'assets'), { recursive: true });

  const searchIndex = [];

  for (const page of PAGES) {
    let html, headings;
    if (page.src.startsWith('gen:')) {
      ({ html, headings } = renderProgressPage());
    } else {
      const file = join(PROJECT, page.src);
      try {
        statSync(file);
      } catch {
        throw new Error(`缺少源文件：${page.src}`);
      }
      const md = readFileSync(file, 'utf8');
      ({ html, headings } = renderMarkdown(md, page.url));
    }
    writeFileSync(join(OUT, page.url), renderPage({ page, bodyHtml: html, headings }), 'utf8');

    // 搜索索引：按标题分段，便于定位
    const flat = stripTags(html);
    searchIndex.push({
      url: page.url,
      nav: page.nav,
      title: page.title,
      text: flat.slice(0, 4000),
      sections: headings.slice(0, 60).map((h) => ({ t: h.text, u: `${page.url}#${encodeURIComponent(h.id)}` })),
    });
    console.log(`  ✓ ${page.url}  (${(html.length / 1024).toFixed(1)} KB, ${headings.length} 目录项)`);
  }

  writeFileSync(join(OUT, 'assets', 'search-index.json'), JSON.stringify(searchIndex), 'utf8');
  writeFileSync(join(OUT, 'assets', 'style.css'), STYLE, 'utf8');
  writeFileSync(join(OUT, 'assets', 'app.js'), APP_JS, 'utf8');

  console.log(`\n构建完成 → ${OUT}`);
}

// ---------------------------------------------------------------- assets
const STYLE = String.raw`
:root{
  --bg:#fbfaf7; --bg-soft:#fffefb; --bg-elev:#ffffff; --bg-hover:#f3f0e8;
  --fg:#2b2a27; --fg-dim:#55534b; --fg-mute:#8b8579;
  --line:#e2dfd8; --line-soft:#eceae2;
  --accent:#b03a2e; --accent-soft:rgba(176,58,46,.08); --accent-2:#3f6b8a;
  --mark:rgba(176,58,46,.2);
  --radius:12px; --sidebar-w:262px; --toc-w:250px; --topbar-h:58px;
  --sans:"Noto Serif SC","Source Han Serif SC","Songti SC","SimSun",Georgia,serif;
  --serif:"Songti SC","Noto Serif SC","Source Han Serif SC",Georgia,serif;
  --mono:"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
}
html[data-theme="dark"]{
  --bg:#14130f; --bg-soft:#1b1a15; --bg-elev:#211f19; --bg-hover:#292720;
  --fg:#e9e5db; --fg-dim:#b4aea1; --fg-mute:#8b8478;
  --line:#33302a; --line-soft:#262420;
  --accent:#d4674f; --accent-soft:rgba(212,103,79,.14); --accent-2:#6fa8cf;
  --mark:rgba(212,103,79,.28);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:calc(var(--topbar-h) + 16px)}
body{
  margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);
  font-size:16px;line-height:1.85;-webkit-font-smoothing:antialiased;
}
a{color:inherit;text-decoration:none}
.progress{position:fixed;top:0;left:0;height:2px;width:0;background:linear-gradient(90deg,var(--accent),var(--accent-2));z-index:100;transition:width .1s linear}

/* topbar */
.topbar{
  position:sticky;top:0;z-index:60;height:var(--topbar-h);
  display:flex;align-items:center;gap:14px;padding:0 18px;
  background:color-mix(in srgb,var(--bg) 86%,transparent);
  backdrop-filter:saturate(180%) blur(12px);
  border-bottom:1px solid var(--line);
}
.brand{display:flex;align-items:center;gap:10px;min-width:0}
.brand-mark{
  width:30px;height:30px;flex:none;display:grid;place-items:center;border-radius:8px;
  background:linear-gradient(135deg,var(--accent),#7a2f22);color:#fff;
  font-family:var(--serif);font-weight:700;font-size:16px;
}
.brand-text{display:flex;flex-direction:column;line-height:1.25;min-width:0}
.brand-text strong{font-size:15px;letter-spacing:.02em}
.brand-text em{font-style:normal;font-size:11.5px;color:var(--fg-mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.topbar-actions{margin-left:auto;display:flex;align-items:center;gap:8px}
.icon-btn{
  display:inline-flex;align-items:center;gap:6px;height:34px;padding:0 10px;
  background:transparent;border:1px solid var(--line);border-radius:9px;color:var(--fg-dim);
  cursor:pointer;font-size:13px;font-family:inherit;transition:.16s;
}
.icon-btn:hover{background:var(--bg-hover);color:var(--fg);border-color:var(--fg-mute)}
.btn-label{font-size:13px}
.menu-btn{display:none}

/* layout */
.layout{display:flex;align-items:flex-start;max-width:1440px;margin:0 auto}
.sidebar{
  width:var(--sidebar-w);flex:none;position:sticky;top:var(--topbar-h);
  height:calc(100vh - var(--topbar-h));overflow-y:auto;
  padding:22px 14px 26px 20px;border-right:1px solid var(--line-soft);
}
.nav-group{margin-bottom:22px}
.nav-group-title{
  font-size:11.5px;letter-spacing:.14em;color:var(--fg-mute);
  text-transform:uppercase;margin:0 0 8px 10px;font-weight:600;
}
.nav-group ul{list-style:none;margin:0;padding:0}
.nav-group a{
  display:flex;align-items:center;gap:9px;padding:7px 10px;border-radius:8px;
  font-size:14px;color:var(--fg-dim);transition:.14s;line-height:1.5;
}
.nav-group a:hover{background:var(--bg-hover);color:var(--fg)}
.nav-group a .dot{width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.35;flex:none}
.nav-group a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.nav-group a.active .dot{opacity:1}
.sidebar-foot{
  margin-top:26px;padding:12px 10px;border-top:1px solid var(--line-soft);
  font-size:11.5px;color:var(--fg-mute);line-height:1.8;
}
.scrim{display:none}

/* main */
.main{flex:1;min-width:0;padding:38px 44px 70px}
.doc{max-width:820px}
.hero{
  border:1px solid var(--line);border-radius:16px;padding:30px 30px 26px;margin-bottom:38px;
  background:
    radial-gradient(120% 140% at 0% 0%,var(--accent-soft),transparent 58%),
    var(--bg-soft);
}
.hero-kicker{
  display:inline-block;font-size:11.5px;letter-spacing:.18em;color:var(--accent);
  border:1px solid var(--accent-soft);background:var(--accent-soft);
  padding:4px 10px;border-radius:999px;margin-bottom:14px;
}
.hero-title{
  font-family:var(--serif);font-size:44px;line-height:1.15;margin:0 0 12px;
  letter-spacing:.06em;font-weight:700;
}
.hero-sub{color:var(--fg-dim);font-size:15px;max-width:62ch;line-height:1.8}
.hero-stats{display:flex;gap:30px;margin-top:22px;padding-top:18px;border-top:1px solid var(--line-soft)}
.hero-stats div{display:flex;flex-direction:column}
.hero-stats b{font-size:24px;font-family:var(--serif);color:var(--fg);line-height:1.2}
.hero-stats span{font-size:11.5px;color:var(--fg-mute);letter-spacing:.08em}

/* prose */
.doc h1{
  font-family:var(--serif);font-size:33px;line-height:1.35;margin:0 0 26px;
  padding-bottom:18px;border-bottom:1px solid var(--line);letter-spacing:.02em;font-weight:700;
}
.doc h2{
  font-size:22px;line-height:1.5;margin:52px 0 16px;padding-left:13px;
  border-left:3px solid var(--accent);font-weight:650;letter-spacing:.01em;
}
.doc h3{font-size:17.5px;line-height:1.6;margin:34px 0 12px;color:var(--fg);font-weight:650}
.doc h4{font-size:15.5px;margin:26px 0 10px;color:var(--fg-dim)}
.doc h2:first-of-type,.doc h3:first-of-type{margin-top:34px}
.doc p{margin:0 0 15px;color:var(--fg-dim)}
.doc strong{color:var(--fg);font-weight:650}
.doc em{color:var(--fg-dim);font-style:italic}
.doc a{
  color:var(--accent-2);border-bottom:1px solid color-mix(in srgb,var(--accent-2) 35%,transparent);
  transition:.14s;padding-bottom:1px;
}
.doc a:hover{border-bottom-color:var(--accent-2)}
.doc ul,.doc ol{margin:0 0 16px;padding-left:1.35em;color:var(--fg-dim)}
.doc li{margin:5px 0}
.doc li::marker{color:var(--accent)}
.doc hr{border:0;height:1px;background:var(--line);margin:34px 0}
.doc blockquote{
  margin:0 0 20px;padding:14px 18px;border-left:3px solid var(--accent);
  background:var(--bg-soft);border-radius:0 10px 10px 0;color:var(--fg-dim);
}
.doc blockquote p:last-child{margin-bottom:0}
.doc code{
  font-family:var(--mono);font-size:.88em;background:var(--bg-elev);
  border:1px solid var(--line-soft);border-radius:5px;padding:1px 5px;color:var(--accent);
}
.doc pre{
  margin:0 0 20px;padding:15px 17px;background:var(--bg-elev);
  border:1px solid var(--line);border-radius:var(--radius);overflow-x:auto;
}
.doc pre code{background:none;border:0;padding:0;color:var(--fg-dim);font-size:13px;line-height:1.7}
.doc pre{position:relative}
.copy-btn{
  position:absolute;top:8px;right:8px;padding:4px 10px;font-size:11.5px;font-family:inherit;
  background:var(--bg);border:1px solid var(--line);border-radius:7px;
  color:var(--fg-mute);cursor:pointer;opacity:0;transition:.16s;
}
.doc pre:hover .copy-btn{opacity:1}
.copy-btn:hover{color:var(--accent);border-color:var(--accent)}
.doc table{
  width:100%;border-collapse:collapse;margin:0 0 22px;font-size:14.5px;
  border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
}
.doc th,.doc td{padding:10px 13px;border-bottom:1px solid var(--line-soft);text-align:left;vertical-align:top}
.doc th{background:var(--bg-elev);color:var(--fg);font-weight:650;white-space:nowrap}
.doc tr:last-child td{border-bottom:0}
.doc tbody tr:hover{background:var(--bg-hover)}
.doc td strong{color:var(--accent)}
mark{background:var(--mark);color:inherit;border-radius:3px;padding:0 2px}

/* prevnext */
.prevnext{display:flex;gap:14px;margin:56px 0 0;padding-top:26px;border-top:1px solid var(--line);max-width:820px}
.pn{
  flex:1;min-width:0;padding:13px 16px;border:1px solid var(--line);border-radius:var(--radius);
  background:var(--bg-soft);transition:.16s;display:flex;flex-direction:column;gap:3px;
}
.pn:hover{border-color:var(--accent);background:var(--bg-hover)}
.pn.next{text-align:right}
.pn span{font-size:11.5px;color:var(--fg-mute)}
.pn strong{font-size:14px;color:var(--fg);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.site-foot{margin-top:44px;font-size:12px;color:var(--fg-mute);text-align:center}

/* toc */
.toc{
  width:var(--toc-w);flex:none;position:sticky;top:var(--topbar-h);
  max-height:calc(100vh - var(--topbar-h));overflow-y:auto;
  padding:30px 20px 40px 8px;border-left:1px solid var(--line-soft);
}
.toc-title{
  font-size:11.5px;letter-spacing:.14em;color:var(--fg-mute);font-weight:600;
  margin-bottom:10px;text-transform:uppercase;
}
.toc ul{list-style:none;margin:0;padding:0}
.toc li{margin:1px 0}
.toc a{
  display:block;font-size:12.8px;line-height:1.6;color:var(--fg-mute);padding:4px 8px;
  border-radius:6px;border-left:2px solid transparent;transition:.14s;
}
.toc a:hover{color:var(--fg);background:var(--bg-hover)}
.toc a.active{color:var(--accent);border-left-color:var(--accent);background:var(--accent-soft)}
.toc .lv3 a{padding-left:20px;font-size:12.2px}

/* search */
.search-modal{
  position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.55);
  backdrop-filter:blur(3px);display:flex;justify-content:center;padding:12vh 20px 20px;
}
.search-modal[hidden]{display:none}
.search-box{
  width:min(640px,100%);max-height:70vh;display:flex;flex-direction:column;
  background:var(--bg-elev);border:1px solid var(--line);border-radius:14px;
  box-shadow:0 24px 70px rgba(0,0,0,.45);overflow:hidden;
}
.search-input-row{
  display:flex;align-items:center;gap:10px;padding:13px 15px;
  border-bottom:1px solid var(--line);color:var(--fg-mute);
}
.search-input-row input{
  flex:1;background:none;border:0;outline:0;color:var(--fg);
  font-size:15px;font-family:inherit;
}
.search-input-row input::placeholder{color:var(--fg-mute)}
.search-results{overflow-y:auto;padding:8px}
.sr-item{padding:11px 12px;border-radius:9px;cursor:pointer;border:1px solid transparent}
.sr-item:hover,.sr-item.sel{background:var(--bg-hover);border-color:var(--line)}
.sr-title{font-size:14px;color:var(--fg);font-weight:600;display:flex;gap:8px;align-items:baseline}
.sr-title .badge{
  font-size:10.5px;color:var(--accent);background:var(--accent-soft);
  padding:2px 7px;border-radius:999px;font-weight:500;flex:none;
}
.sr-title .sr-count{font-size:11.5px;color:var(--fg-mute);font-weight:400;margin-left:auto;flex:none}
.sr-snippet{font-size:12.8px;color:var(--fg-mute);margin-top:4px;line-height:1.65;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sr-empty{padding:26px;text-align:center;color:var(--fg-mute);font-size:13.5px}

.totop{
  position:fixed;right:26px;bottom:26px;width:40px;height:40px;border-radius:50%;
  background:var(--bg-elev);border:1px solid var(--line);color:var(--fg-dim);
  font-size:17px;cursor:pointer;opacity:0;pointer-events:none;transition:.2s;z-index:50;
}
.totop.show{opacity:1;pointer-events:auto}
.totop:hover{color:var(--accent);border-color:var(--accent)}

/* responsive */
@media (max-width:1180px){
  .toc{display:none}
}
@media (max-width:900px){
  .menu-btn{display:inline-flex}
  .sidebar{
    position:fixed;left:0;top:var(--topbar-h);z-index:70;width:280px;
    background:var(--bg-soft);transform:translateX(-100%);transition:transform .24s;
  }
  .sidebar.open{transform:none;box-shadow:0 0 40px rgba(0,0,0,.4)}
  .scrim{display:block;position:fixed;inset:var(--topbar-h) 0 0;background:rgba(0,0,0,.5);
    opacity:0;pointer-events:none;transition:.24s;z-index:65}
  .scrim.open{opacity:1;pointer-events:auto}
  .main{padding:26px 20px 60px}
  .hero{padding:22px}
  .hero-title{font-size:33px}
  .doc h1{font-size:26px}
  .doc h2{font-size:19px}
  .btn-label{display:none}
}
@media (max-width:520px){
  body{font-size:15.5px}
  .prevnext{flex-direction:column}
  .pn.next{text-align:left}
  .hero-stats{gap:20px}
}

/* notice */
.notice{
  display:flex;gap:13px;align-items:flex-start;margin:0 0 32px;padding:14px 18px;
  border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;
  background:var(--bg-soft);color:var(--fg-dim);font-size:14.5px;line-height:1.8;
}
.notice-tag{
  flex:none;font-size:11.5px;letter-spacing:.1em;color:var(--accent);
  border:1px solid var(--accent-soft);background:var(--accent-soft);
  padding:3px 9px;border-radius:999px;margin-top:3px;
}

/* progress table */
.doc td.c-no{width:54px;color:var(--fg-mute);font-variant-numeric:tabular-nums}
.doc td.c-title{color:var(--fg);font-weight:600}
.doc td.c-day{color:var(--fg-mute);white-space:nowrap}
.doc td.c-wc{color:var(--fg-mute);white-space:nowrap;text-align:right}
.badge{display:inline-block;font-size:11.5px;padding:2px 9px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}
.badge.done{color:#2f6b4f;border-color:rgba(47,107,79,.3);background:rgba(47,107,79,.1)}
.badge.todo{color:var(--fg-mute)}
html[data-theme="dark"] .badge.done{color:#7fc9a1;border-color:rgba(127,201,161,.32);background:rgba(127,201,161,.12)}
tr.row-done td{background:rgba(47,107,79,.05)}
html[data-theme="dark"] tr.row-done td{background:rgba(127,201,161,.06)}

@media print{
  .topbar,.sidebar,.toc,.prevnext,.totop,.search-modal,.progress{display:none!important}
  body{background:#fff;color:#000}
  .main{padding:0}
}
`;

const APP_JS = String.raw`(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- theme ---------- */
  var THEME_KEY = 'zxtz-theme';
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
  }
  var saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch (e) {}
  if (!saved) saved = 'light';
  applyTheme(saved);
  var themeBtn = $('#themeBtn');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  /* ---------- mobile sidebar ---------- */
  var sidebar = $('#sidebar'), scrim = $('#scrim'), menuBtn = $('#menuBtn');
  function closeNav() { if (sidebar) sidebar.classList.remove('open'); if (scrim) scrim.classList.remove('open'); }
  if (menuBtn) menuBtn.addEventListener('click', function () {
    sidebar.classList.toggle('open'); scrim.classList.toggle('open');
  });
  if (scrim) scrim.addEventListener('click', closeNav);

  /* ---------- reading progress + back to top ---------- */
  var bar = $('#progress'), toTop = $('#toTop');
  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var p = max > 0 ? (h.scrollTop / max) * 100 : 0;
    if (bar) bar.style.width = p + '%';
    if (toTop) toTop.classList.toggle('show', h.scrollTop > 600);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  if (toTop) toTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });

  /* ---------- TOC scrollspy ---------- */
  var tocLinks = $$('.toc a');
  if (tocLinks.length) {
    var targets = tocLinks.map(function (a) {
      var id = decodeURIComponent(a.getAttribute('href').slice(1));
      return { a: a, el: document.getElementById(id) };
    }).filter(function (t) { return t.el; });

    var spy = function () {
      var y = window.scrollY + 120, cur = -1;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i].el.offsetTop <= y) cur = i; else break;
      }
      tocLinks.forEach(function (a) { a.classList.remove('active'); });
      if (cur >= 0) targets[cur].a.classList.add('active');
    };
    window.addEventListener('scroll', spy, { passive: true });
    window.addEventListener('resize', spy);
    spy();
  }

  /* ---------- search ---------- */
  var INDEX = null, INDEX_URL = 'assets/search-index.json';
  var modal = $('#searchModal'), input = $('#searchInput'), results = $('#searchResults');
  var searchBtn = $('#searchBtn'), searchClose = $('#searchClose');
  var sel = 0, hits = [];

  function loadIndex(cb) {
    if (INDEX) return cb();
    fetch(INDEX_URL).then(function (r) { return r.json(); }).then(function (d) {
      INDEX = d; cb();
    }).catch(function () {
      results.innerHTML = '<div class="sr-empty">搜索索引加载失败</div>';
    });
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function snippet(text, q) {
    var i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return esc(text.slice(0, 110));
    var from = Math.max(0, i - 34);
    var raw = text.slice(from, from + 130);
    var pre = from > 0 ? '…' : '';
    var post = from + 130 < text.length ? '…' : '';
    var pos = i - from;
    return pre + esc(raw.slice(0, pos)) + '<mark>' + esc(raw.slice(pos, pos + q.length)) + '</mark>' + esc(raw.slice(pos + q.length)) + post;
  }

  function search(q) {
    if (!INDEX) return [];
    q = q.trim();
    if (!q) return [];
    var ql = q.toLowerCase();
    var out = [];
    INDEX.forEach(function (doc) {
      // 标题命中优先
      var score = 0, titleHit = false;
      if (doc.title.toLowerCase().indexOf(ql) >= 0) { score += 60; titleHit = true; }
      var secHit = null;
      doc.sections.forEach(function (s) {
        if (s.t.toLowerCase().indexOf(ql) >= 0 && !secHit) { secHit = s; score += 30; }
      });
      var bodyIdx = doc.text.toLowerCase().indexOf(ql);
      if (bodyIdx >= 0) score += 10 + Math.min(20, Math.round((doc.text.length - bodyIdx) / 400));
      if (score <= 0) return;
      var count = doc.text.toLowerCase().split(ql).length - 1;
      score += Math.min(15, count);
      out.push({
        score: score, title: titleHit ? doc.title : (secHit ? secHit.t : doc.nav),
        badge: doc.nav, url: secHit ? secHit.u : doc.url,
        text: snippet(doc.text, q), count: count
      });
    });
    out.sort(function (a, b) { return b.score - a.score; });
    return out.slice(0, 24);
  }

  function render(q) {
    hits = search(q);
    if (!q.trim()) {
      results.innerHTML = '<div class="sr-empty">输入关键词检索全站（人名 / 集数 / 世界观 / 审核红线…）</div>';
      return;
    }
    if (!hits.length) { results.innerHTML = '<div class="sr-empty">没有找到「' + esc(q) + '」相关内容</div>'; return; }
    results.innerHTML = hits.map(function (h, i) {
      return '<div class="sr-item' + (i === sel ? ' sel' : '') + '" data-url="' + esc(h.url) + '">' +
        '<div class="sr-title"><span class="badge">' + esc(h.badge) + '</span>' + esc(h.title) +
        (h.count > 1 ? '<span class="sr-count">· ' + h.count + ' 处</span>' : '') + '</div>' +
        '<div class="sr-snippet">' + h.text + '</div></div>';
    }).join('');
  }

  function openSearch() {
    modal.hidden = false;
    loadIndex(function () { render(input.value); });
    input.focus();
    input.select();
  }
  function closeSearch() { modal.hidden = true; }

  if (searchBtn) searchBtn.addEventListener('click', openSearch);
  if (searchClose) searchClose.addEventListener('click', closeSearch);
  if (modal) modal.addEventListener('click', function (e) { if (e.target === modal) closeSearch(); });
  if (input) input.addEventListener('input', function () { sel = 0; render(input.value); });

  if (results) {
    results.addEventListener('click', function (e) {
      var item = e.target.closest('.sr-item');
      if (!item) return;
      window.location.href = item.getAttribute('data-url');
    });
    results.addEventListener('mousemove', function (e) {
      var item = e.target.closest('.sr-item');
      if (!item) return;
      var idx = Array.prototype.indexOf.call(results.children, item);
      if (idx !== sel) { sel = idx; render(input.value); }
    });
  }

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openSearch(); return; }
    if (e.key === '/' && document.activeElement === document.body) { e.preventDefault(); openSearch(); return; }
    if (modal.hidden) return;
    if (e.key === 'Escape') { closeSearch(); return; }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!hits.length) return;
      e.preventDefault();
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + hits.length) % hits.length;
      render(input.value);
      var el = results.children[sel]; if (el) el.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (e.key === 'Enter' && hits[sel]) { window.location.href = hits[sel].url; }
  });

  /* ---------- copy buttons for code blocks ---------- */
  $$('.doc pre').forEach(function (pre) {
    var btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.type = 'button';
    btn.textContent = '复制';
    btn.addEventListener('click', function () {
      navigator.clipboard.writeText(pre.innerText).then(function () {
        btn.textContent = '已复制';
        setTimeout(function () { btn.textContent = '复制'; }, 1400);
      });
    });
    pre.appendChild(btn);
  });
})();
`;

main();
