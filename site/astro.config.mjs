// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const SITE = 'https://drsmile444.github.io';
const BASE = '/lego-indiana-jones-ua';
const REPO = 'https://github.com/DrSmile444/lego-indiana-jones-ua';
const OG_IMAGE = `${SITE}${BASE}/og-image.jpg`;

export default defineConfig({
  site: SITE,
  base: BASE,
  trailingSlash: 'always',
  integrations: [
    starlight({
      title: {
        uk: 'Українізатор LEGO Indiana Jones',
        en: 'LEGO Indiana Jones Ukrainian localization',
      },
      routeMiddleware: './src/routeData.ts',
      description:
        'Неофіційна українська локалізація LEGO Indiana Jones: The Original Adventures — текст, шрифти з ІіЇїЄєҐґ, текстури й меню ПК.',
      defaultLocale: 'root',
      locales: {
        root: { label: 'Українська', lang: 'uk' },
        en: { label: 'English', lang: 'en' },
      },
      favicon: '/favicon.svg',
      social: [
        { icon: 'github', label: 'GitHub', href: REPO },
        { icon: 'telegram', label: 'Telegram', href: 'https://t.me/dimkasmile' },
      ],
      editLink: { baseUrl: `${REPO}/edit/master/site/` },
      lastUpdated: false,
      credits: false,
      customCss: [
        '@fontsource/rubik/500.css',
        '@fontsource/rubik/700.css',
        '@fontsource/rubik/800.css',
        '@fontsource/ibm-plex-sans/400.css',
        '@fontsource/ibm-plex-sans/400-italic.css',
        '@fontsource/ibm-plex-sans/600.css',
        './src/styles/theme.css',
      ],
      components: {
        Header: './src/components/overrides/Header.astro',
        Footer: './src/components/overrides/Footer.astro',
        Hero: './src/components/overrides/Hero.astro',
        MarkdownContent: './src/components/overrides/MarkdownContent.astro',
        Head: './src/components/overrides/Head.astro',
      },
      head: [
        { tag: 'meta', attrs: { property: 'og:image', content: OG_IMAGE } },
        { tag: 'meta', attrs: { property: 'og:image:width', content: '1600' } },
        { tag: 'meta', attrs: { property: 'og:image:height', content: '900' } },
        { tag: 'meta', attrs: { name: 'twitter:image', content: OG_IMAGE } },
        { tag: 'meta', attrs: { name: 'theme-color', content: '#C8102E' } },
      ],
      // Підписи — українською (корінь) і англійською (/en/); slug і autogenerate Starlight сам веде на сторінку мови.
      sidebar: [
        {
          label: 'Гравцям',
          translations: { en: 'For players' },
          items: [
            { label: 'Встановлення й видалення', translations: { en: 'Install & uninstall' }, slug: 'install' },
            { label: 'Питання й відповіді', translations: { en: 'FAQ' }, slug: 'faq' },
            { label: 'Зворотний зв’язок', translations: { en: 'Feedback' }, slug: 'feedback' },
          ],
        },
        {
          label: 'Про переклад',
          translations: { en: 'About the translation' },
          items: [
            { label: 'Як ми це робили', translations: { en: 'How we built it' }, slug: 'approach' },
            { label: 'Культурні адаптації', translations: { en: 'Cultural adaptations' }, slug: 'adaptations' },
            { label: 'Глосарій', translations: { en: 'Glossary' }, slug: 'glossary' },
          ],
        },
        {
          label: 'Дослідження',
          translations: { en: 'Research' },
          items: [{ autogenerate: { directory: 'research' } }],
        },
        {
          label: 'Розробникам',
          translations: { en: 'For developers' },
          items: [
            { label: 'Інструменти', translations: { en: 'Tooling' }, slug: 'tooling' },
            { autogenerate: { directory: 'dev' } },
          ],
        },
      ],
    }),
  ],
});
