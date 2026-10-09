/**
 * CHAI Dynamic Branding & Theme-Aware Palette System
 * 
 * Maps user-selected accent themes and light/dark modes to complementary,
 * high-contrast, visually refined logo color treatments.
 * 
 * Prevents monochromatic blending while ensuring the AI face, smart glasses,
 * circuit-tree branches, and CHAI wordmark remain legible and iconic.
 */

export type AccentChoice =
  | 'violet'
  | 'blue'
  | 'teal'
  | 'rose'
  | 'amber'
  | 'green'
  | 'red'
  | 'yellow'
  | 'cyan'
  | 'monochrome';

export type ThemeMode = 'dark' | 'light';

export interface LogoPalette {
  /** Main circuit branches, face contour, and primary CHAI wordmark */
  primary: string;
  /** Circuit nodes, smart glasses frame highlight, and secondary traces */
  secondary: string;
  /** Glasses lens glow and energy nodes */
  accent: string;
  /** Glasses frame base */
  glasses: string;
  /** Subdued tagline "SINCE 2026" */
  tagline: string;
  /** Inner facial cutouts or negative space */
  contrast: string;
  /** Display label for this accent palette */
  label: string;
  /** Swatch color representing this theme */
  swatch: string;
}

export const ACCENT_PALETTES: Record<
  AccentChoice,
  { label: string; swatch: string; dark: LogoPalette; light: LogoPalette }
> = {
  // 1. Purple / Violet: Deep indigo + lavender
  violet: {
    label: 'Violet',
    swatch: '#7064e8',
    dark: {
      primary: '#c4b5fd', // Soft radiant lavender
      secondary: '#a78bfa', // Electric lavender
      accent: '#818cf8', // Indigo glow
      glasses: '#e0e7ff', // Crisp light frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Violet',
      swatch: '#7064e8',
    },
    light: {
      primary: '#312e81', // Deep indigo
      secondary: '#6d28d9', // Vibrant violet
      accent: '#4338ca', // Royal indigo
      glasses: '#4c1d95', // Deep frame
      tagline: '#64748b',
      contrast: '#ffffff',
      label: 'Violet',
      swatch: '#7064e8',
    },
  },

  // 2. Blue: Deep navy + electric blue
  blue: {
    label: 'Blue',
    swatch: '#3979df',
    dark: {
      primary: '#93c5fd', // Electric sky blue
      secondary: '#60a5fa', // Brilliant blue
      accent: '#38bdf8', // Cyan glow
      glasses: '#e0f2fe', // Crisp ice frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Blue',
      swatch: '#3979df',
    },
    light: {
      primary: '#1e3a8a', // Deep navy
      secondary: '#2563eb', // Electric blue
      accent: '#0284c7', // Cyan highlight
      glasses: '#172554', // Navy frame
      tagline: '#64748b',
      contrast: '#ffffff',
      label: 'Blue',
      swatch: '#3979df',
    },
  },

  // 3. Teal: Deep teal + soft cyan / mint
  teal: {
    label: 'Teal',
    swatch: '#148b7e',
    dark: {
      primary: '#5eead4', // Soft mint cyan
      secondary: '#2dd4bf', // Electric teal
      accent: '#38bdf8', // Luminous aqua
      glasses: '#ccfbf1', // Pale teal frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Teal',
      swatch: '#148b7e',
    },
    light: {
      primary: '#134e4a', // Deep teal
      secondary: '#0d9488', // Emerald teal
      accent: '#0284c7', // Cyan accent
      glasses: '#042f2e', // Deep frame
      tagline: '#64748b',
      contrast: '#ffffff',
      label: 'Teal',
      swatch: '#148b7e',
    },
  },

  // 4. Cyan: Deep teal + soft cyan
  cyan: {
    label: 'Cyan',
    swatch: '#06b6d4',
    dark: {
      primary: '#67e8f9', // Soft cyan
      secondary: '#22d3ee', // Electric cyan
      accent: '#38bdf8', // Aqua glow
      glasses: '#e0f2fe', // Pale ice frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Cyan',
      swatch: '#06b6d4',
    },
    light: {
      primary: '#164e63', // Deep marine cyan
      secondary: '#0891b2', // Rich cyan
      accent: '#0e7490', // Ocean teal
      glasses: '#083344', // Deep cyan frame
      tagline: '#64748b',
      contrast: '#ffffff',
      label: 'Cyan',
      swatch: '#06b6d4',
    },
  },

  // 5. Pink / Rose: Burgundy + rose pink
  rose: {
    label: 'Rose',
    swatch: '#ce5478',
    dark: {
      primary: '#fda4af', // Soft rose petal
      secondary: '#fb7185', // Radiant rose pink
      accent: '#f43f5e', // Ruby glow
      glasses: '#ffe4e6', // Soft light frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Rose',
      swatch: '#ce5478',
    },
    light: {
      primary: '#831843', // Deep burgundy
      secondary: '#e11d48', // Rose crimson
      accent: '#be123c', // Wine accent
      glasses: '#4c0519', // Burgundy frame
      tagline: '#64748b',
      contrast: '#ffffff',
      label: 'Rose',
      swatch: '#ce5478',
    },
  },

  // 6. Orange / Amber: Dark brown bronze + warm amber
  amber: {
    label: 'Amber',
    swatch: '#c86d1a',
    dark: {
      primary: '#fcd34d', // Warm amber gold
      secondary: '#fbbf24', // Amber glow
      accent: '#f59e0b', // Radiant honey
      glasses: '#fef3c7', // Warm pale frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Amber',
      swatch: '#c86d1a',
    },
    light: {
      primary: '#78350f', // Dark brown bronze
      secondary: '#d97706', // Warm amber
      accent: '#b45309', // Deep golden ochre
      glasses: '#451a03', // Bronze frame
      tagline: '#78716c',
      contrast: '#ffffff',
      label: 'Amber',
      swatch: '#c86d1a',
    },
  },

  // 7. Green: Deep forest green + mint
  green: {
    label: 'Green',
    swatch: '#10b981',
    dark: {
      primary: '#6ee7b7', // Soft mint
      secondary: '#34d399', // Electric emerald
      accent: '#10b981', // Jade glow
      glasses: '#d1fae5', // Pale mint frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Green',
      swatch: '#10b981',
    },
    light: {
      primary: '#064e3b', // Deep forest green
      secondary: '#059669', // Vibrant mint
      accent: '#047857', // Emerald green
      glasses: '#022c22', // Forest frame
      tagline: '#6b7280',
      contrast: '#ffffff',
      label: 'Green',
      swatch: '#10b981',
    },
  },

  // 8. Red: Deep maroon + muted crimson
  red: {
    label: 'Red',
    swatch: '#dc2626',
    dark: {
      primary: '#fca5a5', // Soft coral red
      secondary: '#f87171', // Radiant crimson
      accent: '#ef4444', // Ruby glow
      glasses: '#fee2e2', // Light frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Red',
      swatch: '#dc2626',
    },
    light: {
      primary: '#7f1d1d', // Deep maroon
      secondary: '#dc2626', // Muted crimson
      accent: '#b91c1c', // Cardinal red
      glasses: '#450a0a', // Deep maroon frame
      tagline: '#64748b',
      contrast: '#ffffff',
      label: 'Red',
      swatch: '#dc2626',
    },
  },

  // 9. Yellow: Olive + muted golden yellow
  yellow: {
    label: 'Yellow',
    swatch: '#eab308',
    dark: {
      primary: '#fef08a', // Soft sunlight
      secondary: '#facc15', // Golden yellow
      accent: '#fbbf24', // Amber glow
      glasses: '#fef9c3', // Pale gold frame
      tagline: '#94a3b8',
      contrast: '#070812',
      label: 'Yellow',
      swatch: '#eab308',
    },
    light: {
      primary: '#713f12', // Olive brown
      secondary: '#ca8a04', // Muted golden yellow
      accent: '#a16207', // Bronze gold
      glasses: '#422006', // Olive frame
      tagline: '#78716c',
      contrast: '#ffffff',
      label: 'Yellow',
      swatch: '#eab308',
    },
  },

  // 10. Monochrome: Charcoal + neutral gray
  monochrome: {
    label: 'Monochrome',
    swatch: '#71717a',
    dark: {
      primary: '#f4f4f5', // Crisp platinum
      secondary: '#e4e4e7', // Cool silver
      accent: '#d4d4d8', // Slate highlight
      glasses: '#ffffff', // Pure white frame
      tagline: '#71717a',
      contrast: '#070812',
      label: 'Monochrome',
      swatch: '#71717a',
    },
    light: {
      primary: '#18181b', // Deep charcoal
      secondary: '#52525b', // Neutral gray
      accent: '#3f3f46', // Graphite
      glasses: '#09090b', // Black frame
      tagline: '#71717a',
      contrast: '#ffffff',
      label: 'Monochrome',
      swatch: '#71717a',
    },
  },
};

/**
 * Normalizes input accent name to a supported AccentChoice.
 */
export function normalizeAccent(accentName?: string | null): AccentChoice {
  if (!accentName) return 'violet';
  const clean = accentName.toLowerCase().trim();
  if (clean === 'purple') return 'violet';
  if (clean === 'pink') return 'rose';
  if (clean === 'orange') return 'amber';
  if (clean in ACCENT_PALETTES) return clean as AccentChoice;
  return 'violet';
}

/**
 * Returns the theme-aware logo palette based on current accent and light/dark mode.
 */
export function getLogoPalette(accentName?: string | null, isDark = true): LogoPalette {
  const choice = normalizeAccent(accentName);
  const entry = ACCENT_PALETTES[choice] || ACCENT_PALETTES.violet;
  return isDark ? entry.dark : entry.light;
}

/**
 * Synchronizes CSS variables on the document element for consistent CSS-based rendering.
 */
export function syncLogoCssVariables(palette: LogoPalette) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.style.setProperty('--chai-logo-primary', palette.primary);
  root.style.setProperty('--chai-logo-secondary', palette.secondary);
  root.style.setProperty('--chai-logo-accent', palette.accent);
  root.style.setProperty('--chai-logo-glasses', palette.glasses);
  root.style.setProperty('--chai-logo-tagline', palette.tagline);
  root.style.setProperty('--chai-logo-contrast', palette.contrast);
}

/**
 * Generates an optimized, high-contrast standalone SVG favicon data URI.
 */
export function generateFaviconDataUri(palette: LogoPalette): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" fill="none">
  <!-- Circuit tree crown -->
  <path d="M16 12V4" stroke="${palette.primary}" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M16 8L11 4" stroke="${palette.primary}" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M16 8L21 4" stroke="${palette.primary}" stroke-width="1.8" stroke-linecap="round"/>
  <circle cx="16" cy="3" r="1.6" fill="${palette.secondary}"/>
  <circle cx="11" cy="3.5" r="1.4" fill="${palette.secondary}"/>
  <circle cx="21" cy="3.5" r="1.4" fill="${palette.secondary}"/>
  <!-- Temporal circuit branches -->
  <path d="M11 13L7 9" stroke="${palette.secondary}" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="6.5" cy="8.5" r="1.2" fill="${palette.accent}"/>
  <path d="M21 13L25 9" stroke="${palette.secondary}" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="25.5" cy="8.5" r="1.2" fill="${palette.accent}"/>
  <!-- AI Face Silhouette -->
  <path d="M20 12C20 12 21.5 15.5 22 17.5C22.2 18.2 23 18.8 23.5 19.5L24 20.5C23.5 21 22.5 21.2 22.8 22L23 23.5C22 24.2 21.2 24.8 20 25.2L15.5 26.5C13.5 26 12 24.5 11 22.5C10 20.5 10 17 11.5 14C12.5 12 14 11.5 16 11.5" stroke="${palette.primary}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  <!-- Smart Glasses Frame & Glow -->
  <rect x="15" y="15" width="8" height="4.5" rx="1.2" fill="${palette.accent}" fill-opacity="0.25" stroke="${palette.glasses}" stroke-width="1.8"/>
  <path d="M15 17.2H11.5" stroke="${palette.glasses}" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="16.5" y1="16.2" x2="19.5" y2="16.2" stroke="${palette.glasses}" stroke-width="1" stroke-linecap="round"/>
  <!-- Ear node -->
  <circle cx="11.5" cy="18" r="1.5" fill="${palette.secondary}"/>
</svg>`;

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

/**
 * Updates the document favicon in the browser tab to reflect current accent and theme.
 */
export function updateDocumentFavicon(accentName?: string | null, isDark = true) {
  if (typeof document === 'undefined') return;
  const palette = getLogoPalette(accentName, isDark);
  syncLogoCssVariables(palette);

  try {
    let link = document.querySelector<HTMLLinkElement>("link[rel~='icon'][type='image/svg+xml']");
    if (!link) {
      link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
    }
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      link.type = 'image/svg+xml';
      document.head.appendChild(link);
    }
    link.type = 'image/svg+xml';
    link.href = generateFaviconDataUri(palette);
  } catch (err) {
    console.debug('[CHAI Favicon] Failed to update dynamic favicon:', err);
  }
}
