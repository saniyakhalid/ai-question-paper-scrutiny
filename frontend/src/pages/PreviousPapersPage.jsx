import React, { useState, useEffect } from 'react';
import { previousPapersAPI, subjectsAPI } from '../services/api';
import { Database, Upload, FileText, CheckCircle2 } from 'lucide-react';

export default function PreviousPapersPage() {
  const [prevPapers, setPrevPapers] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [year, setYear] = useState('2025');
  const [examType, setExamType] = useState('End-Sem');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const loadData = async () => {
    try {
      const pRes = await previousPapersAPI.list();
      setPrevPapers(pRes.data);
      const sRes = await subjectsAPI.list();
      setSubjects(sRes.data);
      if (sRes.data.length > 0) setSelectedSubject(sRes.data[0].id);
    } catch (err) {
      console.error("Failed to load previous papers", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.append('subject_id', selectedSubject);
    formData.append('year', year);
    formData.append('exam_type', examType);
    formData.append('file', file);

    try {
      const res = await previousPapersAPI.upload(formData);
      setMessage(res.data.message);
      setFile(null);
      loadData();
    } catch (err) {
      alert("Failed to upload previous paper");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Previous Exam Question Papers Repository</h1>
        <p className="text-sm text-slate-500">Upload historical exam papers to auto-index questions for semantic similarity & duplication detection</p>
      </div>

      {message && (
        <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" /> {message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 text-sm">Upload Reference Paper</h3>
          <form onSubmit={handleUpload} className="space-y-4 text-xs">
            <div>
              <label className="block font-medium text-slate-700">Subject</label>
              <select
                value={selectedSubject}
                onChange={(e) => setSelectedSubject(e.target.value)}
                className="mt-1 w-full p-2 border border-slate-300 rounded-lg"
              >
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700">Year</label>
              <input
                type="text"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="mt-1 w-full p-2 border border-slate-300 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700">Exam Type</label>
              <input
                type="text"
                value={examType}
                onChange={(e) => setExamType(e.target.value)}
                className="mt-1 w-full p-2 border border-slate-300 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700">File (PDF / DOCX)</label>
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => e.target.files && setFile(e.target.files[0])}
                className="mt-1 w-full text-xs"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg"
            >
              Upload & Index Questions
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600">
              <tr>
                <th className="p-3">Paper ID</th>
                <th className="p-3">Filename</th>
                <th className="p-3">Year</th>
                <th className="p-3">Exam Type</th>
                <th className="p-3">Questions Indexed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {prevPapers.map((p) => (
                <tr key={p.id}>
                  <td className="p-3 font-mono font-bold text-slate-700">#PREV-{p.id}</td>
                  <td className="p-3 font-medium text-slate-900">{p.filename}</td>
                  <td className="p-3 text-slate-600">{p.year}</td>
                  <td className="p-3 text-slate-600">{p.exam_type}</td>
                  <td className="p-3 font-semibold text-blue-600">{p.questions ? p.questions.length : 5} Questions</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
