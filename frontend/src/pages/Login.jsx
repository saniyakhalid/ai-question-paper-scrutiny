import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { AlertCircle, ArrowRight, LogIn, UserPlus, Eye, EyeOff, Loader2, ShieldCheck, CheckCircle2 } from 'lucide-react';

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

const DEPARTMENTS = [
  'Computer Science & Engineering',
  'Information Technology',
  'Mechanical Engineering',
  'Civil Engineering',
  'Electrical Engineering',
  'Electronics & Telecommunication',
  'First Year Engineering / Basic Sciences',
];

export default function Login({ initialTab = 'login' }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, login } = useAuth();

  const isRegisterPath = location.pathname.includes('register');
  const [tab, setTab] = useState(isRegisterPath ? 'register' : initialTab);

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [department, setDepartment] = useState(DEPARTMENTS[0]);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [registeredSuccess, setRegisteredSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  useEffect(() => {
    setTab(location.pathname.includes('register') ? 'register' : 'login');
    setError('');
  }, [location.pathname]);

  const handleTabChange = (nextTab) => {
    setTab(nextTab);
    setError('');
    navigate(nextTab === 'register' ? '/register' : '/login', { replace: true });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email.trim(), password);
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
        department,
        role: 'FACULTY',
      });
      setRegisteredSuccess(true);
      // Auto login after successful registration
      await login(email.trim(), password);
      navigate('/dashboard');
    } catch (err) {
      setError(formatAuthError(err, 'Registration failed. Please check your details and try again.'));
    } finally {
      setLoading(false);
    }
  };

  const quickFill = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError('');
  };

  return (
    <div className="min-h-screen bg-adcet-cream flex flex-col justify-center items-center p-4 selection:bg-adcet-red selection:text-white">
      <div className="w-full max-w-md">
        {/* Header Branding */}
        <div className="text-center mb-6">
          <Link to="/" className="inline-flex flex-col items-center gap-2 group">
            <div className="w-16 h-16 rounded-2xl bg-white shadow-md p-2 border border-slate-200 group-hover:scale-105 transition-transform">
              <img src="/images/college-logo.png" alt="ADCET Logo" className="w-full h-full object-contain" />
            </div>
            <h1 className="text-xl font-display font-black text-adcet-navy mt-1 tracking-tight">
              ADCET Examination Cell
            </h1>
          </Link>
          <p className="text-xs text-slate-500 font-medium">
            AI-Based Question Paper Scrutiny &amp; Decision Support System
          </p>
        </div>

        {/* Card Container */}
        <div className="bg-white border border-slate-200/80 rounded-3xl shadow-xl overflow-hidden backdrop-blur-md">
          {/* Tab Selector */}
          <div className="flex border-b border-slate-100 bg-slate-50/60 p-1.5 gap-1.5">
            <button
              type="button"
              id="tab-login-btn"
              onClick={() => handleTabChange('login')}
              className={`flex-1 py-2.5 text-xs font-bold rounded-2xl flex items-center justify-center gap-1.5 transition-all ${
                tab === 'login'
                  ? 'bg-white text-adcet-red shadow-sm border border-slate-200/60'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <LogIn className="w-4 h-4" /> Sign In
            </button>
            <button
              type="button"
              id="tab-register-btn"
              onClick={() => handleTabChange('register')}
              className={`flex-1 py-2.5 text-xs font-bold rounded-2xl flex items-center justify-center gap-1.5 transition-all ${
                tab === 'register'
                  ? 'bg-white text-adcet-red shadow-sm border border-slate-200/60'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <UserPlus className="w-4 h-4" /> Faculty Register
            </button>
          </div>

          <div className="p-7">
            {error && (
              <div role="alert" className="mb-5 p-3.5 bg-rose-50 border border-rose-200/80 rounded-2xl flex items-start gap-2.5 text-xs text-rose-800 animate-in fade-in">
                <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
                <span className="leading-relaxed font-medium">{error}</span>
              </div>
            )}

            {registeredSuccess && (
              <div className="mb-5 p-3.5 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2.5 text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Account created successfully! Logging you in...</span>
              </div>
            )}

            {tab === 'login' ? (
              /* LOGIN FORM */
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="login-email-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="e.g. faculty@college.edu"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-adcet-red/20 focus:border-adcet-red transition"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-bold text-slate-700">
                      Password
                    </label>
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="login-password-input"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 pr-10 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-adcet-red/20 focus:border-adcet-red transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                      tabIndex="-1"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  id="login-submit-btn"
                  disabled={loading}
                  className="w-full bg-adcet-red hover:bg-red-700 text-white font-bold py-3 rounded-xl transition-all shadow-md shadow-adcet-red/20 flex items-center justify-center gap-2 text-xs disabled:opacity-50 mt-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Verifying Credentials...</span>
                    </>
                  ) : (
                    <>
                      <span>Sign In to Examination Portal</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                {/* Quick Demo Access Pills */}
                <div className="pt-4 border-t border-slate-100">
                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 text-center">
                    Quick-Fill Demo Accounts
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => quickFill('faculty@college.edu', 'password123')}
                      className="px-2 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-[11px] font-semibold text-slate-700 text-center transition"
                    >
                      👨‍🏫 Faculty
                    </button>
                    <button
                      type="button"
                      onClick={() => quickFill('moderator@college.edu', 'password123')}
                      className="px-2 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-[11px] font-semibold text-slate-700 text-center transition"
                    >
                      🛡️ Moderator
                    </button>
                    <button
                      type="button"
                      onClick={() => quickFill('admin@college.edu', 'password123')}
                      className="px-2 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-[11px] font-semibold text-slate-700 text-center transition"
                    >
                      ⚙️ Admin
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              /* REGISTER FORM */
              <form onSubmit={handleRegister} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Full Name &amp; Title
                  </label>
                  <input
                    type="text"
                    id="register-fullname-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    placeholder="e.g. Prof. Rajesh Sharma"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-adcet-red/20 focus:border-adcet-red transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Academic Department
                  </label>
                  <select
                    id="register-department-select"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-adcet-red/20 focus:border-adcet-red transition"
                  >
                    {DEPARTMENTS.map((dept) => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Institutional Email Address
                  </label>
                  <input
                    type="email"
                    id="register-email-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="e.g. r.sharma@adcet.in"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-adcet-red/20 focus:border-adcet-red transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Password <span className="font-normal text-slate-400">(Min. 8 characters)</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="register-password-input"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      placeholder="At least 8 characters"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 pr-10 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-adcet-red/20 focus:border-adcet-red transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                      tabIndex="-1"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {password && password.length < 8 && (
                    <p className="text-[11px] text-amber-600 mt-1">
                      Must be at least 8 characters ({password.length}/8)
                    </p>
                  )}
                </div>

                <div className="p-3 bg-blue-50/70 border border-blue-200/60 rounded-xl text-[11px] text-slate-600 flex items-start gap-2">
                  <ShieldCheck className="w-4 h-4 text-adcet-navy mt-0.5 shrink-0" />
                  <span>
                    Self-registration creates a certified <strong>Faculty Account</strong>. Moderator &amp; Admin accounts are provisioned by Examination Cell administrators.
                  </span>
                </div>

                <button
                  type="submit"
                  id="register-submit-btn"
                  disabled={loading || password.length < 8}
                  className="w-full bg-adcet-red hover:bg-red-700 text-white font-bold py-3 rounded-xl transition-all shadow-md shadow-adcet-red/20 flex items-center justify-center gap-2 text-xs disabled:opacity-50 mt-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Creating Faculty Account...</span>
                    </>
                  ) : (
                    <>
                      <span>Register &amp; Enter Dashboard</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Footer Back Link */}
        <p className="text-center mt-5 text-xs text-slate-500 font-medium">
          <Link to="/" className="text-adcet-navy hover:text-adcet-red hover:underline inline-flex items-center gap-1 font-semibold">
            ← Back to Institutional Home
          </Link>
        </p>
      </div>
    </div>
  );
}
