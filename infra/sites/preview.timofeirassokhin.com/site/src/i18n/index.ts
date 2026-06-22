import { ru } from './ru';
import { en } from './en';

export type Locale = 'ru' | 'en';
export const defaultLocale: Locale = 'ru';
export const locales: Locale[] = ['ru', 'en'];

export const dict = { ru, en } as const;

export function t(locale: Locale): typeof ru {
  return dict[locale];
}

/** Build a URL for the same logical path in another locale. */
export function localizedHref(path: string, locale: Locale): string {
  // path is the canonical (RU) path, e.g. "/coaching"
  const clean = path.startsWith('/') ? path : `/${path}`;
  return locale === 'ru' ? clean : `/en${clean}`;
}
