import React, { useState, useEffect, useRef } from 'react';
import {
  User, CheckCircle2, RotateCcw,
  Save, Lock, Mail, Camera, LogOut, Check, Ruler, CreditCard, ShieldCheck
} from 'lucide-react';
import { useSettingsStore, UnitType } from '../../app/store/useSettingsStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { authApiService } from '../../services/api/auth';
import { BillingView } from './BillingView';


export const SettingsView: React.FC = () => {
  const {
    units,
    setUnits,
    resetToDefaults
  } = useSettingsStore();

  const { user, setUser, logout } = useAuthStore();

  // Profile Edit State
  const [nameInput, setNameInput] = useState(user?.name || '');
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Avatar Upload & Preview State
  const [avatarPreview, setAvatarPreview] = useState<string | null>(
    user?.avatar_url || (typeof localStorage !== 'undefined' && localStorage.getItem('ANTI_DESIGN_AVATAR')) || null
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Password Change State
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [isChangingPwd, setIsChangingPwd] = useState(false);
  const [pwdMsg, setPwdMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Email Change Flow State
  const [emailStep, setEmailStep] = useState<'idle' | 'request' | 'verify'>('idle');
  const [emailCurrentPwd, setEmailCurrentPwd] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [emailOtp, setEmailOtp] = useState('');
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [emailMsg, setEmailMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [activeTab, setActiveTab] = useState<'account' | 'billing' | 'admin'>('account');
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  useEffect(() => {
    if (user?.name) setNameInput(user.name);
    if (user?.avatar_url) setAvatarPreview(user.avatar_url);
  }, [user]);

  // Handle Avatar file picker & immediate auto-save to Database
  const handleAvatarSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setProfileMsg({ type: 'error', text: 'Please upload a valid image file (PNG, JPG, SVG, WebP).' });
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setProfileMsg({ type: 'error', text: 'Image file size must be less than 5MB.' });
      return;
    }

    const reader = new FileReader();
    reader.onload = async () => {
      const dataUrl = reader.result as string;
      setAvatarPreview(dataUrl);

      // Save locally immediately
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('ANTI_DESIGN_AVATAR', dataUrl);
      }

      // Auto-save immediately to database without requiring separate save button
      try {
        const updatedUser = await authApiService.updateAvatar(dataUrl);
        if (updatedUser) {
          setUser(updatedUser);
        } else if (user) {
          setUser({ ...user, avatar_url: dataUrl });
        }
        setProfileMsg({ type: 'success', text: 'Profile picture uploaded and saved to account successfully!' });
      } catch (err: any) {
        if (user) {
          setUser({ ...user, avatar_url: dataUrl });
        }
        setProfileMsg({ type: 'success', text: 'Profile picture updated!' });
      }
    };
    reader.readAsDataURL(file);
  };

  const handleGlobalSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nameInput.trim()) {
      setProfileMsg({ type: 'error', text: 'Name cannot be empty.' });
      return;
    }
    setIsUpdatingProfile(true);
    setProfileMsg(null);
    try {
      const updatedUser = await authApiService.updateProfile(nameInput.trim(), avatarPreview || undefined);
      setUser(updatedUser);
      setProfileMsg({ type: 'success', text: 'Profile name updated successfully!' });
    } catch (err: any) {
      setProfileMsg({ type: 'error', text: err.message || 'Failed to update profile' });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPwd || !newPwd) return;
    if (newPwd !== confirmPwd) {
      setPwdMsg({ type: 'error', text: 'New passwords do not match' });
      return;
    }
    setIsChangingPwd(true);
    setPwdMsg(null);
    try {
      const res = await authApiService.changePassword(currentPwd, newPwd, confirmPwd);
      setPwdMsg({ type: 'success', text: res.message });
      setCurrentPwd('');
      setNewPwd('');
      setConfirmPwd('');
    } catch (err: any) {
      setPwdMsg({ type: 'error', text: err.message || 'Failed to change password' });
    } finally {
      setIsChangingPwd(false);
    }
  };

  const handleRequestEmailChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailCurrentPwd || !newEmail) return;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(newEmail)) {
      setEmailMsg({ type: 'error', text: 'Please provide a valid email address.' });
      return;
    }

    setIsEmailLoading(true);
    setEmailMsg(null);
    try {
      const res = await authApiService.requestEmailChange(emailCurrentPwd, newEmail);
      setEmailMsg({ type: 'success', text: res.message });
      setEmailStep('verify');
    } catch (err: any) {
      setEmailMsg({ type: 'error', text: err.message || 'Failed to request email change' });
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleVerifyEmailChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailOtp || emailOtp.length !== 6) return;
    setIsEmailLoading(true);
    setEmailMsg(null);
    try {
      const res = await authApiService.verifyEmailChange(newEmail, emailOtp);
      if (res.user) {
        setUser({
          id: res.user.id,
          name: res.user.name,
          email: res.user.email,
          token: res.access_token,
          avatar_url: avatarPreview || undefined
        });
      }
      setEmailMsg({ type: 'success', text: 'Email updated and verified successfully!' });
      setEmailStep('idle');
      setEmailCurrentPwd('');
      setNewEmail('');
      setEmailOtp('');
    } catch (err: any) {
      setEmailMsg({ type: 'error', text: err.message || 'Verification failed' });
    } finally {
      setIsEmailLoading(false);
    }
  };

  return (
    <div className="flex-1 bg-slate-100 flex overflow-hidden font-sans select-none text-slate-800">

      {/* Navigation Sidebar */}
      <aside className="w-56 md:w-64 bg-white border-r border-slate-200 flex flex-col py-5 px-3 space-y-1 shrink-0">
        <div className="px-3 pb-3 mb-2 border-b border-slate-200">
          <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">System Settings</h2>
          <div className="text-[10px] text-slate-400 font-medium">Anti Design</div>
        </div>

        <nav className="flex-1 space-y-1">
          <button
            onClick={() => setActiveTab('account')}
            className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'account'
                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent'
            }`}
          >
            <User className="w-4 h-4 text-indigo-600 ml-2" />
            <span>Account &amp; Identity</span>
          </button>

          <button
            onClick={() => setActiveTab('billing')}
            className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'billing'
                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent'
            }`}
          >
            <CreditCard className="w-4 h-4 text-indigo-600 ml-2" />
            <span>Billing &amp; Subscription</span>
          </button>

          {user?.is_admin && (
            <button
              onClick={() => setActiveTab('admin')}
              className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'admin'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent'
              }`}
            >
              <ShieldCheck className="w-4 h-4 ml-2" />
              <span>Payment Approvals</span>
            </button>
          )}
        </nav>


        {/* Global Controls at bottom of sidebar */}
        <div className="pt-3 border-t border-slate-200 space-y-2">
          <button
            onClick={() => {
              if (confirm('Are you sure you want to reset settings to defaults?')) {
                resetToDefaults();
                alert('Settings reset to defaults.');
              }
            }}
            className="w-full flex items-center justify-center space-x-1.5 px-3 py-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl text-xs font-medium transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5 ml-1" />
            <span>Reset to Defaults</span>
          </button>

          <button
            onClick={handleGlobalSave}
            className="w-full flex items-center justify-center space-x-1.5 px-3 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all"
          >
            {savedSuccess ? <Check className="w-4 h-4 ml-1" /> : <Save className="w-4 h-4 ml-1" />}
            <span>{savedSuccess ? 'Settings Saved!' : 'Save Settings'}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 max-w-4xl space-y-6">

        {/* Save Success Banner */}
        {savedSuccess && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl text-xs flex items-center space-x-2 shadow-xs">
            <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600 shrink-0 ml-1" />
            <span className="font-bold text-slate-900 text-sm">All account settings saved successfully.</span>
          </div>
        )}

        {/* Billing & Subscription View */}
        {(activeTab === 'billing' || activeTab === 'admin') && (
          <BillingView initialTab={activeTab === 'admin' ? 'admin' : 'plans'} />
        )}

        {/* Account & Identity View */}
        {activeTab === 'account' && (
        <div className="space-y-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Account &amp; Identity</h1>
            <p className="text-xs text-slate-500 mt-1">Manage your avatar, account profile, engineering measurement unit, and security credentials.</p>
          </div>


          {/* Avatar & Profile Card */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row items-center sm:items-start space-y-4 sm:space-y-0 sm:space-x-6">
              
              {/* Avatar Preview & Upload Trigger */}
              <div className="relative group shrink-0">
                <div className="w-20 h-20 rounded-2xl bg-indigo-600 text-white font-black text-2xl flex items-center justify-center shadow-md overflow-hidden border-2 border-slate-200">
                  {avatarPreview ? (
                    <img
                      src={avatarPreview}
                      alt="User Avatar"
                      className="w-full h-full object-contain bg-white"
                    />
                  ) : (
                    (user?.name || 'A').charAt(0).toUpperCase()
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute -bottom-1.5 -right-1.5 p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-md border-2 border-white transition-transform group-hover:scale-110"
                  title="Upload Avatar Image (Auto-Saved)"
                >
                  <Camera className="w-3.5 h-3.5" />
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarSelect}
                  className="hidden"
                />
              </div>

              {/* Profile Meta */}
              <div className="space-y-1 text-center sm:text-left flex-1">
                <h3 className="font-bold text-slate-900 text-base">{user?.name || 'Engineer'}</h3>
                <p className="text-xs text-slate-500 font-mono">{user?.email || 'engineer@antidesign.local'}</p>
                <p className="text-[11px] text-slate-400 pt-1">
                  Click the camera icon to upload a personal photo or company logo. Avatar saves automatically to your profile.
                </p>
              </div>
            </div>

            {profileMsg && (
              <div className={`p-3 rounded-xl text-xs font-semibold ${profileMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`}>
                {profileMsg.text}
              </div>
            )}

            {/* Editable User Details Form */}
            <form onSubmit={handleUpdateProfile} className="pt-2 space-y-4 border-t border-slate-100">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Full Name</label>
                  <input
                    type="text"
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Account Email</label>
                  <input
                    type="email"
                    disabled
                    value={user?.email || ''}
                    className="w-full px-3.5 py-2 bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-500 font-mono cursor-not-allowed"
                    title="Use Change Email section below to update email with OTP verification."
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isUpdatingProfile}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all disabled:opacity-50"
              >
                {isUpdatingProfile ? 'Updating…' : 'Save Profile Changes'}
              </button>
            </form>
          </div>

          {/* ── User Preferences: Length Unit (Moved to Account & Identity) ── */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center space-x-2">
              <Ruler className="w-4 h-4 text-indigo-600 ml-1" />
              <h3 className="font-bold text-slate-900 text-sm">Engineering Measurement Preferences</h3>
            </div>
            <p className="text-xs text-slate-500">
              Select your personal default measurement unit for 2D blueprints and 3D modeling workspaces.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Length Unit</label>
                <select
                  value={units}
                  onChange={(e) => {
                    setUnits(e.target.value as UnitType);
                    setSavedSuccess(true);
                    setTimeout(() => setSavedSuccess(false), 2000);
                  }}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
                >
                  <option value="mm">Millimeter (mm) — Precision Engineering Standard</option>
                  <option value="cm">Centimeter (cm)</option>
                  <option value="inch">Inch (in) — Imperial</option>
                  <option value="m">Meter (m)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Password Change Card */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center space-x-2">
              <Lock className="w-4 h-4 text-indigo-600 ml-1" />
              <h3 className="font-bold text-slate-900 text-sm">Change Password</h3>
            </div>

            {pwdMsg && (
              <div className={`p-3 rounded-xl text-xs font-semibold ${pwdMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`}>
                {pwdMsg.text}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Current Password</label>
                <input
                  type="password"
                  value={currentPwd}
                  onChange={(e) => setCurrentPwd(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">New Password</label>
                  <input
                    type="password"
                    value={newPwd}
                    onChange={(e) => setNewPwd(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmPwd}
                    onChange={(e) => setConfirmPwd(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={isChangingPwd || !currentPwd || !newPwd}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs transition-all"
              >
                {isChangingPwd ? 'Updating Password…' : 'Change Password'}
              </button>
            </form>
          </div>

          {/* Email Address Update Card */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center space-x-2">
              <Mail className="w-4 h-4 text-indigo-600 ml-1" />
              <h3 className="font-bold text-slate-900 text-sm">Update Email Address</h3>
            </div>

            {emailMsg && (
              <div className={`p-3 rounded-xl text-xs font-semibold ${emailMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`}>
                {emailMsg.text}
              </div>
            )}

            {emailStep === 'idle' && (
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-600">Current Email: </span>
                  <span className="text-xs font-mono font-bold text-slate-900">{user?.email}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setEmailStep('request')}
                  className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold rounded-xl shadow-xs transition-all"
                >
                  Change Email
                </button>
              </div>
            )}

            {emailStep === 'request' && (
              <form onSubmit={handleRequestEmailChange} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Current Password</label>
                  <input
                    type="password"
                    value={emailCurrentPwd}
                    onChange={(e) => setEmailCurrentPwd(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">New Email Address</label>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900"
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    type="submit"
                    disabled={isEmailLoading || !newEmail || !emailCurrentPwd}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs"
                  >
                    {isEmailLoading ? 'Sending OTP…' : 'Send Verification OTP'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEmailStep('idle')}
                    className="px-3 py-2 text-slate-500 hover:text-slate-800 text-xs"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {emailStep === 'verify' && (
              <form onSubmit={handleVerifyEmailChange} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Verification Code (6 digits)</label>
                  <input
                    type="text"
                    maxLength={6}
                    value={emailOtp}
                    onChange={(e) => setEmailOtp(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-center text-base font-mono font-bold tracking-widest text-slate-900"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isEmailLoading || emailOtp.length !== 6}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs"
                >
                  {isEmailLoading ? 'Verifying…' : 'Confirm Code & Update Email'}
                </button>
              </form>
            )}
          </div>

          {/* Logout Action */}
          <div className="pt-2">
            <button
              onClick={logout}
              className="flex items-center space-x-2 px-4 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold border border-rose-200 transition-colors"
            >
              <LogOut className="w-4 h-4 ml-1" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
        )}

      </main>


    </div>
  );
};
