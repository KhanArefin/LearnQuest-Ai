/**
 * Authentication context - Supabase Auth.
 *
 * OWNER: Member 3. See plan.md §8.2.
 *
 * Handles Supabase session, token refresh, and synchronization with backend public.users.
 * When Supabase keys are not configured, runs in DEV MODE and provides a developer user.
 */
import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { setTokenProvider, setUnauthorizedHandler } from '../api/client';
import { syncUser } from '../api/users';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

const AuthContext = createContext(null);

const DEV_USER = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'dev@learnquest.local',
  full_name: 'Dev User',
  role: 'admin',
  avatar_url: null,
};

function generateDevUserId(email) {
  if (email === 'dev@learnquest.local' || email === 'admin@learnquest.ai') {
    return '00000000-0000-0000-0000-000000000001';
  }
  let hash = 0;
  for (let i = 0; i < email.length; i++) {
    hash = ((hash << 5) - hash) + email.charCodeAt(i);
    hash |= 0;
  }
  const hex = Math.abs(hash).toString(16).padStart(8, '0');
  return `00000000-0000-4000-8000-${hex.padEnd(12, '0').slice(0, 12)}`;
}

function toAppUser(session) {
  if (!session?.user) return null;
  const { id, email, user_metadata: meta = {} } = session.user;
  return {
    id,
    email,
    full_name: meta.full_name ?? meta.name ?? email,
    avatar_url: meta.avatar_url ?? meta.picture ?? null,
    role: meta.role ?? 'student',
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Sync user with backend database to get real role and ensure public.users exists
  const syncWithBackend = async (baseUser) => {
    try {
      const res = await syncUser();
      if (res?.data?.user) {
        setUser((prev) => ({
          ...(prev || baseUser),
          ...res.data.user,
        }));
      }
    } catch (err) {
      console.warn('Backend user sync failed, falling back to session user:', err);
    }
  };

  useEffect(() => {
    if (!isSupabaseConfigured) {
      const stored = localStorage.getItem('learnquest_dev_user');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setTokenProvider(async () => `dev:${parsed.id}:${parsed.email}`);
          setUser(parsed);
        } catch {
          setTokenProvider(async () => null);
          setUser(null);
        }
      } else {
        setTokenProvider(async () => null);
        setUser(null);
      }
      setLoading(false);
      return undefined;
    }

    // The interceptor in api/client.js pulls the token from here on every request.
    setTokenProvider(async () => {
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token ?? null;
    });

    supabase.auth.getSession().then(({ data }) => {
      const appUser = toAppUser(data.session);
      setUser(appUser);
      setLoading(false);
      if (appUser) {
        syncWithBackend(appUser);
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const appUser = toAppUser(session);
      setUser(appUser);
      if (appUser) {
        syncWithBackend(appUser);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === 'admin',
      devMode: !isSupabaseConfigured,

      async login(email, password) {
        setError(null);
        if (!isSupabaseConfigured) {
          const devId = generateDevUserId(email);
          const devAccount = {
            id: devId,
            email,
            full_name: email.split('@')[0].replace('.', ' '),
            role: email.includes('admin') ? 'admin' : 'student',
            avatar_url: null,
          };
          localStorage.setItem('learnquest_dev_user', JSON.stringify(devAccount));
          setTokenProvider(async () => `dev:${devAccount.id}:${devAccount.email}`);
          setUser(devAccount);
          await syncWithBackend(devAccount);
          return null;
        }
        const { data, error: err } = await supabase.auth.signInWithPassword({ email, password });
        if (err) {
          setError(err.message);
          return err;
        }
        const appUser = toAppUser(data.session);
        setUser(appUser);
        if (appUser) await syncWithBackend(appUser);
        return null;
      },

      async loginWithGoogle() {
        setError(null);
        if (!isSupabaseConfigured) {
          const devAccount = { ...DEV_USER };
          localStorage.setItem('learnquest_dev_user', JSON.stringify(devAccount));
          setTokenProvider(async () => `dev:${devAccount.id}:${devAccount.email}`);
          setUser(devAccount);
          return null;
        }
        const { error: err } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: {
            redirectTo: `${window.location.origin}/dashboard`,
            queryParams: {
              access_type: 'offline',
              prompt: 'select_account',
            },
          },
        });
        if (err) {
          setError(err.message);
          return err;
        }
        return null;
      },

      async register(email, password, fullName) {
        setError(null);
        if (!isSupabaseConfigured) {
          const devId = generateDevUserId(email);
          const devAccount = {
            id: devId,
            email,
            full_name: fullName || email.split('@')[0],
            role: 'student',
            avatar_url: null,
          };
          localStorage.setItem('learnquest_dev_user', JSON.stringify(devAccount));
          setTokenProvider(async () => `dev:${devAccount.id}:${devAccount.email}`);
          setUser(devAccount);
          await syncWithBackend(devAccount);
          return null;
        }
        const { data, error: err } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: fullName } },
        });
        if (err) {
          setError(err.message);
          return err;
        }
        if (data?.session) {
          const appUser = toAppUser(data.session);
          setUser(appUser);
          if (appUser) await syncWithBackend(appUser);
        } else if (data?.user) {
          const { data: signData } = await supabase.auth.signInWithPassword({ email, password });
          if (signData?.session) {
            const appUser = toAppUser(signData.session);
            setUser(appUser);
            if (appUser) await syncWithBackend(appUser);
          }
        }
        return null;
      },

      async resetPassword(email) {
        setError(null);
        if (!isSupabaseConfigured) {
          return null;
        }
        const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/login`,
        });
        if (err) {
          setError(err.message);
          return err;
        }
        return null;
      },

      async logout() {
        if (isSupabaseConfigured) await supabase.auth.signOut();
        localStorage.removeItem('learnquest_dev_user');
        setTokenProvider(async () => null);
        setUser(null);
      },
    }),
    [user, loading, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
