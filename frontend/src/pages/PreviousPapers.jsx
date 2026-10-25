import React, { useEffect, useState } from 'react';
import api from '../services/api';
import {
  FileText, UploadCloud, Database, Plus, Search, Layers, CheckCircle2, AlertCircle, BookOpen, Sliders, Trash2
} from 'lucide-react';

export default function PreviousPapers() {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);

  // Upload Modal / Form State
  const [showModal, setShowModal] = useState(false);
  const [uploadSubjectId, setUploadSubjectId] = useState('');
  const [title, setTitle] = useState('');
  const [academicYear, setAcademicYear] = useState('2024-2025');
  const [examType, setExamType] = useState('End-Semester Examination');
  const [file, setFile] = useState(null);

  // Dynamic Units for Selected Subject
  const [availableUnits, setAvailableUnits] = useState([]);
  const [selectedUnits, setSelectedUnits] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSubjects();
  }, []);

  const fetchSubjects = () => {
    api.get('/subjects')
      .then((res) => {
        setSubjects(res.data);
        if (res.data.length > 0) {
          setSelectedSubjectId(res.data[0].id);
          fetchPapers(res.data[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  const fetchPapers = (subjectId) => {
    setLoading(true);
    const url = subjectId ? `/previous-papers?subject_id=${subjectId}` : '/previous-papers';
    api.get(url)
      .then((res) => setPapers(res.data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  const handleSubjectFilterChange = (sId) => {
    const sIdNum = parseInt(sId);
    setSelectedSubjectId(sIdNum);
    fetchPapers(sIdNum);
  };

  const handleUploadSubjectChange = (sId) => {
    const sIdNum = parseInt(sId);
    setUploadSubjectId(sIdNum);

    api.get(`/subjects/${sIdNum}/syllabus`)
      .then((res) => {
        const uNums = res.data.map((u) => u.unit_number);
        setAvailableUnits(uNums);
        setSelectedUnits(uNums);
      })
      .catch(() => {
        setAvailableUnits([]);
        setSelectedUnits([]);
      });
  };

  const openUploadModal = () => {
    const defaultSubjId = selectedSubjectId || (subjects.length > 0 ? subjects[0].id : '');
    setUploadSubjectId(defaultSubjId);
    if (defaultSubjId) {
      handleUploadSubjectChange(defaultSubjId);
    }
    setTitle('');
    setFile(null);
    setError('');
    setShowModal(true);
  };

  const toggleUnit = (uNum) => {
    setSelectedUnits((prev) =>
      prev.includes(uNum) ? prev.filter((u) => u !== uNum) : [...prev, uNum].sort((a, b) => a - b)
    );
  };

  const handleUploadPreviousPaper = async (e) => {
    e.preventDefault();
    if (!file || !uploadSubjectId) {
      setError('Please select a subject and upload a question paper file.');
      return;
    }

    setError('');
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('subject_id', uploadSubjectId);
      formData.append('title', title || file.name.replace(/\.[^/.]+$/, ""));
      formData.append('academic_year', academicYear);
      formData.append('exam_type', examType);
      formData.append('selected_units', JSON.stringify(selectedUnits));
      formData.append('file', file);

      const res = await api.post('/previous-papers/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setUploading(false);
      setShowModal(false);
      setSuccessMessage('Question paper uploaded and indexed successfully.');

      // Refresh paper list immediately
      fetchPapers(selectedSubjectId || uploadSubjectId);

      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setUploading(false);
      setError(err.response?.data?.detail || 'Failed to upload and index question paper.');
    }
  };

  const handleDeletePaper = async (paperId) => {
    if (!window.confirm('Delete this historical question paper and its vector embeddings?')) return;
    try {
      await api.delete(`/previous-papers/${paperId}`);
      fetchPapers(selectedSubjectId);
    } catch (err) {
      alert('Failed to delete previous question paper');
    }
  };

  const selectedSubjectObj = subjects.find((s) => s.id === parseInt(selectedSubjectId));

  if (loading && subjects.length === 0) {
    return <div className="p-8 text-center text-slate-500 dark:text-slate-400">Loading Previous Papers...</div>;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Previous Papers</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Store subject-specific historical papers for TF-IDF similarity review. This is not a separately curated question bank.
          </p>
        </div>

        {subjects.length > 0 && (
          <button
            onClick={openUploadModal}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-lg shadow-indigo-600/30 flex items-center space-x-2 shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>+ Upload Previous Paper</span>
          </button>
        )}
      </div>

      {/* Success Notification Banner */}
      {successMessage && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center shadow-lg">
          <CheckCircle2 className="w-5 h-5 mr-2 flex-shrink-0" />
          <span className="font-semibold">{successMessage}</span>
        </div>
      )}

      {/* Subject Filter Selector */}
      {subjects.length > 0 && (
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <BookOpen className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-bold text-slate-900 dark:text-white">Select Subject Workspace:</span>
          </div>

          <select
            value={selectedSubjectId}
            onChange={(e) => handleSubjectFilterChange(e.target.value)}
            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-900 dark:text-white font-semibold focus:outline-none focus:border-indigo-500 max-w-md"
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                [{s.code}] {s.name} ({s.branch})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Main Papers List */}
      {papers.length === 0 ? (
        /* Empty State */
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center space-y-4 max-w-2xl mx-auto my-8">
          <div className="w-12 h-12 bg-indigo-600/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center mx-auto text-indigo-400">
            <Database className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">No previous question papers uploaded yet.</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Upload a previous paper to enable same-subject historical comparison.
            </p>
          </div>

          {subjects.length > 0 ? (
            <button
              onClick={openUploadModal}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-lg shadow-indigo-600/30 inline-flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>+ Upload Previous Paper</span>
            </button>
          ) : (
            <p className="text-xs text-slate-500 italic">Create a subject in 'Subjects & Curriculum' first to upload previous question papers.</p>
          )}
        </div>
      ) : (
        /* Paper Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {papers.map((p) => (
            <div key={p.id} className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4 hover:border-slate-300 dark:border-slate-700 transition-all relative">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="px-2.5 py-0.5 bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-mono text-[10px] font-bold rounded-md">
                    {p.academic_year} | {p.exam_type}
                  </span>
                  <h3 className="font-bold text-slate-900 dark:text-white text-sm">{p.title}</h3>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono px-2 py-0.5 bg-slate-50 dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800">
                    {p.questions?.length || 0} Questions Indexed
                  </span>
                  <button
                    onClick={() => handleDeletePaper(p.id)}
                    className="p-1 text-slate-500 dark:text-slate-400 hover:text-rose-400 hover:bg-slate-50 dark:bg-slate-950 rounded-lg transition-colors"
                    title="Delete Question Paper"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Indexed Question Snippets */}
              {p.questions && p.questions.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800/80">
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Indexed Questions in Vector Bank:</label>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                    {p.questions.map((q, idx) => (
                      <div key={q.id || idx} className="p-2 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800/60 text-xs flex items-start space-x-2">
                        <span className="font-mono text-indigo-400 font-bold shrink-0">{q.question_number || `Q${idx+1}`}:</span>
                        <span className="text-slate-700 dark:text-slate-300 line-clamp-2">{q.question_text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload Previous Question Paper Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-50 dark:bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleUploadPreviousPaper} className="bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center">
                <UploadCloud className="w-4 h-4 mr-2 text-indigo-400" />
                <span>Upload Previous Question Paper</span>
              </h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:text-white">
                ✕
              </button>
            </div>

            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center">
                <AlertCircle className="w-4 h-4 mr-2 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 mb-1 font-semibold">Select Subject</label>
                <select
                  value={uploadSubjectId}
                  onChange={(e) => handleUploadSubjectChange(e.target.value)}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 text-slate-900 dark:text-white font-semibold"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      [{s.code}] {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 mb-1 font-semibold font-mono">Paper Title</label>
                <input
                  type="text"
                  placeholder="e.g. 2024-25 End Semester Question Paper"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 text-slate-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 mb-1 font-semibold">Academic Year</label>
                  <input
                    type="text"
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                    required
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-2 text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 mb-1 font-semibold">Examination Type</label>
                  <select
                    value={examType}
                    onChange={(e) => setExamType(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-2 text-slate-900 dark:text-white"
                  >
                    <option value="End-Semester Examination">End-Semester Examination</option>
                    <option value="Mid-Semester Examination">Mid-Semester Examination</option>
                    <option value="Internal 1">Internal 1</option>
                    <option value="Internal 2">Internal 2</option>
                  </select>
                </div>
              </div>

              {/* Dynamic Applicable Units */}
              {availableUnits.length > 0 && (
                <div className="space-y-1.5 p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl">
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold text-[11px]">Applicable Examination Units:</label>
                  <div className="flex flex-wrap gap-2">
                    {availableUnits.map((uNum) => {
                      const checked = selectedUnits.includes(uNum);
                      return (
                        <button
                          key={uNum}
                          type="button"
                          onClick={() => toggleUnit(uNum)}
                          className={`px-2.5 py-1 rounded-lg border text-xs font-semibold transition-all ${
                            checked
                              ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300'
                              : 'bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400'
                          }`}
                        >
                          Unit {uNum} {checked && '✓'}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-slate-700 dark:text-slate-300 mb-1 font-semibold">Upload Question Paper File (PDF / DOCX)</label>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setFile(e.target.files[0])}
                  required
                  className="w-full text-slate-500 dark:text-slate-400 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold rounded-xl text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-xs disabled:opacity-50 flex items-center space-x-1"
              >
                {uploading ? 'Processing & Indexing...' : 'Upload and Index Question Paper'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
