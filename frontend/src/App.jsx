import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import MainLayout from './layouts/MainLayout';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const UploadPaper = lazy(() => import('./pages/UploadPaper'));
const PaperScrutiny = lazy(() => import('./pages/PaperScrutiny'));
const PaperHistory = lazy(() => import('./pages/PaperHistory'));
const SubjectManagement = lazy(() => import('./pages/SubjectManagement'));
const SyllabusUploadPage = lazy(() => import('./pages/SyllabusUploadPage'));
const PreviousPapers = lazy(() => import('./pages/PreviousPapers'));
const FeedbackExport = lazy(() => import('./pages/FeedbackExport'));
const PapersListPage = lazy(() => import('./pages/PapersListPage'));
const ModeratorQueuePage = lazy(() => import('./pages/ModeratorQueuePage'));
const UsersAdminPage = lazy(() => import('./pages/UsersAdminPage'));
const Login = lazy(() => import('./pages/Login'));

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-adcet-cream text-slate-500">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-adcet-red border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium">Verifying credentials...</p>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RoleRoute({ allowedRoles, children }) {
  const { user } = useAuth();
  if (!allowedRoles.includes(user?.role)) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<div className="min-h-screen bg-adcet-cream px-6 py-16 text-center text-sm font-medium text-slate-500">Loading the examination portal…</div>}>
          <Routes>
            {/* Public College Landing Page */}
            <Route path="/" element={<LandingPage />} />

            {/* Dedicated Authentication Pages */}
            <Route path="/login" element={<Login initialTab="login" />} />
            <Route path="/register" element={<Login initialTab="register" />} />

            {/* Protected Application Workspace */}
            <Route
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/papers/upload" element={<UploadPaper />} />
            <Route path="/papers" element={<PapersListPage />} />
            <Route path="/syllabus" element={<RoleRoute allowedRoles={['FACULTY', 'MODERATOR', 'ADMIN']}><SyllabusUploadPage /></RoleRoute>} />
            <Route path="/papers/:id" element={<PaperScrutiny />} />
            <Route path="/history" element={<PaperHistory />} />
            <Route path="/subjects" element={<SubjectManagement />} />
            <Route path="/previous-papers" element={<PreviousPapers />} />
            <Route path="/moderator/queue" element={<RoleRoute allowedRoles={['MODERATOR', 'ADMIN']}><ModeratorQueuePage /></RoleRoute>} />
            <Route path="/moderator/feedback" element={<RoleRoute allowedRoles={['MODERATOR', 'ADMIN']}><FeedbackExport /></RoleRoute>} />
            <Route path="/admin/users" element={<RoleRoute allowedRoles={['ADMIN']}><UsersAdminPage /></RoleRoute>} />
            </Route>

            {/* Catch-all redirect to Landing Page */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
