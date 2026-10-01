import React, { useState } from 'react';
import { SignIn, SignUp } from '@clerk/react';

export default function AuthScreen() {
  const [mode, setMode] = useState('signin');
  const signUp = mode === 'signup';
  const appearance = {
    variables: { colorPrimary: '#fb923c', colorBackground: '#120c11', colorText: '#f8f4f2', colorInputBackground: '#09070a', colorInputText: '#f8f4f2', borderRadius: '0.75rem', fontFamily: 'Instrument Sans, ui-sans-serif, system-ui, sans-serif' },
    elements: { card: 'shadow-none bg-transparent', headerTitle: 'text-[#f8f4f2]', headerSubtitle: 'text-zinc-400', socialButtonsBlockButton: 'border-white/10 text-[#f8f4f2] hover:bg-white/5', formButtonPrimary: 'bg-orange-500 text-black hover:bg-orange-400', formFieldInput: 'border-white/10 bg-black/30 text-[#f8f4f2]', footerActionLink: 'text-orange-400 hover:text-orange-300' },
  };
  return <main className="min-h-screen grid place-items-center bg-[#09070a] px-4 text-[#f8f4f2] font-sans">
    <section className="w-full max-w-md rounded-3xl border border-white/10 bg-[#120c11] p-7 shadow-2xl sm:p-10">
      <div className="mb-8"><div className="mb-5 grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-orange-400 to-orange-600 text-xl font-black">✦</div>
        <p className="mb-2 text-[11px] font-bold tracking-[.18em] text-orange-400">AI SCIENTIST</p>
        <h1 className="text-3xl font-semibold tracking-tight">{signUp ? 'Create your workspace' : 'Welcome back'}</h1>
        <p className="mt-2 text-sm text-zinc-400">Your autonomous ML research workspace.</p></div>
      {signUp ? <SignUp appearance={appearance} signInUrl="/" /> : <SignIn appearance={appearance} signUpUrl="/" />}
      <button onClick={() => setMode(signUp ? 'signin' : 'signup')} className="mt-3 w-full text-center text-sm text-zinc-400 hover:text-orange-400">{signUp ? 'Already have an account? Sign in' : 'New here? Create an account'}</button>
    </section>
  </main>;
}
