import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ImageSlider from '../components/common/ImageSlider';
import AuthModal from '../components/common/AuthModal';
import api from '../services/api';
import {
  Brain, BookOpen, ShieldCheck, CheckCircle2, ArrowRight, FileText,
  Sliders, Sparkles, Scale, GraduationCap, MapPin,
  Upload, Search, UserCheck, Layers, Award, BarChart3,
  CheckSquare, FileSpreadsheet, AlertTriangle, Shield, Check, Menu, X
} from 'lucide-react';

const CAMPUS_SLIDES = [
  {
    src: '/images/campus-3.png',
    alt: 'ADCET Campus Panoramic View',
    badge: 'College Campus',
    title: 'Annasaheb Dange College of Engineering & Technology',
    subtitle: 'Campus view • Ashta, Sangli district',
  },
  {
    src: '/images/campus-2.png',
    alt: 'ADCET Academic Infrastructure',
    badge: 'Academic Spaces',
    title: 'College Campus & Learning Environment',
    subtitle: 'A view of the college campus and its academic setting',
  },
  {
    src: '/images/campus-1.png',
    alt: 'ADCET Main Building & Playground',
    badge: 'Examination Cell DSS',
    title: 'AI-Powered Question Paper Scrutiny System',
    subtitle: 'Automated cognitive balance verification, syllabus alignment, and examination governance',
  },
];

const FEATURES = [
  {
    icon: ShieldCheck,
    color: 'text-adcet-red',
    bg: 'bg-red-50',
    title: 'Subject Isolation Guard',
    desc: 'Strictly ensures uploaded question papers correspond to the chosen subject workspace — preventing cross-subject upload errors before analysis begins.',
  },
  {
    icon: Brain,
    color: 'text-adcet-navy',
    bg: 'bg-blue-50',
    title: "Bloom's Cognitive Taxonomy (K1–K6)",
    desc: 'Suggests a Bloom level from question wording. Compliance is evaluated only when an institutional target is configured.',
  },
  {
    icon: BookOpen,
    color: 'text-emerald-700',
    bg: 'bg-emerald-50',
    title: 'Course Outcome (CO) Mapping',
    desc: 'Suggests mappings against the course outcomes configured for the selected subject; uncertain mappings remain for human review.',
  },
  {
    icon: Layers,
    color: 'text-indigo-700',
    bg: 'bg-indigo-50',
    title: 'Syllabus Unit Boundary Verification',
    desc: 'Checks question-to-unit mappings against the selected subject curriculum and configured examination scope.',
  },
  {
    icon: Scale,
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    title: 'Deterministic Rule Engine (100 Pts)',
    desc: 'Checks marks and numbering, plus configured CO/unit thresholds, choice rules, Bloom targets, and solving time when evidence is available.',
  },
  {
    icon: UserCheck,
    color: 'text-purple-700',
    bg: 'bg-purple-50',
    title: 'Human-in-the-Loop Moderator Sign-Off',
    desc: 'Chief moderators review explainable AI evidence, record official remarks, and issue binding Approve, Modify, or Reject decisions.',
  },
  {
    icon: Search,
    color: 'text-cyan-700',
    bg: 'bg-cyan-50',
    title: 'Similar Question Detection',
    desc: 'Uses TF-IDF text matching against uploaded previous papers for the same subject. Similarity is a review flag, not a plagiarism finding.',
  },
  {
    icon: FileSpreadsheet,
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    title: 'Examination Pattern Checks',
    desc: 'Checks configured marks, question distribution, internal choice, and estimated completion time.',
  },
  {
    icon: FileText,
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    title: 'Reports and Scrutiny History',
    desc: 'Keeps scrutiny results and decision history available, with PDF, CSV, and JSON report exports.',
  },
  {
    icon: Shield,
    color: 'text-emerald-700',
    bg: 'bg-emerald-50',
    title: 'Role-Based Access',
    desc: 'Separates faculty, moderator, and administrator actions through authenticated backend permissions.',
  },
];

const WORKFLOW = [
  {
    step: '01',
    icon: Upload,
    title: 'Subject-Isolated Ingestion',
    desc: 'Faculty selects the subject workspace and uploads a PDF, DOCX, or TXT paper for pre-flight subject validation.',
  },
  {
    step: '02',
    icon: Search,
    title: 'Intelligent Question Parsing',
    desc: 'High-speed document parsers extract question statements, sub-questions, marks, and section schemes into structured examination objects.',
  },
  {
    step: '03',
    icon: Sliders,
    title: 'Dual Scrutiny Engine Audit',
    desc: 'Optional Gemini analysis and offline keyword heuristics provide suggestions; configured deterministic rules check examination evidence.',
  },
  {
    step: '04',
    icon: UserCheck,
    title: 'Moderator Review & Report',
    desc: 'The moderator reviews available evidence, records a decision and remarks, and can export the report.',
  },
];

export default function LandingPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState('login');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [stats, setStats] = useState({
    total_papers_analyzed: null,
    active_curriculum_subjects: null,
    avg_scrutiny_score: null,
    rule_compliance_rate: null,
  });

  useEffect(() => {
    api.get('/dashboard/public-stats')
      .then((res) => {
        if (res.data) setStats((prev) => ({ ...prev, ...res.data }));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) {
      if (searchParams.get('register') === '1') {
        setAuthTab('register');
        setAuthOpen(true);
      } else if (searchParams.get('login') === '1') {
        setAuthTab('login');
        setAuthOpen(true);
      }
    }
  }, [searchParams, user]);

  const openLogin = () => {
    setAuthTab('login');
    setAuthOpen(true);
  };

  const openRegister = () => {
    setAuthTab('register');
    setAuthOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-slate-800 font-sans selection:bg-adcet-red selection:text-white">
      {/* 1. Top Institutional Banner */}
      <div className="bg-adcet-navy text-white text-xs py-2 px-4 border-b border-blue-950 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
          <div className="flex items-center gap-2 font-medium tracking-wide">
            <span className="font-bold text-amber-300">Sant Dnyaneshwar Shikshan Sanstha's</span>
            <span className="hidden sm:inline text-white/60">|</span>
            <span>Annasaheb Dange College of Engineering & Technology, Ashta</span>
          </div>
          <div className="flex items-center gap-3 text-white/90 text-[11px]">
            <span className="px-2 py-0.5 rounded bg-white/10 font-bold text-amber-200">
              Examination Decision Support
            </span>
            <span>॥ ज्ञान ज्योति नमोस्तु ते ॥</span>
            <span className="hidden md:inline text-white/60">|</span>
            <span className="hidden md:inline text-white/80">AI-powered question paper scrutiny</span>
          </div>
        </div>
      </div>

      {/* 2. Main Institutional Navbar */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 min-h-20 flex items-center justify-between gap-2 sm:gap-4">
          {/* Logo & College Name */}
          <div
            className="flex min-w-0 items-center gap-2 sm:gap-3.5 cursor-pointer group"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            <img
              src="/images/college-logo.png"
              alt="ADCET Seal Logo"
              className="w-10 h-10 sm:w-12 sm:h-12 shrink-0 object-contain drop-shadow-sm group-hover:scale-105 transition-transform"
            />
            <div className="min-w-0 border-l border-slate-200 pl-2 sm:pl-3">
              <div className="flex items-center gap-2">
                <img
                  src="/images/logo-ndcet.png"
                  alt="ADCET Typography"
                  className="h-4 sm:h-5 object-contain"
                />
                <span className="hidden md:inline text-[10px] font-bold text-adcet-navy uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  Autonomous
                </span>
              </div>
              <p className="hidden sm:block text-[11px] font-bold text-slate-800 leading-tight mt-0.5 truncate">
                AI Question Paper Scrutiny & Quality Assurance Cell
              </p>
              <p className="hidden lg:block text-[10px] text-slate-500">
                Decision Support System for University & Autonomous Examinations
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden xl:flex items-center gap-6 text-xs font-bold text-slate-600 uppercase tracking-wider">
            <a href="#about" className="hover:text-adcet-red transition-colors">About System</a>
            <a href="#workflow" className="hover:text-adcet-red transition-colors">How It Works</a>
            <a href="#features" className="hover:text-adcet-red transition-colors">Features</a>
              <a href="#standards" className="hover:text-adcet-red transition-colors">Institutional Setup</a>
            <a href="#contact" className="hover:text-adcet-red transition-colors">Contact</a>
          </nav>

          {/* Authentication Actions */}
          <div className="flex shrink-0 items-center gap-2">
            {user ? (
              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2.5 rounded-xl bg-adcet-red hover:bg-red-700 text-white text-xs font-bold transition-all shadow-md hover:shadow-lg flex items-center gap-2"
              >
                <span className="hidden sm:inline">{user.role === 'ADMIN' ? 'Admin Dashboard' : user.role === 'MODERATOR' ? 'Moderator Dashboard' : 'Teacher Dashboard'}</span>
                <span className="sm:hidden">Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={openLogin}
                  className="px-3 sm:px-4 py-2.5 rounded-xl border border-adcet-navy text-adcet-navy text-xs font-bold hover:bg-adcet-navy hover:text-white transition-all shadow-sm"
                >
                  <span className="hidden sm:inline">Portal Login</span>
                  <span className="sm:hidden">Login</span>
                </button>
                <button
                  type="button"
                  onClick={openRegister}
                  className="hidden sm:flex px-4 py-2.5 rounded-xl bg-adcet-red hover:bg-red-700 text-white text-xs font-bold transition-all shadow-md items-center gap-1.5"
                >
                  <span>Register</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
          <button
            type="button"
            onClick={() => setMobileNavOpen((open) => !open)}
            className="xl:hidden inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-adcet-navy hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-adcet-red"
            aria-label={mobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileNavOpen}
          >
            {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        {mobileNavOpen && (
          <nav className="xl:hidden border-t border-slate-200 bg-white px-4 py-3 shadow-lg">
            <div className="mx-auto grid max-w-7xl gap-1 sm:grid-cols-2">
              {[
                ['#about', 'About System'],
                ['#workflow', 'How It Works'],
                ['#features', 'Features'],
                ['#standards', 'Institutional Setup'],
                ['#contact', 'Contact'],
              ].map(([href, label]) => (
                <a
                  key={href}
                  href={href}
                  onClick={() => setMobileNavOpen(false)}
                  className="rounded-lg px-3 py-2.5 text-sm font-semibold text-slate-700 hover:bg-red-50 hover:text-adcet-red"
                >
                  {label}
                </a>
              ))}
              {!user && (
                <button
                  type="button"
                  onClick={() => { setMobileNavOpen(false); openRegister(); }}
                  className="rounded-lg px-3 py-2.5 text-left text-sm font-semibold text-adcet-red hover:bg-red-50"
                >
                  Register as Faculty
                </button>
              )}
            </div>
          </nav>
        )}
      </header>

      {/* 3. Hero College Image Slider */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 pb-2">
        <ImageSlider
          slides={CAMPUS_SLIDES}
          intervalMs={2000}
          className="shadow-2xl border border-slate-200"
        />
        <div className="mx-auto mt-6 max-w-4xl text-center">
          <h1 className="font-display text-2xl font-bold tracking-tight text-adcet-navy sm:text-3xl">
            AI-Powered Question Paper Scrutiny
          </h1>
          <p className="mx-auto mt-2 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base">
            An intelligent decision-support platform designed to help engineering colleges evaluate question papers against their syllabus, course outcomes, examination pattern, and configured academic scrutiny criteria.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <button type="button" onClick={() => (user ? navigate('/dashboard') : openLogin())} className="inline-flex items-center gap-2 rounded-xl bg-adcet-red px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700">
              Get Started <ArrowRight className="h-4 w-4" />
            </button>
            <a href="#features" className="inline-flex items-center gap-2 rounded-xl border border-adcet-navy px-5 py-2.5 text-sm font-bold text-adcet-navy transition hover:bg-blue-50">
              Explore Features
            </a>
          </div>
        </div>
        <div className="mt-3 text-center">
          <p className="text-[11px] text-slate-500 font-medium">
            Campus images rotate automatically every 2 seconds • Use the controls to pause or choose a photo
          </p>
        </div>
      </section>

      {/* 4. Live Scrutiny Metrics Strip */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              val: stats.total_papers_analyzed ?? '—',
              label: 'Papers Scrutinized',
              sub: 'Evaluated with explainable AI dossiers',
              icon: FileText,
              color: 'text-adcet-red',
            },
            {
              val: stats.active_curriculum_subjects ?? '—',
              label: 'Curriculum Subjects',
              sub: 'Active isolated subject workspaces',
              icon: BookOpen,
              color: 'text-adcet-navy',
            },
            {
              val: stats.avg_scrutiny_score == null ? '—' : `${Number(stats.avg_scrutiny_score).toFixed(1)}/100`,
              label: 'Avg. Scrutiny Score',
              sub: 'Institutional quality benchmark',
              icon: Award,
              color: 'text-amber-600',
            },
            {
              val: stats.rule_compliance_rate == null ? '—' : `${Number(stats.rule_compliance_rate).toFixed(1)}%`,
              label: 'Rule Compliance Rate',
              sub: 'Marks, time & syllabus coverage',
              icon: ShieldCheck,
              color: 'text-emerald-600',
            },
          ].map((s, idx) => {
            const Icon = s.icon;
            return (
              <div
                key={idx}
                className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow-md hover:border-slate-300 transition-all flex items-center gap-4"
              >
                <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center shrink-0">
                  <Icon className={`w-6 h-6 ${s.color}`} />
                </div>
                <div>
                  <p className="text-2xl font-black text-slate-900 tracking-tight">{s.val}</p>
                  <p className="text-xs font-bold text-slate-700">{s.label}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">{s.sub}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 5. What is the Project? (Detailed Overview) */}
      <section id="about" className="py-16 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            {/* Left Column Description */}
            <div className="lg:col-span-7 space-y-5">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 text-adcet-red text-xs font-bold border border-red-100">
                <Sparkles className="w-3.5 h-3.5" /> Examination Quality Governance
              </span>

              <h2 className="text-3xl sm:text-4xl font-display font-black text-adcet-navy tracking-tight leading-tight">
                What is the AI Question Paper Scrutiny System?
              </h2>

              <p className="text-sm text-slate-600 leading-relaxed">
                The <strong>AI Question Paper Scrutiny System</strong> is a decision-support workspace for faculty and examination moderators at Annasaheb Dange College of Engineering & Technology.
              </p>

              <p className="text-sm text-slate-600 leading-relaxed">
                Manual scrutiny takes time and makes it harder to apply the same checks across papers. This system organizes document validation, configured curriculum and examination checks, review evidence, and the moderator's final decision in one workflow.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-xs font-bold text-adcet-navy flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-adcet-red" />
                    Cognitive Difficulty Balance
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Shows question-level Bloom suggestions. Distribution compliance is checked only when a target has been configured.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-xs font-bold text-adcet-navy flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-adcet-red" />
                    Strict Subject Isolation
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Blocks cross-subject uploads (e.g. DBMS paper uploaded to ML workspace) with real-time curriculum validation.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-xs font-bold text-adcet-navy flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-adcet-red" />
                    Deterministic Rule Validation
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Checks marks and numbering; other checks run only when their rules and required evidence are configured.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-xs font-bold text-adcet-navy flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-adcet-red" />
                    Human-in-the-Loop Oversight
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Analysis supports review; the moderator retains authority to approve, request changes, or reject.
                  </p>
                </div>
              </div>
            </div>

            {/* Right Column Highlights Card */}
            <div className="lg:col-span-5 bg-gradient-to-br from-adcet-navy to-slate-900 rounded-3xl p-8 text-white space-y-6 shadow-2xl relative overflow-hidden border border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-adcet-red flex items-center justify-center text-white shadow-lg">
                  <GraduationCap className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-white">ADCET Examination Cell</h3>
                  <p className="text-xs text-white/70">Ashta, Dist. Sangli (Maharashtra)</p>
                </div>
              </div>

              <div className="space-y-3 border-y border-white/10 py-5">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-adcet-red shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-bold text-white">Evidence-Based Scrutiny Score</p>
                    <p className="text-[11px] text-white/70">
                      Core checks are scored only when evidence is available. Partial evaluation and unavailable checks are shown in the report.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <FileSpreadsheet className="w-5 h-5 text-adcet-red shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-bold text-white">Scrutiny Report Exports</p>
                    <p className="text-[11px] text-white/70">
                      Export PDF, JSON, and CSV reports with rule results, analysis notices, and question details.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => (user ? navigate('/dashboard') : openLogin())}
                  className="w-full py-3.5 bg-adcet-red hover:bg-red-700 rounded-xl text-xs font-bold transition-all shadow-lg flex items-center justify-center gap-2"
                >
                  <span>{user ? `Enter ${user.role === 'ADMIN' ? 'Admin' : user.role === 'MODERATOR' ? 'Moderator' : 'Faculty'} Dashboard` : 'Portal Login'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. How It Works (Process Flow) */}
      <section id="workflow" className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-bold text-adcet-red uppercase tracking-widest">
              End-to-End Operational Workflow
            </span>
            <h2 className="text-3xl font-display font-black text-adcet-navy">
              How the Scrutiny Pipeline Operates
            </h2>
            <p className="text-xs text-slate-500">
              A four-stage workflow that supports scrutiny before moderator sign-off.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {WORKFLOW.map((w, idx) => {
              const Icon = w.icon;
              return (
                <div
                  key={idx}
                  className="relative bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md hover:border-adcet-navy/30 transition-all flex flex-col justify-between"
                >
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-xl bg-adcet-navy text-white flex items-center justify-center">
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-3xl font-display font-black text-slate-200">
                        {w.step}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">{w.title}</h3>
                      <p className="text-xs text-slate-500 leading-relaxed mt-2">{w.desc}</p>
                    </div>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-[11px] font-bold text-adcet-red">
                    <span>Stage {idx + 1} Automated</span>
                    <ArrowRight className="w-3 h-3" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 7. Core Features */}
      <section id="features" className="py-16 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-bold text-adcet-red uppercase tracking-widest">
              Institutional Capabilities
            </span>
            <h2 className="text-3xl font-display font-black text-adcet-navy">
              Comprehensive Platform Features
            </h2>
            <p className="text-xs text-slate-500">
                Checks use the subject curriculum and examination requirements configured by the institution.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  className="bg-[#FAF8F5] rounded-2xl p-6 border border-slate-200 hover:border-adcet-red/40 hover:bg-white hover:shadow-md transition-all space-y-3"
                >
                  <div className={`w-11 h-11 rounded-xl ${f.bg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${f.color}`} />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{f.title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 8. Institutional Configuration */}
      <section id="standards" className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="bg-slate-50 rounded-3xl border border-slate-200 p-8 sm:p-12 space-y-8">
            <div className="text-center max-w-2xl mx-auto space-y-2">
              <span className="text-xs font-bold text-adcet-red uppercase tracking-widest">
                Institutional Configuration
              </span>
              <h2 className="text-2xl sm:text-3xl font-display font-black text-adcet-navy">
                Configure the Checks That Matter
              </h2>
              <p className="text-xs text-slate-500">
                Add course outcomes, syllabus units, marks thresholds, and optional cognitive-level requirements for each subject.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-2">
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700">Curriculum</span>
                <p className="text-xs font-bold text-slate-900">Subject Outcomes & Syllabus</p>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Configure the outcomes, units, and topics used for subject-specific mapping and coverage.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-2">
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700">Optional Rule</span>
                <p className="text-xs font-bold text-slate-900">Bloom's Distribution Target</p>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Set a target if your institution uses one. The report marks the check unavailable until configured evidence exists.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-2">
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700">Review Workflow</span>
                <p className="text-xs font-bold text-slate-900">Moderator Decisions & Audit Events</p>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Store moderator remarks and decision events alongside the paper's scrutiny history.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 9. Call to Action Banner */}
      <section className="py-14 bg-gradient-to-r from-adcet-navy via-slate-900 to-adcet-navy text-white">
        <div className="max-w-4xl mx-auto px-4 text-center space-y-5">
          <h2 className="text-2xl sm:text-3xl font-display font-black tracking-tight">
            Ready to Scrutinize Your Engineering Question Papers?
          </h2>
          <p className="text-xs sm:text-sm text-white/80 max-w-2xl mx-auto leading-relaxed">
            Faculty can validate a paper against its selected subject, review the available scrutiny evidence, and send it for moderator review.
          </p>
          <div className="flex flex-wrap justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => (user ? navigate('/dashboard') : openLogin())}
              className="px-6 py-3 bg-adcet-red hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-all shadow-lg flex items-center gap-2"
            >
              <span>{user ? 'Enter Dashboard' : 'Portal Login'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            {!user && (
              <button
                type="button"
                onClick={openRegister}
                className="px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-xl text-xs font-bold transition-colors"
              >
                Register as Faculty
              </button>
            )}
          </div>
        </div>
      </section>

      {/* 10. Institutional Footer */}
      <footer id="contact" className="border-t border-slate-200 bg-white py-14 text-xs text-slate-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Col 1: College Info */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <img
                src="/images/college-logo.png"
                alt="Annasaheb Dange College logo"
                className="w-12 h-12 object-contain"
              />
              <div>
                <p className="text-adcet-navy font-bold text-sm">ADCET Ashta</p>
                <p className="text-[10px] text-slate-500">Ashta, Sangli district</p>
              </div>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-600">
              Sant Dnyaneshwar Shikshan Sanstha's Annasaheb Dange College of Engineering & Technology, Ashta.
              Ashta, Sangli district.
            </p>
            <div className="text-[11px] font-semibold text-adcet-red">
              ॥ ज्ञान ज्योति नमोस्तु ते ॥
            </div>
          </div>

          {/* Col 2: Navigation Links */}
          <div>
            <p className="mb-4 border-b border-slate-200 pb-2 text-xs font-bold uppercase tracking-wider text-adcet-navy">
              System Modules
            </p>
            <ul className="space-y-2.5 text-[11px]">
              <li><a href="#about" className="transition-colors hover:text-adcet-red">About Scrutiny System</a></li>
              <li><a href="#workflow" className="transition-colors hover:text-adcet-red">Four-Stage Workflow</a></li>
              <li><a href="#features" className="transition-colors hover:text-adcet-red">Platform Features</a></li>
              <li><a href="#standards" className="transition-colors hover:text-adcet-red">Institutional Setup</a></li>
              <li><button type="button" onClick={openLogin} className="transition-colors hover:text-adcet-red">Portal Login</button></li>
            </ul>
          </div>

          {/* Col 3: Quality Compliance */}
          <div>
            <p className="mb-4 border-b border-slate-200 pb-2 text-xs font-bold uppercase tracking-wider text-adcet-navy">
              Available Checks
            </p>
            <ul className="space-y-2 text-[11px]">
              <li className="flex items-center gap-2 text-slate-600">
                <Check className="w-3.5 h-3.5 text-adcet-red" />
                Bloom's Taxonomy (K1 to K6)
              </li>
              <li className="flex items-center gap-2 text-slate-600">
                <Check className="w-3.5 h-3.5 text-adcet-red" />
                Configured Course Outcomes
              </li>
              <li className="flex items-center gap-2 text-slate-600">
                <Check className="w-3.5 h-3.5 text-adcet-red" />
                Configured Examination Pattern
              </li>
              <li className="flex items-center gap-2 text-slate-600">
                <Check className="w-3.5 h-3.5 text-adcet-red" />
                Subject-Specific Previous Paper Comparison
              </li>
            </ul>
          </div>

          {/* Col 4: Support */}
          <div>
            <p className="mb-4 border-b border-slate-200 pb-2 text-xs font-bold uppercase tracking-wider text-adcet-navy">
              Examination Cell
            </p>
            <div className="space-y-2.5 text-[11px] text-slate-600">
              <p className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-adcet-red shrink-0 mt-0.5" />
                <span>Annasaheb Dange College of Engineering & Technology, Ashta</span>
              </p>
              <p className="leading-relaxed">
                For access assistance, sign in with your authorized college account or contact your institution's examination cell.
              </p>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-10 pt-6 border-t border-slate-200 text-[11px] flex flex-col sm:flex-row items-center justify-between gap-3 text-slate-500">
          <p>© 2026 ADCET. AI Question Paper Scrutiny Decision Support System.</p>
          <p className="text-slate-500">AI-assisted analysis with deterministic academic checks</p>
        </div>
      </footer>

      {/* Interactive Authentication Modal */}
      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        initialTab={authTab}
      />
    </div>
  );
}
