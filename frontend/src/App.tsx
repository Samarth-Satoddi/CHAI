import React, { useState, useEffect } from 'react';
import { ChaiCover } from './components/chai-cover';
import { ChatWorkspace } from './components/chat-workspace';
import { AuthForm } from './components/auth-form';
import { AssistantSpeech } from './components/assistant-speech';
import { useSession, type UserSession } from './lib/auth-client';
import { handleSupabaseRedirectSession, subscribeToSupabaseAuth } from './lib/supabase';
import {
  normalizeAccent,
  updateDocumentFavicon,
  syncLogoCssVariables,
  getLogoPalette,
  ACCENT_PALETTES,
} from './lib/chai-branding';

export default function App() {
  const [currentPath, setCurrentPath] = useState<string>(() => {
    return typeof window !== 'undefined' ? window.location.pathname || '/' : '/';
  });

  const { data: sessionData } = useSession();
  const [currentUser, setCurrentUser] = useState<UserSession | null>(sessionData?.user || null);

  useEffect(() => {
    // Detect Supabase OAuth redirect session
    handleSupabaseRedirectSession().then((sbUser) => {
      if (sbUser) {
        localStorage.setItem('chai_auth_user', JSON.stringify(sbUser));
        setCurrentUser(sbUser);
        if (window.location.hash.includes('access_token')) {
          window.history.replaceState({}, '', window.location.pathname);
        }
      }
    });

    // Real-time listener for OAuth logins
    const unsubscribe = subscribeToSupabaseAuth((sbUser) => {
      if (sbUser) {
        localStorage.setItem('chai_auth_user', JSON.stringify(sbUser));
        setCurrentUser(sbUser);
      }
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (sessionData?.user) {
      setCurrentUser(sessionData.user);
    }
  }, [sessionData]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const getTheme = () => localStorage.getItem('chai-theme') || 'dark';
    const applyTheme = (theme: string) => {
      const root = document.documentElement;
      const isDark = theme !== 'light';
      root.classList.toggle('dark', isDark);
      root.classList.toggle('light', !isDark);
      return isDark;
    };

    const isDark = applyTheme(getTheme());

    // Initialize accent color
    const savedAccent = normalizeAccent(localStorage.getItem('chai-accent'));
    const entry = ACCENT_PALETTES[savedAccent] || ACCENT_PALETTES.violet;
    document.documentElement.style.setProperty('--profile-accent-color', entry.swatch);

    // Sync logo CSS variables & browser favicon
    const palette = getLogoPalette(savedAccent, isDark);
    syncLogoCssVariables(palette);
    updateDocumentFavicon(savedAccent, isDark);

    const handleThemeChange = (e: Event) => {
      const custom = e as CustomEvent<string>;
      const activeTheme = custom.detail || getTheme();
      const nextIsDark = applyTheme(activeTheme);
      const currentAccent = normalizeAccent(localStorage.getItem('chai-accent'));
      const nextPalette = getLogoPalette(currentAccent, nextIsDark);
      syncLogoCssVariables(nextPalette);
      updateDocumentFavicon(currentAccent, nextIsDark);
    };

    const handleAccentChange = (e: Event) => {
      const custom = e as CustomEvent<string>;
      const nextAccent = normalizeAccent(custom.detail);
      const nextIsDark = document.documentElement.classList.contains('dark');
      const nextPalette = getLogoPalette(nextAccent, nextIsDark);
      syncLogoCssVariables(nextPalette);
      updateDocumentFavicon(nextAccent, nextIsDark);
    };

    window.addEventListener('chai-theme-change', handleThemeChange);
    window.addEventListener('chai-accent-change', handleAccentChange);
    return () => {
      window.removeEventListener('chai-theme-change', handleThemeChange);
      window.removeEventListener('chai-accent-change', handleAccentChange);
    };
  }, []);

  useEffect(() => {
    const handleNav = (e: Event) => {
      const custom = e as CustomEvent<string>;
      const nextPath = custom.detail || window.location.pathname || '/';
      setCurrentPath(nextPath);
    };

    const handleAuthChange = (e: Event) => {
      const custom = e as CustomEvent<UserSession | null>;
      setCurrentUser(custom.detail || null);
      if (!custom.detail) {
        // Logged out -> go to cover page
        window.history.pushState({}, '', '/');
        setCurrentPath('/');
      }
    };

    window.addEventListener('chai-navigate', handleNav);
    window.addEventListener('popstate', handleNav);
    window.addEventListener('chai-auth-change', handleAuthChange);

    return () => {
      window.removeEventListener('chai-navigate', handleNav);
      window.removeEventListener('popstate', handleNav);
      window.removeEventListener('chai-auth-change', handleAuthChange);
    };
  }, []);

  const navigateTo = (path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
    window.dispatchEvent(new CustomEvent('chai-navigate', { detail: path }));
  };

  // Dedicated Route: /sign-in
  if (currentPath === '/sign-in' || currentPath === '/login') {
    return (
      <main className="min-h-screen flex items-center justify-center p-4 bg-background">
        <AuthForm
          mode="sign-in"
          variant="page"
          onBack={() => navigateTo('/')}
          onModeChange={(mode) => navigateTo(mode === 'sign-up' ? '/sign-up' : '/sign-in')}
        />
      </main>
    );
  }

  // Dedicated Route: /sign-up
  if (currentPath === '/sign-up' || currentPath === '/register') {
    return (
      <main className="min-h-screen flex items-center justify-center p-4 bg-background">
        <AuthForm
          mode="sign-up"
          variant="page"
          onBack={() => navigateTo('/')}
          onModeChange={(mode) => navigateTo(mode === 'sign-up' ? '/sign-up' : '/sign-in')}
        />
      </main>
    );
  }

  // Dedicated Route: /speech, /assistant, or /assistant-speech
  if (
    currentPath === '/speech' ||
    currentPath === '/assistant' ||
    currentPath === '/assistant-speech' ||
    currentPath === '/voice'
  ) {
    return (
      <main className="min-h-screen bg-[#030408]">
        <AssistantSpeech onBack={() => navigateTo(currentUser ? '/workspace' : '/guest')} />
      </main>
    );
  }

  // Workspace Route: /workspace or /guest
  if (currentPath.includes('workspace') || currentPath.includes('guest')) {
    const activeUser = currentUser || (currentPath.includes('guest') ? {
      id: 'guest_session',
      name: 'Guest Operator',
      email: 'guest@chai.ai',
      provider: 'guest' as const,
    } : null);

    return (
      <div className="min-h-screen bg-background text-foreground">
        <ChatWorkspace user={activeUser} />
      </div>
    );
  }

  // Root / Cover Landing Page
  return (
    <div className="min-h-screen bg-background text-foreground">
      <ChaiCover />
    </div>
  );
}
