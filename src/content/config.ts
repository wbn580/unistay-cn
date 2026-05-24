import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    tags: z.array(z.string()).default([]),
    readingTime: z.number().optional(),
    modDatetime: z.string(),
    category: z.string(),
    publishDate: z.string(),
    title: z.string(),
    description: z.string(),
    pubDatetime: z.string(),
    ogImage: z.string().optional(),

  },
});

export const collections = { articles };
