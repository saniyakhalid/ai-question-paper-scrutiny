import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { X, AlertCircle, ArrowRight, LogIn, UserPlus, Eye, EyeOff, Loader2 } from 'lucide-react';

function formatAuthError(err, fallback = 'Authentication failed. Please try again.') {
  if (!err) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join('; ');
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.error || fallback;
  }
  return err.message || fallback;
}

const DEMO_CREDENTIALS = {
  FACULTY: { email: 'faculty@college.edu', pass: 'password123' },
  MODERATOR: { email: 'moderator@college.edu', pass: 'password123' },
  ADMIN: { email: 'admin@college.edu', pass: 'password123' },
};

export default function AuthModal({ isOpen, onClose, initialTab = 'login' }) {
  const [tab, setTab] = useState(initialTab);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [department, setDepartment] = useState('Computer Engineering');
  const [loginRole, setLoginRole] = useState('FACULTY');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setTab(initialTab);
      setError('');
    }
  }, [initialTab, isOpen]);

  if (!isOpen) return null;

  const resetForm = () => {
    setError('');
    setEmail('');
    setPassword('');
    setFullName('');
    setShowPassword(false);
    setLoginRole('FACULTY');
  };

  const switchTab = (next) => {
    setTab(next);
    resetForm();
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email.trim(), password);
      onClose();
      navigate('/dashboard');
    } catch (err) {
      setError(formatAuthError(err, 'Invalid email or password. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/register', {
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        department: department.trim() || 'General Engineering',
        role: 'FACULTY',
      });
      await login(email.trim(), password);
      onClose();
      navigate('/dashboard');
    } catch (err) {
      setError(formatAuthError(err, 'Registration failed. Please check your details and try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleRolePillClick = (role) => {
    setLoginRole(role);
    setError('');
    if (!email || email.includes('@college.edu')) {
      setEmail(DEMO_CREDENTIALS[role].email);
      setPassword(DEMO_CREDENTIALS[role].pass);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-adcet-navy/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md max-h-[calc(100dvh-2rem)] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
        <div className="bg-adcet-navy px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-white font-display font-bold text-sm">ADCET Examination Portal</p>
            <p className="text-white/70 text-xs">Question Paper Scrutiny System</p>
          </div>
          <button type="button" onClick={onClose} className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex border-b border-slate-200">
          <button
            type="button"
            onClick={() => switchTab('login')}
            className={`flex-1 py-3 text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
              tab === 'login' ? 'text-adcet-red border-b-2 border-adcet-red bg-red-50/50' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <LogIn className="w-4 h-4" /> Sign In
          </button>
          <button
            type="button"
            onClick={() => switchTab('register')}
            className={`flex-1 py-3 text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
              tab === 'register' ? 'text-adcet-red border-b-2 border-adcet-red bg-red-50/50' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <UserPlus className="w-4 h-4" /> Faculty Register
          </button>
        </div>

        <div className="p-6">
          {error && (
            <div role="alert" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
              <span className="leading-relaxed font-medium">{error}</span>
            </div>
          )}

          {tab === 'login' ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <fieldset className="space-y-1.5">
                <legend className="mb-1.5 block text-xs font-semibold text-slate-700">Choose demo role to autofill or enter custom login</legend>
                <div className="grid grid-cols-3 gap-2" role="group" aria-label="Choose your account role">
                  {[
                    ['FACULTY', '👨‍🏫 Faculty'],
                    ['MODERATOR', '🛡️ Moderator'],
                    ['ADMIN', '⚙️ Admin'],
                  ].map(([role, label]) => (
                    <button
                      key={role}
                      type="button"
                      aria-pressed={loginRole === role}
                      onClick={() => handleRolePillClick(role)}
                      className={`rounded-xl border px-2 py-2 text-xs font-bold transition-colors ${loginRole === role ? 'border-adcet-red bg-red-50 text-adcet-red' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </fieldset>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="e.g. faculty@college.edu"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-adcet-red focus:ring-1 focus:ring-adcet-red"
                />
              </div>
              <div>
                <label htmlFor="modal-login-password" className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
                <div className="relative">
                  <input
                    id="modal-login-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-4 pr-10 text-xs text-slate-900 focus:border-adcet-red focus:outline-none focus:ring-1 focus:ring-adcet-red"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-adcet-red hover:bg-red-700 text-white font-bold py-2.5 rounded-xl transition-all flex items-center justify-center gap-2 text-xs shadow-md disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name &amp; Title</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="e.g. Dr. Rajesh Sharma"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-adcet-red focus:ring-1 focus:ring-adcet-red"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Department</label>
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  required
                  placeholder="e.g. Computer Science & Engineering"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-adcet-red focus:ring-1 focus:ring-adcet-red"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="e.g. r.sharma@adcet.in"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-adcet-red focus:ring-1 focus:ring-adcet-red"
                />
              </div>
              <div>
                <label htmlFor="modal-register-password" className="block text-xs font-semibold text-slate-700 mb-1">
                  Password <span className="font-normal text-slate-400">(Min. 8 characters)</span>
                </label>
                <div className="relative">
                  <input
                    id="modal-register-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    placeholder="At least 8 characters"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-4 pr-10 text-xs text-slate-900 focus:border-adcet-red focus:outline-none focus:ring-1 focus:ring-adcet-red"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              <button
                type="submit"
                disabled={loading || password.length < 8}
                className="w-full bg-adcet-red hover:bg-red-700 text-white font-bold py-2.5 rounded-xl transition-all flex items-center justify-center gap-2 text-xs shadow-md disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating account...</span>
                  </>
                ) : (
                  <>
                    <span>Create Faculty Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

        </div>
      </div>
    </div>
  );
}
