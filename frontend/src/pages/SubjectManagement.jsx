import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import AddSubjectModal from '../components/common/AddSubjectModal';
import ConfirmModal from '../components/common/ConfirmModal';
import { downloadDocument } from '../utils/downloadDocument';
import {
  BookOpen, Plus, Shield, FileText, UploadCloud, Trash2, CheckCircle2,
  Sliders, Layers, X, PlusCircle, Save, AlertCircle, ChevronDown,
  ChevronUp, Loader2, HelpCircle, Check, Search, Pencil, Download
} from 'lucide-react';

export default function SubjectManagement() {
  const { user } = useAuth();
  const location = useLocation();
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [cos, setCos] = useState([]);
  const [syllabus, setSyllabus] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [examRules, setExamRules] = useState({
    total_marks: '', duration_minutes: '', min_co_coverage_pct: '',
    min_unit_coverage_pct: '', min_higher_order_bloom_pct: '',
    internal_choice_required: '', similarity_threshold: '',
  });
  const [rulesLoading, setRulesLoading] = useState(false);
  const [rulesSaving, setRulesSaving] = useState(false);
  const [rulesMessage, setRulesMessage] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(() => new URLSearchParams(window.location.search).get('tab') === 'ppt_library' ? 'ppt_library' : 'units');
  const [searchFilter, setSearchFilter] = useState('');
  const [addSubjectOpen, setAddSubjectOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState(null);
  const [deletingSubjectId, setDeletingSubjectId] = useState(null);
  const [subjectActionError, setSubjectActionError] = useState('');
  const [materialToDelete, setMaterialToDelete] = useState(null);
  const [deletingMaterial, setDeletingMaterial] = useState(false);
  const selectedSubjectIdRef = useRef(null);

  // Unit Title Edit Inputs State: { unit_id: 'Unit Name' }
  const [unitTitles, setUnitTitles] = useState({});
  const [topicInputs, setTopicInputs] = useState({}); // { unit_id: 'topic_name' }
  const [showUnitForm, setShowUnitForm] = useState(false);
  const [newUnitTitle, setNewUnitTitle] = useState('');
  const [savingUnit, setSavingUnit] = useState(false);

  // Dynamic Multiple CO State for selected subject
  const [coRows, setCoRows] = useState([]);
  const [savingCos, setSavingCos] = useState(false);
  const [coMessage, setCoMessage] = useState({ type: '', text: '' });
  const [editingCo, setEditingCo] = useState(null);
  const [editCoCode, setEditCoCode] = useState('');
  const [editCoDesc, setEditCoDesc] = useState('');
  const [savingEditCo, setSavingEditCo] = useState(false);

  // Unit PPT Upload Modal/Form State
  const [activeUnitUpload, setActiveUnitUpload] = useState(null);
  const [unitDocTitle, setUnitDocTitle] = useState('');
  const [unitDocFile, setUnitDocFile] = useState(null);
  const [unitDocFiles, setUnitDocFiles] = useState([]);
  const [uploadingUnitDoc, setUploadingUnitDoc] = useState(false);
  const [unitUploadError, setUnitUploadError] = useState('');
  const [editingPpt, setEditingPpt] = useState(null);
  const [editPptTitle, setEditPptTitle] = useState('');
  const [editPptUnitId, setEditPptUnitId] = useState('');
  const [editPptFile, setEditPptFile] = useState(null);
  const [savingPptEdit, setSavingPptEdit] = useState(false);
  const [pptEditError, setPptEditError] = useState('');
  const [importingSyllabus, setImportingSyllabus] = useState(false);
  const [syllabusImportError, setSyllabusImportError] = useState('');
  const syllabusImportRef = useRef(null);

  useEffect(() => {
    fetchSubjects();
  }, []);

  useEffect(() => {
    if (new URLSearchParams(location.search).get('tab') === 'ppt_library') setActiveTab('ppt_library');
  }, [location.search]);

  const fetchSubjects = (selectId = null) => {
    api.get('/subjects')
      .then((res) => {
        setSubjects(res.data || []);
        if (res.data.length > 0) {
          const target = selectId ? res.data.find((s) => s.id === selectId) : (selectedSubject || res.data[0]);
          selectSubject(target || res.data[0]);
        } else {
          selectedSubjectIdRef.current = null;
          setSelectedSubject(null);
          setCos([]);
          setSyllabus([]);
          setDocuments([]);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  const selectSubject = (subj) => {
    if (!subj) return;
    selectedSubjectIdRef.current = subj.id;
    setSelectedSubject(subj);
    setUnitTitles({});
    setTopicInputs({});
    setShowUnitForm(false);
    setNewUnitTitle('');
    setCoRows([]);
    setCoMessage({ type: '', text: '' });
    setActiveUnitUpload(null);
    setUnitDocTitle('');
    setUnitDocFile(null);
    setCos([]);
    setSyllabus([]);
    setDocuments([]);
    setRulesMessage({ type: '', text: '' });
    fetchExamRules(subj);
    fetchCos(subj.id);
    fetchSyllabus(subj.id);
    fetchDocuments(subj.id);
  };

  const fetchExamRules = (subject) => {
    setRulesLoading(true);
    api.get(`/subjects/${subject.id}/rules`)
      .then((res) => {
        if (selectedSubjectIdRef.current !== subject.id) return;
        const data = res.data || {};
        setExamRules({
          total_marks: data.total_marks ?? subject.total_marks ?? '',
          duration_minutes: data.duration_minutes ?? subject.duration_minutes ?? '',
          min_co_coverage_pct: data.min_co_coverage_pct ?? data.min_co_coverage ?? '',
          min_unit_coverage_pct: data.min_unit_coverage_pct ?? data.min_unit_coverage ?? '',
          min_higher_order_bloom_pct: data.min_higher_order_bloom_pct ?? '',
          internal_choice_required: data.internal_choice_required == null ? '' : String(data.internal_choice_required),
          similarity_threshold: data.similarity_threshold ?? '',
        });
      })
      .catch(() => {
        if (selectedSubjectIdRef.current === subject.id) {
          setRulesMessage({ type: 'error', text: 'Examination rules could not be loaded.' });
        }
      })
      .finally(() => {
        if (selectedSubjectIdRef.current === subject.id) setRulesLoading(false);
      });
  };

  const handleSaveExamRules = async (event) => {
    event.preventDefault();
    if (!selectedSubject || !['FACULTY', 'ADMIN', 'MODERATOR'].includes(user?.role)) return;
    const asOptionalNumber = (value) => value === '' ? null : Number(value);
    setRulesSaving(true);
    setRulesMessage({ type: '', text: '' });
    try {
      await api.put(`/subjects/${selectedSubject.id}/rules`, {
        total_marks: Number(examRules.total_marks),
        duration_minutes: Number(examRules.duration_minutes),
        min_co_coverage_pct: asOptionalNumber(examRules.min_co_coverage_pct),
        min_unit_coverage_pct: asOptionalNumber(examRules.min_unit_coverage_pct),
        min_higher_order_bloom_pct: asOptionalNumber(examRules.min_higher_order_bloom_pct),
        internal_choice_required: examRules.internal_choice_required === '' ? null : examRules.internal_choice_required === 'true',
        similarity_threshold: asOptionalNumber(examRules.similarity_threshold),
      });
      setRulesMessage({ type: 'success', text: 'Examination policy saved. Unset thresholds remain informational.' });
      fetchExamRules(selectedSubject);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setRulesMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Could not save the examination policy.' });
    } finally {
      setRulesSaving(false);
    }
  };

  const fetchCos = (subjId) => {
    api.get(`/subjects/${subjId}/cos`).then((res) => {
      if (selectedSubjectIdRef.current === subjId) setCos(res.data || []);
    }).catch(() => { if (selectedSubjectIdRef.current === subjId) setCos([]); });
  };

  const fetchSyllabus = (subjId) => {
    api.get(`/subjects/${subjId}/syllabus`).then((res) => {
      if (selectedSubjectIdRef.current !== subjId) return;
      setSyllabus(res.data || []);
      const titleMap = {};
      (res.data || []).forEach((u) => {
        titleMap[u.id] = u.title || '';
      });
      setUnitTitles(titleMap);
    }).catch(() => { if (selectedSubjectIdRef.current === subjId) setSyllabus([]); });
  };

  const fetchDocuments = (subjId) => {
    api.get(`/subjects/${subjId}/documents`).then((res) => {
      if (selectedSubjectIdRef.current === subjId) setDocuments(res.data || []);
    }).catch(() => { if (selectedSubjectIdRef.current === subjId) setDocuments([]); });
  };

  const handleDeleteMaterial = async () => {
    if (!materialToDelete || !selectedSubject) return;
    setDeletingMaterial(true);
    setSubjectActionError('');
    try {
      await api.delete(`/subjects/${selectedSubject.id}/documents/${materialToDelete.id}`);
      setMaterialToDelete(null);
      fetchDocuments(selectedSubject.id);
    } catch (err) {
      setSubjectActionError(err.response?.data?.detail || 'Could not remove this uploaded file.');
    } finally {
      setDeletingMaterial(false);
    }
  };

  const handleDeleteSubject = async (subj) => {
    if (!window.confirm(`Delete ${subj.code} — ${subj.name}? All associated questions, curriculum, and PPTs will also be removed.`)) return;
    setDeletingSubjectId(subj.id);
    setSubjectActionError('');
    try {
      await api.delete(`/subjects/${subj.id}`);
      const remaining = subjects.filter((item) => item.id !== subj.id);
      setSubjects(remaining);
      if (selectedSubject?.id === subj.id) {
        selectedSubjectIdRef.current = null;
        setSelectedSubject(null);
        setCos([]);
        setSyllabus([]);
        setDocuments([]);
        if (remaining.length) selectSubject(remaining[0]);
      }
    } catch (err) {
      setSubjectActionError(err.response?.data?.detail || 'Could not delete this subject.');
    } finally {
      setDeletingSubjectId(null);
    }
  };

  // --- Dynamic Unit Operations (+ Add Unit) ---
  const handleAddUnit = async () => {
    if (!selectedSubject || !newUnitTitle.trim()) return;
    const nextNum = Math.max(0, ...syllabus.map((unit) => Number(unit.unit_number) || 0)) + 1;

    try {
      setSavingUnit(true);
      await api.post(`/subjects/${selectedSubject.id}/syllabus`, {
        unit_number: nextNum,
        title: newUnitTitle.trim(),
        description: ''
      });
      setNewUnitTitle('');
      setShowUnitForm(false);
      fetchSyllabus(selectedSubject.id);
    } catch (err) {
      setSubjectActionError(err.response?.data?.detail || 'Failed to add unit.');
    } finally {
      setSavingUnit(false);
    }
  };

  const handleSaveUnitTitle = async (unitId) => {
    const titleVal = unitTitles[unitId] ?? '';
    try {
      const unit = syllabus.find((item) => item.id === unitId);
      await api.put(`/subjects/${selectedSubject.id}/syllabus/${unitId}`, {
        unit_number: unit?.unit_number,
        title: titleVal
      });
    } catch (err) {
      console.error('Failed to save unit title', err);
    }
  };

  const handleRemoveUnit = async (unitId) => {
    if (!window.confirm('Delete Unit? This will remove this unit and its topics/documents.')) return;
    try {
      await api.delete(`/subjects/${selectedSubject.id}/syllabus/${unitId}`);
      fetchSyllabus(selectedSubject.id);
    } catch (err) {
      alert('Failed to delete unit');
    }
  };

  // --- Dynamic Topic Operations (+ Add Topic) ---
  const handleAddTopic = async (unitId) => {
    const text = topicInputs[unitId];
    if (!text || !text.trim()) return;

    try {
      await api.post(`/subjects/${selectedSubject.id}/syllabus/${unitId}/topics`, {
        topic_name: text.trim()
      });
      setTopicInputs((prev) => ({ ...prev, [unitId]: '' }));
      fetchSyllabus(selectedSubject.id);
    } catch (err) {
      alert('Failed to add topic');
    }
  };

  const handleRemoveTopic = async (unitId, topicId) => {
    try {
      await api.delete(`/subjects/${selectedSubject.id}/syllabus/${unitId}/topics/${topicId}`);
      fetchSyllabus(selectedSubject.id);
    } catch (err) {
      alert('Failed to delete topic');
    }
  };

  // --- Dynamic Multiple CO Operations ---
  const handleAddCoRow = () => {
    const allCodes = [...cos.map((c) => c.co_code), ...coRows.map((r) => r.co_code)];
    let highest = 0;
    allCodes.forEach((c) => {
      const m = c && c.match(/CO(\d+)/i);
      if (m) {
        const val = parseInt(m[1], 10);
        if (val > highest) highest = val;
      }
    });
    setCoRows([...coRows, { co_code: `CO${highest + 1}`, description: '' }]);
  };

  const handleRemoveCoRow = (index) => {
    setCoRows(coRows.filter((_, idx) => idx !== index));
  };

  const handleUpdateCoRow = (index, field, value) => {
    const updated = [...coRows];
    updated[index][field] = value;
    setCoRows(updated);
  };

  const handleSaveAllCos = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!selectedSubject) return;
    const validRows = coRows.filter((r) => r.co_code.trim() && r.description.trim());
    if (validRows.length === 0) {
      setCoMessage({ type: 'error', text: 'Please enter at least 1 Course Outcome with valid code and description.' });
      return;
    }
    setSavingCos(true);
    setCoMessage({ type: '', text: '' });
    try {
      await api.post(`/subjects/${selectedSubject.id}/cos/batch`, {
        cos: validRows.map((r) => ({ co_code: r.co_code.trim(), description: r.description.trim() }))
      });
      setCoMessage({ type: 'success', text: `Saved ${validRows.length} Course Outcome(s) successfully!` });
      setCoRows([]);
      fetchCos(selectedSubject.id);
      setTimeout(() => setCoMessage({ type: '', text: '' }), 4000);
    } catch (err) {
      try {
        for (const row of validRows) {
          await api.post(`/subjects/${selectedSubject.id}/cos`, {
            co_code: row.co_code.trim(),
            description: row.description.trim()
          });
        }
        setCoMessage({ type: 'success', text: `Saved ${validRows.length} Course Outcome(s) successfully!` });
        setCoRows([]);
        fetchCos(selectedSubject.id);
        setTimeout(() => setCoMessage({ type: '', text: '' }), 4000);
      } catch (innerErr) {
        setCoMessage({ type: 'error', text: 'Failed to save Course Outcomes. Please try again.' });
      }
    } finally {
      setSavingCos(false);
    }
  };

  const handleRemoveCo = async (coId) => {
    if (!window.confirm('Delete this Course Outcome? This will affect Bloom & CO coverage evaluations.')) return;
    try {
      await api.delete(`/subjects/${selectedSubject.id}/cos/${coId}`);
      fetchCos(selectedSubject.id);
    } catch (err) {
      alert('Failed to remove Course Outcome');
    }
  };

  const handleSaveEditCo = async (e) => {
    e.preventDefault();
    if (!editingCo || !selectedSubject) return;
    setSavingEditCo(true);
    try {
      await api.put(`/subjects/${selectedSubject.id}/cos/${editingCo.id}`, {
        co_code: editCoCode.trim(),
        description: editCoDesc.trim()
      });
      setEditingCo(null);
      fetchCos(selectedSubject.id);
      setCoMessage({ type: 'success', text: `Updated ${editCoCode.trim()} successfully!` });
      setTimeout(() => setCoMessage({ type: '', text: '' }), 4000);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update Course Outcome');
    } finally {
      setSavingEditCo(false);
    }
  };

  // --- Unit-Specific & Subject PPT Upload ---
  const handleUploadUnitDocument = async (e) => {
    e.preventDefault();
    const filesToUpload = unitDocFiles.length > 0 ? unitDocFiles : (unitDocFile ? [unitDocFile] : []);
    if (filesToUpload.length === 0 || !activeUnitUpload || !selectedSubject) return;
    setUnitUploadError('');
    setUploadingUnitDoc(true);

    const linkedUnitId = activeUnitUpload.id || activeUnitUpload.selectedUnitId || null;
    let successCount = 0;
    const errors = [];

    for (const f of filesToUpload) {
      const formData = new FormData();
      const title = filesToUpload.length === 1 && unitDocTitle.trim() ? unitDocTitle.trim() : f.name.replace(/\.[^.]+$/, '');
      formData.append('title', title);
      if (linkedUnitId) formData.append('unit_id', String(linkedUnitId));
      if (selectedSubject.academic_year) formData.append('academic_year', selectedSubject.academic_year);
      if (selectedSubject.semester) formData.append('semester', String(selectedSubject.semester));
      formData.append('file', f);

      try {
        await api.post(`/subjects/${selectedSubject.id}/documents`, formData);
        successCount++;
      } catch (err) {
        errors.push(`${f.name}: ${err.response?.data?.detail || 'Could not upload'}`);
      }
    }

    setUploadingUnitDoc(false);
    if (errors.length > 0) {
      setUnitUploadError(errors.join(' | '));
      if (successCount > 0) {
        fetchDocuments(selectedSubject.id);
      }
    } else {
      setUnitDocTitle('');
      setUnitDocFile(null);
      setUnitDocFiles([]);
      setActiveUnitUpload(null);
      fetchSyllabus(selectedSubject.id);
      fetchDocuments(selectedSubject.id);
    }
  };

  const openEditPpt = (doc) => {
    setPptEditError('');
    setEditingPpt(doc);
    setEditPptTitle(doc.title || doc.filename || '');
    setEditPptUnitId(doc.unit_id ? String(doc.unit_id) : '');
    setEditPptFile(null);
  };

  const handleSavePptEdit = async (event) => {
    event.preventDefault();
    if (!editingPpt || !selectedSubject) return;
    setSavingPptEdit(true);
    setPptEditError('');
    const formData = new FormData();
    formData.append('title', editPptTitle.trim() || editingPpt.filename);
    if (editPptUnitId) formData.append('unit_id', editPptUnitId);
    else formData.append('clear_unit', 'true');
    if (editPptFile) formData.append('file', editPptFile);
    try {
      await api.put(`/subjects/${selectedSubject.id}/documents/${editingPpt.id}`, formData);
      setEditingPpt(null);
      fetchDocuments(selectedSubject.id);
    } catch (err) {
      setPptEditError(err.response?.data?.detail || 'Could not update this PPT.');
    } finally {
      setSavingPptEdit(false);
    }
  };

  const handleImportSyllabusFile = async (file) => {
    if (!file || !selectedSubject) return;
    setImportingSyllabus(true);
    setSyllabusImportError('');
    const formData = new FormData();
    formData.append('file', file);
    if (selectedSubject.academic_year) formData.append('academic_year', selectedSubject.academic_year);
    formData.append('replace_existing', 'true');
    try {
      await api.post(`/subjects/${selectedSubject.id}/syllabus/upload`, formData);
      fetchSubjects(selectedSubject.id);
      fetchSyllabus(selectedSubject.id);
      fetchCos(selectedSubject.id);
    } catch (err) {
      setSyllabusImportError(err.response?.data?.detail || 'Could not import syllabus details from this file.');
    } finally {
      setImportingSyllabus(false);
      if (syllabusImportRef.current) syllabusImportRef.current.value = '';
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 text-sm font-semibold">
        Loading Subject & Curriculum Profiles...
      </div>
    );
  }

  const filteredSubjects = subjects.filter((s) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      (s.code || '').toLowerCase().includes(q) ||
      (s.name || '').toLowerCase().includes(q)
    );
  });
  const canManageCurriculum = ['FACULTY', 'ADMIN', 'MODERATOR'].includes(user?.role);
  const canEditExamRules = ['FACULTY', 'ADMIN', 'MODERATOR'].includes(user?.role);
  const canUploadPpt = user?.role === 'FACULTY' || ['ADMIN', 'MODERATOR'].includes(user?.role);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* 1. Page Header */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-adcet-red"></span>
            <h1 className="text-xl font-bold text-adcet-navy">
              Curriculum & Subject Configuration
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Add, edit, or delete subjects. Import curriculum from a syllabus file or enter it manually. Upload multiple PPTs per subject.
          </p>
        </div>

        {canManageCurriculum && (
          <button
            type="button"
            onClick={() => setAddSubjectOpen(true)}
            className="px-4 py-2.5 bg-adcet-red hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-1.5 shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Subject</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (4 cols): Subject Profiles List */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <BookOpen className="w-4 h-4 text-adcet-red" />
                <span>Subject Profiles</span>
              </h2>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                {subjects.length} Subjects
              </span>
            </div>

            {/* Search Filter */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search subject code or name..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-adcet-red"
              />
            </div>

            {subjectActionError && (
              <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                {subjectActionError}
              </div>
            )}
            {syllabusImportError && (
              <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                {syllabusImportError}
              </div>
            )}

            {/* List */}
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              {filteredSubjects.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 bg-white p-5 text-center text-xs text-slate-500">{subjects.length ? 'No subjects match your search.' : 'No subjects have been added yet.'}</p>}
              {filteredSubjects.map((s) => {
                const isSelected = selectedSubject?.id === s.id;
                return (
                  <div key={s.id} className={`flex items-center gap-1 rounded-xl border p-2 transition-all ${isSelected ? 'border-adcet-red bg-red-50/60 shadow-sm' : 'border-slate-200 bg-slate-50/70 hover:bg-slate-100'}`}>
                    <button type="button" onClick={() => selectSubject(s)} className="min-w-0 flex-1 px-1.5 py-1 text-left">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-bold text-adcet-navy">{s.code}</span>
                        <span className="text-[10px] font-medium text-slate-400">Sem {s.semester}</span>
                      </div>
                      <p className={`mt-1 line-clamp-1 text-xs font-bold ${isSelected ? 'text-adcet-navy' : 'text-slate-800'}`}>{s.name}</p>
                      <p className="mt-0.5 truncate text-[10px] text-slate-400">{s.department || 'Department not set'}</p>
                    </button>
                    {canManageCurriculum && <button type="button" title={`Edit ${s.code}`} aria-label={`Edit ${s.name}`} onClick={() => setEditingSubject(s)} className="rounded-lg p-2 text-slate-500 hover:bg-white hover:text-adcet-navy"><Pencil className="h-3.5 w-3.5" /></button>}
                    {canManageCurriculum && <button type="button" title={`Delete ${s.code}`} aria-label={`Delete ${s.name}`} disabled={deletingSubjectId === s.id} onClick={() => handleDeleteSubject(s)} className="rounded-lg p-2 text-slate-400 hover:bg-white hover:text-rose-600 disabled:opacity-50"><Trash2 className="h-3.5 w-3.5" /></button>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column (8 cols): Selected Subject Workspace */}
        <div className="lg:col-span-8 space-y-4">
          {!selectedSubject && <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">Add a subject or select one from the list to manage its curriculum and PPTs.</div>}
          {selectedSubject && (
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              {/* Header */}
              <div className="p-6 border-b border-slate-200 bg-slate-50/60">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 bg-adcet-navy text-white font-mono font-bold text-xs rounded-lg">
                        {selectedSubject.code}
                      </span>
                      <h2 className="text-base font-bold text-slate-900">{selectedSubject.name}</h2>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {selectedSubject.department || 'Department not set'} • Semester {selectedSubject.semester} • AY {selectedSubject.academic_year || 'Not set'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-semibold">
                      {syllabus.length} Units
                    </span>
                    <span className="px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-xl text-xs font-semibold">
                      {cos.length} COs
                    </span>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-2 mt-5 border-b border-slate-200">
                  <button
                    type="button"
                    onClick={() => setActiveTab('units')}
                    className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                      activeTab === 'units'
                        ? 'border-adcet-red text-adcet-red bg-red-50/40 rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Syllabus Units ({syllabus.length})</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('cos')}
                    className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                      activeTab === 'cos'
                        ? 'border-adcet-red text-adcet-red bg-red-50/40 rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Course Outcomes ({cos.length})</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('ppt_library')}
                    className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                      activeTab === 'ppt_library'
                        ? 'border-adcet-red text-adcet-red bg-red-50/40 rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>PPT Upload ({documents.length})</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('exam_rules')}
                    className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                      activeTab === 'exam_rules'
                        ? 'border-adcet-red text-adcet-red bg-red-50/40 rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>Examination Rules</span>
                  </button>
                </div>
              </div>

              {/* TAB 1: SYLLABUS UNITS */}
              {activeTab === 'units' && (
                <div className="p-6 space-y-6">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                        Syllabus Units & Examination Boundaries
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        Units configured here are verified during question paper scrutiny.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {canManageCurriculum && (
                        <>
                          <input ref={syllabusImportRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={(e) => handleImportSyllabusFile(e.target.files?.[0])} />
                          <button type="button" disabled={importingSyllabus} onClick={() => syllabusImportRef.current?.click()} className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-bold text-adcet-navy hover:bg-slate-50 flex items-center gap-1">
                            {importingSyllabus ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
                            <span>{importingSyllabus ? 'Importing…' : 'Import syllabus file'}</span>
                          </button>
                        </>
                      )}
                      {canManageCurriculum && <button
                        type="button"
                        onClick={() => setShowUnitForm((open) => !open)}
                        className="px-3 py-1.5 rounded-lg bg-adcet-navy text-white text-xs font-bold hover:bg-slate-800 transition-colors flex items-center gap-1 shadow-sm"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Unit</span>
                      </button>}
                    </div>
                  </div>

                  {showUnitForm && canManageCurriculum && (
                    <form onSubmit={(event) => { event.preventDefault(); handleAddUnit(); }} className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:flex-row">
                      <input autoFocus required value={newUnitTitle} onChange={(event) => setNewUnitTitle(event.target.value)} placeholder="Enter the official syllabus unit title" className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 focus:border-adcet-red focus:outline-none" />
                      <button type="submit" disabled={savingUnit || !newUnitTitle.trim()} className="rounded-lg bg-adcet-red px-3 py-2 text-xs font-bold text-white disabled:opacity-50">{savingUnit ? 'Adding…' : 'Save unit'}</button>
                      <button type="button" onClick={() => { setShowUnitForm(false); setNewUnitTitle(''); }} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600">Cancel</button>
                    </form>
                  )}

                  {syllabus.length === 0 ? (
                    <div className="p-8 bg-slate-50 rounded-2xl border border-dashed border-slate-300 text-center space-y-3">
                      <Layers className="w-8 h-8 mx-auto text-slate-400" />
                      <p className="text-xs text-slate-600 font-medium">
                        No syllabus units configured for {selectedSubject.name} yet.
                      </p>
                      {canManageCurriculum && <button
                        type="button"
                        onClick={() => setShowUnitForm(true)}
                        className="px-4 py-2 bg-adcet-red text-white text-xs font-bold rounded-xl shadow-sm hover:bg-red-700 transition-colors"
                      >
                        + Add First Syllabus Unit
                      </button>}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {syllabus.map((u) => (
                        <div key={u.id} className="p-5 bg-slate-50 rounded-2xl border border-slate-200 space-y-3 shadow-xs">
                          {/* Unit Header */}
                          <div className="flex items-center justify-between">
                            <span className="px-2.5 py-1 bg-white border border-slate-200 text-adcet-navy font-mono font-bold text-xs rounded-lg shadow-2xs">
                              Unit {u.unit_number}
                            </span>
                            <div className="flex items-center gap-2">
                              {canUploadPpt && (
                                <button
                                  type="button"
                                  onClick={() => { setUnitUploadError(''); setActiveUnitUpload(u); }}
                                  className="px-2.5 py-1 bg-white hover:bg-slate-100 text-adcet-navy border border-slate-200 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
                                >
                                  <UploadCloud className="w-3.5 h-3.5 text-adcet-red" />
                                  <span>+ Upload PPT</span>
                                </button>
                              )}
                              {canManageCurriculum && <button
                                type="button"
                                onClick={() => handleRemoveUnit(u.id)}
                                className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg transition-colors"
                                title="Delete Unit"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>}
                            </div>
                          </div>

                          {/* Unit Title Input */}
                          {canManageCurriculum ? <div className="flex items-center gap-2">
                            <input
                              type="text"
                              placeholder="Enter Unit Title (e.g. Linear Regression & Gradient Descent)"
                              value={unitTitles[u.id] ?? u.title}
                              onChange={(e) => setUnitTitles({ ...unitTitles, [u.id]: e.target.value })}
                              onBlur={() => handleSaveUnitTitle(u.id)}
                              className="flex-1 bg-white border border-slate-200 rounded-xl px-3.5 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-adcet-red"
                            />
                            <button
                              type="button"
                              onClick={() => handleSaveUnitTitle(u.id)}
                              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold"
                              title="Save Title"
                            >
                              <Save className="w-3.5 h-3.5" />
                            </button>
                          </div> : <p className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-800">{u.title}</p>}

                          {/* Unit Topics */}
                          <div className="pt-2 border-t border-slate-200/60 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] font-bold text-slate-600">
                                Topics (Used by AI for Unit Verification):
                              </span>
                              <span className="text-[10px] text-slate-400 font-semibold">
                                {(u.topics || []).length} topics
                              </span>
                            </div>

                            <div className="flex flex-wrap gap-1.5">
                              {(!u.topics || u.topics.length === 0) ? (
                                <p className="text-[11px] text-slate-400 italic">No topics added yet.</p>
                              ) : (
                                u.topics.map((t) => (
                                  <span
                                    key={t.id || t}
                                    className="inline-flex items-center px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-xs text-slate-700 font-medium"
                                  >
                                    {t.topic_name || t}
                                    {canManageCurriculum && <button
                                      type="button"
                                      onClick={() => handleRemoveTopic(u.id, t.id)}
                                      className="ml-1.5 text-slate-400 hover:text-red-600"
                                    >
                                      <X className="w-3 h-3" />
                                    </button>}
                                  </span>
                                ))
                              )}
                            </div>

                            {/* Add Topic Input */}
                            {canManageCurriculum && <div className="flex items-center gap-2 pt-1">
                              <input
                                type="text"
                                placeholder="Add specific topic (e.g. Cross-Validation, SVM Kernels)..."
                                value={topicInputs[u.id] || ''}
                                onChange={(e) => setTopicInputs({ ...topicInputs, [u.id]: e.target.value })}
                                onKeyDown={(e) => { if (e.key === 'Enter') handleAddTopic(u.id); }}
                                className="flex-1 bg-white border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-adcet-red"
                              />
                              <button
                                type="button"
                                onClick={() => handleAddTopic(u.id)}
                                className="px-3 py-1.5 bg-adcet-navy hover:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center gap-1"
                              >
                                <Plus className="w-3.5 h-3.5" />
                                <span>Add Topic</span>
                              </button>
                            </div>}
                          </div>

                          {/* Unit Attached PPTs */}
                          {(() => {
                            const unitPpts = documents.filter((d) => d.unit_id === u.id);
                            if (unitPpts.length === 0) return null;
                            return (
                              <div className="pt-2 border-t border-slate-200/60 space-y-1.5">
                                <span className="text-[11px] font-bold text-slate-600 flex items-center gap-1">
                                  <FileText className="w-3 h-3 text-adcet-red" />
                                  <span>Unit PPTs ({unitPpts.length}):</span>
                                </span>
                                <div className="space-y-1">
                                  {unitPpts.map((d) => (
                                    <div key={d.id} className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs">
                                      <div className="flex items-center gap-2 min-w-0">
                                        <span className="text-adcet-navy font-semibold truncate" title={d.filename}>{d.title || d.filename}</span>
                                        <span className="text-[10px] text-slate-400 shrink-0">PPT</span>
                                      </div>
                                      <div className="flex items-center gap-1 shrink-0">
                                        <button
                                          type="button"
                                          onClick={() => downloadDocument(`/subjects/${selectedSubject.id}/documents/${d.id}/download`, d.filename).catch(() => setSubjectActionError('Could not download this PPT.'))}
                                          className="p-1 text-slate-500 hover:text-adcet-navy"
                                          title="Download PPT"
                                        >
                                          <Download className="w-3.5 h-3.5" />
                                        </button>
                                        {canUploadPpt && (
                                          <button
                                            type="button"
                                            onClick={() => openEditPpt(d)}
                                            className="p-1 text-slate-500 hover:text-adcet-navy"
                                            title="Edit PPT"
                                          >
                                            <Pencil className="w-3.5 h-3.5" />
                                          </button>
                                        )}
                                        {canUploadPpt && (
                                          <button
                                            type="button"
                                            onClick={() => setMaterialToDelete(d)}
                                            className="p-1 text-slate-400 hover:text-rose-600"
                                            title="Remove PPT"
                                          >
                                            <Trash2 className="w-3.5 h-3.5" />
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          })()}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: COURSE OUTCOMES */}
              {activeTab === 'cos' && (
                <div className="p-6 space-y-6">
                  {coMessage.text && (
                    <div
                      className={`p-3.5 rounded-xl text-xs font-semibold flex items-center justify-between ${
                        coMessage.type === 'success'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-red-50 text-red-800 border border-red-200'
                      }`}
                    >
                      <span>{coMessage.text}</span>
                      <button type="button" onClick={() => setCoMessage({ type: '', text: '' })}>✕</button>
                    </div>
                  )}

                  {/* Add CO Form */}
                  {canManageCurriculum && <div className="p-5 bg-slate-50 border border-slate-200 rounded-2xl space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                          Define Course Outcomes
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Automated paper scrutiny maps each question to these course outcomes.
                        </p>
                      </div>

                    </div>

                    <form onSubmit={handleSaveAllCos} className="space-y-3">
                      <div className="space-y-2">
                        {coRows.map((row, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            <input
                              type="text"
                              value={row.co_code}
                              onChange={(e) => handleUpdateCoRow(idx, 'co_code', e.target.value)}
                              placeholder="CO1"
                              className="w-20 bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-mono font-bold text-adcet-navy focus:outline-none focus:border-adcet-red"
                            />
                            <input
                              type="text"
                              value={row.description}
                              onChange={(e) => handleUpdateCoRow(idx, 'description', e.target.value)}
                              placeholder="Outcome description (e.g. Understand and apply regression models)..."
                              className="flex-1 bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-adcet-red"
                            />
                            <button
                              type="button"
                              onClick={() => handleRemoveCoRow(idx)}
                              className="p-2 text-slate-400 hover:text-red-600 rounded-lg"
                              aria-label={`Remove unsaved course outcome ${idx + 1}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>

                      <div className="flex items-center justify-between pt-2">
                        <button
                          type="button"
                          onClick={handleAddCoRow}
                          className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-xl flex items-center gap-1"
                        >
                          <Plus className="w-3.5 h-3.5 text-adcet-red" />
                          <span>+ Add Another CO</span>
                        </button>

                        <button
                          type="submit"
                          disabled={savingCos}
                          className="px-4 py-2 bg-adcet-red hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
                        >
                          {savingCos ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              <span>Saving...</span>
                            </>
                          ) : (
                            <>
                              <Save className="w-3.5 h-3.5" />
                              <span>Save Outcomes</span>
                            </>
                          )}
                        </button>
                      </div>
                    </form>
                  </div>}

                  {/* Configured COs */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Currently Configured Course Outcomes ({cos.length})
                    </h4>

                    {cos.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No course outcomes configured yet.</p>
                    ) : (
                      <div className="space-y-2">
                        {cos.map((c) => (
                          <div
                            key={c.id}
                            className="p-3 bg-white border border-slate-200 rounded-xl flex items-start justify-between gap-3 text-xs shadow-2xs"
                          >
                            <div className="flex items-start gap-2.5">
                              <span className="font-mono font-bold text-adcet-navy px-2 py-0.5 bg-slate-100 rounded text-xs border border-slate-200 shrink-0">
                                {c.co_code}
                              </span>
                              <p className="text-slate-800 leading-relaxed pt-0.5">
                                {c.description}
                              </p>
                            </div>
                            {canManageCurriculum && (
                              <div className="flex items-center gap-1 shrink-0">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingCo(c);
                                    setEditCoCode(c.co_code);
                                    setEditCoDesc(c.description);
                                  }}
                                  className="p-1 text-slate-400 hover:text-adcet-navy rounded transition"
                                  title="Edit Course Outcome"
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveCo(c.id)}
                                  className="p-1 text-slate-400 hover:text-red-600 rounded transition"
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

                    {/* Edit CO Modal */}
                    {editingCo && (
                      <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
                        <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
                          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                            <h3 className="font-bold text-slate-900 text-sm">Edit Course Outcome</h3>
                            <button
                              type="button"
                              onClick={() => setEditingCo(null)}
                              className="text-slate-400 hover:text-slate-600 p-1"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                          <form onSubmit={handleSaveEditCo} className="space-y-3">
                            <div>
                              <label className="block text-xs font-semibold text-slate-700 mb-1">CO Code</label>
                              <input
                                type="text"
                                required
                                value={editCoCode}
                                onChange={(e) => setEditCoCode(e.target.value)}
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 font-mono focus:outline-none focus:border-adcet-red"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-semibold text-slate-700 mb-1">Description</label>
                              <textarea
                                required
                                rows={3}
                                value={editCoDesc}
                                onChange={(e) => setEditCoDesc(e.target.value)}
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-adcet-red"
                              />
                            </div>
                            <div className="flex items-center justify-end gap-2 pt-2">
                              <button
                                type="button"
                                onClick={() => setEditingCo(null)}
                                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                              >
                                Cancel
                              </button>
                              <button
                                type="submit"
                                disabled={savingEditCo}
                                className="px-4 py-2 bg-adcet-red hover:bg-red-700 text-white text-xs font-bold rounded-xl shadow disabled:opacity-50 flex items-center gap-1.5"
                              >
                                {savingEditCo ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                <span>Save Changes</span>
                              </button>
                            </div>
                          </form>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 3: POWERPOINT LIBRARY */}
              {activeTab === 'ppt_library' && (
                <div className="p-6 space-y-5">
                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">PPT Upload</h3>
                      <p className="text-xs text-slate-500 mt-1">Upload multiple PowerPoint files for this subject. Each file can be linked to a syllabus unit.</p>
                    </div>
                    {canUploadPpt && <button
                      type="button"
                      onClick={() => { setUnitUploadError(''); setActiveUnitUpload({ id: null, unit_number: null }); }}
                      className="px-4 py-2 bg-adcet-navy hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-1.5 shrink-0"
                    >
                      <UploadCloud className="w-4 h-4" />
                      <span>Upload PPT</span>
                    </button>}
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">PowerPoint files ({documents.length})</h4>
                    {documents.map((d) => (
                      <div key={`ppt-${d.id}`} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 text-xs">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-slate-900" title={d.filename}>{d.title || d.filename}</p>
                          <p className="mt-1 text-[10px] text-slate-500">PPT{d.unit_id ? ` • Unit ${syllabus.find((unit) => unit.id === d.unit_id)?.unit_number || ''}` : ''}{d.academic_year ? ` • ${d.academic_year}` : ''} • Uploaded by {d.uploaded_by_name || 'Faculty'}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <button type="button" onClick={() => downloadDocument(`/subjects/${selectedSubject.id}/documents/${d.id}/download`, d.filename).catch(() => setSubjectActionError('Could not download this PPT.'))} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-2 font-semibold text-adcet-navy hover:bg-slate-50" aria-label={`Download ${d.filename}`}>
                            <Download className="h-3.5 w-3.5" /><span>Download</span>
                          </button>
                          {(['ADMIN', 'MODERATOR', 'FACULTY'].includes(user?.role)) && (
                            <button type="button" onClick={() => openEditPpt(d)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-2 font-semibold text-adcet-navy hover:bg-slate-50" aria-label={`Edit ${d.filename}`} title="Edit PPT">
                              <Pencil className="h-3.5 w-3.5" /><span className="hidden sm:inline">Edit</span>
                            </button>
                          )}
                          {(['ADMIN', 'MODERATOR', 'FACULTY'].includes(user?.role)) && <button type="button" onClick={() => setMaterialToDelete(d)} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-2 font-semibold text-rose-700 hover:bg-rose-50" aria-label={`Remove ${d.filename}`} title="Remove uploaded PPT">
                            <Trash2 className="h-3.5 w-3.5" /><span className="hidden sm:inline">Remove</span>
                          </button>}
                        </div>
                      </div>
                    ))}
                    {documents.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-xs text-slate-500">No PPTs have been uploaded for this subject yet.</p>}
                  </div>
                </div>
              )}

              {/* TAB 4: EXAMINATION POLICY */}
              {activeTab === 'exam_rules' && (
                <form onSubmit={handleSaveExamRules} className="p-6 space-y-5">
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Institutional Examination Policy</h3>
                      <p className="mt-1 max-w-2xl text-xs text-slate-500">
                        Set the rules used by scrutiny for this subject. Leave a threshold blank when the institution has not set one; scrutiny will mark that check as not evaluated.
                      </p>
                    </div>
                    <span className="shrink-0 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-600">
                      {canEditExamRules ? 'Faculty can edit' : 'Read only'}
                    </span>
                  </div>

                  {rulesMessage.text && (
                    <div role={rulesMessage.type === 'error' ? 'alert' : 'status'} className={`rounded-xl border p-3 text-xs ${rulesMessage.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
                      {rulesMessage.text}
                    </div>
                  )}

                  {rulesLoading ? (
                    <div className="flex items-center gap-2 py-8 text-xs text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading examination rules…</div>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        {[
                          ['total_marks', 'Configured maximum marks', 'Positive whole number', '1'],
                          ['duration_minutes', 'Examination duration (minutes)', 'Positive whole number', '1'],
                          ['min_co_coverage_pct', 'Minimum CO coverage (%)', 'Optional institutional threshold', '0.1'],
                          ['min_unit_coverage_pct', 'Minimum syllabus unit coverage (%)', 'Optional institutional threshold', '0.1'],
                          ['min_higher_order_bloom_pct', 'Minimum higher-order Bloom share (%)', 'Optional K3–K6 threshold', '0.1'],
                          ['similarity_threshold', 'Historical similarity flag threshold (%)', 'Optional threshold for review flags', '0.1'],
                        ].map(([key, label, hint, step]) => (
                          <label key={key} className="space-y-1.5">
                            <span className="block text-xs font-semibold text-slate-700">{label}</span>
                            <input
                              type="number"
                              min={key === 'total_marks' || key === 'duration_minutes' ? 1 : 0}
                              max={['min_co_coverage_pct', 'min_unit_coverage_pct', 'min_higher_order_bloom_pct', 'similarity_threshold'].includes(key) ? 100 : undefined}
                              step={step}
                              required={key === 'total_marks' || key === 'duration_minutes'}
                              value={examRules[key]}
                              disabled={!canEditExamRules}
                              onChange={(event) => setExamRules((current) => ({ ...current, [key]: event.target.value }))}
                              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-adcet-red disabled:bg-slate-50 disabled:text-slate-500"
                            />
                            <span className="block text-[10px] text-slate-500">{hint}</span>
                          </label>
                        ))}

                        <label className="space-y-1.5">
                          <span className="block text-xs font-semibold text-slate-700">Are internal choices required?</span>
                          <select
                            value={examRules.internal_choice_required}
                            disabled={!canEditExamRules}
                            onChange={(event) => setExamRules((current) => ({ ...current, internal_choice_required: event.target.value }))}
                            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-adcet-red disabled:bg-slate-50 disabled:text-slate-500"
                          >
                            <option value="">Not configured</option>
                            <option value="true">Required</option>
                            <option value="false">Not required</option>
                          </select>
                          <span className="block text-[10px] text-slate-500">Scrutiny checks this only when a policy is selected.</span>
                        </label>
                      </div>

                      {canEditExamRules && (
                        <div className="flex justify-end border-t border-slate-100 pt-4">
                          <button type="submit" disabled={rulesSaving} className="inline-flex items-center gap-2 rounded-xl bg-adcet-red px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-red-700 disabled:opacity-50">
                            {rulesSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            {rulesSaving ? 'Saving rules…' : 'Save examination policy'}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </form>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Subject or unit PPT upload modal */}
      {activeUnitUpload && (
        <div className="fixed inset-0 bg-adcet-navy/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form
            onSubmit={handleUploadUnitDocument}
            className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl animate-in fade-in"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-adcet-navy">
                {activeUnitUpload.id ? `Upload PPT for Unit ${activeUnitUpload.unit_number}` : `Upload PPT for ${selectedSubject?.name}`}
              </h3>
              <button
                type="button"
                onClick={() => setActiveUnitUpload(null)}
                className="text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {unitUploadError && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">{unitUploadError}</div>}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  PPT title <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="Uses the file name if left blank"
                  value={unitDocTitle}
                  onChange={(e) => setUnitDocTitle(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-adcet-red"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Link to syllabus unit <span className="font-normal text-slate-400">(optional)</span></label>
                <select
                  value={activeUnitUpload.id || activeUnitUpload.selectedUnitId || ''}
                  onChange={(e) => setActiveUnitUpload((current) => ({ ...current, id: e.target.value ? Number(e.target.value) : null, selectedUnitId: e.target.value ? Number(e.target.value) : null, unit_number: syllabus.find((u) => u.id === Number(e.target.value))?.unit_number || null }))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-adcet-red"
                >
                  <option value="">Entire subject (no specific unit)</option>
                  {syllabus.map((unit) => (
                    <option key={unit.id} value={unit.id}>Unit {unit.unit_number}: {unit.title || 'Untitled'}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Select PowerPoint file(s) <span className="font-normal text-slate-400">(.ppt or .pptx, select one or multiple)</span>
                </label>
                <input
                  type="file"
                  accept=".ppt,.pptx"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files || []);
                    setUnitDocFiles(files);
                    if (files.length === 1) {
                      setUnitDocFile(files[0]);
                      setUnitDocTitle(files[0].name.replace(/\.[^.]+$/, ''));
                    } else if (files.length > 1) {
                      setUnitDocFile(null);
                      setUnitDocTitle(`${files.length} PowerPoint files selected`);
                    } else {
                      setUnitDocFile(null);
                      setUnitDocTitle('');
                    }
                    setUnitUploadError('');
                  }}
                  required
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-adcet-navy hover:file:bg-slate-200"
                />
                {unitDocFiles.length > 1 && (
                  <p className="mt-1 text-[11px] text-emerald-700 font-semibold">
                    ✓ {unitDocFiles.length} PPT files selected for upload.
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setActiveUnitUpload(null)}
                className="px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploadingUnitDoc}
                className="px-4 py-2 bg-adcet-red hover:bg-red-700 text-white font-bold rounded-xl text-xs transition-colors shadow-md disabled:opacity-50"
              >
                {uploadingUnitDoc ? 'Uploading…' : unitDocFiles.length > 1 ? `Upload ${unitDocFiles.length} PPTs` : 'Upload PPT'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Add Subject Modal */}
      <AddSubjectModal
        isOpen={addSubjectOpen}
        onClose={() => setAddSubjectOpen(false)}
        onSubjectCreated={(newSubj) => fetchSubjects(newSubj.id)}
        allowSyllabusImport={user?.role === 'FACULTY'}
      />
      <AddSubjectModal
        isOpen={Boolean(editingSubject)}
        subject={editingSubject}
        onClose={() => setEditingSubject(null)}
        allowSyllabusImport={user?.role === 'FACULTY'}
        onSubjectCreated={(updatedSubject) => {
          setSubjects((current) => current.map((item) => item.id === updatedSubject.id ? updatedSubject : item));
          selectSubject(updatedSubject);
        }}
      />
      {/* Edit PPT modal */}
      {editingPpt && (
        <div className="fixed inset-0 bg-adcet-navy/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form
            onSubmit={handleSavePptEdit}
            className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl animate-in fade-in"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-adcet-navy">Edit PPT</h3>
              <button
                type="button"
                onClick={() => setEditingPpt(null)}
                className="text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {pptEditError && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">{pptEditError}</div>}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">PPT title</label>
                <input
                  type="text"
                  value={editPptTitle}
                  onChange={(e) => setEditPptTitle(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-adcet-red"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Link to syllabus unit <span className="font-normal text-slate-400">(optional)</span></label>
                <select
                  value={editPptUnitId}
                  onChange={(e) => setEditPptUnitId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-adcet-red"
                >
                  <option value="">Entire subject (no specific unit)</option>
                  {syllabus.map((unit) => (
                    <option key={unit.id} value={unit.id}>Unit {unit.unit_number}: {unit.title || 'Untitled'}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Replace file <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <input
                  type="file"
                  accept=".ppt,.pptx"
                  onChange={(e) => setEditPptFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-adcet-navy hover:file:bg-slate-200"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditingPpt(null)}
                className="px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingPptEdit}
                className="px-4 py-2 bg-adcet-red hover:bg-red-700 text-white font-bold rounded-xl text-xs transition-colors shadow-md disabled:opacity-50"
              >
                {savingPptEdit ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>
        </div>
      )}

      <ConfirmModal
        isOpen={materialToDelete !== null}
        title="Remove uploaded study material?"
        message={`This will permanently remove “${materialToDelete?.title || materialToDelete?.filename || 'this file'}” from the subject library.`}
        confirmLabel="Remove file"
        loading={deletingMaterial}
        onConfirm={handleDeleteMaterial}
        onCancel={() => setMaterialToDelete(null)}
      />
    </div>
  );
}
