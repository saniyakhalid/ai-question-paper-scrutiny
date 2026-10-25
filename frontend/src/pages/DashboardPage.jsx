import React, { useState, useEffect } from 'react';
import { dashboardAPI } from '../services/api';
import { 
  FileText, Clock, CheckCircle2, AlertTriangle, XCircle, Award, 
  BarChart2, PieChart as PieIcon 
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend 
} from 'recharts';

const COLORS = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444'];

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const res = await dashboardAPI.getStats();
        setStats(res.data);
      } catch (err) {
        console.error("Failed to load dashboard stats", err);
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-500 font-medium">Loading Dashboard Analytics...</div>;
  }

  const cards = stats?.cards || {};
  const bloomData = stats?.charts?.bloom_distribution || [];
  const statusData = stats?.charts?.status_breakdown || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Scrutiny Executive Dashboard</h1>
        <p className="text-sm text-slate-500">Real-time scrutiny analytics, Bloom cognitive metrics & decision status</p>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><FileText className="w-5 h-5" /></div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{cards.total_papers || 0}</div>
            <div className="text-xs text-slate-500 font-medium">Total Papers</div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
          <div className="p-3 bg-amber-50 text-amber-600 rounded-lg"><Clock className="w-5 h-5" /></div>
          <div>
            <div className="text-2xl font-bold text-amber-600">{cards.pending_reviews || 0}</div>
            <div className="text-xs text-slate-500 font-medium">Pending Review</div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg"><CheckCircle2 className="w-5 h-5" /></div>
          <div>
            <div className="text-2xl font-bold text-emerald-600">{cards.approved || 0}</div>
            <div className="text-xs text-slate-500 font-medium">Approved</div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
          <div className="p-3 bg-orange-50 text-orange-600 rounded-lg"><AlertTriangle className="w-5 h-5" /></div>
          <div>
            <div className="text-2xl font-bold text-orange-600">{cards.needs_modification || 0}</div>
            <div className="text-xs text-slate-500 font-medium">Needs Modify</div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
          <div className="p-3 bg-red-50 text-red-600 rounded-lg"><XCircle className="w-5 h-5" /></div>
          <div>
            <div className="text-2xl font-bold text-red-600">{cards.rejected || 0}</div>
            <div className="text-xs text-slate-500 font-medium">Rejected</div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg"><Award className="w-5 h-5" /></div>
          <div>
            <div className="text-2xl font-bold text-purple-600">{cards.avg_scrutiny_score == null ? '—' : `${cards.avg_scrutiny_score}%`}</div>
            <div className="text-xs text-slate-500 font-medium">Avg DSS Score</div>
          </div>
        </div>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bloom Distribution Bar Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-blue-600" />
              Cognitive Level (Bloom Taxonomy) Distribution
            </h3>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bloomData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="level" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Paper Decision Breakdown Pie Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-emerald-600" />
              Paper Status Breakdown
            </h3>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
