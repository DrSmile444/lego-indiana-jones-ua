/**
 * Рядки інтерфейсу власних компонентів сайту українською (корінь) та англійською (/en/).
 *
 * Мова сторінки береться з Starlight (`Astro.locals.starlightRoute.locale`): `undefined` — корінь (uk),
 * `'en'` — англійська. Посилання всередині компонентів будуються через `localePath`, щоб вести на сторінку
 * тієї ж мови. Англійський словник має ту саму форму, що й український (`Strings`), — пропущений рядок
 * зупинить перевірку типів.
 */

export type Lang = 'uk' | 'en';

export const LANGS: Lang[] = ['uk', 'en'];

const BASE = import.meta.env.BASE_URL.replace(/\/?$/, '/');

/** Мова поточної сторінки Starlight. */
export function langOf(locals: unknown): Lang {
  const route = (locals as { starlightRoute?: { locale?: string } } | undefined)?.starlightRoute;
  return route?.locale === 'en' ? 'en' : 'uk';
}

/** Шлях сторінки сайту в потрібній мові: localePath('en', 'install/') -> /lego-indiana-jones-ua/en/install/. */
export function localePath(lang: Lang, page = ''): string {
  return `${BASE}${lang === 'en' ? 'en/' : ''}${page.replace(/^\//, '')}`;
}

/** Мовний тег для Intl і атрибута lang. */
export const BCP47: Record<Lang, string> = { uk: 'uk-UA', en: 'en-US' };

const REPO = 'https://github.com/DrSmile444/lego-indiana-jones-ua';

const uk = {
  header: {
    kicker: 'українізатор',
    name: 'LEGO Індіана Джонс',
    homeLabel: 'LEGO Індіана Джонс — українізатор, на головну',
    /** Короткий перемикач мови в шапці на вузьких екранах без бічної панелі (головна). */
    switchTo: { lang: 'en' as Lang, short: 'EN', label: 'English version of this page' },
    navLabel: 'Головні розділи',
    nav: [
      { page: 'install/', label: 'Встановлення' },
      { page: 'approach/', label: 'Як ми це робили' },
      { page: 'glossary/', label: 'Глосарій' },
    ],
  },
  footer: {
    brand: 'LEGO Індіана Джонс — українізатор.',
    tagline: 'Зроблено з любов’ю до гри й до української мови.',
    releases: 'Релізи',
    feedback: 'Зворотний зв’язок',
    code: 'Код на GitHub',
    otherLang: { lang: 'en' as Lang, label: 'English version' },
    disclaimer:
      'Неофіційний фанатський проєкт; не пов’язаний з LEGO Group, Lucasfilm, TT Games чи Warner Bros. Усі торговельні марки належать їхнім власникам; скриншоти гри використано як ілюстрації перекладу. Код — MIT, переклад і документація — CC BY 4.0:',
    licenses: 'ліцензії проєкту',
  },
  head: {
    ogImageAlt: 'Головне меню гри з українським логотипом «Індіана Джонс: Оригінальні пригоди»',
  },
  hero: {
    kicker: 'Неофіційна фанатська локалізація',
    badgesLabel: 'Статус і сумісність',
    badges: [
      { tone: 'ok', label: 'Повний переклад' },
      { tone: 'ok', label: 'Steam — перевірено' },
      { tone: '', label: 'Steam Deck — перевірено' },
      { tone: 'no', label: 'GOG — не перевірено' },
    ],
    linksLabel: 'Швидкі посилання',
    links: [
      { page: 'install/', label: 'Як встановити' },
      { page: 'approach/', label: 'Як ми це робили' },
      { page: 'feedback/', label: 'Знайшли помилку?' },
    ],
    imageAlt:
      'Головне меню гри українською: логотип «Індіана Джонс: Оригінальні пригоди» і пункти «Нова гра», «Завантажити гру», «Налаштування», «Вийти до Windows»',
    imageEmpty: 'Головне меню українською',
    caption: 'Головне меню — з новим логотипом і шрифтами',
  },
  compass: { n: 'Пн', s: 'Пд', e: 'С', w: 'З' },
  download: {
    label: 'Завантажити',
    version: 'версія',
    source: 'ZIP з GitHub',
    note: 'Безкоштовно. Потрібна гра LEGO Indiana Jones: The Original Adventures (PC).',
    all: 'Усі версії',
  },
  beforeAfter: {
    before: 'Англійською: ',
    after: 'Українською: ',
    range: 'Частка українського знімка',
  },
  gallery: {
    zoom: 'Збільшити: ',
    dialog: 'Перегляд скриншота',
    prev: 'Попередній скриншот',
    next: 'Наступний скриншот',
    close: 'Закрити',
  },
  glossary: {
    search: 'Пошук у глосарії',
    placeholder: 'Пошук: Інді, круглики, Ковчег…',
    categoryGroup: 'Категорія',
    all: 'Усі',
    /** {shown} і {total} підставляються на клієнті. */
    count: 'Показано {shown} з {total} термінів',
    empty: 'Нічого не знайдено. Спробуйте інше слово.',
    columns: { category: 'Категорія', en: 'Оригінал', uk: 'Українською', status: 'Статус', note: 'Примітка' },
    categories: {
      characters: 'Персонажі',
      artifacts: 'Артефакти',
      items: 'Предмети',
      game_mechanics: 'Ігрові механіки',
      places: 'Місця',
      chapter_titles: 'Назви розділів',
    } as Record<string, string>,
    status: {
      'team-approved': { label: 'Затверджено', tone: 'ok', hint: 'Рішення команди, перевірене в грі' },
      high: { label: 'Усталене', tone: 'ok', hint: 'Усталений відповідник, висока впевненість' },
      'medium-high': { label: 'Ймовірне', tone: 'mid', hint: 'Впевненість вище середньої' },
      medium: { label: 'Обговорюється', tone: 'mid', hint: 'Середня впевненість' },
      'low-proposal': { label: 'Пропозиція', tone: 'low', hint: 'Попередня пропозиція, може змінитися' },
    } as Record<string, { label: string; tone: string; hint: string }>,
  },
  install: {
    steps: [
      { title: 'Завантажте ZIP', html: 'Натисніть цеглинку «Завантажити» — архів береться просто з GitHub Releases.' },
      {
        title: 'Розпакуйте в теку гри',
        html: 'Поруч із <code>LEGOIndy.exe</code> мають опинитися <code>dinput8.dll</code> і тека <code>scripts/</code>.',
      },
      { title: 'Грайте українською', html: 'Запустіть гру через Steam. Оригінальні файли гри й збереження не змінюються.' },
    ],
    more: 'Докладно, з видаленням і перевіркою контрольних сум:',
    moreLink: 'інструкція зі встановлення',
  },
  stats: [
    { big: '598', label: 'рядків гри', text: 'діалоги, підказки, меню, імена — плюс TRC.CSV і титри', tone: 'red' },
    { big: '38', label: 'рядків меню ПК', text: 'налаштування відео, звуку й керування з виконуваного файлу', tone: 'yellow' },
    { big: 'ІіЇїЄєҐґ', label: 'у шрифтах', text: 'нові гліфи в ігрових атласах, підігнані до оригінального стилю', tone: 'blue' },
    { big: '9', label: 'текстур', text: 'написи на текстурах, зокрема логотип на титульному екрані', tone: 'leather' },
  ],
  adaptations: {
    cards: [
      { uk: 'Валєра', en: 'Jungle Guide', why: 'жартівливе ім’я провідника, привіт українському дубляжу «Тачок»' },
      { uk: 'Пластун', en: 'Boy Scout', why: 'український відповідник скаута' },
      { uk: 'Круглики', en: 'Studs', why: 'ігрова валюта — круглі деталі LEGO' },
      { uk: 'Бандюган', en: 'Bandit', why: 'з характером, а не просто «бандит»' },
      { uk: 'Чорний археолог', en: 'Grave Robber', why: 'той, хто розкопує без дозволу' },
      { uk: 'Шанхайський батяр', en: 'Shanghai Hoodlum', why: 'львівський «батяр» у шанхайських декораціях' },
      { uk: 'Форелька', en: 'редактор персонажів', plain: true, why: 'ім’я власного персонажа в редакторі' },
      { uk: 'Льоля', en: 'редактор персонажів', plain: true, why: 'ще одне ім’я власного персонажа' },
    ] as { uk: string; en: string; gloss?: string; plain?: boolean; why: string }[],
    moreBefore: 'Чому саме так — на сторінці ',
    moreAdaptations: 'культурних адаптацій',
    moreMiddle: ', а всі терміни — у ',
    moreGlossary: 'глосарії',
    moreAfter: '.',
  },
  route: [
    {
      title: 'Дослідження',
      text: 'Розібралися, де гра зберігає текст, шрифти й текстури, і які формати TT Games доведеться змінювати.',
    },
    {
      title: 'Розпакування',
      text: 'Розпакували DAT-архіви, знайшли ENGLISH.TXT, TRC.CSV, титри, атласи шрифтів і текстури з написами.',
    },
    {
      title: 'Шрифти',
      text: 'Додали в ігрові атласи літери І, Ї, Є, Ґ та їхні малі пари, підігнали метрики й перевірили кожен шрифт гри.',
    },
    {
      title: 'Переклад і глосарій',
      text: '598 рядків гри, TRC.CSV і титри: спершу глосарій і контекст кожного рядка, потім переклад, вичитка й культурні адаптації.',
    },
    {
      title: 'Рушій (UAP/ASI)',
      text: 'ASI-плагін через dinput8.dll підставляє ресурси з пакета UKRAINIAN.uap під час гри — оригінальні файли лишаються недоторканими.',
    },
    { title: 'Текстури', text: 'Перемалювали 9 текстур із написами, зокрема логотип на титульному екрані.' },
    {
      title: 'QA наживо',
      text: 'Проходили гру з перекладом: шукали обрізаний текст, криві переноси й рядки без контексту, правили й перевіряли знову.',
    },
    {
      title: 'Реліз',
      text: 'Зібрали ZIP із контрольними сумами SHA256SUMS і опублікували на GitHub — перша публічна версія 1.1.10.',
    },
  ],
  studHunt: {
    /** {value} підставляється. */
    collect: 'Зібрати круглик (+{value})',
    counter: 'Круглики:',
    allCollected: 'Справжній шукач пригод!',
  },
};

export type Strings = typeof uk;

const en: Strings = {
  header: {
    kicker: 'Ukrainian localization',
    name: 'LEGO Indiana Jones',
    homeLabel: 'LEGO Indiana Jones — Ukrainian localization, home page',
    switchTo: { lang: 'uk', short: 'УКР', label: 'Українська версія цієї сторінки' },
    navLabel: 'Main sections',
    nav: [
      { page: 'install/', label: 'Install' },
      { page: 'approach/', label: 'How we built it' },
      { page: 'glossary/', label: 'Glossary' },
    ],
  },
  footer: {
    brand: 'LEGO Indiana Jones — Ukrainian localization.',
    tagline: 'Made with love for the game and for the Ukrainian language.',
    releases: 'Releases',
    feedback: 'Feedback',
    code: 'Code on GitHub',
    otherLang: { lang: 'uk', label: 'Українська версія' },
    disclaimer:
      'Unofficial fan project; not affiliated with or endorsed by the LEGO Group, Lucasfilm, TT Games or Warner Bros. All trademarks belong to their respective owners; game screenshots are used to illustrate the translation. Code is MIT, translation and documentation are CC BY 4.0:',
    licenses: 'project licenses',
  },
  head: {
    ogImageAlt:
      'The game’s main menu with the Ukrainian logo «Індіана Джонс: Оригінальні пригоди» (Indiana Jones: The Original Adventures)',
  },
  hero: {
    kicker: 'Unofficial fan localization',
    badgesLabel: 'Status and compatibility',
    badges: [
      { tone: 'ok', label: 'Complete translation' },
      { tone: 'ok', label: 'Steam — verified' },
      { tone: '', label: 'Steam Deck — verified' },
      { tone: 'no', label: 'GOG — not verified' },
    ],
    linksLabel: 'Quick links',
    links: [
      { page: 'install/', label: 'How to install' },
      { page: 'approach/', label: 'How we built it' },
      { page: 'feedback/', label: 'Found a bug?' },
    ],
    imageAlt:
      'The game’s main menu in Ukrainian: the logo «Індіана Джонс: Оригінальні пригоди» and the items «Нова гра» (New Game), «Завантажити гру» (Load Game), «Налаштування» (Options), «Вийти до Windows» (Quit to Windows)',
    imageEmpty: 'Main menu in Ukrainian',
    caption: 'The main menu — with the new logo and fonts',
  },
  compass: { n: 'N', s: 'S', e: 'E', w: 'W' },
  download: {
    label: 'Download',
    version: 'version',
    source: 'ZIP from GitHub',
    note: 'Free. Requires LEGO Indiana Jones: The Original Adventures (PC).',
    all: 'All versions',
  },
  beforeAfter: {
    before: 'In English: ',
    after: 'In Ukrainian: ',
    range: 'How much of the Ukrainian screenshot to reveal',
  },
  gallery: {
    zoom: 'Enlarge: ',
    dialog: 'Screenshot viewer',
    prev: 'Previous screenshot',
    next: 'Next screenshot',
    close: 'Close',
  },
  glossary: {
    search: 'Search the glossary',
    placeholder: 'Search: Indy, studs, Ark, Валєра…',
    categoryGroup: 'Category',
    all: 'All',
    count: 'Showing {shown} of {total} terms',
    empty: 'Nothing found. Try another word.',
    columns: {
      category: 'Category',
      en: 'English term',
      uk: 'Ukrainian translation',
      status: 'Status',
      note: 'Note',
    },
    categories: {
      characters: 'Characters',
      artifacts: 'Artifacts',
      items: 'Items',
      game_mechanics: 'Game mechanics',
      places: 'Places',
      chapter_titles: 'Chapter titles',
    },
    status: {
      'team-approved': { label: 'Approved', tone: 'ok', hint: 'Decided by the author and checked in-game' },
      high: { label: 'Established', tone: 'ok', hint: 'Established equivalent, high confidence' },
      'medium-high': { label: 'Likely', tone: 'mid', hint: 'Above-average confidence' },
      medium: { label: 'Under discussion', tone: 'mid', hint: 'Medium confidence' },
      'low-proposal': { label: 'Proposal', tone: 'low', hint: 'Early proposal, may change' },
    },
  },
  install: {
    steps: [
      { title: 'Download the ZIP', html: 'Press the «Download» brick — the archive comes straight from GitHub Releases.' },
      {
        title: 'Unpack into the game folder',
        html: '<code>dinput8.dll</code> and the <code>scripts/</code> folder must end up next to <code>LEGOIndy.exe</code>.',
      },
      {
        title: 'Play in Ukrainian',
        html: 'Launch the game from Steam with the game language set to English. Original game files and saves stay untouched.',
      },
    ],
    more: 'Full details, uninstalling and checksum verification:',
    moreLink: 'installation guide',
  },
  stats: [
    { big: '598', label: 'game strings', text: 'dialogue, hints, menus, names — plus TRC.CSV and the credits', tone: 'red' },
    { big: '38', label: 'PC menu strings', text: 'video, audio and controls settings baked into the executable', tone: 'yellow' },
    { big: 'ІіЇїЄєҐґ', label: 'in the fonts', text: 'new glyphs in the game’s font atlases, matched to the original style', tone: 'blue' },
    { big: '9', label: 'textures', text: 'text painted on textures, including the title-screen logo', tone: 'leather' },
  ],
  adaptations: {
    cards: [
      {
        uk: 'Валєра',
        en: 'Jungle Guide',
        gloss: 'Valera',
        why: 'a playful everyday name for the guide, a nod to the Ukrainian dub of Cars',
      },
      { uk: 'Пластун', en: 'Boy Scout', gloss: 'Plastun', why: 'the Ukrainian word for a scout' },
      { uk: 'Круглики', en: 'Studs', gloss: 'kruhlyky, “little round ones”', why: 'the in-game currency — round LEGO pieces' },
      { uk: 'Бандюган', en: 'Bandit', gloss: 'Bandiuhan', why: 'a bandit with attitude, not just a plain “bandit”' },
      { uk: 'Чорний археолог', en: 'Grave Robber', gloss: 'Chornyi arkheoloh, “black archaeologist”', why: 'the Ukrainian term for someone who digs without a permit' },
      {
        uk: 'Шанхайський батяр',
        en: 'Shanghai Hoodlum',
        gloss: 'Shanhaiskyi batiar',
        why: 'a “batiar” — a Lviv street rogue — in a Shanghai setting',
      },
      { uk: 'Форелька', en: 'character editor', gloss: 'Forelka, “little trout”', plain: true, why: 'default name of the first custom character' },
      { uk: 'Льоля', en: 'character editor', gloss: 'Lyolya', plain: true, why: 'default name of the second custom character' },
    ],
    moreBefore: 'Why we chose these names — see ',
    moreAdaptations: 'cultural adaptations',
    moreMiddle: '; every term is listed in the ',
    moreGlossary: 'glossary',
    moreAfter: '.',
  },
  route: [
    {
      title: 'Research',
      text: 'Found out where the game keeps its text, fonts and textures, and which TT Games formats would have to change.',
    },
    {
      title: 'Unpacking',
      text: 'Unpacked the DAT archives and located ENGLISH.TXT, TRC.CSV, the credits, the font atlases and the textures with text.',
    },
    {
      title: 'Fonts',
      text: 'Added І, Ї, Є, Ґ and their lowercase pairs to the game’s font atlases, tuned the metrics and checked every font in the game.',
    },
    {
      title: 'Translation & glossary',
      text: '598 game strings, TRC.CSV and the credits: first a glossary and context for every line, then translation, proofreading and cultural adaptations.',
    },
    {
      title: 'Engine (UAP/ASI)',
      text: 'An ASI plugin loaded through dinput8.dll serves resources from the UKRAINIAN.uap package at runtime — original files stay untouched.',
    },
    { title: 'Textures', text: 'Repainted 9 textures with text, including the title-screen logo.' },
    {
      title: 'Live QA',
      text: 'Played through the game with the translation: hunted for clipped text, bad line breaks and lines without context, fixed and re-checked.',
    },
    {
      title: 'Release',
      text: 'Built a ZIP with SHA256SUMS checksums and published it on GitHub — the first public release, 1.1.10.',
    },
  ],
  studHunt: {
    collect: 'Collect a stud (+{value})',
    counter: 'Studs:',
    allCollected: 'A true adventurer!',
  },
};

export const STRINGS: Record<Lang, Strings> = { uk, en };

/** Словник для мови сторінки. */
export function strings(locals: unknown): Strings {
  return STRINGS[langOf(locals)];
}

/** Підставляє {ключ} у рядок. */
export function fmt(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (m, k) => (k in values ? String(values[k]) : m));
}

export const REPO_URL = REPO;
