import React from 'react';
import { useChaiTheme } from '@/lib/use-chai-theme';
import { getLogoPalette, type LogoPalette } from '@/lib/chai-branding';
import { cn } from '@/lib/utils';

export type LogoVariant = 'full' | 'compact' | 'icon' | 'favicon';
export type LogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | number;

export interface ChaiLogoProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: LogoVariant;
  size?: LogoSize;
  accentOverride?: string;
  themeOverride?: 'dark' | 'light';
  showTagline?: boolean;
  interactive?: boolean;
  animated?: boolean;
}

const SIZE_MAP: Record<string, { icon: number; text: string; tagline: string; gap: string }> = {
  xs: { icon: 20, text: 'text-xs tracking-wider', tagline: 'text-[8px] tracking-[0.2em]', gap: 'gap-1.5' },
  sm: { icon: 26, text: 'text-sm tracking-wider', tagline: 'text-[9px] tracking-[0.22em]', gap: 'gap-2' },
  md: { icon: 34, text: 'text-base tracking-widest', tagline: 'text-[10px] tracking-[0.22em]', gap: 'gap-2.5' },
  lg: { icon: 44, text: 'text-xl tracking-widest', tagline: 'text-[11px] tracking-[0.24em]', gap: 'gap-3' },
  xl: { icon: 56, text: 'text-2xl tracking-widest', tagline: 'text-xs tracking-[0.25em]', gap: 'gap-3.5' },
};

/**
 * Scalable SVG vector icon of the CHAI AI Face, Smart Glasses, and Circuit-Tree Crown.
 */
export function ChaiIconSymbol({
  palette,
  size = 32,
  isFavicon = false,
  animated = false,
  className,
}: {
  palette: LogoPalette;
  size?: number;
  isFavicon?: boolean;
  animated?: boolean;
  className?: string;
}) {
  const strokeWidth = isFavicon ? 2.6 : 2;
  const secondaryStroke = isFavicon ? 2.2 : 1.6;

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('shrink-0 select-none overflow-visible', className)}
      aria-hidden="true"
    >
      <defs>
        {/* Subtle glow filter for circuit nodes */}
        <filter id={`node-glow-${palette.swatch.replace('#', '')}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* ─── 1. CIRCUIT-TREE CROWN & NEURAL TRACES ─── */}
      <g stroke={palette.primary} strokeLinecap="round" strokeLinejoin="round">
        {/* Central main trunk */}
        <path d="M32 23 V10" strokeWidth={strokeWidth} />
        {/* Central bifurcation branches */}
        <path d="M32 16 L22 8" strokeWidth={strokeWidth} />
        <path d="M32 16 L42 8" strokeWidth={strokeWidth} />

        {/* Left temporal circuit branch */}
        <path d="M24 25 L16 19 V13 L11 8" stroke={palette.secondary} strokeWidth={secondaryStroke} />
        <path d="M16 16 H8" stroke={palette.secondary} strokeWidth={secondaryStroke} />

        {/* Right frontal circuit branch */}
        <path d="M39 24 L48 18 V12 L53 7" stroke={palette.secondary} strokeWidth={secondaryStroke} />
        <path d="M48 15 H56" stroke={palette.secondary} strokeWidth={secondaryStroke} />
      </g>

      {/* ─── 2. TERMINAL CIRCUIT NODES / DOTS ─── */}
      <g fill={palette.secondary} className={cn(animated && 'animate-pulse')}>
        {/* Top central terminal node */}
        <circle cx="32" cy="7" r="2.4" fill={palette.accent} />
        {/* Upper lateral nodes */}
        <circle cx="22" cy="8" r="2.2" />
        <circle cx="42" cy="8" r="2.2" />
        {/* Outer leaf nodes */}
        <circle cx="11" cy="8" r="1.8" fill={palette.accent} />
        <circle cx="8" cy="16" r="1.8" />
        <circle cx="53" cy="7" r="1.8" fill={palette.accent} />
        <circle cx="56" cy="15" r="1.8" />
      </g>

      {/* ─── 3. AI HUMAN/ANDROID FACE SILHOUETTE ─── */}
      {/* Sleek, forward-looking geometric face profile */}
      <path
        d="M37 23
           C39.5 25 41 27.5 41.5 30.5
           L45 35
           L42 37.5
           L43 39
           L41.5 40.5
           L43 45
           L34 48
           L33 57
           M20 57
           L22 47
           C19 41 18.5 33 21 27
           C22.5 24.5 25 23 27 22.5"
        stroke={palette.primary}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Chin-to-neck connector contour */}
      <path
        d="M34 48 C28 49 24 45 22 40"
        stroke={palette.secondary}
        strokeWidth={secondaryStroke}
        strokeLinecap="round"
        opacity="0.85"
      />

      {/* Cybernetic Ear Node & Cheek Seam */}
      <circle
        cx="27"
        cy="39"
        r="3"
        stroke={palette.secondary}
        strokeWidth={secondaryStroke}
        fill={palette.contrast}
      />
      <circle cx="27" cy="39" r="1.2" fill={palette.accent} />
      <path
        d="M27 39 H34 L37 43"
        stroke={palette.secondary}
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.7"
      />

      {/* ─── 4. SIGNATURE SMART GLASSES ─── */}
      {/* Glasses Frame Outer Rim */}
      <path
        d="M32.5 31.5 H45 C46.2 31.5 46.8 32.8 46.2 34.2 L44.2 38 C43.6 39.2 42.4 39.8 41.2 39.8 H33 C31.8 39.8 31.2 38.8 31.6 37.6 L32.5 34.5 Z"
        fill={palette.accent}
        fillOpacity="0.22"
        stroke={palette.glasses}
        strokeWidth={isFavicon ? 2.4 : 2}
        strokeLinejoin="round"
      />

      {/* Glasses Temple Arm extending back to ear */}
      <path
        d="M32.5 33 L25 34.5"
        stroke={palette.glasses}
        strokeWidth={isFavicon ? 2.4 : 2}
        strokeLinecap="round"
      />

      {/* Luminous Smart Lens Highlight / Brow Line */}
      <line
        x1="34"
        y1="33"
        x2="43.5"
        y2="33"
        stroke={palette.accent}
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.9"
      />
      <line
        x1="35.5"
        y1="35"
        x2="38.5"
        y2="37.5"
        stroke={palette.glasses}
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.65"
      />
    </svg>
  );
}

/**
 * Universal dynamic CHAI logo component.
 * Adapts to active accent color, dark/light theme, and provides
 * 'full', 'compact', 'icon', and 'favicon' visual variants.
 */
export function ChaiLogo({
  variant = 'compact',
  size = 'md',
  accentOverride,
  themeOverride,
  showTagline = true,
  interactive = true,
  animated = false,
  className,
  ...rest
}: ChaiLogoProps) {
  const { accent, isDark } = useChaiTheme();

  const effectiveDark = themeOverride !== undefined ? themeOverride === 'dark' : isDark;
  const effectiveAccent = accentOverride || accent;
  const palette = getLogoPalette(effectiveAccent, effectiveDark);

  const isNumericSize = typeof size === 'number';
  const sizeConfig = isNumericSize
    ? {
        icon: size,
        text: size < 28 ? 'text-xs tracking-wider' : size < 40 ? 'text-sm tracking-wider' : 'text-lg tracking-widest',
        tagline: size < 28 ? 'text-[8px] tracking-[0.2em]' : 'text-[10px] tracking-[0.22em]',
        gap: size < 28 ? 'gap-1.5' : 'gap-2.5',
      }
    : SIZE_MAP[size] || SIZE_MAP.md;

  const accessibleLabel = variant === 'full' ? 'CHAI - Since 2026' : 'CHAI';

  if (variant === 'icon' || variant === 'favicon') {
    return (
      <div
        role="img"
        aria-label={accessibleLabel}
        className={cn(
          'inline-flex items-center justify-center transition-transform duration-200',
          interactive && 'hover:scale-105 active:scale-95',
          className
        )}
        {...rest}
      >
        <ChaiIconSymbol
          palette={palette}
          size={sizeConfig.icon}
          isFavicon={variant === 'favicon'}
          animated={animated}
        />
      </div>
    );
  }

  return (
    <div
      role="img"
      aria-label={accessibleLabel}
      className={cn(
        'group inline-flex items-center select-none transition-all duration-200',
        sizeConfig.gap,
        interactive && 'hover:opacity-95',
        className
      )}
      {...rest}
    >
      <div className={cn('shrink-0 transition-transform duration-200', interactive && 'group-hover:scale-105')}>
        <ChaiIconSymbol
          palette={palette}
          size={sizeConfig.icon}
          animated={animated}
        />
      </div>

      <div className="flex flex-col justify-center leading-none">
        {/* Wordmark "CHAI" */}
        <span
          style={{ color: palette.primary }}
          className={cn(
            'font-extrabold uppercase transition-colors duration-200 font-sans',
            sizeConfig.text
          )}
        >
          CHAI
        </span>

        {/* Tagline "SINCE 2026" */}
        {variant === 'full' && showTagline && (
          <span
            style={{ color: palette.tagline }}
            className={cn(
              'font-mono uppercase transition-colors duration-200 mt-0.5 opacity-85',
              sizeConfig.tagline
            )}
          >
            SINCE 2026
          </span>
        )}
      </div>
    </div>
  );
}
