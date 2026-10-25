import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/common/Badge';
import {
  LayoutDashboard, UploadCloud, History, BookOpen,
  LogOut, Sliders, Menu, X, Home, FolderSync, Database,
  FileText, ClipboardCheck, Users
} from 'lucide-react';

export default function MainLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isFaculty = user?.role === 'FACULTY';
  const isModerator = user?.role === 'MODERATOR';
  const isAdmin = user?.role === 'ADMIN';
  const canUpload = isFaculty || isModerator || isAdmin;

  const navClass = ({ isActive }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
      isActive
        ? 'bg-adcet-red text-white shadow-md shadow-red-200'
        : 'text-slate-600 hover:text-adcet-navy hover:bg-slate-100'
    }`;

  return (
    <div className="flex h-screen overflow-hidden bg-adcet-cream text-slate-800">
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-adcet-navy/40 z-30 md:hidden backdrop-blur-sm"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200 flex flex-col justify-between transition-transform duration-200 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div>
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => navigate('/dashboard')}>
              <img src="/images/college-logo.png" alt="ADCET" className="w-10 h-10 object-contain" />
              <div>
                <img src="/images/logo-ndcet.png" alt="ADCET" className="h-5 object-contain" />
                <p className="text-[9px] text-adcet-navy font-bold uppercase tracking-wide">Examination Portal</p>
              </div>
            </div>
            <button onClick={() => setMobileMenuOpen(false)} className="md:hidden text-slate-400">
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="p-3 space-y-1 overflow-y-auto max-h-[calc(100vh-160px)]">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 px-3 pb-1">Workspace</p>

            <NavLink to="/dashboard" className={navClass} onClick={() => setMobileMenuOpen(false)}>
              <LayoutDashboard className="w-4 h-4" /><span>Dashboard</span>
            </NavLink>

            {canUpload && (
              <>
                <NavLink to="/papers/upload" className={navClass} onClick={() => setMobileMenuOpen(false)}>
                  <UploadCloud className="w-4 h-4" /><span>Upload Paper</span>
                </NavLink>
                <NavLink to="/syllabus" className={navClass} onClick={() => setMobileMenuOpen(false)}>
                  <FolderSync className="w-4 h-4" /><span>Syllabus & CO Upload</span>
                </NavLink>
              </>
            )}

            <NavLink to="/papers" className={navClass} onClick={() => setMobileMenuOpen(false)}>
              <FileText className="w-4 h-4" /><span>All Question Papers</span>
            </NavLink>

            <NavLink to="/history" className={navClass} onClick={() => setMobileMenuOpen(false)}>
              <History className="w-4 h-4" /><span>Scrutiny History</span>
            </NavLink>

            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 px-3 pt-3 pb-1">Curriculum</p>

            <NavLink to="/subjects" className={navClass} onClick={() => setMobileMenuOpen(false)}>
              <BookOpen className="w-4 h-4" /><span>Subjects & Rules</span>
            </NavLink>

            <NavLink to="/previous-papers" className={navClass} onClick={() => setMobileMenuOpen(false)}>
              <Database className="w-4 h-4" /><span>Previous Papers</span>
            </NavLink>

            {(isModerator || isAdmin) && (
              <>
                <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 px-3 pt-3 pb-1">Moderator</p>
                <NavLink to="/moderator/queue" className={navClass} onClick={() => setMobileMenuOpen(false)}>
                  <ClipboardCheck className="w-4 h-4" /><span>Review Queue</span>
                </NavLink>
              </>
            )}

            {isAdmin && (
              <>
                <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 px-3 pt-3 pb-1">Administration</p>
                <NavLink to="/admin/users" className={navClass} onClick={() => setMobileMenuOpen(false)}>
                  <Users className="w-4 h-4" /><span>User Access</span>
                </NavLink>
              </>
            )}

            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 px-3 pt-3 pb-1">Institutional</p>
            <button
              onClick={() => navigate('/')}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-adcet-navy hover:bg-slate-100 transition-colors"
            >
              <Home className="w-4 h-4" /><span>College Home</span>
            </button>
          </nav>
        </div>

        <div className="p-3 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="truncate pr-2">
              <p className="text-xs font-bold truncate text-slate-900">{user?.full_name || 'User'}</p>
              <Badge status={user?.role || 'FACULTY'} />
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-adcet-red hover:bg-red-50 rounded-xl transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-14 border-b border-slate-200 bg-white px-4 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 text-slate-500 hover:text-adcet-navy"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="hidden sm:block">
              <p className="text-xs font-bold text-adcet-navy">ADCET — Question Paper Scrutiny System</p>
              <p className="text-[10px] text-slate-400">Annasaheb Dange College of Engineering & Technology</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="hidden sm:inline px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-200 font-semibold">
              Human-in-the-Loop
            </span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
