import { useStore } from '../store/useStore';
import { TRANSLATIONS, type Lang, type Translations } from './translations';

export function useLang(): { t: Translations; lang: Lang } {
  const lang = useStore((s) => s.uiLanguage);
  return { t: TRANSLATIONS[lang], lang };
}
