import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export function getSupabaseConfigError() {
  return null;
}

const authUnavailable = async () => ({
  data: { session: null },
  error: new Error('Authentication is currently unavailable. Please try again later.'),
});

// Keep application startup safe when deployment configuration is incomplete.
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
