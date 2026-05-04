import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://timofeirassokhin.com',
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
