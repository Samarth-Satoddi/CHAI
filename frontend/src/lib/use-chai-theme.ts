import { useState, useEffect, useCallback } from 'react';
import {
  AccentChoice,
  ThemeMode,
  LogoPalette,
  getLogoPalette,
  normalizeAccent,
  updateDocumentFavicon,
  syncLogoCssVariables,
} from './chai-branding';

export interface ChaiThemeState {
  accent: AccentChoice;
  theme: ThemeMode;
  isDark: boolean;
  palette: LogoPalette;
  setAccent: (accent: AccentChoice) => void;
  setTheme: (theme: ThemeMode) => void;
}

export function useChaiTheme(): ChaiThemeState {
  const [accent, setAccentState] = useState<AccentChoice>(() => {
    if (typeof window === 'undefined') return 'violet';
    return normalizeAccent(localStorage.getItem('chai-accent'));
  });

  const [theme, setThemeState] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'dark';
    const stored = localStorage.getItem('chai-theme');
    if (stored === 'light') return 'light';
    return 'dark';
  });

  const isDark = theme === 'dark';
  const palette = getLogoPalette(accent, isDark);

  // Sync favicon and CSS variables when state changes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    syncLogoCssVariables(palette);
    updateDocumentFavicon(accent, isDark);
  }, [accent, isDark, palette]);

  // Listen to external theme/accent events
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleAccentChange = (e: Event) => {
      const custom = e as CustomEvent<string>;
      if (custom.detail) {
        setAccentState(normalizeAccent(custom.detail));
      }
    };

    const handleThemeChange = (e: Event) => {
      const custom = e as CustomEvent<string>;
      if (custom.detail) {
        setThemeState(custom.detail === 'light' ? 'light' : 'dark');
      }
    };

    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'chai-accent' && e.newValue) {
        setAccentState(normalizeAccent(e.newValue));
      }
      if (e.key === 'chai-theme' && e.newValue) {
        setThemeState(e.newValue === 'light' ? 'light' : 'dark');
      }
    };

    window.addEventListener('chai-accent-change', handleAccentChange as EventListener);
    window.addEventListener('chai-theme-change', handleThemeChange as EventListener);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener('chai-accent-change', handleAccentChange as EventListener);
      window.removeEventListener('chai-theme-change', handleThemeChange as EventListener);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const setAccent = useCallback((nextAccent: AccentChoice) => {
    setAccentState(nextAccent);
    if (typeof window !== 'undefined') {
      localStorage.setItem('chai-accent', nextAccent);
      window.dispatchEvent(new CustomEvent('chai-accent-change', { detail: nextAccent }));
    }
  }, []);

  const setTheme = useCallback((nextTheme: ThemeMode) => {
    setThemeState(nextTheme);
    if (typeof window !== 'undefined') {
      localStorage.setItem('chai-theme', nextTheme);
      window.dispatchEvent(new CustomEvent('chai-theme-change', { detail: nextTheme }));
    }
  }, []);

  return {
    accent,
    theme,
    isDark,
    palette,
    setAccent,
    setTheme,
  };
}
