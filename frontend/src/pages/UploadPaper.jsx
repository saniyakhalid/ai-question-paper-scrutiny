import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import AddSubjectModal from '../components/common/AddSubjectModal';
import {
  UploadCloud, FileText, CheckCircle2, Loader2, AlertCircle, ArrowRight,
  BookOpen, Sliders, CheckSquare, Square, Plus, ShieldCheck, XCircle, Info
} from 'lucide-react';

export default function UploadPaper() {
  const { user } = useAuth();
  const canManageCurriculum = ['FACULTY', 'ADMIN', 'MODERATOR'].includes(user?.role);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [subjectId, setSubjectId] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [examType, setExamType] = useState('End-Semester Examination');
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);

  // Dynamic Examination Unit & CO Selection State
  const [availableUnits, setAvailableUnits] = useState([]);
  const [selectedUnits, setSelectedUnits] = useState([]);
  const [availableCos, setAvailableCos] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [step, setStep] = useState(0); // 0:Idle, 1:Uploading, 2:Extracting, 3:Analyzing, 4:Completed
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');
  const [validationError, setValidationError] = useState('');
  const [validationOutcome, setValidationOutcome] = useState('');
  const [validationPaperId, setValidationPaperId] = useState(null);
  const [validatingFile, setValidatingFile] = useState(false);
  const [addSubjectOpen, setAddSubjectOpen] = useState(false);
  const validationRequestRef = useRef(0);
  const subjectDataRequestRef = useRef(0);

  const navigate = useNavigate();

  useEffect(() => {
    fetchSubjects();
  }, []);

  const fetchSubjects = (selectId = null) => {
    api.get('/subjects')
      .then((res) => {
        setSubjects(res.data || []);
        if (res.data.length > 0) {
          const target = selectId ? res.data.find(s => s.id === selectId) : res.data[0];
          const initial = target || res.data[0];
          handleSubjectChange(initial.id, res.data);
        }
      })
      .catch((err) => console.error(err));
  };

  const handleSubjectChange = (sId, subList = subjects) => {
    const sIdNum = parseInt(sId, 10);
    const requestId = ++subjectDataRequestRef.current;
    setSubjectId(sIdNum);
    const subj = subList.find((s) => s.id === sIdNum);
    setSelectedSubject(subj);
    setAcademicYear(subj?.academic_year || '');
    setError('');
    setWarning('');
    setValidationError('');
    setValidationOutcome('');
    setValidationPaperId(null);
    setAvailableUnits([]);
    setSelectedUnits([]);
    setAvailableCos([]);

    if (subj) {
      Promise.all([
        api.get(`/subjects/${subj.id}/syllabus`),
        api.get(`/subjects/${subj.id}/cos`),
      ]).then(([syllabusRes, coRes]) => {
        if (subjectDataRequestRef.current !== requestId) return;
        const units = (syllabusRes.data || []).map((unit) => unit.unit_number);
        setAvailableUnits(units);
        setSelectedUnits(units);
        setAvailableCos(coRes.data || []);
      }).catch(() => {
        if (subjectDataRequestRef.current !== requestId) return;
        setAvailableUnits([]);
        setSelectedUnits([]);
        setAvailableCos([]);
      });

      // If file is already selected, re-validate with new subject
      if (file) {
        validateSelectedFile(file, subj);
      }
    }
  };

  const toggleUnit = (uNum) => {
    setSelectedUnits((prev) =>
      prev.includes(uNum) ? prev.filter((u) => u !== uNum) : [...prev, uNum].sort((a, b) => a - b)
    );
  };

  const handleSelectAllUnits = () => setSelectedUnits(availableUnits);
  const handleClearAllUnits = () => setSelectedUnits([]);

  const validateSelectedFile = async (chosenFile, currentSubj) => {
    if (!chosenFile || !currentSubj) return;
    const requestId = ++validationRequestRef.current;

    // The backend inspects extracted document text; filenames are not treated as proof of subject identity.
    setValidatingFile(true);
    setValidationError('');
    try {
      const fd = new FormData();
      fd.append('subject_id', currentSubj.id);
      fd.append('file', chosenFile);
      const res = await api.post('/papers/validate-subject', fd);
      if (validationRequestRef.current !== requestId) return;
      if (res.data && !res.data.valid) {
        setValidationError(res.data.message || 'Subject is not as per selected.');
        setValidationOutcome(res.data.outcome || 'mismatch');
      } else {
        setValidationError('');
        setValidationOutcome('');
      }
    } catch (err) {
      if (validationRequestRef.current !== requestId) return;
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string' ? detail : detail?.message;
      setValidationError(
        message
        || 'Subject verification could not be completed. Please try again before uploading.'
      );
      setValidationOutcome(detail?.outcome || 'inconclusive');
    } finally {
      if (validationRequestRef.current === requestId) setValidatingFile(false);
    }
  };

  const selectFile = (selected) => {
    if (!selected) return;
    validationRequestRef.current += 1;
    setFile(selected);
    setError('');
    setWarning('');
    setValidationError('');
    setValidationOutcome('');
    setValidatingFile(false);
    setStep(0);

    if (!title) setTitle(selected.name.replace(/\.[^/.]+$/, ''));
    if (selected.size > 10 * 1024 * 1024) {
      setValidationError('This file exceeds the 10 MB upload limit. Choose a smaller document.');
      setValidationOutcome('inconclusive');
      return;
    }
    if (!/\.(pdf|docx|txt)$/i.test(selected.name)) {
      setValidationError('Unsupported document type. Choose a PDF, DOCX, or TXT file.');
      setValidationOutcome('inconclusive');
      return;
    }
    if (selectedSubject) validateSelectedFile(selected, selectedSubject);
  };

  const handleFileChange = (event) => selectFile(event.target.files?.[0]);

  const handleFileDrop = (event) => {
    event.preventDefault();
    selectFile(event.dataTransfer.files?.[0]);
  };

  const handleSubjectCreated = (newSubject) => {
    fetchSubjects(newSubject.id);
  };

  const handleUploadAndScrutinize = async (e) => {
    e.preventDefault();
    if (!file || !subjectId) {
      setError('Please select a subject and upload a question paper file.');
      return;
    }
    if (validationError) {
      setError(validationError);
      return;
    }
    if (validatingFile) {
      setError('Wait for document subject validation to finish before starting scrutiny.');
      return;
    }
    if (selectedUnits.length === 0) {
      setError('Please select at least one applicable unit for this examination.');
      return;
    }

    setError('');
    setUploading(true);
    setStep(1);

    try {
      const formData = new FormData();
      formData.append('subject_id', subjectId);
      formData.append('academic_year', academicYear);
      formData.append('exam_type', examType);
      formData.append('title', title);
      formData.append('selected_units', JSON.stringify(selectedUnits));
      formData.append('auto_analyze', 'true');
      formData.append('file', file);

      setStep(2);
      // Backend validates subject and extracts questions
      const res = await api.post('/papers/upload', formData, {
        timeout: 180000,
      });
      const paperId = res.data.id;
      const status = res.data.status;

      setStep(3);
      if (status !== 'PENDING_REVIEW' && status !== 'ANALYZED') {
        await api.post(`/papers/${paperId}/analyze`, null, { timeout: 180000 });
      }

      setStep(4);
      setTimeout(() => {
        navigate(`/papers/${paperId}`);
      }, 800);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail?.message || (Array.isArray(detail) ? detail.map((d) => d.msg || d).join('; ') : null));
      
      const finalMsg = msg || err.message || 'Document processing or AI analysis failed.';
      setError(finalMsg);
      if (detail && typeof detail === 'object' && detail.outcome) {
        setValidationError(finalMsg);
        setValidationOutcome(detail.outcome);
        setValidationPaperId(detail.paper_id || null);
      } else if (finalMsg.toLowerCase().includes('subject is not as per selected')) {
        setValidationError(finalMsg);
        setValidationOutcome(detail?.outcome || 'mismatch');
      }
      setStep(0);
      setUploading(false);
    }
  };

  const pipelineSteps = [
    { title: "Uploading Question Paper", desc: `Subject Workspace: ${selectedSubject?.code || ''} | Active Units: ${selectedUnits.join(', ')}` },
    { title: "Subject Verification & Question Extraction", desc: "Verifying subject curriculum match & parsing questions/marks via PyMuPDF/python-docx" },
    { title: "AI Cognitive Analysis & Rule Verification", desc: "Bloom's taxonomy (K1-K6), CO mapping, syllabus alignment, and deterministic rule validation" },
    { title: "Scrutiny Report Generation", desc: "Compiling 100-point scrutiny score and moderator review dossier" }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-adcet-red"></span>
            <h1 className="text-xl font-bold text-adcet-navy">Upload Question Paper for AI Scrutiny</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Upload PDF or DOCX question papers into the subject's isolated workspace. The system verifies curriculum alignment, Bloom's cognitive taxonomy, Course Outcomes, and examination formatting rules.
          </p>
        </div>

        {canManageCurriculum && (
          <button
            type="button"
            onClick={() => setAddSubjectOpen(true)}
            className="shrink-0 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-adcet-navy text-xs font-bold transition-colors flex items-center gap-1.5 border border-slate-200"
          >
            <Plus className="w-3.5 h-3.5 text-adcet-red" />
            Add New Subject
          </button>
        )}
      </div>

      {/* Critical Subject Mismatch Error Banner */}
      {validationError && (
        <div className="p-4 bg-red-50 border-2 border-red-300 rounded-2xl text-red-800 text-xs shadow-sm flex items-start gap-3 animate-in fade-in duration-200">
          <XCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold text-sm text-red-900">{validationOutcome === 'mismatch' ? 'Subject Mismatch Prevented' : 'Document Validation Needs Attention'}</p>
            <p className="leading-relaxed">{validationError}</p>
            <p className="text-[11px] text-red-700 font-semibold pt-1">
              Action Required: Please select the matching subject from the dropdown above, or upload the question paper corresponding to {selectedSubject?.code} - {selectedSubject?.name}.
            </p>
            {validationPaperId && (
              <button type="button" className="text-[11px] text-adcet-navy underline font-semibold pt-1" onClick={() => navigate(`/papers/${validationPaperId}`)}>
                Open saved validation record
              </button>
            )}
          </div>
        </div>
      )}

      {/* General Error Banner */}
      {error && !validationError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs flex items-center">
          <AlertCircle className="w-4 h-4 mr-2 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Warning Banner */}
      {warning && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-xs flex items-center">
          <AlertCircle className="w-4 h-4 mr-2 shrink-0" />
          <span>{warning}</span>
        </div>
      )}

      {uploading ? (
        <div className="bg-white border border-slate-200 p-8 rounded-2xl shadow-sm space-y-6">
          <h2 className="text-base font-bold text-adcet-navy text-center">Executing Automated Scrutiny Pipeline</h2>
          
          <div className="space-y-4 max-w-lg mx-auto">
            {pipelineSteps.map((s, idx) => {
              const active = step === idx + 1;
              const completed = step > idx + 1;

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border transition-all flex items-center justify-between ${
                    completed
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : active
                      ? 'bg-red-50 border-adcet-red/40 text-adcet-red shadow-sm'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {completed ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    ) : active ? (
                      <Loader2 className="w-5 h-5 text-adcet-red animate-spin" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border border-slate-300 flex items-center justify-center text-xs font-semibold text-slate-500">
                        {idx + 1}
                      </div>
                    )}
                    <div>
                      <p className="text-xs font-bold text-slate-900">{s.title}</p>
                      <p className="text-[11px] text-slate-500">{s.desc}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <form onSubmit={handleUploadAndScrutinize} className="space-y-6">
          <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-5">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-adcet-red" />
              1. Select Subject Workspace & Examination Metadata
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700">
                    Subject Workspace <span className="text-adcet-red">*</span>
                  </label>
                  {canManageCurriculum && (
                    <button
                      type="button"
                      onClick={() => setAddSubjectOpen(true)}
                      className="text-[11px] font-bold text-adcet-red hover:underline flex items-center gap-1"
                    >
                      + Add Subject
                    </button>
                  )}
                </div>
                <select
                  value={subjectId}
                  onChange={(e) => handleSubjectChange(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-800 focus:outline-none focus:border-adcet-red focus:bg-white transition-all cursor-pointer"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.code} — {s.name} (Sem {s.semester})
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-slate-400 mt-1">
                  Papers uploaded will be strictly validated against this subject's syllabus and keywords.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Examination Type
                </label>
                <select
                  value={examType}
                  onChange={(e) => setExamType(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-800 font-medium focus:outline-none focus:border-adcet-red focus:bg-white transition-all"
                >
                  <option value="End-Semester Examination">End-Semester Examination (Full Syllabus)</option>
                  <option value="Mid-Semester Examination">Mid-Semester Examination (Units 1-3)</option>
                  <option value="In-Semester Evaluation 1">In-Semester Evaluation 1 (ISE-1)</option>
                  <option value="In-Semester Evaluation 2">In-Semester Evaluation 2 (ISE-2)</option>
                  <option value="Re-Examination">Re-Examination / Make-Up Examination</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Academic Year
                </label>
                <input
                  type="text"
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-800 font-medium focus:outline-none focus:border-adcet-red focus:bg-white transition-all"
                  placeholder="Enter the academic year"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Paper Title / Identifier
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. End-Sem Exam Question Paper May 2026"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-800 font-medium focus:outline-none focus:border-adcet-red focus:bg-white transition-all"
                />
              </div>
            </div>

            {/* Applicable Syllabus Units */}
            <div className="pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-adcet-navy" />
                  Active Syllabus Units for this Examination:
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleSelectAllUnits}
                    className="text-[11px] text-adcet-navy hover:text-adcet-red font-semibold transition-colors"
                  >
                    Select All
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    type="button"
                    onClick={handleClearAllUnits}
                    className="text-[11px] text-slate-500 hover:text-adcet-red font-semibold transition-colors"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              {availableUnits.length === 0 ? (
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-800">
                  No syllabus units configured for this subject yet. You can add units in Curriculum Management.
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                  {availableUnits.map((uNum) => {
                    const isSelected = selectedUnits.includes(uNum);
                    return (
                      <button
                        key={uNum}
                        type="button"
                        onClick={() => toggleUnit(uNum)}
                        className={`p-2.5 rounded-xl border text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                          isSelected
                            ? 'bg-adcet-navy text-white border-adcet-navy shadow-sm'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        {isSelected ? <CheckSquare className="w-3.5 h-3.5 text-adcet-red" /> : <Square className="w-3.5 h-3.5 text-slate-400" />}
                        Unit {uNum}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Document Upload Area */}
          <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <UploadCloud className="w-4 h-4 text-adcet-red" />
              2. Upload Question Paper Document (PDF or DOCX)
            </h2>

            <div onDragOver={(event) => event.preventDefault()} onDrop={handleFileDrop} className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
              validationError
                ? 'border-red-300 bg-red-50/30'
                : file
                ? 'border-emerald-300 bg-emerald-50/20'
                : 'border-slate-300 hover:border-adcet-red bg-slate-50/50'
            }`}>
              <input
                type="file"
                id="paper-file-input"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="paper-file-input" className="cursor-pointer block">
                <div className="w-12 h-12 rounded-full bg-red-50 text-adcet-red flex items-center justify-center mx-auto mb-3">
                  <FileText className="w-6 h-6" />
                </div>
                <p className="text-xs font-bold text-slate-800">
                  {file ? file.name : 'Click to select or drag and drop question paper'}
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB · ` : ''}Supported formats: PDF, DOCX, TXT (Max 10 MB)
                </p>

                {validatingFile && (
                  <div className="mt-2 flex items-center justify-center gap-1.5 text-xs text-adcet-navy font-semibold">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Validating document against {selectedSubject?.code} curriculum...
                  </div>
                )}

                {file && !validationError && !validatingFile && (
                  <div className="mt-2 inline-flex items-center gap-1 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-200 text-xs font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    Document verified for {selectedSubject?.code} - {selectedSubject?.name}
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Submit Action */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={!file || !subjectId || selectedUnits.length === 0 || Boolean(validationError) || validatingFile}
              className="px-6 py-3 rounded-xl bg-adcet-red hover:bg-red-700 text-white text-xs font-bold transition-all shadow-md flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>Upload & Run Scrutiny Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      )}

      {/* Add Subject Modal */}
      <AddSubjectModal
        isOpen={addSubjectOpen}
        onClose={() => setAddSubjectOpen(false)}
        onSubjectCreated={handleSubjectCreated}
      />
    </div>
  );
}
