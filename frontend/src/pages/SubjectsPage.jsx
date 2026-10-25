import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { subjectsAPI } from '../services/api';
import { BookOpen, Plus, ExternalLink } from 'lucide-react';

export default function SubjectsPage() {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSubjects = async () => {
      try {
        const res = await subjectsAPI.list();
        setSubjects(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadSubjects();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Academic Subject & Curriculum Management</h1>
          <p className="text-sm text-slate-500">Manage Course Outcomes (COs), Syllabus Units, Topics, and Examination Policy Rules</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {subjects.map((s) => (
          <div key={s.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-1 bg-blue-100 text-blue-800 font-extrabold text-xs rounded-md">{s.code}</span>
              <span className="text-xs text-slate-500 font-medium">Sem {s.semester} | {s.branch}</span>
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">{s.name}</h3>
              <p className="text-xs text-slate-500 mt-1">Total Marks: {s.total_marks} | Duration: {s.exam_duration} Mins</p>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-600 font-medium">{s.course_outcomes?.length || 0} COs | {s.syllabus_units?.length || 0} Units</span>
              <Link
                to={`/subjects/${s.id}`}
                className="font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                Manage COs & Rules <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
