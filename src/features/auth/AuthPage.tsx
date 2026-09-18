import React, { useState, useEffect } from 'react';
import { Mail, Lock, User as UserIcon, Eye, EyeOff, CheckCircle2, Sparkles, Hexagon, ShieldCheck, ArrowRight, RefreshCw } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { BrandLogo } from '../../components/common/BrandLogo';
import { useAuthStore } from '../../app/store/useAuthStore';
import { authService } from '../../services/auth/authService';

type AuthMode = 'login' | 'signup' | 'otp' | 'forgot' | 'reset';

export const AuthPage: React.FC = () => {
  const { setViewMode } = useWorkspaceStore();
  const { setUser } = useAuthStore();

  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [otp, setOtp] = useState('');
  const [otpPurpose, setOtpPurpose] = useState<'registration' | 'password_reset'>('registration');

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Resend OTP Cooldown Timer
  const [cooldown, setCooldown] = useState<number>(0);

  useEffect(() => {
    let timer: any;
    if (cooldown > 0) {
      timer = setInterval(() => {
        setCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [cooldown]);

  const startCooldown = (seconds: number = 60) => {
    setCooldown(seconds);
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.signup(name || email.split('@')[0], email, password, confirmPassword);
      setSuccessMessage(res.message);
      setOtpPurpose('registration');
      setMode('otp');
      startCooldown(60);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsLoading(true);

    try {
      const u = await authService.login(email, password);
      setUser(u);
      setViewMode('dashboard');
    } catch (err: any) {
      if (err.code === 'AUTH_UNVERIFIED_EMAIL') {
        setError('Email not verified. A verification code has been sent to your email.');
        setOtpPurpose('registration');
        setMode('otp');
        startCooldown(60);
      } else {
        setError(err.message || 'Login failed. Please check your credentials.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!otp || otp.length !== 6) {
      setError('Please enter a valid 6-digit security code.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.verifyOtp(email, otp, otpPurpose);
      if ('access_token' in res && res.access_token) {
        setUser({
          id: res.user.id,
          name: res.user.name,
          email: res.user.email,
          token: res.access_token,
          created_at: res.user.created_at
        });
        setViewMode('dashboard');
      } else {
        setSuccessMessage(res.message || 'Code verified successfully.');
        if (otpPurpose === 'password_reset') {
          setMode('reset');
        } else {
          setMode('login');
        }
      }
    } catch (err: any) {
      setError(err.message || 'Code verification failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (cooldown > 0) return;
    setError(null);
    setSuccessMessage(null);
    setIsLoading(true);

    try {
      const res = await authService.resendOtp(email, otpPurpose);
      setSuccessMessage(res.message);
      startCooldown(60);
    } catch (err: any) {
      setError(err.message || 'Failed to resend code.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!email) {
      setError('Please enter your email address.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.forgotPassword(email);
      setSuccessMessage(res.message);
      setOtpPurpose('password_reset');
      setMode('otp');
      startCooldown(60);
    } catch (err: any) {
      setError(err.message || 'Request failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.resetPassword(email, otp, password, confirmPassword);
      setSuccessMessage(res.message);
      setMode('login');
      setPassword('');
      setConfirmPassword('');
      setOtp('');
    } catch (err: any) {
      setError(err.message || 'Password reset failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError(null);
    setSuccessMessage(null);
    setIsLoading(true);
    try {
      const u = await authService.googleLogin();
      setUser(u);
      setViewMode('dashboard');
    } catch (err: any) {
      setError(err.message || 'Google sign-in failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full h-full min-h-screen flex bg-slate-950 text-slate-100 font-sans select-none overflow-hidden">
      
      {/* RIGHT HALF - Dark AI CAD Preview & Branding */}
      <div className="w-1/2 relative bg-[#090C15] flex flex-col justify-between p-12 overflow-hidden border-l border-slate-800/60">
        
        {/* Subdued CAD Grid Background Pattern */}
        <div 
          className="absolute inset-0 opacity-20 pointer-events-none" 
          style={{
            backgroundImage: `
              linear-gradient(to right, #334155 1px, transparent 1px),
              linear-gradient(to bottom, #334155 1px, transparent 1px)
            `,
            backgroundSize: '32px 32px'
          }}
        />

        {/* Top Header Badge */}
        <div className="relative z-10 space-y-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs font-medium text-slate-300 backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 ml-1.5" />
            <span>AI-Powered CAD & Engineering Design</span>
          </div>

          <h1 className="text-4xl lg:text-5xl font-black text-white leading-tight tracking-tight">
            Design manufacturing-ready parts{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-indigo-300 to-purple-400">
              without complex CAD software.
            </span>
          </h1>

          <p className="text-base text-slate-400 max-w-lg leading-relaxed">
            Join engineers and manufacturers using AI to generate, edit, and export 3D models and technical drawings in minutes.
          </p>

          <ul className="space-y-3 pt-2 text-sm text-slate-300 font-medium">
            <li className="flex items-center space-x-3">
              <div className="w-5 h-5 rounded-full bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center ml-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <span>Full 3D models + 2D DXF engineering drawings</span>
            </li>
            <li className="flex items-center space-x-3">
              <div className="w-5 h-5 rounded-full bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center ml-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <span>Export STL, STEP, OBJ, DXF & G-Code formats</span>
            </li>
            <li className="flex items-center space-x-3">
              <div className="w-5 h-5 rounded-full bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center ml-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <span>Secure, dedicated desktop workspace</span>
            </li>
          </ul>
        </div>

        {/* Bottom Interactive CAD Live Preview Card */}
        <div className="relative z-10 bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-xl max-w-md space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold tracking-wider text-slate-400 uppercase">
              Live Preview
            </span>
            <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-800/60 text-[10px] font-mono font-bold text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse ml-1" />
              <span>Generated</span>
            </span>
          </div>

          <div className="h-32 flex items-center justify-center bg-slate-950/80 rounded-xl border border-slate-800/80 p-4">
            <svg viewBox="0 0 200 100" className="w-full h-full stroke-indigo-400 fill-none" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round">
              <path d="M 40 80 L 40 40 Q 40 20 60 20 L 160 20" className="opacity-90" />
              <circle cx="40" cy="80" r="8" className="fill-indigo-600 stroke-indigo-300" strokeWidth="3" />
              <circle cx="160" cy="20" r="8" className="fill-indigo-600 stroke-indigo-300" strokeWidth="3" />
            </svg>
          </div>

          <div className="flex items-center space-x-2 text-[11px] font-mono">
            <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 ml-1">
              Ø50mm dia
            </span>
            <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 ml-1">
              5mm wall
            </span>
            <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
              124,532 tris
            </span>
          </div>
        </div>

      </div>

      {/* LEFT HALF - Clean Light Theme Auth Form */}
      <div className="w-1/2 bg-[#F8FAFC] text-slate-900 flex flex-col justify-between p-12 overflow-y-auto">
        
        {/* Top Header Logo */}
        <div className="flex justify-center pt-4">
          <div 
            onClick={() => setViewMode('auth')}
            className="flex items-center space-x-2 cursor-pointer group"
          >
            <BrandLogo size="lg" />
          </div>
        </div>

        {/* Main Form Container */}
        <div className="w-full max-w-sm mx-auto space-y-6 py-8">
          
          {/* Tab Control for Login / Signup */}
          {(mode === 'login' || mode === 'signup') && (
            <div className="bg-slate-200/80 p-1 rounded-xl flex text-xs font-semibold">
              <button
                type="button"
                onClick={() => { setMode('login'); setError(null); setSuccessMessage(null); }}
                className={`flex-1 py-2 rounded-lg transition-all ${
                  mode === 'login' 
                    ? 'bg-white text-slate-900 shadow-sm font-bold' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Login
              </button>
              <button
                type="button"
                onClick={() => { setMode('signup'); setError(null); setSuccessMessage(null); }}
                className={`flex-1 py-2 rounded-lg transition-all ${
                  mode === 'signup' 
                    ? 'bg-white text-slate-900 shadow-sm font-bold' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Create Account
              </button>
            </div>
          )}

          {/* Back button for secondary views */}
          {(mode === 'otp' || mode === 'forgot' || mode === 'reset') && (
            <button
              type="button"
              onClick={() => { setMode('login'); setError(null); setSuccessMessage(null); }}
              className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
            >
              <ArrowRight className="w-4 h-4 ml-1" />
              <span>Back to Login</span>
            </button>
          )}

          {/* Dynamic Headings */}
          <div className="space-y-1">
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              {mode === 'login' && 'Welcome back'}
              {mode === 'signup' && 'Create your account'}
              {mode === 'otp' && 'Verify security code'}
              {mode === 'forgot' && 'Forgot your password?'}
              {mode === 'reset' && 'Reset your password'}
            </h2>
            <p className="text-xs text-slate-500">
              {mode === 'login' && 'Sign in to access your design and manufacturing projects.'}
              {mode === 'signup' && 'Start generating and editing engineering drawings with AI.'}
              {mode === 'otp' && `Enter the 6-digit code sent to ${email}`}
              {mode === 'forgot' && 'Enter your email to receive a password reset code.'}
              {mode === 'reset' && 'Enter your new password below.'}
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs flex items-start space-x-2">
              <div className="flex-1">{error}</div>
            </div>
          )}

          {/* Success Banner */}
          {successMessage && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0 ml-1" />
              <div className="flex-1 font-medium">{successMessage}</div>
            </div>
          )}

          {/* LOGIN FORM */}
          {mode === 'login' && (
            <>
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Email Address</label>
                <div className="relative flex items-center">
                  <Mail className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type="email"
                    required
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pr-9 pl-3 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Password</label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pr-9 pl-9 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute left-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center space-x-2 text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 ml-1.5"
                  />
                  <span>Remember me</span>
                </label>
                <button 
                  type="button" 
                  onClick={() => { setMode('forgot'); setError(null); setSuccessMessage(null); }}
                  className="font-medium text-indigo-600 hover:underline"
                >
                  Forgot your password?
                </button>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center space-x-2"
              >
                <span>{isLoading ? 'Signing in…' : 'Sign In'}</span>
              </button>
            </form>

            {/* Google Login Divider */}
            <div className="relative flex items-center py-1">
              <div className="flex-1 border-t border-slate-200" />
              <span className="px-3 text-[10px] text-slate-400 font-medium">or continue with</span>
              <div className="flex-1 border-t border-slate-200" />
            </div>

            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={isLoading}
              id="google-login-btn"
              className="w-full flex items-center justify-center space-x-2.5 py-2.5 px-4 bg-white border border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {/* Google G SVG logo */}
              <svg width="16" height="16" viewBox="0 0 48 48" className="shrink-0">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              </svg>
              <span>{isLoading ? 'Opening browser…' : 'Continue with Google'}</span>
            </button>
            </>
          )}

          {/* SIGNUP FORM */}
          {mode === 'signup' && (
            <>
            <form onSubmit={handleRegisterSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Full Name</label>
                <div className="relative flex items-center">
                  <UserIcon className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type="text"
                    required
                    placeholder="John Engineer"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full pr-9 pl-3 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Email Address</label>
                <div className="relative flex items-center">
                  <Mail className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type="email"
                    required
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pr-9 pl-3 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Password</label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pr-9 pl-9 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute left-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Confirm Password</label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pr-9 pl-9 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute left-3 text-slate-400 hover:text-slate-600"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center space-x-2"
              >
                <span>{isLoading ? 'Creating account…' : 'Create Account'}</span>
              </button>
            </form>

            {/* Google Signup Divider */}
            <div className="relative flex items-center py-1">
              <div className="flex-1 border-t border-slate-200" />
              <span className="px-3 text-[10px] text-slate-400 font-medium">or sign up with</span>
              <div className="flex-1 border-t border-slate-200" />
            </div>

            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={isLoading}
              id="google-signup-btn"
              className="w-full flex items-center justify-center space-x-2.5 py-2.5 px-4 bg-white border border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg width="16" height="16" viewBox="0 0 48 48" className="shrink-0">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              </svg>
              <span>{isLoading ? 'Opening browser…' : 'Continue with Google'}</span>
            </button>
            </>
          )}

          {/* OTP VERIFICATION FORM */}
          {mode === 'otp' && (
            <form onSubmit={handleVerifyOtpSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Security Code (6 digits)</label>
                <div className="relative flex items-center">
                  <ShieldCheck className="w-4 h-4 text-indigo-600 absolute right-3" />
                  <input
                    type="text"
                    required
                    maxLength={6}
                    placeholder="123456"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/[^0-9]/g, ''))}
                    className="w-full pr-9 pl-3 py-3 bg-white border border-slate-300 rounded-xl text-center text-lg font-mono font-bold tracking-widest text-slate-900 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading || otp.length !== 6}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center space-x-2"
              >
                <span>{isLoading ? 'Verifying…' : 'Verify Code & Continue'}</span>
              </button>

              <div className="flex items-center justify-between text-xs pt-2">
                <span className="text-slate-500">Didn't receive the code?</span>
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={cooldown > 0 || isLoading}
                  className="font-bold text-indigo-600 hover:underline disabled:text-slate-400 flex items-center space-x-1"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''} ml-1`} />
                  <span>{cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Code'}</span>
                </button>
              </div>
            </form>
          )}

          {/* FORGOT PASSWORD FORM */}
          {mode === 'forgot' && (
            <form onSubmit={handleForgotPasswordSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Account Email</label>
                <div className="relative flex items-center">
                  <Mail className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type="email"
                    required
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pr-9 pl-3 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center space-x-2"
              >
                <span>{isLoading ? 'Sending…' : 'Send Reset Code'}</span>
              </button>
            </form>
          )}

          {/* RESET PASSWORD FORM */}
          {mode === 'reset' && (
            <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">New Password</label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pr-9 pl-9 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute left-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Confirm New Password</label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-slate-400 absolute right-3" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pr-9 pl-9 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute left-3 text-slate-400 hover:text-slate-600"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center space-x-2"
              >
                <span>{isLoading ? 'Resetting…' : 'Save Password & Sign In'}</span>
              </button>
            </form>
          )}

        </div>

        {/* Bottom Footer Copyright */}
        <div className="text-center text-[11px] text-slate-400">
          © {new Date().getFullYear()} CNC Design Generator Inc. All rights reserved.
        </div>

      </div>

    </div>
  );
};
