import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    category: z.string(),
    publishDate: z.string(),
    pubDatetime: z.string(),
    modDatetime: z.string(),
    readingTime: z.number().optional(),
    tags: z.array(z.string()).default([]),
    ogImage: z.string().optional(),
<<<<<<< HEAD
=======
    heroImage: z.string().optional(),
>>>>>>> 3299e1a (重设计: 留学生公寓 现代清新视觉 + heroImage配图 + 全站部署)
  }),
});

export const collections = { articles };
