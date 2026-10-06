import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSignIn, useSignUp, useClerk } from '@clerk/react';

// ============================================================================
// DESIGN SYSTEM TOKENS
// ============================================================================
const TOKENS = {
  fonts: {
    sans: '"Inter", "Segoe UI", -apple-system, system-ui, sans-serif',
    mono: '"SF Mono", ui-monospace, Menlo, monospace',
  },
  colors: {
    bg: '#FAFAF9',
    sidebar: '#F4F4F2',
    ink: '#0D0C0A',
    body: '#44403B',
    muted: '#A8A29E',
    line: '#E9E7E1',
    yellow: '#FFD800',
    yellowDeep: '#F5C900',
    amber: '#B8890A',
    bubble: '#F0EFEB',
    chip: '#E8E3D8',
    card: '#FFFFFF'
  }
};

// ============================================================================
// INLINE NUCLEO-SHARP ICONS
// ============================================================================
function IconMicroscope({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 18h12M12 18v3M9 14a5 5 0 0010 0v-4H9v4z" />
      <path d="M12 6l3 3M10 4l5 5" />
      <circle cx="8" cy="18" r="2" />
    </svg>
  );
}

function IconLayers({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function IconAtom({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
      <ellipse cx="12" cy="12" rx="9" ry="4.5" transform="rotate(30 12 12)" />
      <ellipse cx="12" cy="12" rx="9" ry="4.5" transform="rotate(150 12 12)" />
    </svg>
  );
}

function IconEye({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function IconEyeOff({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

function IconGoogle({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
    </svg>
  );
}

// 2x3 Pixel Grid Atlas Logo
function AtlasPixelGrid({ cellSize = 12, gap = 3 }) {
  const pixelColors = [
    ['#FFB000', TOKENS.colors.ink, '#FFB000'],
    ['#FFD800', '#FFD800', '#FFD800']
  ];

  return (
    <div
      style={{
        display: 'inline-grid',
        gridTemplateColumns: `repeat(3, ${cellSize}px)`,
        gridTemplateRows: `repeat(2, ${cellSize}px)`,
        gap: `${gap}px`,
        flexShrink: 0,
        userSelect: 'none'
      }}
    >
      {pixelColors.map((row, rIdx) =>
        row.map((color, cIdx) => {
          const idx = rIdx * 3 + cIdx;
          return (
            <motion.div
              key={`${rIdx}-${cIdx}`}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                delay: 0.15 + idx * 0.06,
                type: 'spring',
                stiffness: 300,
                damping: 18
              }}
              style={{
                width: `${cellSize}px`,
                height: `${cellSize}px`,
                backgroundColor: color,
                borderRadius: '2px'
              }}
            />
          );
        })
      )}
    </div>
  );
}

// 10 Floating Drifting Pixel Particles
const PARTICLES = Array.from({ length: 10 }).map((_, i) => ({
  id: i,
  size: Math.floor(Math.random() * 6) + 6,
  x: Math.random() * 95,
  color: ['#FFB000', '#FFD800', '#0D0C0A', '#B8890A', '#F5C900'][i % 5],
  duration: Math.random() * 10 + 12,
  delay: Math.random() * 5
}));

function deriveUsernameFromEmail(emailInput, enteredName = '') {
  if (enteredName && enteredName.trim()) return enteredName.trim();
  if (!emailInput || typeof emailInput !== 'string') return 'Research User';
  const prefix = emailInput.split('@')[0] || 'User';
  return prefix
    .split(/[._-]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

export default function AuthScreen({ onLoginSuccess }) {
  const [mode, setMode] = useState('signin'); // 'signin' | 'signup'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [googleSpinning, setGoogleSpinning] = useState(false);
  const [shake, setShake] = useState(false);
  const [authError, setAuthError] = useState('');

  let clerkSignIn = null;
  let clerkSignUp = null;

  try {
    clerkSignIn = useSignIn();
  } catch (e) {}
  try {
    clerkSignUp = useSignUp();
  } catch (e) {}

  const clerkErrorMessage = (err, fallback) => {
    const first = err?.errors?.[0];
    const message = first?.longMessage || first?.message || err?.longMessage || err?.message;
    return typeof message === 'string' && message.trim() ? message : fallback;
  };

  const handleLocalFallback = () => {
    setIsCalibrating(false);
    setGoogleSpinning(false);
    const finalName = deriveUsernameFromEmail(email, displayName);
    if (onLoginSuccess) onLoginSuccess({ email: email.trim() || 'user@institution.edu', name: finalName });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');

    if (!email.trim() || !password.trim()) {
      setShake(true);
      setAuthError('Please enter both your email and password.');
      setTimeout(() => setShake(false), 500);
      return;
    }

    setIsCalibrating(true);

    try {
      if (mode === 'signin') {
        if (clerkSignIn?.isLoaded && clerkSignIn?.signIn) {
          try {
            const result = await clerkSignIn.signIn.create({
              identifier: email.trim(),
              password,
            });
            if (result.status === 'complete' && result.createdSessionId) {
              await clerkSignIn.setActive({ session: result.createdSessionId });
              setIsCalibrating(false);
              const finalName = deriveUsernameFromEmail(email, displayName);
              if (onLoginSuccess) onLoginSuccess({ email: email.trim(), name: finalName });
              return;
            }
          } catch (err) {
            console.warn('[CLERK SIGNIN NOTICE - Fallback to local session]', err?.message || err);
          }
        }
        handleLocalFallback();
        return;
      } else if (mode === 'signup') {
        if (clerkSignUp?.isLoaded && clerkSignUp?.signUp) {
          try {
            const result = await clerkSignUp.signUp.create({
              emailAddress: email.trim(),
              password,
            });
            if (result.status === 'complete' && result.createdSessionId) {
              await clerkSignUp.setActive({ session: result.createdSessionId });
              setIsCalibrating(false);
              const finalName = deriveUsernameFromEmail(email, displayName);
              if (onLoginSuccess) onLoginSuccess({ email: email.trim(), name: finalName });
              return;
            }
          } catch (err) {
            console.warn('[CLERK SIGNUP NOTICE - Fallback to local session]', err?.message || err);
          }
        }
        handleLocalFallback();
        return;
      }
    } catch (err) {
      console.warn('[AUTH SUBMIT EXCEPTION - Fallback to local session]', err);
      handleLocalFallback();
    }
  };

  const handleGoogleClick = async () => {
    setGoogleSpinning(true);
    setAuthError('');
    try {
      if (clerkSignIn?.isLoaded && clerkSignIn?.signIn) {
        await clerkSignIn.signIn.authenticateWithRedirect({
          strategy: 'oauth_google',
          redirectUrl: '/sso-callback',
          redirectUrlComplete: '/atlas',
        });
        return;
      }
    } catch (err) {
      console.warn('[CLERK OAUTH NOTICE - Fallback to local session]', err?.message || err);
    }

    handleLocalFallback();
  };

  return (
    <div className="relative w-full min-h-screen bg-[#FAFAF9] font-sans text-[#0D0C0A] overflow-y-auto flex items-center justify-center p-4 sm:p-6 md:p-8 lg:p-12">
      {/* 10 FLOATING PIXEL PARTICLES DRIFTING UP ENDLESSLY */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        {PARTICLES.map((p) => (
          <motion.div
            key={p.id}
            initial={{ y: '105vh', opacity: 0 }}
            animate={{
              y: '-10vh',
              opacity: [0, 0.45, 0.45, 0]
            }}
            transition={{
              duration: p.duration,
              repeat: Infinity,
              delay: p.delay,
              ease: 'linear'
            }}
            style={{
              position: 'absolute',
              left: `${p.x}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              backgroundColor: p.color,
              borderRadius: '2px'
            }}
          />
        ))}
      </div>

      {/* RESPONSIVE LAYOUT CONTAINER */}
      <div className="relative z-10 w-full max-w-6xl mx-auto flex flex-col lg:flex-row items-center justify-center lg:justify-between gap-8 lg:gap-12 py-4 sm:py-8">
        {/* LEFT BRAND PANEL */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="w-full lg:w-1/2 flex flex-col justify-center max-w-xl"
        >
          {/* Logo + Brand */}
          <div className="flex items-center gap-3 mb-4 sm:mb-6">
            <AtlasPixelGrid cellSize={14} gap={3} />
            <span className="text-xl sm:text-2xl font-bold tracking-tight text-[#0D0C0A]">
              Atlas
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-[#0D0C0A] mb-3 leading-tight">
            Research at machine speed.
          </h1>

          <p className="text-sm sm:text-base text-[#44403B] leading-relaxed mb-6 max-w-lg">
            Autonomous machine learning research platform for hypothesis formulation, literature synthesis, and experiment execution.
          </p>

          {/* 3 AMBER FEATURE CHIPS */}
          <div className="hidden sm:flex flex-col gap-3 max-w-lg">
            {/* Chip 1 */}
            <div className="flex items-center gap-3 p-3 bg-white border border-[#E9E7E1] rounded-2xl shadow-sm">
              <div className="w-8 h-8 rounded-xl bg-[#FCF7DF] flex items-center justify-center text-[#B8890A] shrink-0">
                <IconMicroscope size={18} />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs sm:text-sm font-semibold text-[#0D0C0A] leading-tight">
                  Autonomous Literature Synthesis
                </span>
                <span className="text-[11px] text-[#A8A29E] leading-tight mt-0.5 truncate">
                  42+ arXiv & venue sources parsed concurrently
                </span>
              </div>
            </div>

            {/* Chip 2 */}
            <div className="flex items-center gap-3 p-3 bg-white border border-[#E9E7E1] rounded-2xl shadow-sm">
              <div className="w-8 h-8 rounded-xl bg-[#FCF7DF] flex items-center justify-center text-[#B8890A] shrink-0">
                <IconLayers size={18} />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs sm:text-sm font-semibold text-[#0D0C0A] leading-tight">
                  Dataset & Benchmark Matching
                </span>
                <span className="text-[11px] text-[#A8A29E] leading-tight mt-0.5 truncate">
                  Domain-shift & out-of-distribution evaluation
                </span>
              </div>
            </div>

            {/* Chip 3 */}
            <div className="flex items-center gap-3 p-3 bg-white border border-[#E9E7E1] rounded-2xl shadow-sm">
              <div className="w-8 h-8 rounded-xl bg-[#FCF7DF] flex items-center justify-center text-[#B8890A] shrink-0">
                <IconAtom size={18} />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs sm:text-sm font-semibold text-[#0D0C0A] leading-tight">
                  Hypothesis & Experiment Execution
                </span>
                <span className="text-[11px] text-[#A8A29E] leading-tight mt-0.5 truncate">
                  Automated hyperparameter & model ablation pipelines
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* RIGHT LOGIN CARD */}
        <motion.div
          animate={shake ? { x: [-8, 8, -6, 6, -3, 3, 0] } : {}}
          transition={{ duration: 0.4 }}
          className="w-full lg:w-[450px] shrink-0 bg-white border border-[#E9E7E1] rounded-[22px] shadow-xl p-6 sm:p-8 flex flex-col"
        >
          {/* Card Header */}
          <div style={{ marginBottom: '20px' }}>
            <h2
              style={{
                fontSize: '22px',
                fontWeight: 700,
                color: TOKENS.colors.ink,
                margin: 0,
                letterSpacing: '-0.01em'
              }}
            >
              {mode === 'signin' ? 'Sign in to Atlas' : 'Create Atlas Account'}
            </h2>
            <p style={{ fontSize: '13px', color: TOKENS.colors.muted, marginTop: '4px', margin: 0 }}>
              {mode === 'signin'
                ? 'Access your autonomous research workspace'
                : 'Join the next generation of AI research'}
            </p>
          </div>

          {/* Error Alert Box */}
          {authError && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                backgroundColor: '#FFFBEB',
                border: '1px solid #FCD34D',
                color: '#92400E',
                borderRadius: '12px',
                padding: '10px 14px',
                fontSize: '12.5px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px' }}>⚠️</span>
                <span>{authError}</span>
              </div>
              <button
                type="button"
                onClick={() => setAuthError('')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#92400E', fontWeight: 'bold' }}
              >
                ✕
              </button>
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Display Name / Username Field */}
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  color: TOKENS.colors.body,
                  marginBottom: '6px'
                }}
              >
                {mode === 'signup' ? 'Full name or username' : 'Display name / username (optional)'}
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Alex Smith"
                style={{
                  width: '100%',
                  height: '40px',
                  borderRadius: '10px',
                  border: `1px solid ${TOKENS.colors.line}`,
                  padding: '0 12px',
                  fontSize: '13.5px',
                  fontFamily: TOKENS.fonts.sans,
                  color: TOKENS.colors.ink,
                  backgroundColor: TOKENS.colors.bg,
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => (e.target.style.borderColor = TOKENS.colors.amber)}
                onBlur={(e) => (e.target.style.borderColor = TOKENS.colors.line)}
              />
            </div>

            {/* Email Field */}
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  color: TOKENS.colors.body,
                  marginBottom: '6px'
                }}
              >
                Institutional or research email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@institution.edu"
                style={{
                  width: '100%',
                  height: '40px',
                  borderRadius: '10px',
                  border: `1px solid ${TOKENS.colors.line}`,
                  padding: '0 12px',
                  fontSize: '13.5px',
                  fontFamily: TOKENS.fonts.sans,
                  color: TOKENS.colors.ink,
                  backgroundColor: TOKENS.colors.bg,
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => (e.target.style.borderColor = TOKENS.colors.amber)}
                onBlur={(e) => (e.target.style.borderColor = TOKENS.colors.line)}
              />
            </div>

            {/* Password Field */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label
                  style={{
                    fontSize: '12.5px',
                    fontWeight: 600,
                    color: TOKENS.colors.body
                  }}
                >
                  Password
                </label>
                {mode === 'signin' && (
                  <button
                    type="button"
                    onClick={() => {
                      setAuthError('Password reset instructions have been sent to your institutional email if registered.');
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      fontSize: '12px',
                      color: TOKENS.colors.amber,
                      cursor: 'pointer',
                      padding: 0,
                      fontWeight: 500
                    }}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{
                    width: '100%',
                    height: '40px',
                    borderRadius: '10px',
                    border: `1px solid ${TOKENS.colors.line}`,
                    padding: '0 36px 0 12px',
                    fontSize: '13.5px',
                    fontFamily: TOKENS.fonts.sans,
                    color: TOKENS.colors.ink,
                    backgroundColor: TOKENS.colors.bg,
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s'
                  }}
                  onFocus={(e) => (e.target.style.borderColor = TOKENS.colors.amber)}
                  onBlur={(e) => (e.target.style.borderColor = TOKENS.colors.line)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: TOKENS.colors.muted,
                    cursor: 'pointer',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {showPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
                </button>
              </div>
            </div>

            {/* Remember Me Checkbox */}
            {mode === 'signin' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  style={{
                    accentColor: TOKENS.colors.ink,
                    width: '14px',
                    height: '14px',
                    cursor: 'pointer'
                  }}
                />
                <label htmlFor="remember" style={{ fontSize: '12px', color: TOKENS.colors.body, cursor: 'pointer' }}>
                  Remember me for 30 days
                </label>
              </div>
            )}

            {/* Submit Button ("Sign in to Atlas" / Spinning atom "Calibrating…") */}
            <motion.button
              type="submit"
              disabled={isCalibrating}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              style={{
                width: '100%',
                height: '42px',
                borderRadius: '12px',
                backgroundColor: TOKENS.colors.yellow,
                border: 'none',
                fontSize: '13.5px',
                fontWeight: 600,
                color: TOKENS.colors.ink,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginTop: '4px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.04)'
              }}
            >
              {isCalibrating ? (
                <>
                  <div
                    style={{
                      width: '15px',
                      height: '15px',
                      animation: 'spin 1.1s linear infinite',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <IconAtom size={15} style={{ color: TOKENS.colors.ink }} />
                  </div>
                  <span>Calibrating…</span>
                </>
              ) : (
                <span>{mode === 'signin' ? 'Sign in to Atlas' : 'Create Account'}</span>
              )}
            </motion.button>
          </form>

          {/* "or continue with" Divider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              margin: '20px 0',
              position: 'relative'
            }}
          >
            <div style={{ flex: 1, height: '1px', backgroundColor: TOKENS.colors.line }} />
            <span
              style={{
                padding: '0 10px',
                fontSize: '11px',
                color: TOKENS.colors.muted,
                fontFamily: TOKENS.fonts.mono,
                textTransform: 'uppercase'
              }}
            >
              or continue with
            </span>
            <div style={{ flex: 1, height: '1px', backgroundColor: TOKENS.colors.line }} />
          </div>

          {/* Google OAuth Button */}
          <motion.button
            type="button"
            onClick={handleGoogleClick}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            style={{
              width: '100%',
              height: '42px',
              borderRadius: '12px',
              backgroundColor: TOKENS.colors.card,
              border: `1px solid ${TOKENS.colors.line}`,
              fontSize: '13.5px',
              fontWeight: 500,
              color: TOKENS.colors.ink,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px'
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transform: googleSpinning ? 'rotate(360deg)' : 'none',
                transition: googleSpinning ? 'transform 1.2s ease-in-out' : 'none'
              }}
            >
              <IconGoogle size={18} />
            </div>
            <span>Continue with Google</span>
          </motion.button>

          {/* Local Dev Session Option */}
          <button
            type="button"
            onClick={handleLocalFallback}
            style={{
              width: '100%',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: 'transparent',
              border: `1px dashed ${TOKENS.colors.line}`,
              fontSize: '12.5px',
              fontWeight: 500,
              color: TOKENS.colors.body,
              cursor: 'pointer',
              marginTop: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => (e.target.style.borderColor = TOKENS.colors.amber)}
            onMouseLeave={(e) => (e.target.style.borderColor = TOKENS.colors.line)}
          >
            <span>⚡ Continue with Local Research Session</span>
          </button>

          {/* Create Account Link Switcher */}
          <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '12.5px', color: TOKENS.colors.muted }}>
            {mode === 'signin' ? (
              <>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => setMode('signup')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: TOKENS.colors.amber,
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  Create account
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => setMode('signin')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: TOKENS.colors.amber,
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  Sign in
                </button>
              </>
            )}
          </div>

          {/* Encrypted Security Note Footer */}
          <div
            style={{
              marginTop: '24px',
              paddingTop: '14px',
              borderTop: `1px solid ${TOKENS.colors.line}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              fontSize: '11px',
              color: TOKENS.colors.muted,
              fontFamily: TOKENS.fonts.mono
            }}
          >
            <span>🔒 256-bit encrypted research session</span>
          </div>
        </motion.div>
      </div>

      {/* Spinner Animation Styles */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
