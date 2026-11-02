import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader, i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      extend: z.object({
        /** Показати пунктирний маршрут «Як ми це робили» перед текстом сторінки. */
        routeTimeline: z.boolean().optional(),
        /** Сторінку згенеровано з docs/ скриптом sync-docs. */
        syncedFrom: z.string().optional(),
      }),
    }),
  }),
  /** Перевизначення рядків інтерфейсу Starlight: src/content/i18n/{uk,en}.json. */
  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),
};
