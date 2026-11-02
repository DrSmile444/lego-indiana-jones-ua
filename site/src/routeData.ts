/**
 * SEO for every page (Starlight route middleware):
 * - home titles built around real search queries (no "X | X" duplication);
 * - og:locale in ll_CC form, og:type website for the home pages, robots directives;
 * - JSON-LD: WebSite + SoftwareApplication (the localization) on the home pages,
 *   FAQPage built from the FAQ headings, BreadcrumbList on every other page.
 */
import { defineRouteMiddleware } from '@astrojs/starlight/route-data';
import release from './generated/release.json';

const SITE = 'https://drsmile444.github.io';
const BASE = '/lego-indiana-jones-ua/';
const ROOT = `${SITE}${BASE}`;
const REPO = 'https://github.com/DrSmile444/lego-indiana-jones-ua';
const SCREENSHOTS = ['main-menu', 'hint-dig', 'shop-valera', 'studs-krugliky', 'editor-forelka'].map(
  // Stable public URLs: the gallery ships hashed WebP files, the sources live in the repository.
  (name) => `https://raw.githubusercontent.com/DrSmile444/lego-indiana-jones-ua/master/docs/screenshots/${name}.jpg`,
);

const TEXT = {
  uk: {
    homeTitle: 'Українізатор LEGO Indiana Jones: The Original Adventures — завантажити українську локалізацію',
    siteName: 'Українізатор LEGO Indiana Jones',
    appName: 'Українізатор LEGO Indiana Jones: The Original Adventures',
    alternateNames: [
      'LEGO Індіана Джонс українською',
      'Лего Індіана Джонс українізатор',
      'LEGO Indiana Jones українська локалізація',
      'LEGO Indiana Jones Ukrainian',
    ],
    description:
      'Безкоштовний український переклад LEGO Indiana Jones: The Original Adventures (ПК, Steam, Steam Deck): увесь текст, шрифти з ІіЇїЄєҐґ, логотип і текстури.',
    locale: 'uk_UA',
    alternate: 'en_US',
    home: 'Головна',
  },
  en: {
    homeTitle: 'LEGO Indiana Jones: The Original Adventures Ukrainian translation — download',
    siteName: 'LEGO Indiana Jones Ukrainian localization',
    appName: 'LEGO Indiana Jones: The Original Adventures — Ukrainian localization',
    alternateNames: ['LEGO Indiana Jones Ukrainian translation', 'LEGO Indiana Jones Ukrainian mod'],
    description:
      'Free Ukrainian fan translation of LEGO Indiana Jones: The Original Adventures (PC, Steam, Steam Deck): all game text, fonts with ІіЇїЄєҐґ, the logo and textures.',
    locale: 'en_US',
    alternate: 'uk_UA',
    home: 'Home',
  },
} as const;

type HeadEntry = { tag: string; attrs?: Record<string, string | boolean | undefined>; content?: string };

function setMeta(head: HeadEntry[], key: 'name' | 'property', value: string, content: string) {
  const entry = head.find((e) => e.tag === 'meta' && e.attrs?.[key] === value);
  if (entry) entry.attrs = { ...entry.attrs, content };
  else head.push({ tag: 'meta', attrs: { [key]: value, content } });
}

function jsonLd(head: HeadEntry[], data: object) {
  head.push({ tag: 'script', attrs: { type: 'application/ld+json' }, content: JSON.stringify(data) });
}

/** Plain text of a markdown fragment: drops code ticks, links and emphasis. */
function plain(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[*_>#|]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function faqItems(body: string) {
  const sections = body.split(/^## /m).slice(1);
  return sections
    .map((section) => {
      const [question, ...rest] = section.split('\n');
      return { question: plain(question), answer: plain(rest.join('\n')) };
    })
    .filter((item) => item.question.endsWith('?') && item.answer);
}

export const onRequest = defineRouteMiddleware((context) => {
  const route = context.locals.starlightRoute;
  const lang = route.lang === 'en' ? 'en' : 'uk';
  const t = TEXT[lang];
  const head = route.head as HeadEntry[];
  const slug = route.id.replace(/^en\/?/, '').replace(/\/$/, '');
  const isHome = slug === '' || slug === 'index';
  const isNotFound = slug === '404';
  const homeUrl = lang === 'en' ? `${ROOT}en/` : ROOT;
  const pageUrl = new URL(context.url.pathname, SITE).href;

  setMeta(head, 'property', 'og:locale', t.locale);
  setMeta(head, 'property', 'og:locale:alternate', t.alternate);
  setMeta(head, 'property', 'og:site_name', t.siteName);
  setMeta(head, 'name', 'robots', isNotFound ? 'noindex, follow' : 'index, follow, max-image-preview:large, max-snippet:-1');
  setMeta(head, 'name', 'author', 'Dmytro Vakulenko (DrSmile444)');

  const title = head.find((e) => e.tag === 'title');
  if (isHome) {
    if (title) title.content = t.homeTitle;
    setMeta(head, 'property', 'og:title', t.homeTitle);
    setMeta(head, 'property', 'og:type', 'website');
    setMeta(head, 'name', 'twitter:title', t.homeTitle);
    setMeta(head, 'name', 'twitter:description', t.description);

    jsonLd(head, {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: t.siteName,
      alternateName: t.alternateNames,
      url: homeUrl,
      inLanguage: lang === 'en' ? 'en' : 'uk',
    });
    jsonLd(head, {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: t.appName,
      alternateName: t.alternateNames,
      description: t.description,
      url: homeUrl,
      applicationCategory: 'GameApplication',
      applicationSubCategory: 'Game localization / mod',
      operatingSystem: 'Windows, SteamOS (Steam Deck, Proton)',
      softwareVersion: release.version,
      downloadUrl: release.downloadUrl,
      installUrl: `${homeUrl}install/`,
      fileSize: '3 MB',
      inLanguage: 'uk',
      isAccessibleForFree: true,
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'UAH' },
      license: `${REPO}/blob/master/LICENSE`,
      screenshot: SCREENSHOTS,
      image: `${ROOT}og-image.jpg`,
      author: { '@type': 'Person', name: 'Dmytro Vakulenko', url: 'https://github.com/DrSmile444' },
      codeRepository: REPO,
      about: {
        '@type': 'VideoGame',
        name: 'LEGO Indiana Jones: The Original Adventures',
        alternateName: 'LEGO Індіана Джонс: Оригінальні пригоди',
        gamePlatform: ['PC', 'Steam', 'Steam Deck'],
        author: { '@type': 'Organization', name: "Traveller's Tales" },
        datePublished: '2008',
      },
    });
    return;
  }

  if (isNotFound) return;

  if (slug === 'faq' && route.entry?.body) {
    const items = faqItems(route.entry.body);
    if (items.length) {
      jsonLd(head, {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        inLanguage: lang,
        mainEntity: items.map((item) => ({
          '@type': 'Question',
          name: item.question,
          acceptedAnswer: { '@type': 'Answer', text: item.answer },
        })),
      });
    }
  }

  jsonLd(head, {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: t.siteName, item: homeUrl },
      { '@type': 'ListItem', position: 2, name: route.entry.data.title, item: pageUrl },
    ],
  });
});
