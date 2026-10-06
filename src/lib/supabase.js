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

const dummyUrl = 'https://placeholder-project.supabase.co';
const dummyAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBsYWNlaG9sZGVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE2MDAwMDAwMDAsImV4cCI6MjAwMDAwMDAwMH0.placeholder';

export const supabase = createClient(
  supabaseUrl || dummyUrl,
  supabaseAnonKey || dummyAnonKey,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
);
