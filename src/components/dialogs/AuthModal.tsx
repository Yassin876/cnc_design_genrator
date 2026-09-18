import React, { useState } from 'react';
import { X, Lock, Mail, User as UserIcon, ShieldCheck, KeyRound, RefreshCw } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { authService } from '../../services/auth/authService';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, setAuthModalOpen } = useWorkspaceStore();
  const { setUser } = useAuthStore();

  const [mode, setMode] = useState<'login' | 'signup' | 'otp'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [otp, setOtp] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setInfoMessage(null);

    try {
      if (mode === 'login') {
        const u = await authService.login(email, password);
        setUser(u);
        setAuthModalOpen(false);
      } else if (mode === 'signup') {
        const res = await authService.signup(name || email.split('@')[0], email, password);
        setInfoMessage(res.message || 'Verification code sent to your email.');
        setMode('otp');
      } else if (mode === 'otp') {
        const res = await authService.verifyOtp(email, otp, 'registration');
        if ('access_token' in res && res.access_token) {
          setUser({
            id: res.user.id,
            name: res.user.name,
            email: res.user.email,
            token: res.access_token,
            created_at: res.user.created_at
          });
          setAuthModalOpen(false);
        }
      }
    } catch (err: any) {
      if (err.code === 'AUTH_UNVERIFIED_EMAIL') {
        setInfoMessage('Your email is unverified. Verification code sent.');
        setMode('otp');
      } else {
        setError(err.message || 'Authentication failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await authService.resendOtp(email, 'registration');
      setInfoMessage(res.message);
    } catch (err: any) {
      setError(err.message || 'Resend code failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 select-none font-sans">
      <div className="bg-cad-panel border border-cad-border w-full max-w-md rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-cad-border flex items-center justify-between bg-cad-panel">
          <div className="flex items-center space-x-2 font-bold text-sm text-white">
            <Lock className="w-5 h-5 text-violet-400" />
            <span>
              {mode === 'login' && 'Engineer Sign In'}
              {mode === 'signup' && 'Register CAD Account'}
              {mode === 'otp' && 'Verify Email OTP Code'}
            </span>
          </div>
          <button
            onClick={() => setAuthModalOpen(false)}
            className="text-cad-textMuted hover:text-white p-1 rounded-lg hover:bg-cad-surface"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          
          {error && (
            <div className="p-3 bg-red-950/60 border border-red-800 text-red-300 rounded-xl text-xs font-mono">
              {error}
            </div>
          )}

          {infoMessage && (
            <div className="p-3 bg-indigo-950/60 border border-indigo-800 text-indigo-300 rounded-xl text-xs font-mono">
              {infoMessage}
            </div>
          )}

          {mode === 'signup' && (
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-cad-textMuted">Full Name</label>
              <div className="flex items-center bg-cad-surface border border-cad-border rounded-xl px-3 py-2 text-xs">
                <UserIcon className="w-4 h-4 text-cad-textMuted mr-2" />
                <input
                  type="text"
                  required
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-transparent text-white outline-none w-full"
                />
              </div>
            </div>
          )}

          {(mode === 'login' || mode === 'signup') && (
            <>
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-cad-textMuted">Email Address</label>
                <div className="flex items-center bg-cad-surface border border-cad-border rounded-xl px-3 py-2 text-xs">
                  <Mail className="w-4 h-4 text-cad-textMuted mr-2" />
                  <input
                    type="email"
                    required
                    placeholder="engineer@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-transparent text-white outline-none w-full"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-mono text-cad-textMuted">Password</label>
                <div className="flex items-center bg-cad-surface border border-cad-border rounded-xl px-3 py-2 text-xs">
                  <KeyRound className="w-4 h-4 text-cad-textMuted mr-2" />
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-transparent text-white outline-none w-full"
                  />
                </div>
              </div>
            </>
          )}

          {mode === 'otp' && (
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-cad-textMuted">6-Digit Code for {email}</label>
              <div className="flex items-center bg-cad-surface border border-cad-border rounded-xl px-3 py-2 text-xs">
                <ShieldCheck className="w-4 h-4 text-violet-400 mr-2" />
                <input
                  type="text"
                  required
                  maxLength={6}
                  placeholder="123456"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/[^0-9]/g, ''))}
                  className="bg-transparent text-white text-center font-mono font-bold tracking-widest outline-none w-full"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || (mode === 'otp' && otp.length !== 6)}
            className="w-full py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-violet-600/30 flex items-center justify-center space-x-2 transition-all mt-2 disabled:opacity-50"
          >
            <span>
              {isLoading ? 'Processing...' : mode === 'login' ? 'Sign In to CAD Studio' : mode === 'signup' ? 'Create Account' : 'Verify Code'}
            </span>
          </button>

          {mode === 'otp' && (
            <div className="text-center pt-1">
              <button
                type="button"
                onClick={handleResendOtp}
                disabled={isLoading}
                className="text-xs text-violet-400 font-bold hover:underline inline-flex items-center space-x-1"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Resend Code</span>
              </button>
            </div>
          )}

          <div className="pt-2 text-center text-xs text-cad-textMuted">
            {mode === 'login' ? (
              <span>Don't have an account? <button type="button" onClick={() => { setMode('signup'); setError(null); }} className="text-violet-400 font-bold hover:underline">Register Now</button></span>
            ) : (
              <span>Already registered? <button type="button" onClick={() => { setMode('login'); setError(null); }} className="text-violet-400 font-bold hover:underline">Sign In</button></span>
            )}
          </div>

        </form>

      </div>
    </div>
  );
};
