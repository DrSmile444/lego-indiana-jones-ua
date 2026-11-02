#!/usr/bin/env node
/**
 * sync-docs — переносить тексти з репозиторію в сайт перед збіркою.
 *
 * Джерела (єдине джерело правди):
 *   docs/**\/*.md               -> src/content/docs/... (сторінки Starlight, українська — корінь сайту)
 *   docs/en/**\/*.md            -> src/content/docs/en/... (англійське дзеркало з тими самими відносними шляхами)
 *   docs/**\/*.{jpg,png,...}    -> public/docs-media/... (якщо на них посилаються)
 *   docs/screenshots/*.jpg      -> src/generated/screenshots/ (галерея, hero) + public/og-image.jpg
 *   translations/glossary.json  -> src/generated/glossary.json
 *   manifests/releases/*.json   -> src/generated/release.json (версія за замовчуванням для кнопки)
 *
 * Відносні посилання переписуються: .md -> маршрут сайту, інші файли репозиторію -> GitHub,
 * зображення -> public/docs-media. Бите посилання — помилка.
 *
 * Англійські документи проходять ті самі правила: посилання на інший документ docs/en/ веде на /en/…,
 * медіа (зокрема спільні docs/screenshots/) — у той самий public/docs-media. Якщо англійський документ
 * посилається відносним шляхом на медіа, якого немає в docs/en/, але є дзеркальний файл у docs/, —
 * використовується він.
 *
 * Режими:
 *   (за замовчуванням)  відсутні документи (зокрема англійські відповідники) замінюються заглушками з попередженням;
 *   --strict або SYNC_STRICT=1  будь-який відсутній документ (українською чи англійською), скриншот чи бите
 *                       посилання зупиняє збірку (CI).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPO_DIR = path.resolve(SITE_DIR, '..');
const DOCS_DIR = path.join(REPO_DIR, 'docs');
const CONTENT_DIR = path.join(SITE_DIR, 'src', 'content', 'docs');
const GENERATED_DIR = path.join(SITE_DIR, 'src', 'generated');
const PUBLIC_DIR = path.join(SITE_DIR, 'public');
const MEDIA_PUBLIC = 'docs-media';

const BASE = '/lego-indiana-jones-ua';
const REPO_URL = 'https://github.com/DrSmile444/lego-indiana-jones-ua';
const BRANCH = 'master';

const STRICT = process.argv.includes('--strict') || process.env.SYNC_STRICT === '1';

/** Документи, які сайт обов'язково показує (назва для заглушки українською й англійською). */
const EXPECTED_DOCS = {
  'approach.md': { uk: 'Як ми це робили', en: 'How we built it' },
  'tooling.md': { uk: 'Інструменти', en: 'Tooling' },
  'setup.md': { uk: 'Налаштування середовища', en: 'Development setup' },
  'architecture.md': { uk: 'Архітектура', en: 'Architecture' },
  'research/fonts.md': { uk: 'Шрифти', en: 'Fonts' },
  'research/textures.md': { uk: 'Текстури', en: 'Textures' },
  'research/pc-menu.md': { uk: 'Меню ПК', en: 'PC menu' },
  'research/runtime-loading.md': { uk: 'Завантаження під час гри', en: 'Runtime loading' },
  'research/character-editor.md': { uk: 'Редактор персонажів', en: 'Character editor' },
  'research/cultural-adaptations.md': { uk: 'Культурні адаптації', en: 'Cultural adaptations' },
};

/** Префікс англійського дзеркала: docs/en/ -> /en/. */
const EN = 'en/';

/** Тексти, які скрипт пише сам (огляд досліджень, заглушки). */
const L10N = {
  uk: {
    fallbackDescription: (title) => `${title} — українізатор LEGO Індіана Джонс.`,
    researchTitle: 'Дослідження',
    researchDescription:
      'Технічні дослідження українізатора LEGO Індіана Джонс: шрифти, завантаження ресурсів під час гри, текстури, меню ПК і редактор персонажів.',
    researchLabel: 'Огляд',
    researchIntro:
      'Як влаштована гра всередині й що довелося змінити, щоб вона заговорила українською. Кожна сторінка — окрема історія з доказами й висновками.',
    researchAdaptations: (href) => `- **[Культурні адаптації](${href})** — чому «Валєра», «Пластун» і «круглики».`,
  },
  en: {
    fallbackDescription: (title) => `${title} — LEGO Indiana Jones Ukrainian localization.`,
    researchTitle: 'Research',
    researchDescription:
      'Technical research behind the LEGO Indiana Jones Ukrainian localization: fonts, runtime resource loading, textures, the PC menu and the character editor.',
    researchLabel: 'Overview',
    researchIntro:
      'How the game works inside and what had to change to make it speak Ukrainian. Each page is a separate story with evidence and conclusions.',
    researchAdaptations: (href) =>
      `- **[Cultural adaptations](${href})** — why «Валєра» (Valera), «Пластун» (Plastun) and «круглики» (kruhlyky).`,
  },
};

const EXPECTED_SCREENSHOTS = [
  'main-menu.jpg',
  'hint-dig.jpg',
  'pause-barnett.jpg',
  'exit-dialog.jpg',
  'hint-switch.jpg',
  'studs-krugliky.jpg',
  'shop-valera.jpg',
  'editor-forelka.jpg',
  'pause-post-room.jpg',
];

/** Порядок у бічній панелі. */
const SIDEBAR_ORDER = {
  'research/fonts.md': 1,
  'research/runtime-loading.md': 2,
  'research/textures.md': 3,
  'research/pc-menu.md': 4,
  'research/character-editor.md': 5,
  'setup.md': 1,
  'architecture.md': 2,
};

/** Сторінки, що мають власні позиції в sidebar (не потрапляють в autogenerate). */
const FIXED_SLUGS = {
  'approach.md': 'approach',
  'tooling.md': 'tooling',
  'research/cultural-adaptations.md': 'adaptations',
};

const FALLBACK_RELEASE = {
  version: '1.1.10',
  asset: 'lego-indiana-jones-ua-1.1.10.zip',
};

/** Службові документи docs/, що лишаються лише в репозиторії (посилання на них ведуть на GitHub). */
const REPO_ONLY_DOCS = new Set(['README.md', 'migration.md']);

const IGNORED_REPO_PREFIXES = ['local/', 'game/', 'build/', 'dist/'];

// ---------------------------------------------------------------------------

const warnings = [];
const errors = [];
const warn = (msg) => warnings.push(msg);
/** У суворому режимі — помилка, інакше — попередження. */
const problem = (msg) => (STRICT ? errors.push(msg) : warnings.push(msg));
const fail = (msg) => errors.push(msg);

const toPosix = (p) => p.split(path.sep).join('/');

/** docs-відносний шлях -> мова й шлях усередині мови ('en/setup.md' -> { lang: 'en', local: 'setup.md' }). */
function splitLocale(rel) {
  return rel.startsWith(EN) ? { lang: 'en', local: rel.slice(EN.length) } : { lang: 'uk', local: rel };
}

/** Корінь маршрутів мови: /lego-indiana-jones-ua або /lego-indiana-jones-ua/en. */
const routeRoot = (lang) => (lang === 'en' ? `${BASE}/en` : BASE);

function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || entry.name.startsWith('_')) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

function rmrf(p) {
  fs.rmSync(p, { recursive: true, force: true });
}

function writeFile(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

function copyFile(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
}

/** docs-відносний шлях .md (зокрема en/...) -> slug сторінки сайту (en/... для англійської). */
function slugForDoc(rel) {
  const { lang, local } = splitLocale(rel);
  const slug = localSlug(local);
  return lang === 'en' ? `en/${slug}` : slug;
}

/** Шлях .md усередині мови -> slug без мовного префікса. */
function localSlug(rel) {
  if (FIXED_SLUGS[rel]) return FIXED_SLUGS[rel];
  const noExt = rel.replace(/\.mdx?$/i, '');
  const parts = noExt.split('/');
  const last = parts[parts.length - 1].toLowerCase();
  const isIndex = last === 'readme' || last === 'index';
  if (parts[0] === 'research') {
    if (isIndex) parts.pop();
    return parts.join('/') || 'research';
  }
  if (isIndex) parts.pop();
  return ['dev', ...parts].join('/');
}

function outputFileForSlug(slug, isIndex) {
  return path.join(CONTENT_DIR, ...(isIndex ? [...slug.split('/'), 'index.md'] : [`${slug}.md`]));
}

const isIndexDoc = (rel) => /(^|\/)(readme|index)\.mdx?$/i.test(rel);

/** Прибирає Markdown-розмітку для опису. */
function plainText(md) {
  return md
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/[*_~]{1,3}([^*_~]+)[*_~]{1,3}/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncate(text, max = 180) {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  return `${cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;:—–-]$/, '')}…`;
}

/** Розбирає простий YAML frontmatter (ключ: значення) без залежностей. */
function splitFrontmatter(src) {
  const m = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!m) return { fm: {}, rawFm: '', body: src };
  const fm = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) fm[kv[1]] = kv[2].replace(/^["']|["']$/g, '');
  }
  return { fm, rawFm: m[1], body: src.slice(m[0].length) };
}

/** Повертає масив рядків із позначкою, чи вони всередині блоку коду. */
function markCode(lines) {
  let fence = null;
  return lines.map((line) => {
    const f = line.match(/^\s*(```+|~~~+)/);
    if (fence) {
      if (f && f[1][0] === fence[0] && f[1].length >= fence.length) fence = null;
      return { line, code: true };
    }
    if (f) {
      fence = f[1];
      return { line, code: true };
    }
    return { line, code: false };
  });
}

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|svg|avif)$/i;

/**
 * Переписує одне посилання з документа `fromRel` (шлях відносно docs/).
 * Повертає новий URL або null, якщо посилання биле.
 */
function rewriteUrl(url, fromRel, mediaUsed) {
  if (!url || /^(?:[a-z][a-z0-9+.-]*:|\/\/|#)/i.test(url)) return url; // http:, mailto:, якорі
  if (url.startsWith('/')) {
    problem(`docs/${fromRel}: абсолютний шлях «${url}» — використовуйте відносне посилання`);
    return url;
  }
  const [pathPartRaw, ...hashParts] = url.split('#');
  const hash = hashParts.length ? `#${hashParts.join('#')}` : '';
  const [pathPart] = pathPartRaw.split('?');
  let decoded;
  try {
    decoded = decodeURIComponent(pathPart);
  } catch {
    decoded = pathPart;
  }
  if (!decoded) return url;

  const fromLang = splitLocale(fromRel).lang;
  let repoRel = path.posix.normalize(path.posix.join('docs', path.posix.dirname(fromRel), decoded));
  if (repoRel.startsWith('..')) {
    problem(`docs/${fromRel}: посилання «${url}» веде за межі репозиторію`);
    return null;
  }
  if (IGNORED_REPO_PREFIXES.some((p) => repoRel === p.slice(0, -1) || repoRel.startsWith(p))) {
    problem(`docs/${fromRel}: посилання «${url}» веде в неопубліковану теку (${repoRel})`);
    return null;
  }
  let abs = path.join(REPO_DIR, repoRel);
  // Англійський документ посилається на файл docs/en/…, якого немає, але є дзеркальний у docs/:
  // медіа беремо спільне, а на відсутній англійський документ ведемо за англійським маршрутом
  // (там заглушка; сама відсутність документа вже повідомлена окремо).
  if (!fs.existsSync(abs) && repoRel.startsWith(`docs/${EN}`)) {
    const mirror = `docs/${repoRel.slice(`docs/${EN}`.length)}`;
    const mirrorAbs = path.join(REPO_DIR, mirror);
    if (fs.existsSync(mirrorAbs)) {
      const local = mirror.slice('docs/'.length);
      if (fs.statSync(mirrorAbs).isFile() && /\.mdx?$/i.test(local) && !REPO_ONLY_DOCS.has(local)) {
        return `${BASE}/${slugForDoc(EN + local)}/${hash}`;
      }
      repoRel = mirror;
      abs = mirrorAbs;
    }
  }
  if (!fs.existsSync(abs)) {
    problem(`docs/${fromRel}: бите посилання «${url}» (немає ${repoRel})`);
    return null;
  }
  const stat = fs.statSync(abs);

  if (repoRel.startsWith('docs/') && stat.isFile()) {
    const docRel = repoRel.slice('docs/'.length);
    if (/\.mdx?$/i.test(docRel) && !REPO_ONLY_DOCS.has(splitLocale(docRel).local)) {
      const slug = slugForDoc(docRel);
      return `${BASE}/${slug}/${hash}`;
    }
    if (/\.mdx?$/i.test(docRel)) {
      return `${REPO_URL}/blob/${BRANCH}/${repoRel.split('/').map(encodeURIComponent).join('/')}${hash}`;
    }
    // Медіа з docs/ публікуються поруч зі сторінками.
    mediaUsed.add(docRel);
    return `${BASE}/${MEDIA_PUBLIC}/${docRel.split('/').map(encodeURIComponent).join('/')}${hash}`;
  }

  // Тека docs/research/ (чи docs/en/research/) — оглядова сторінка досліджень мови документа.
  if (stat.isDirectory() && /^docs\/(en\/)?research$/.test(repoRel.replace(/\/$/, ''))) {
    return `${routeRoot(fromLang)}/research/${hash}`;
  }

  // Інші файли репозиторію — на GitHub.
  const kind = stat.isDirectory() ? 'tree' : 'blob';
  const encoded = repoRel.split('/').map(encodeURIComponent).join('/');
  return `${REPO_URL}/${kind}/${BRANCH}/${encoded}${hash}`;
}

function rewriteLinks(body, fromRel, mediaUsed) {
  const marked = markCode(body.split(/\r?\n/));
  return marked
    .map(({ line, code }) => {
      if (code) return line;
      // Ховаємо інлайн-код, щоб не чіпати приклади.
      const spans = [];
      let l = line.replace(/(`+)([\s\S]*?)\1/g, (m) => {
        spans.push(m);
        return `\u0000${spans.length - 1}\u0000`;
      });
      const fix = (url) => rewriteUrl(url, fromRel, mediaUsed) ?? url;
      // [text](url "title") та ![alt](url)
      l = l.replace(/\]\(\s*(<[^>]*>|[^)\s]+)((?:\s+(?:"[^"]*"|'[^']*'))?)\s*\)/g, (m, rawUrl, title) => {
        const url = rawUrl.startsWith('<') ? rawUrl.slice(1, -1) : rawUrl;
        return `](${fix(url)}${title})`;
      });
      // [ref]: url
      l = l.replace(/^(\s{0,3}\[[^\]]+\]:\s*)(<[^>]*>|\S+)/, (m, pre, rawUrl) => {
        const url = rawUrl.startsWith('<') ? rawUrl.slice(1, -1) : rawUrl;
        return `${pre}${fix(url)}`;
      });
      // HTML src="" / href=""
      l = l.replace(/\b(src|href)=("([^"]*)"|'([^']*)')/g, (m, attr, _q, dq, sq) => {
        const url = dq ?? sq;
        return `${attr}="${fix(url)}"`;
      });
      return l.replace(/\u0000(\d+)\u0000/g, (m, i) => spans[Number(i)]);
    })
    .join('\n');
}

/** Витягує H1 як title і перший абзац як description. */
function extractTitleAndDescription(body) {
  const lines = body.split(/\r?\n/);
  const marked = markCode(lines);
  let title = null;
  let titleIdx = -1;
  for (let i = 0; i < marked.length; i++) {
    if (marked[i].code) continue;
    const h = marked[i].line.match(/^#\s+(.+?)\s*#*\s*$/);
    if (h) {
      title = plainText(h[1]);
      titleIdx = i;
      break;
    }
    if (marked[i].line.trim() && !/^<!--/.test(marked[i].line.trim())) break; // H1 має бути першим
  }
  const rest = titleIdx >= 0 ? [...lines.slice(0, titleIdx), ...lines.slice(titleIdx + 1)] : lines;

  let description = '';
  const restMarked = markCode(rest);
  let para = [];
  for (const { line, code } of restMarked) {
    const t = line.trim();
    if (code) {
      if (para.length) break;
      continue;
    }
    if (!t) {
      if (para.length) break;
      continue;
    }
    if (/^(#|!\[|\||>|<|[-*+]\s|\d+\.\s|---|\[!)/.test(t)) {
      if (para.length) break;
      continue;
    }
    para.push(t);
  }
  description = truncate(plainText(para.join(' ')));
  return { title, description, body: rest.join('\n').replace(/^\s*\n/, '') };
}

const yamlString = (s) => JSON.stringify(String(s));

// ---------------------------------------------------------------------------
// 1. Документи

/** Згенеровані сторінки (обох мов), які скрипт перезаписує щоразу. */
const GENERATED_CONTENT = ['research', 'dev', 'tooling.md', 'approach.md', 'adaptations.md'];

function syncDocs() {
  // Очищаємо попередні згенеровані сторінки.
  for (const p of GENERATED_CONTENT) {
    rmrf(path.join(CONTENT_DIR, p));
    rmrf(path.join(CONTENT_DIR, EN, p));
  }
  rmrf(path.join(PUBLIC_DIR, MEDIA_PUBLIC));

  const docFiles = walk(DOCS_DIR)
    .map((f) => toPosix(path.relative(DOCS_DIR, f)))
    .filter((rel) => /\.mdx?$/i.test(rel) && !REPO_ONLY_DOCS.has(splitLocale(rel).local));

  const ukPresent = new Set(docFiles.filter((r) => splitLocale(r).lang === 'uk'));
  const enPresent = new Set(docFiles.filter((r) => splitLocale(r).lang === 'en').map((r) => splitLocale(r).local));

  for (const [rel, titles] of Object.entries(EXPECTED_DOCS)) {
    if (!ukPresent.has(rel)) {
      problem(`немає docs/${rel} — ${STRICT ? 'сторінку не можна зібрати' : 'створено заглушку'}`);
      if (!STRICT) writePlaceholder('uk', rel, titles.uk);
    }
  }
  // Кожна сторінка має англійський відповідник з тим самим шляхом у docs/en/.
  for (const rel of new Set([...Object.keys(EXPECTED_DOCS), ...ukPresent])) {
    if (enPresent.has(rel)) continue;
    problem(`немає англійського відповідника docs/${EN}${rel} — ${STRICT ? 'сторінку не можна зібрати' : 'створено заглушку'}`);
    if (!STRICT) writePlaceholder('en', rel, EXPECTED_DOCS[rel]?.en ?? prettyName(rel));
  }
  for (const rel of enPresent) {
    if (!ukPresent.has(rel)) problem(`docs/${EN}${rel} не має українського оригіналу docs/${rel}`);
  }

  const mediaUsed = new Set();
  const slugs = new Map();
  const pages = [];
  let count = 0;

  for (const rel of docFiles) {
    const { lang, local } = splitLocale(rel);
    const src = fs.readFileSync(path.join(DOCS_DIR, rel), 'utf8').replace(/^﻿/, '');
    const { fm, rawFm, body: rawBody } = splitFrontmatter(src);
    const { title: h1, description: firstPara, body } = extractTitleAndDescription(rawBody);
    const title = fm.title || h1 || EXPECTED_DOCS[local]?.[lang] || path.posix.basename(rel, '.md');
    if (!fm.title && !h1) warn(`docs/${rel}: немає заголовка H1, використано «${title}»`);
    const description = fm.description || firstPara || L10N[lang].fallbackDescription(title);

    const slug = slugForDoc(rel);
    if (slugs.has(slug)) fail(`docs/${rel} і docs/${slugs.get(slug)} дають однаковий маршрут /${slug}/`);
    slugs.set(slug, rel);

    const rewritten = rewriteLinks(body, rel, mediaUsed);

    const extraFm = rawFm
      .split(/\r?\n/)
      .filter((l) => l.trim() && !/^(title|description):/.test(l))
      .join('\n');
    const fmLines = [
      '---',
      '# ЗГЕНЕРОВАНО scripts/sync-docs.mjs — редагуйте ' + `docs/${rel}`,
      `title: ${yamlString(title)}`,
      `description: ${yamlString(description)}`,
      `editUrl: ${yamlString(`${REPO_URL}/edit/${BRANCH}/docs/${rel}`)}`,
      `syncedFrom: ${yamlString(`docs/${rel}`)}`,
    ];
    if (local === 'approach.md') fmLines.push('routeTimeline: true');
    if (SIDEBAR_ORDER[local] && !/^sidebar:/m.test(extraFm)) {
      fmLines.push('sidebar:', `  order: ${SIDEBAR_ORDER[local]}`);
    }
    if (isIndexDoc(local) && !/^sidebar:/m.test(extraFm)) fmLines.push('sidebar:', '  order: 0');
    if (extraFm) fmLines.push(extraFm);
    fmLines.push('---', '');

    writeFile(outputFileForSlug(slug, isIndexDoc(local)), `${fmLines.join('\n')}\n${rewritten.trim()}\n`);
    pages.push({ rel, lang, local, slug, title, description });
    count++;
  }

  // Оглядова сторінка досліджень кожної мови, якщо в docs/(en/)research/ немає власного README/index.
  for (const lang of ['uk', 'en']) {
    const t = L10N[lang];
    const researchPages = pages.filter(
      (p) =>
        p.lang === lang && p.local.startsWith('research/') && !isIndexDoc(p.local) && localSlug(p.local).startsWith('research/'),
    );
    const hasOwnIndex = pages.some((p) => p.lang === lang && /^research\/(readme|index)\.mdx?$/i.test(p.local));
    if (hasOwnIndex || !researchPages.length) continue;
    researchPages.sort((a, b) => (SIDEBAR_ORDER[a.local] ?? 50) - (SIDEBAR_ORDER[b.local] ?? 50));
    const list = researchPages.map((p) => `- **[${p.title}](${BASE}/${p.slug}/)** — ${p.description}`).join('\n');
    writeFile(
      path.join(CONTENT_DIR, ...(lang === 'en' ? ['en'] : []), 'research', 'index.md'),
      [
        '---',
        `# ЗГЕНЕРОВАНО scripts/sync-docs.mjs зі списку docs/${lang === 'en' ? EN : ''}research/`,
        `title: ${yamlString(t.researchTitle)}`,
        `description: ${yamlString(t.researchDescription)}`,
        'editUrl: false',
        'sidebar:',
        `  label: ${yamlString(t.researchLabel)}`,
        '  order: 0',
        '---',
        '',
        t.researchIntro,
        '',
        list,
        t.researchAdaptations(`${routeRoot(lang)}/adaptations/`),
        '',
      ].join('\n'),
    );
  }

  for (const rel of mediaUsed) {
    copyFile(path.join(DOCS_DIR, rel), path.join(PUBLIC_DIR, MEDIA_PUBLIC, rel));
  }

  return {
    count,
    uk: pages.filter((p) => p.lang === 'uk').length,
    en: pages.filter((p) => p.lang === 'en').length,
    media: mediaUsed.size,
  };
}

/** 'research/pc-menu.md' -> 'Pc menu' (назва заглушки, якщо документа немає в EXPECTED_DOCS). */
function prettyName(rel) {
  const base = path.posix.basename(rel).replace(/\.mdx?$/i, '').replace(/[-_]+/g, ' ');
  return base.charAt(0).toUpperCase() + base.slice(1);
}

function writePlaceholder(lang, rel, title) {
  const slug = slugForDoc(lang === 'en' ? EN + rel : rel);
  const docPath = `docs/${lang === 'en' ? EN : ''}${rel}`;
  const fm = [
    '---',
    `# ЗАГЛУШКА scripts/sync-docs.mjs — документа ще немає: ${docPath}`,
    `title: ${yamlString(title)}`,
    `description: ${yamlString(lang === 'en' ? `${title} — this page is being written.` : `${title} — сторінка готується.`)}`,
    lang === 'en' ? 'editUrl: false' : null,
    `syncedFrom: ${yamlString(docPath)}`,
    rel === 'approach.md' ? 'routeTimeline: true' : null,
    SIDEBAR_ORDER[rel] ? `sidebar:\n  order: ${SIDEBAR_ORDER[rel]}` : null,
    '---',
  ]
    .filter(Boolean)
    .join('\n');
  const body =
    lang === 'en'
      ? `:::caution[Translation in progress]\nThe English version of this page is not ready yet. Meanwhile, read the [Ukrainian original](${BASE}/${localSlug(rel)}/).\n:::\n`
      : `:::caution[Сторінка готується]\nТекст з’явиться тут, щойно в репозиторії буде файл \`${docPath}\`.\n:::\n`;
  writeFile(outputFileForSlug(slug, isIndexDoc(rel)), `${fm}\n\n${body}`);
}

// ---------------------------------------------------------------------------
// 2. Скриншоти

function syncScreenshots() {
  const srcDir = path.join(DOCS_DIR, 'screenshots');
  const outDir = path.join(GENERATED_DIR, 'screenshots');
  rmrf(outDir);
  fs.mkdirSync(outDir, { recursive: true });
  let copied = 0;
  for (const name of EXPECTED_SCREENSHOTS) {
    const from = path.join(srcDir, name);
    if (!fs.existsSync(from)) {
      problem(`немає docs/screenshots/${name}`);
      continue;
    }
    copyFile(from, path.join(outDir, name));
    copied++;
  }
  // Необов'язкові англійські знімки для слайдера «до/після» (наприклад, main-menu-en.jpg).
  if (fs.existsSync(srcDir)) {
    for (const name of fs.readdirSync(srcDir)) {
      if (/-en\.(jpe?g|png|webp)$/i.test(name)) copyFile(path.join(srcDir, name), path.join(outDir, name));
    }
  }
  const og = path.join(srcDir, 'main-menu.jpg');
  if (fs.existsSync(og)) copyFile(og, path.join(PUBLIC_DIR, 'og-image.jpg'));
  return copied;
}

// ---------------------------------------------------------------------------
// 3. Глосарій

const GLOSSARY_CATEGORIES = {
  characters: 'Персонажі',
  artifacts: 'Артефакти',
  items: 'Предмети',
  game_mechanics: 'Ігрові механіки',
  places: 'Місця',
  chapter_titles: 'Назви розділів',
};

function syncGlossary() {
  const file = path.join(REPO_DIR, 'translations', 'glossary.json');
  const out = path.join(GENERATED_DIR, 'glossary.json');
  if (!fs.existsSync(file)) {
    problem('немає translations/glossary.json — глосарій буде порожнім');
    writeFile(out, JSON.stringify({ categories: [], terms: [] }, null, 2));
    return 0;
  }
  let data;
  try {
    data = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    fail(`translations/glossary.json не розбирається: ${e.message}`);
    return 0;
  }
  const terms = [];
  const categories = [];
  for (const [key, entries] of Object.entries(data)) {
    if (key.startsWith('_') || typeof entries !== 'object' || entries === null) continue;
    const label = GLOSSARY_CATEGORIES[key] ?? key.replace(/_/g, ' ');
    if (!GLOSSARY_CATEGORIES[key]) warn(`glossary.json: невідома категорія «${key}», показано як «${label}»`);
    categories.push({ key, label });
    for (const [en, entry] of Object.entries(entries)) {
      if (!entry || typeof entry.uk !== 'string') {
        fail(`glossary.json: термін «${en}» (${key}) не має поля uk`);
        continue;
      }
      terms.push({
        category: key,
        en,
        uk: entry.uk,
        confidence: entry.confidence ?? 'unknown',
        note: entry.note ?? '',
      });
    }
  }
  writeFile(out, JSON.stringify({ categories, terms }, null, 2));
  return terms.length;
}

// ---------------------------------------------------------------------------
// 4. Реліз за замовчуванням

function compareVersions(a, b) {
  const pa = a.split(/[.-]/).map((x) => (/^\d+$/.test(x) ? Number(x) : x));
  const pb = b.split(/[.-]/).map((x) => (/^\d+$/.test(x) ? Number(x) : x));
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const x = pa[i] ?? 0;
    const y = pb[i] ?? 0;
    if (x === y) continue;
    if (typeof x === 'number' && typeof y === 'number') return x - y;
    return String(x).localeCompare(String(y));
  }
  return 0;
}

function findZipName(obj) {
  let found = null;
  const visit = (v) => {
    if (found) return;
    if (typeof v === 'string' && /\.zip$/i.test(v)) found = v.split(/[\\/]/).pop();
    else if (v && typeof v === 'object') Object.values(v).forEach(visit);
  };
  visit(obj);
  return found;
}

function syncRelease() {
  const dir = path.join(REPO_DIR, 'manifests', 'releases');
  const candidates = [];
  if (fs.existsSync(dir)) {
    for (const name of fs.readdirSync(dir)) {
      if (!name.endsWith('.json')) continue;
      try {
        const json = JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
        const version = String(json.version ?? name.replace(/\.json$/, '')).replace(/^v/, '');
        if (!/^\d+\.\d+\.\d+/.test(version)) {
          warn(`manifests/releases/${name}: не вдалося визначити версію`);
          continue;
        }
        candidates.push({ version, asset: (typeof json.archive === 'string' ? json.archive : findZipName(json)) ?? `lego-indiana-jones-ua-${version}.zip` });
      } catch (e) {
        fail(`manifests/releases/${name} не розбирається: ${e.message}`);
      }
    }
  }
  candidates.sort((a, b) => compareVersions(b.version, a.version));
  const chosen = candidates[0] ?? FALLBACK_RELEASE;
  if (!candidates.length) warn(`у manifests/releases/ немає маніфестів — версія за замовчуванням ${FALLBACK_RELEASE.version}`);
  const release = {
    version: chosen.version,
    asset: chosen.asset,
    tag: `v${chosen.version}`,
    downloadUrl: `${REPO_URL}/releases/download/v${chosen.version}/${chosen.asset}`,
    releasesUrl: `${REPO_URL}/releases`,
    latestApi: 'https://api.github.com/repos/DrSmile444/lego-indiana-jones-ua/releases/latest',
    fromManifest: candidates.length > 0,
  };
  writeFile(path.join(GENERATED_DIR, 'release.json'), JSON.stringify(release, null, 2));
  return release;
}

// ---------------------------------------------------------------------------

const docs = syncDocs();
const shots = syncScreenshots();
const terms = syncGlossary();
const release = syncRelease();

for (const w of warnings) console.warn(`sync-docs: попередження: ${w}`);
for (const e of errors) console.error(`sync-docs: ПОМИЛКА: ${e}`);
console.log(
  `sync-docs${STRICT ? ' (strict)' : ''}: сторінок ${docs.count} (uk ${docs.uk}, en ${docs.en}), медіа ${docs.media}, скриншотів ${shots}, ` +
    `термінів ${terms}, версія ${release.version}${release.fromManifest ? '' : ' (за замовчуванням)'}`,
);
if (errors.length) {
  console.error(`sync-docs: збірку зупинено — ${errors.length} помилок.`);
  process.exit(1);
}
