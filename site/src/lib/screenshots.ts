import type { ImageMetadata } from 'astro';

/** Скриншоти копіює scripts/sync-docs.mjs з docs/screenshots/. */
const files = import.meta.glob<{ default: ImageMetadata }>('../generated/screenshots/*.{jpg,jpeg,png,webp}', {
  eager: true,
});

const byName = new Map<string, ImageMetadata>(
  Object.entries(files).map(([p, mod]) => [p.split('/').pop()!, mod.default]),
);

export function screenshot(name: string): ImageMetadata | undefined {
  return byName.get(name);
}

import type { Lang } from '../i18n/strings';

export interface Shot {
  file: string;
  alt: Record<Lang, string>;
  caption: Record<Lang, string>;
}

/** Підписи галереї (порядок = порядок показу). */
export const gallery: Shot[] = [
  {
    file: 'main-menu.jpg',
    caption: { uk: 'Головне меню з українським логотипом', en: 'Main menu with the Ukrainian logo' },
    alt: {
      uk: 'Головне меню: логотип «Індіана Джонс: Оригінальні пригоди», пункти «Нова гра», «Завантажити гру», «Налаштування», «Вийти до Windows»',
      en: 'Main menu: the logo «Індіана Джонс: Оригінальні пригоди» and the items «Нова гра» (New Game), «Завантажити гру» (Load Game), «Налаштування» (Options), «Вийти до Windows» (Quit to Windows)',
    },
  },
  {
    file: 'hint-dig.jpg',
    caption: { uk: 'Підказка з «ї» та «є» у шрифті гри', en: 'A hint with «ї» and «є» in the game font' },
    alt: {
      uk: 'Індіана копає в джунглях; підказка: «Слідкуйте за об’єктами LEGO, захованими в землі. Якщо у вас є лопата, натисніть B, щоб їх викопати»',
      en: 'Indiana digging in the jungle; the hint reads «Слідкуйте за об’єктами LEGO, захованими в землі. Якщо у вас є лопата, натисніть B, щоб їх викопати» (Look out for LEGO objects buried in the ground. If you have a shovel, press B to dig them up)',
    },
  },
  {
    file: 'shop-valera.jpg',
    caption: { uk: 'Крамниця персонажів: «Валєра»', en: 'Character shop: «Валєра» (Valera), the Jungle Guide' },
    alt: {
      uk: 'Крамниця персонажів у коледжі: портрет з підписом «Валєра» і ціною 18 000 кругликів',
      en: 'The character shop at the college: a portrait labelled «Валєра» (Valera) priced at 18,000 kruhlyky (studs)',
    },
  },
  {
    file: 'studs-krugliky.jpg',
    caption: { uk: 'Ігрова валюта — «круглики»', en: 'The in-game currency — «круглики» (kruhlyky, studs)' },
    alt: {
      uk: 'Підсумок рівня з написом «Круглики» та сумою 442 617 на тлі мапи з пірамідами',
      en: 'Level summary with the label «Круглики» (Studs) and a total of 442,617 over a map with pyramids',
    },
  },
  {
    file: 'editor-forelka.jpg',
    caption: { uk: 'Редактор персонажів: «Форелька»', en: 'Character editor: «Форелька» (Forelka, “little trout”)' },
    alt: {
      uk: 'Редактор персонажів: мініфігурка в капелюсі з лопатою, ім’я «Форелька»',
      en: 'Character editor: a minifigure in a hat holding a shovel, named «Форелька» (Forelka)',
    },
  },
  {
    file: 'exit-dialog.jpg',
    caption: { uk: 'Діалог виходу з рівня', en: 'The level exit dialog' },
    alt: {
      uk: 'Пауза на рівні «Колодязь душ»: «Вийти до коледжу Барнетта?», «Вийти без збереження», «Зберегти і вийти», «Скасувати»',
      en: 'Pause on the «Колодязь душ» (Well of Souls) level: «Вийти до коледжу Барнетта?» (Exit to Barnett College?), «Вийти без збереження» (Exit without saving), «Зберегти і вийти» (Save and exit), «Скасувати» (Cancel)',
    },
  },
  {
    file: 'pause-post-room.jpg',
    caption: { uk: 'Пауза в поштовій кімнаті', en: 'Pause in the Mail Room' },
    alt: {
      uk: 'Меню паузи в «Поштовій кімнаті»: «Продовжити», «Налаштування», «Бонуси», «Вийти»',
      en: 'Pause menu in «Поштова кімната» (the Mail Room): «Продовжити» (Resume), «Налаштування» (Options), «Бонуси» (Extras), «Вийти» (Quit)',
    },
  },
  {
    file: 'pause-barnett.jpg',
    caption: { uk: 'Пауза на рівні «У гори»', en: 'Pause on the «У гори» (Into the Mountains) level' },
    alt: {
      uk: 'Меню паузи за Меріон на рівні «У гори»: «Продовжити», «Налаштування», «Бонуси», «Коледж Барнетта»',
      en: 'Pause menu as Marion on the «У гори» (Into the Mountains) level: «Продовжити» (Resume), «Налаштування» (Options), «Бонуси» (Extras), «Коледж Барнетта» (Barnett College)',
    },
  },
  {
    file: 'hint-switch.jpg',
    caption: { uk: 'Підказка про перемикання персонажів', en: 'A hint about switching characters' },
    alt: {
      uk: 'Підказка в єгипетській гробниці: «Деякі головоломки можна розв’язати лише перемкнувшись на іншого персонажа за допомогою Y»',
      en: 'A hint in an Egyptian tomb: «Деякі головоломки можна розв’язати лише перемкнувшись на іншого персонажа за допомогою Y» (Some puzzles can only be solved by switching to another character with Y)',
    },
  },
];
