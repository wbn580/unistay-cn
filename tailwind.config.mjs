/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
<<<<<<< HEAD
        primary: '#9C5BD9',
        accent:  '#4DB6AC',
        bg:      '#FAFAFA',
        ink:     '#212121',
        muted:   '#757575',
      },
      fontFamily: {
        heading: ['Sarasa Gothic SC', 'Georgia', 'serif'],
        body:    ['PingFang SC', 'system-ui', 'sans-serif'],
        mono:    ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      maxWidth: {
        prose: '896px',
=======
        primary: '#0D9488',
        accent:  '#F97316',
        bg:      '#FFFFFF',
        ink:     '#1E293B',
        muted:   '#64748B',
      },
      fontFamily: {
        heading: ['Noto Sans SC', 'system-ui', 'sans-serif'],
        body:    ['Noto Sans SC', 'PingFang SC', 'system-ui', 'sans-serif'],
        mono:    ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      maxWidth: {
        prose: '768px',
>>>>>>> 3299e1a (重设计: 留学生公寓 现代清新视觉 + heroImage配图 + 全站部署)
      },
    },
  },
  plugins: [],
};
