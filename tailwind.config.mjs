/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
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
      },
    },
  },
  plugins: [],
};
