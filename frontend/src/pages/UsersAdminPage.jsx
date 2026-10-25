import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { AlertCircle, Users, Plus, X, Loader2, CheckCircle2 } from 'lucide-react';

export default function UsersAdminPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [newUser, setNewUser] = useState({ full_name: '', email: '', department: '', role: 'MODERATOR', password: '' });

  useEffect(() => {
    let active = true;
    api.get('/admin/users')
      .then(({ data }) => { if (active) setUsers(data || []); })
      .catch((err) => { if (active) setError(err.response?.data?.detail || 'Could not load user accounts.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const handleCreateUser = async (event) => {
    event.preventDefault();
    setCreating(true);
    setCreateError('');
    setCreateSuccess('');
    try {
      const { data } = await api.post('/admin/users', newUser);
      setUsers((current) => [data, ...current]);
      setCreateSuccess(`${data.role} account created for ${data.full_name}. They can sign in using the role option on the login screen.`);
      setNewUser({ full_name: '', email: '', department: '', role: 'MODERATOR', password: '' });
      setShowCreateForm(false);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setCreateError(typeof detail === 'string' ? detail : 'Could not create this account. Check the fields and try again.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-adcet-red">Administration</p>
          <h1 className="mt-1 text-2xl font-bold text-adcet-navy">User access</h1>
          <p className="mt-1 text-sm text-slate-500">Review accounts and provision faculty, moderator, or administrator access.</p>
        </div>
        <button type="button" onClick={() => { setShowCreateForm((open) => !open); setCreateError(''); setCreateSuccess(''); }} className="inline-flex items-center justify-center gap-2 rounded-xl bg-adcet-red px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-red-700">
          {showCreateForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showCreateForm ? 'Cancel' : 'Create account'}
        </button>
      </header>

      {error && <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><AlertCircle className="h-4 w-4" />{error}</div>}
      {createSuccess && <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><CheckCircle2 className="h-4 w-4" />{createSuccess}</div>}
      {createError && <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><AlertCircle className="h-4 w-4" />{createError}</div>}

      {showCreateForm && (
        <form onSubmit={handleCreateUser} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div>
            <h2 className="text-sm font-bold text-adcet-navy">Create a portal account</h2>
            <p className="mt-1 text-xs text-slate-500">The selected role is saved by the server and checked at every protected endpoint.</p>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-xs font-semibold text-slate-700">Full name
              <input required autoComplete="name" value={newUser.full_name} onChange={(event) => setNewUser((current) => ({ ...current, full_name: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal outline-none focus:border-adcet-red" />
            </label>
            <label className="space-y-1 text-xs font-semibold text-slate-700">Institution email
              <input required type="email" autoComplete="email" value={newUser.email} onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal outline-none focus:border-adcet-red" />
            </label>
            <label className="space-y-1 text-xs font-semibold text-slate-700">Department
              <input required value={newUser.department} onChange={(event) => setNewUser((current) => ({ ...current, department: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal outline-none focus:border-adcet-red" />
            </label>
            <label className="space-y-1 text-xs font-semibold text-slate-700">Role
              <select value={newUser.role} onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal outline-none focus:border-adcet-red">
                <option value="FACULTY">Faculty</option>
                <option value="MODERATOR">Moderator</option>
                <option value="ADMIN">Administrator</option>
              </select>
            </label>
            <label className="space-y-1 text-xs font-semibold text-slate-700 sm:col-span-2">Temporary password (at least 8 characters)
              <input required type="password" minLength={8} autoComplete="new-password" value={newUser.password} onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal outline-none focus:border-adcet-red" />
            </label>
          </div>
          <div className="flex justify-end">
            <button type="submit" disabled={creating} className="inline-flex items-center gap-2 rounded-xl bg-adcet-navy px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-50">
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              {creating ? 'Creating account…' : 'Create account'}
            </button>
          </div>
        </form>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? <div className="p-10 text-center text-sm text-slate-500">Loading user accounts…</div> : error ? null : users.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="mx-auto h-10 w-10 text-slate-300" />
            <p className="mt-3 font-semibold text-slate-800">No user accounts found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr><th className="px-5 py-3">Account</th><th className="px-5 py-3">Email</th><th className="px-5 py-3">Department</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Status</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50/70">
                    <td className="px-5 py-4"><p className="font-semibold text-slate-900">{user.full_name || '—'}</p><p className="text-xs text-slate-400">Account #{user.id}</p></td>
                    <td className="px-5 py-4 text-slate-600">{user.email}</td>
                    <td className="px-5 py-4 text-slate-600">{user.department || '—'}</td>
                    <td className="px-5 py-4"><span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">{user.role}</span></td>
                    <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${user.is_active === false ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'}`}>{user.is_active === false ? 'Inactive' : 'Active'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
