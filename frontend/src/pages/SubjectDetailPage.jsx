import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { subjectsAPI } from '../services/api';
import { BookOpen, CheckCircle2, Save } from 'lucide-react';

export default function SubjectDetailPage() {
  const { id } = useParams();
  const [subject, setSubject] = useState(null);
  const [cos, setCos] = useState([]);
  const [syllabus, setSyllabus] = useState([]);
  const [rules, setRules] = useState({
    total_marks: 100,
    exam_duration_mins: 180,
    min_co_coverage: 80.0,
    min_unit_coverage: 80.0,
    similarity_threshold: 70.0
  });
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const loadSubjectData = async () => {
      try {
        const sRes = await subjectsAPI.get(id);
        setSubject(sRes.data);
        const coRes = await subjectsAPI.getCOs(id);
        setCos(coRes.data);
        const sylRes = await subjectsAPI.getSyllabus(id);
        setSyllabus(sylRes.data);
        try {
          const rRes = await subjectsAPI.getRules(id);
          setRules(rRes.data);
        } catch (e) {}
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadSubjectData();
  }, [id]);

  const handleSaveRules = async (e) => {
    e.preventDefault();
    try {
      await subjectsAPI.updateRules(id, rules);
      setMessage("Examination rules updated successfully.");
    } catch (err) {
      alert("Failed to update exam rules");
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Loading Subject Curriculum...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <h1 className="text-xl font-bold text-slate-900">{subject?.code} - {subject?.name}</h1>
        <p className="text-xs text-slate-500">Department: {subject?.department} | Semester: {subject?.semester}</p>
      </div>

      {message && (
        <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" /> {message}
        </div>
      )}

      {/* Course Outcomes */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <h3 className="font-bold text-slate-900 text-sm">Configured Course Outcomes (COs)</h3>
        <div className="space-y-2">
          {cos.map((co) => (
            <div key={co.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs flex items-center space-x-3">
              <span className="font-extrabold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-md">{co.co_code}</span>
              <span className="text-slate-800 font-medium">{co.description}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Examination Policy Rules Config */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="font-bold text-slate-900 text-sm">Configured Institutional Examination Policy Rules</h3>
        <form onSubmit={handleSaveRules} className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">Target Total Marks</label>
            <input
              type="number"
              value={rules.total_marks}
              onChange={(e) => setRules({ ...rules, total_marks: parseInt(e.target.value) })}
              className="w-full p-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">Exam Duration (Minutes)</label>
            <input
              type="number"
              value={rules.exam_duration_mins}
              onChange={(e) => setRules({ ...rules, exam_duration_mins: parseInt(e.target.value) })}
              className="w-full p-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">Min Course Outcome Coverage (%)</label>
            <input
              type="number"
              value={rules.min_co_coverage}
              onChange={(e) => setRules({ ...rules, min_co_coverage: parseFloat(e.target.value) })}
              className="w-full p-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">Min Syllabus Unit Coverage (%)</label>
            <input
              type="number"
              value={rules.min_unit_coverage}
              onChange={(e) => setRules({ ...rules, min_unit_coverage: parseFloat(e.target.value) })}
              className="w-full p-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">Similarity Flag Threshold (%)</label>
            <input
              type="number"
              value={rules.similarity_threshold}
              onChange={(e) => setRules({ ...rules, similarity_threshold: parseFloat(e.target.value) })}
              className="w-full p-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div className="col-span-2 pt-2">
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5"
            >
              <Save className="w-4 h-4" /> Save Examination Rules
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
