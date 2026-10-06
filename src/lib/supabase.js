import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export function getSupabaseConfigError() {
  if (!supabaseUrl || supabaseUrl.trim() === '') {
    return 'VITE_SUPABASE_URL is not set';
  }
  if (!supabaseAnonKey || supabaseAnonKey.trim() === '') {
    return 'VITE_SUPABASE_ANON_KEY is not set';
  }
  return null;
}

const authUnavailable = async () => ({
  data: { session: null },
  error: new Error(getSupabaseConfigError() || 'Supabase authentication is unavailable.'),
});

// Keep application startup safe when deployment configuration is incomplete,
// but never fabricate a client, session, user, or login result.
export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : {
      auth: {
        getSession: authUnavailable,
        signInWithPassword: authUnavailable,
        signUp: authUnavailable,
        resetPasswordForEmail: authUnavailable,
        signInWithOAuth: authUnavailable,
        signOut: async () => ({ error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
      },
    };
