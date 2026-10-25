import React, { useEffect, useRef, useState } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { downloadDocument } from '../utils/downloadDocument';
import Badge from '../components/common/Badge';
import ConfirmModal from '../components/common/ConfirmModal';
import {
  UploadCloud, FileText, CheckCircle2, AlertTriangle, Trash2, Download,
  Layers, BookOpen, Loader2, RefreshCw, ChevronRight, Eye,
  Plus, X, PlusCircle, Edit3
} from 'lucide-react';

export default function SyllabusUploadPage() {
  const { user } = useAuth();
  const canUpload = user?.role === 'FACULTY' || user?.role === 'MODERATOR' || user?.role === 'ADMIN';
  const canManage = user?.role === 'FACULTY' || user?.role === 'MODERATOR' || user?.role === 'ADMIN';
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [syllabusStatus, setSyllabusStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(false);

  // Dynamic 1 or more COs state on Syllabus Page
  const [showAddCoModal, setShowAddCoModal] = useState(false);
  const [coRows, setCoRows] = useState([]);
  const [savingCos, setSavingCos] = useState(false);
  const [coFeedback, setCoFeedback] = useState({ type: '', text: '' });
  const [editingCo, setEditingCo] = useState(null);
  const [savingEditCo, setSavingEditCo] = useState(false);

  // Upload Form State
  const [file, setFile] = useState(null);
  const [academicYear, setAcademicYear] = useState('');
  const [replaceExisting, setReplaceExisting] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState('');
  const [uploadError, setUploadError] = useState('');

  // Delete Modal State
  const [deleteDocId, setDeleteDocId] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Active view tab: 'units' | 'cos'
  const [activeTab, setActiveTab] = useState('units');
  const statusRequestId = useRef(0);

  useEffect(() => {
    fetchSubjects();
  }, []);

  const fetchSubjects = async () => {
    try {
      setLoading(true);
      const res = await api.get('/subjects');
      const data = res.data || [];
      setSubjects(data);
      if (data.length > 0) {
        setSelectedSubjectId(data[0].id);
        setAcademicYear(data[0].academic_year || '');
        fetchSyllabusStatus(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load subjects:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSyllabusStatus = async (subjId) => {
    if (!subjId) return;
    const requestId = ++statusRequestId.current;
    try {
      setStatusLoading(true);
      const res = await api.get(`/subjects/${subjId}/syllabus/status`);
      if (requestId === statusRequestId.current) setSyllabusStatus(res.data);
    } catch (err) {
      console.error('Failed to load syllabus status:', err);
      if (requestId === statusRequestId.current) setSyllabusStatus(null);
    } finally {
      if (requestId === statusRequestId.current) setStatusLoading(false);
    }
  };

  const handleSubjectChange = (e) => {
    const subjId = e.target.value;
    setSelectedSubjectId(subjId);
    setSyllabusStatus(null);
    setShowAddCoModal(false);
    setCoRows([]);
    setCoFeedback({ type: '', text: '' });
    setAcademicYear(subjects.find((subject) => String(subject.id) === String(subjId))?.academic_year || '');
    setUploadSuccess('');
    setUploadError('');
    setFile(null);
    fetchSyllabusStatus(subjId);
  };

  const handleOpenAddCoModal = () => {
    const existingCos = syllabusStatus?.course_outcomes || [];
    let highest = 0;
    existingCos.forEach((c) => {
      const m = c.co_code && c.co_code.match(/CO(\d+)/i);
      if (m) {
        const val = parseInt(m[1]);
        if (val > highest) highest = val;
      }
    });
    setCoRows([{ co_code: `CO${highest + 1}`, description: '' }]);
    setCoFeedback({ type: '', text: '' });
    setShowAddCoModal(true);
  };

  const handleAddCoRow = () => {
    const existingCos = syllabusStatus?.course_outcomes || [];
    const allCodes = [...existingCos.map((c) => c.co_code), ...coRows.map((r) => r.co_code)];
    let highest = 0;
    allCodes.forEach((c) => {
      const m = c && c.match(/CO(\d+)/i);
      if (m) {
        const val = parseInt(m[1]);
        if (val > highest) highest = val;
      }
    });
    setCoRows([...coRows, { co_code: `CO${highest + 1}`, description: '' }]);
  };

  const handleRemoveCoRow = (idx) => {
    setCoRows(coRows.filter((_, i) => i !== idx));
  };

  const handleUpdateCoRow = (idx, field, val) => {
    const updated = [...coRows];
    updated[idx][field] = val;
    setCoRows(updated);
  };

  const handleSaveCos = async (e) => {
    e.preventDefault();
    if (!selectedSubjectId) return;
    const validRows = coRows.filter((r) => r.co_code.trim() && r.description.trim());
    if (validRows.length === 0) {
      setCoFeedback({ type: 'error', text: 'Please fill in at least 1 Course Outcome.' });
      return;
    }
    setSavingCos(true);
    setCoFeedback({ type: '', text: '' });
    try {
      await api.post(`/subjects/${selectedSubjectId}/cos/batch`, {
        cos: validRows.map((r) => ({ co_code: r.co_code.trim(), description: r.description.trim() }))
      });
      fetchSyllabusStatus(selectedSubjectId);
      setShowAddCoModal(false);
    } catch (err) {
      try {
        for (const row of validRows) {
          await api.post(`/subjects/${selectedSubjectId}/cos`, {
            co_code: row.co_code.trim(),
            description: row.description.trim()
          });
        }
        fetchSyllabusStatus(selectedSubjectId);
        setShowAddCoModal(false);
      } catch (innerErr) {
        setCoFeedback({ type: 'error', text: 'Failed to save Course Outcomes.' });
      }
    } finally {
      setSavingCos(false);
    }
  };

  const handleDeleteCo = async (coId) => {
    if (!window.confirm('Delete this Course Outcome?')) return;
    try {
      await api.delete(`/subjects/${selectedSubjectId}/cos/${coId}`);
      fetchSyllabusStatus(selectedSubjectId);
    } catch (err) {
      alert('Failed to delete Course Outcome');
    }
  };

  const handleSaveEditCo = async (e) => {
    e.preventDefault();
    if (!editingCo || !selectedSubjectId) return;
    setSavingEditCo(true);
    try {
      await api.put(`/subjects/${selectedSubjectId}/cos/${editingCo.id}`, {
        co_code: editingCo.co_code.trim(),
        description: editingCo.description.trim()
      });
      setEditingCo(null);
      fetchSyllabusStatus(selectedSubjectId);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update Course Outcome');
    } finally {
      setSavingEditCo(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file || !selectedSubjectId) {
      setUploadError('Please select a syllabus file (PDF, DOCX, TXT).');
      return;
    }

    setUploading(true);
    setUploadSuccess('');
    setUploadError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('academic_year', academicYear);
    formData.append('replace_existing', replaceExisting);

    try {
      const res = await api.post(`/subjects/${selectedSubjectId}/syllabus/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadSuccess(res.data?.message || 'Syllabus successfully uploaded and processed.');
      setFile(null);
      fetchSyllabusStatus(selectedSubjectId);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setUploadError(typeof detail === 'string' ? detail : 'Failed to upload and parse syllabus document.');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async () => {
    if (!deleteDocId || !selectedSubjectId) return;
    setDeleting(true);
    try {
      await api.delete(`/subjects/${selectedSubjectId}/syllabus/documents/${deleteDocId}`);
      setDeleteDocId(null);
      fetchSyllabusStatus(selectedSubjectId);
      setUploadSuccess('Syllabus document removed successfully.');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setUploadError(typeof detail === 'string' ? detail : 'Failed to remove syllabus document.');
    } finally {
      setDeleting(false);
    }
  };

  const selectedSubject = subjects.find((s) => String(s.id) === String(selectedSubjectId));

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-500 dark:text-slate-400">
        Loading Subject Syllabus Configuration...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              Subject Syllabus Library
            </h1>
            <Badge variant="info">Subject Isolated</Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {canUpload
              ? 'Upload the official syllabus for your subject. Moderators and administrators can review and download faculty uploads.'
              : 'Review faculty syllabus uploads by subject, download the source files, and inspect the extracted curriculum.'}
          </p>
        </div>

        {/* Subject Selector */}
        <div className="flex items-center space-x-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-2.5 rounded-xl text-xs">
          <BookOpen className="w-4 h-4 text-brand-600 dark:text-indigo-400 shrink-0" />
          <span className="text-slate-500 dark:text-slate-400 font-semibold shrink-0">Subject:</span>
          <select
            value={selectedSubjectId}
            onChange={handleSubjectChange}
            className="bg-transparent text-slate-900 dark:text-white font-bold focus:outline-none cursor-pointer"
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                [{s.code}] {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Notifications */}
      {uploadSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
          <button onClick={() => setUploadSuccess('')} className="text-emerald-500 hover:text-emerald-700">✕</button>
        </div>
      )}

      {uploadError && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-700 dark:text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
          <button onClick={() => setUploadError('')} className="text-rose-500 hover:text-rose-700">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Upload Form & Active Document Status */}
        <div className="lg:col-span-5 space-y-6">
          {/* Active Syllabus Status Card */}
          <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2">
                <FileText className="w-4 h-4 text-brand-600 dark:text-indigo-400" />
                <span>Active Syllabus Status</span>
              </h2>
              {syllabusStatus?.has_uploaded_syllabus ? (
                <Badge variant="success">Active in Scrutiny</Badge>
              ) : (
                <Badge variant="warning">No Document Uploaded</Badge>
              )}
            </div>

            {statusLoading ? (
              <div className="py-6 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                <span>Checking subject syllabus...</span>
              </div>
            ) : syllabusStatus?.documents?.length ? (
              <div className="space-y-3">
                {syllabusStatus.documents.map((doc) => (
                  <div key={doc.id} className="p-3.5 bg-slate-50 dark:bg-slate-950/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-bold text-xs text-slate-900 dark:text-white truncate max-w-[200px]" title={doc.filename}>
                          {doc.filename}
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                          Academic Year: {doc.academic_year || 'Not specified'} • Type: {doc.file_type?.toUpperCase()} • Uploaded by: {doc.uploaded_by_name || 'Faculty'}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => downloadDocument(`/subjects/${selectedSubjectId}/syllabus/documents/${doc.id}/download`, doc.filename).catch(() => setUploadError('Could not download this syllabus file.'))}
                          className="p-1.5 text-adcet-navy hover:bg-slate-200 rounded-lg transition-colors"
                          title="Download syllabus"
                          aria-label={`Download ${doc.filename}`}
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        {(canManage || (canUpload && doc.uploaded_by_id === user?.id)) && (
                          <button
                            type="button"
                            onClick={() => setDeleteDocId(doc.id)}
                            className="p-1.5 text-rose-500 hover:bg-rose-500/10 rounded-lg transition-colors"
                            title="Delete syllabus document"
                            aria-label={`Delete ${doc.filename}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-slate-200 dark:border-slate-800">
                      <div>
                        <span className="text-slate-500 dark:text-slate-400">Extracted Units:</span>{' '}
                        <strong className="text-brand-600 dark:text-indigo-400">{doc.unit_count ?? syllabusStatus.unit_count}</strong>
                      </div>
                      <div>
                        <span className="text-slate-500 dark:text-slate-400">Extracted COs:</span>{' '}
                        <strong className="text-emerald-600 dark:text-emerald-400">{doc.co_count ?? syllabusStatus.co_count}</strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-3 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800">
                No official syllabus document has been uploaded for {selectedSubject?.code || 'this subject'}. Upload a file below to populate units and Course Outcomes.
              </p>
            )}
          </div>

          {/* Faculty Upload Form */}
          {canUpload ? <form onSubmit={handleUploadSubmit} className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl space-y-4">
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <UploadCloud className="w-4 h-4 text-brand-600 dark:text-indigo-400" />
              <span>Upload Official Syllabus File</span>
            </h2>

            {/* Drag & Drop File Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-brand-500 dark:hover:border-indigo-500 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-slate-50 dark:bg-slate-950/60"
              onClick={() => document.getElementById('syllabus-file-input').click()}
            >
              <input
                id="syllabus-file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setFile(e.target.files[0]);
                  }
                }}
              />
              <div className="mx-auto w-10 h-10 rounded-xl bg-brand-50 dark:bg-indigo-950/80 text-brand-600 dark:text-indigo-400 flex items-center justify-center mb-3">
                <UploadCloud className="w-5 h-5" />
              </div>
              {file ? (
                <div>
                  <p className="text-xs font-bold text-slate-900 dark:text-white">{file.name}</p>
                  <p className="text-[10px] text-slate-500 mt-1">{(file.size / 1024).toFixed(1)} KB • Click to change</p>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                    Click to select syllabus document or drag & drop
                  </p>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">
                    Supported formats: PDF, DOCX, TXT
                  </p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">Academic Year</label>
                <input
                  type="text"
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-brand-600"
                  placeholder="Enter the academic year"
                />
              </div>

              <div className="flex items-center pt-5">
                <label className="flex items-center space-x-2 cursor-pointer text-xs text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={replaceExisting}
                    onChange={(e) => setReplaceExisting(e.target.checked)}
                    className="rounded text-brand-600 focus:ring-0 cursor-pointer"
                  />
                  <span>Replace existing curriculum</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-brand-600/20 flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Parsing & Storing Curriculum in MongoDB...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload & Process Syllabus</span>
                </>
              )}
            </button>
          </form> : (
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-xs leading-relaxed text-blue-900">
              Faculty upload official syllabus documents here. This subject’s uploaded syllabus is available above for review and download.
            </div>
          )}
        </div>

        {/* Right Column: Extracted Curriculum Breakdown */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden">
            {/* Header & Tabs */}
            <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 dark:bg-slate-950/40">
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  {selectedSubject?.code} Curriculum Structure
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {syllabusStatus?.unit_count ?? 0} Units • {syllabusStatus?.co_count ?? 0} Course Outcomes
                </p>
              </div>

              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('units')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    activeTab === 'units'
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Units ({syllabusStatus?.unit_count ?? 0})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('cos')}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    activeTab === 'cos'
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Course Outcomes ({syllabusStatus?.co_count ?? 0})</span>
                </button>
              </div>
            </div>

            {/* TAB CONTENT: UNITS */}
            {activeTab === 'units' && (
              <div className="p-5 space-y-4 max-h-[600px] overflow-y-auto">
                {(!syllabusStatus?.units || syllabusStatus.units.length === 0) ? (
                  <p className="text-xs text-slate-500 italic text-center py-8">
                    No syllabus units configured yet. Upload a syllabus document to automatically extract and populate units and topics.
                  </p>
                ) : (
                  syllabusStatus.units.map((unit) => (
                    <div
                      key={unit.id || unit.unit_number}
                      className="p-4 bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="px-2.5 py-0.5 rounded-lg text-xs font-mono font-bold bg-brand-600/10 border border-brand-600/20 text-brand-600 dark:text-indigo-400">
                          Unit {unit.unit_number}
                        </span>
                        <span className="text-[11px] text-slate-400 font-medium">
                          {(unit.topics || []).length} Topics
                        </span>
                      </div>

                      <h3 className="text-xs font-bold text-slate-900 dark:text-white">
                        {unit.title || `Unit ${unit.unit_number}`}
                      </h3>

                      {unit.description && (
                        <p className="text-[11px] text-slate-600 dark:text-slate-400">{unit.description}</p>
                      )}

                      {unit.topics && unit.topics.length > 0 && (
                        <div className="pt-2 flex flex-wrap gap-1.5 border-t border-slate-200 dark:border-slate-800/80">
                          {unit.topics.map((t, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 text-[11px] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800"
                            >
                              {t.topic_name || t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* TAB CONTENT: COURSE OUTCOMES */}
            {activeTab === 'cos' && (
              <div className="p-5 space-y-4 max-h-[600px] overflow-y-auto">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                      Subject Course Outcomes ({syllabusStatus?.course_outcomes?.length || 0})
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Evaluated during automated Bloom&apos;s Taxonomy analysis.
                    </p>
                  </div>
                  {canManage && (
                    <button
                      type="button"
                      onClick={handleOpenAddCoModal}
                      className="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>+ Add Course Outcome(s)</span>
                    </button>
                  )}
                </div>

                {(!syllabusStatus?.course_outcomes || syllabusStatus.course_outcomes.length === 0) ? (
                  <div className="text-center py-8 space-y-3">
                    <p className="text-xs text-slate-500 italic">
                      No Course Outcomes configured or extracted yet for this subject.
                    </p>
                    {canManage && (
                      <button
                        type="button"
                        onClick={handleOpenAddCoModal}
                        className="px-4 py-2 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 text-indigo-700 dark:text-indigo-300 rounded-xl text-xs font-semibold inline-flex items-center gap-1.5 transition-colors"
                      >
                        <PlusCircle className="w-4 h-4 text-indigo-500" />
                        <span>Add 1 or More Course Outcomes Now</span>
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {syllabusStatus.course_outcomes.map((co) => (
                      <div
                        key={co.id || co.co_code}
                        className="p-3.5 bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 rounded-xl flex items-start justify-between gap-3 text-xs"
                      >
                        <div className="flex items-start space-x-3">
                          <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 px-2 py-0.5 bg-emerald-500/10 rounded border border-emerald-500/30 shrink-0">
                            {co.co_code}
                          </span>
                          <p className="text-slate-700 dark:text-slate-300 text-xs leading-relaxed">{co.description}</p>
                        </div>
                        {canManage && co.id && (
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              type="button"
                              onClick={() => setEditingCo({ id: co.id, co_code: co.co_code, description: co.description })}
                              className="p-1 text-slate-400 hover:text-adcet-navy dark:hover:text-white rounded"
                              title="Edit Course Outcome"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteCo(co.id)}
                              className="p-1 text-slate-400 hover:text-rose-500 rounded"
                              title="Delete Course Outcome"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Dynamic 1 or More Course Outcomes Modal */}
      {canManage && showAddCoModal && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <PlusCircle className="w-5 h-5 text-brand-600 dark:text-indigo-400" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Add Course Outcomes (COs)
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Add 1 or more Course Outcomes for {selectedSubject?.code || 'this subject'}.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowAddCoModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {coFeedback.text && (
              <div
                className={`p-3 rounded-xl text-xs font-semibold ${
                  coFeedback.type === 'error'
                    ? 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                    : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                }`}
              >
                {coFeedback.text}
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Course Outcome Items ({coRows.length})
              </span>
            </div>

            <form onSubmit={handleSaveCos} className="space-y-3">
              <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                {coRows.map((row, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center gap-2"
                  >
                    <input
                      type="text"
                      placeholder="CO1"
                      value={row.co_code}
                      onChange={(e) => handleUpdateCoRow(idx, 'co_code', e.target.value)}
                      required
                      className="w-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-2 text-xs font-mono font-bold text-brand-600 dark:text-indigo-400 focus:outline-none focus:border-brand-500"
                    />
                    <input
                      type="text"
                      placeholder="Course Outcome Description..."
                      value={row.description}
                      onChange={(e) => handleUpdateCoRow(idx, 'description', e.target.value)}
                      required
                      className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-brand-500"
                    />
                    {coRows.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveCoRow(idx)}
                        className="p-1.5 text-slate-400 hover:text-rose-500 rounded"
                        title="Remove row"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={handleAddCoRow}
                className="w-full py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border border-slate-200 dark:border-slate-700 transition-colors"
              >
                <Plus className="w-4 h-4 text-emerald-500" />
                <span>+ Add Another Course Outcome Row</span>
              </button>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddCoModal(false)}
                  className="px-4 py-2 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingCos}
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md shadow-brand-600/20 disabled:opacity-50"
                >
                  {savingCos ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Save {coRows.length} Course Outcome{coRows.length > 1 ? 's' : ''}</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Single Course Outcome Modal */}
      {editingCo && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-adcet-navy dark:text-indigo-400" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Edit Course Outcome
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Update code or description for this outcome.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEditingCo(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEditCo} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  CO Code
                </label>
                <input
                  type="text"
                  value={editingCo.co_code}
                  onChange={(e) => setEditingCo({ ...editingCo, co_code: e.target.value })}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 text-xs font-mono font-bold text-emerald-600 focus:outline-none focus:border-adcet-red"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Outcome Description
                </label>
                <textarea
                  value={editingCo.description}
                  onChange={(e) => setEditingCo({ ...editingCo, description: e.target.value })}
                  rows={4}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-adcet-red leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingCo(null)}
                  className="px-4 py-2 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEditCo}
                  className="px-5 py-2 bg-adcet-navy hover:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md disabled:opacity-50"
                >
                  {savingEditCo ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Update Course Outcome</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={deleteDocId !== null}
        title="Delete Syllabus Document"
        message="Are you sure you want to remove this official syllabus file? The parsed curriculum in MongoDB will be preserved until a replacement is uploaded."
        confirmLabel="Delete Syllabus Document"
        confirmVariant="danger"
        loading={deleting}
        onConfirm={handleDeleteDocument}
        onCancel={() => setDeleteDocId(null)}
      />
    </div>
  );
}
