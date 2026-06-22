import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://preview.timofeirassokhin.com',
  output: 'static',
  trailingSlash: 'ignore',
  i18n: {
    defaultLocale: 'ru',
    locales: ['ru', 'en'],
    routing: {
      prefixDefaultLocale: false, // RU без префикса (/), EN — /en
    },
  },
});
