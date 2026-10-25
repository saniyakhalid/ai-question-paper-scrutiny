import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { X, BookOpen, Plus, AlertCircle, Loader2, Trash2, UploadCloud, FileText, CheckCircle2 } from 'lucide-react';

const blankUnit = (number) => ({ unit_number: number, title: '', topics: [{ topic_name: '' }] });
const blankOutcome = () => ({ co_code: '', description: '' });

export default function AddSubjectModal({ isOpen, onClose, onSubjectCreated, subject = null, allowSyllabusImport = true }) {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [department, setDepartment] = useState('');
  const [branch, setBranch] = useState('');
  const [semester, setSemester] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [totalMarks, setTotalMarks] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('');
  const [units, setUnits] = useState([]);
  const [outcomes, setOutcomes] = useState([]);
  const [syllabusFile, setSyllabusFile] = useState(null);
  const [syllabusPreview, setSyllabusPreview] = useState(null);
  const [previewingSyllabus, setPreviewingSyllabus] = useState(false);
  const [createdSubjectId, setCreatedSubjectId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setSuccess('');
    setCreatedSubjectId(null);
    setSyllabusFile(null);
    setSyllabusPreview(null);
    setCode(subject?.code || '');
    setName(subject?.name || '');
    setDepartment(subject?.department || '');
    setBranch(subject?.branch || '');
    setSemester(subject?.semester ?? '');
    setAcademicYear(subject?.academic_year || '');
    setTotalMarks(subject?.total_marks ?? '');
    setDurationMinutes(subject?.duration_minutes || subject?.exam_duration || '');
    setUnits([]);
    setOutcomes([]);

    if (subject?.id) {
      api.get(`/subjects/${subject.id}/syllabus`).then((res) => {
        if (res.data && res.data.length > 0) {
          setUnits(res.data.map((u) => ({
            unit_number: u.unit_number,
            title: u.title || '',
            topics: (u.topics && u.topics.length > 0) ? u.topics : [{ topic_name: '' }]
          })));
        }
      }).catch(() => {});
      api.get(`/subjects/${subject.id}/cos`).then((res) => {
        if (res.data && res.data.length > 0) {
          setOutcomes(res.data.map((c) => ({
            co_code: c.co_code,
            description: c.description
          })));
        }
      }).catch(() => {});
    }
  }, [isOpen, subject]);

  if (!isOpen) return null;

  const close = () => {
    if (!loading) onClose();
  };

  const updateUnit = (index, key, value) => {
    setUnits((current) => current.map((unit, i) => i === index ? { ...unit, [key]: value } : unit));
  };

  const updateTopic = (unitIndex, topicIndex, value) => {
    setUnits((current) => current.map((unit, i) => i === unitIndex
      ? { ...unit, topics: unit.topics.map((topic, j) => j === topicIndex ? { ...topic, topic_name: value } : topic) }
      : unit));
  };

  const updateOutcome = (index, key, value) => {
    setOutcomes((current) => current.map((outcome, i) => i === index ? { ...outcome, [key]: value } : outcome));
  };

  const handleSyllabusFileChange = async (file) => {
    setSyllabusFile(file || null);
    setSyllabusPreview(null);
    setError('');
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    setPreviewingSyllabus(true);
    try {
      const { data } = await api.post('/subjects/syllabus/preview', formData);
      const metadata = data.metadata || {};
      if (metadata.code) setCode(metadata.code);
      if (metadata.name) setName(metadata.name);
      if (metadata.department) setDepartment(metadata.department);
      if (metadata.branch) setBranch(metadata.branch);
      if (metadata.semester) setSemester(metadata.semester);
      if (metadata.academic_year) setAcademicYear(metadata.academic_year.replace(/[–/]/g, '-'));
      if (metadata.total_marks) setTotalMarks(String(metadata.total_marks));
      else if (!totalMarks) setTotalMarks('100');
      if (metadata.duration_minutes) setDurationMinutes(String(metadata.duration_minutes));
      else if (!durationMinutes) setDurationMinutes('180');

      // Auto-populate units and course outcomes from extracted file
      if (data.units && data.units.length > 0) {
        setUnits(data.units.map((u) => ({
          unit_number: u.unit_number,
          title: u.title || `Unit ${u.unit_number}`,
          topics: (u.topics && u.topics.length > 0)
            ? u.topics.map((t) => ({ topic_name: typeof t === 'string' ? t : (t.topic_name || '') }))
            : [{ topic_name: '' }]
        })));
      }
      if (data.course_outcomes && data.course_outcomes.length > 0) {
        setOutcomes(data.course_outcomes.map((co) => ({
          co_code: co.co_code,
          description: co.description
        })));
      }
      setSyllabusPreview(data);
    } catch (previewError) {
      setError(previewError.response?.data?.detail || 'Could not read the syllabus file. Upload a searchable PDF, DOCX, or TXT file.');
    } finally {
      setPreviewingSyllabus(false);
    }
  };

  const importSyllabusForSubject = async (subjectId, year) => {
    const formData = new FormData();
    formData.append('file', syllabusFile);
    if (year) formData.append('academic_year', year);
    formData.append('replace_existing', 'true');
    return api.post(`/subjects/${subjectId}/syllabus/upload`, formData);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (createdSubjectId) {
      onClose();
      return;
    }

    if (previewingSyllabus) {
      setError('Wait for the syllabus file to finish processing before saving.');
      return;
    }

    const payload = {
      code: code.trim().toUpperCase(),
      name: name.trim(),
      department: department.trim(),
      branch: branch.trim(),
      semester: Number(semester),
      academic_year: academicYear.trim() || null,
      total_marks: Number(totalMarks),
      duration_minutes: Number(durationMinutes),
    };
    const filledOutcomes = outcomes.filter((outcome) => outcome.co_code.trim() || outcome.description.trim());
    const filledUnits = units.filter((unit) => unit.title.trim());

    if (!Number.isInteger(payload.semester) || payload.semester < 1 || payload.semester > 16) {
      setError('Choose the subject semester.');
      return;
    }
    if (!Number.isInteger(payload.total_marks) || payload.total_marks < 1 || !Number.isInteger(payload.duration_minutes) || payload.duration_minutes < 1) {
      setError('Enter the actual maximum marks and exam duration for this subject.');
      return;
    }
    if (filledOutcomes.some((outcome) => !outcome.co_code.trim() || !outcome.description.trim())) {
      setError('Complete both the code and description for each course outcome, or remove the empty row.');
      return;
    }
    if (filledUnits.some((unit) => !Number.isInteger(Number(unit.unit_number)) || Number(unit.unit_number) < 1)) {
      setError('Syllabus unit numbers must be positive whole numbers.');
      return;
    }
    const unitNumbers = filledUnits.map((unit) => Number(unit.unit_number));
    if (new Set(unitNumbers).size !== unitNumbers.length) {
      setError('Each syllabus unit must have a unique unit number.');
      return;
    }

    setLoading(true);
    try {
      if (createdSubjectId) {
        if (syllabusFile) await importSyllabusForSubject(createdSubjectId, payload.academic_year);
        onSubjectCreated?.({ id: createdSubjectId });
        onClose();
        return;
      }

      if (subject) {
        const { data } = await api.put(`/subjects/${subject.id}`, payload);
        if (syllabusFile) {
          try {
            await importSyllabusForSubject(subject.id, payload.academic_year);
          } catch (uploadError) {
            console.warn('Syllabus file archiving notice:', uploadError);
          }
        }
        setSuccess(`Saved changes for ${data.code} — ${data.name}.`);
        onSubjectCreated?.(data);
        onClose();
        return;
      }

      const selectedUnits = filledUnits.map((unit) => ({
        unit_number: Number(unit.unit_number),
        title: unit.title.trim(),
        topics: unit.topics.map((topic) => topic.topic_name.trim()).filter(Boolean).map((topic_name) => ({ topic_name })),
      }));
      const course_outcomes = filledOutcomes.map((outcome) => ({
        co_code: outcome.co_code.trim(),
        description: outcome.description.trim(),
      }));
      const { data: created } = await api.post('/subjects', {
        ...payload,
        syllabus_units: selectedUnits,
        course_outcomes,
      });

      if (syllabusFile) {
        try {
          await importSyllabusForSubject(created.id, payload.academic_year);
        } catch (uploadError) {
          console.warn('Syllabus file archiving notice:', uploadError);
        }
      }

      setSuccess(`Created ${created.code} — ${created.name} with the curriculum details.`);
      onSubjectCreated?.(created);
      onClose();
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not save this subject. Check the fields and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" role="dialog" aria-modal="true" aria-labelledby="subject-modal-title">
      <button type="button" aria-label="Close dialog" className="absolute inset-0 cursor-default bg-adcet-navy/40" onClick={close} />
      <div className="relative flex max-h-[calc(100dvh-1.5rem)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-50 text-adcet-red"><BookOpen className="h-5 w-5" /></div>
            <div>
              <h2 id="subject-modal-title" className="font-bold text-adcet-navy">{subject ? 'Edit subject' : 'Add a subject'}</h2>
              <p className="text-xs text-slate-500">Enter actual subject details or extract them from the official syllabus.</p>
            </div>
          </div>
          <button type="button" onClick={close} disabled={loading} className="rounded-lg p-2 text-slate-500 hover:bg-white hover:text-slate-900 disabled:opacity-50"><X className="h-5 w-5" /></button>
        </header>

        <form onSubmit={handleSubmit} className="overflow-y-auto p-5 sm:p-6 space-y-6">
          {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
          {success && <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{success}</div>}

          {/* 1. TOP SECTION: Syllabus File Auto-Extraction */}
          {allowSyllabusImport && (
            <section className="rounded-2xl border-2 border-dashed border-red-200 bg-red-50/30 p-4 transition-all hover:bg-red-50/50">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-adcet-red text-[10px] font-bold text-white">1</span>
                    <h3 className="text-sm font-bold text-adcet-navy">
                      {subject ? 'Re-extract or update from Syllabus File' : 'Upload Syllabus File (Auto-Extract All Details)'}
                    </h3>
                  </div>
                  <p className="mt-1 text-xs text-slate-500 max-w-xl">
                    Upload a syllabus document (.pdf, .docx, .txt). The system will automatically extract Subject Name, Course Code, Department, Semester, Marks, Syllabus Units with topics, and Course Outcomes!
                  </p>
                </div>
                <UploadCloud className="h-6 w-6 shrink-0 text-adcet-red" />
              </div>

              <div className="mt-3">
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => handleSyllabusFileChange(e.target.files?.[0] || null)}
                  className="block w-full text-xs text-slate-600 file:mr-3 file:rounded-xl file:border-0 file:bg-adcet-navy file:px-3.5 file:py-2 file:text-xs file:font-bold file:text-white hover:file:bg-slate-800 file:cursor-pointer"
                />
              </div>

              {syllabusFile && (
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-3 text-xs shadow-xs">
                  <span className="flex min-w-0 items-center gap-2 font-medium text-slate-800">
                    <FileText className="h-4 w-4 shrink-0 text-adcet-red" />
                    <span className="truncate">{syllabusFile.name}</span>
                  </span>
                  <button type="button" onClick={() => handleSyllabusFileChange(null)} className="font-bold text-rose-600 hover:underline">
                    Remove file
                  </button>
                </div>
              )}

              {previewingSyllabus && (
                <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-adcet-red animate-pulse">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Extracting subject code, name, units, and course outcomes from document…</span>
                </div>
              )}

              {syllabusPreview && (
                <div role="status" className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-900 shadow-xs">
                  <p className="flex items-center gap-1.5 font-bold text-emerald-800">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    Syllabus details extracted successfully!
                  </p>
                  <p className="mt-1 text-slate-700">
                    Extracted <strong>{syllabusPreview.units_extracted} unit(s)</strong> and <strong>{syllabusPreview.course_outcomes_extracted} course outcome(s)</strong>.
                    All details have been filled into the form below. Review or adjust any field before saving.
                  </p>
                  {!!syllabusPreview.warnings?.length && (
                    <p className="mt-1 font-semibold text-amber-800">{syllabusPreview.warnings.join(' ')}</p>
                  )}
                </div>
              )}
            </section>
          )}

          {/* 2. CORE SUBJECT DETAILS */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-700">2</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                Subject Information (Auto-Filled or Manual)
              </h3>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="text-xs font-semibold text-slate-700">Subject code
                <input required value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. CS401" className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm uppercase text-slate-900 outline-none focus:border-adcet-red font-mono font-bold" />
              </label>
              <label className="text-xs font-semibold text-slate-700">Subject name
                <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Machine Learning" className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red font-semibold" />
              </label>
              <label className="text-xs font-semibold text-slate-700">Department
                <input required value={department} onChange={(e) => setDepartment(e.target.value)} placeholder="Department name" className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red" />
              </label>
              <label className="text-xs font-semibold text-slate-700">Branch / program
                <input required value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="Branch or degree program" className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red" />
              </label>
              <label className="text-xs font-semibold text-slate-700">Semester
                <select required value={semester} onChange={(e) => setSemester(e.target.value ? Number(e.target.value) : '')} className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red">
                  <option value="">Choose semester</option>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((value) => <option key={value} value={value}>Semester {value}</option>)}
                </select>
              </label>
              <label className="text-xs font-semibold text-slate-700">Academic year <span className="font-normal text-slate-400">(optional)</span>
                <input value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="e.g. 2026–2027" className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red" />
              </label>
              <label className="text-xs font-semibold text-slate-700">Maximum exam marks
                <input required type="number" min="1" value={totalMarks} onChange={(e) => setTotalMarks(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red" />
              </label>
              <label className="text-xs font-semibold text-slate-700">Exam duration (minutes)
                <input required type="number" min="1" value={durationMinutes} onChange={(e) => setDurationMinutes(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-adcet-red" />
              </label>
            </div>
          </section>

          {/* 3. SYLLABUS UNITS SECTION */}
          <section className="rounded-2xl border border-slate-200 p-4 space-y-3 bg-slate-50/50">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-700">3</span>
                  <h3 className="text-sm font-bold text-slate-900">
                    Syllabus Units {units.length > 0 && <span className="font-mono text-adcet-red">({units.length})</span>}
                  </h3>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {syllabusPreview ? 'Review or edit the extracted syllabus units and topics below.' : 'Official syllabus units for question paper scrutiny boundaries.'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setUnits((current) => [...current, blankUnit(Math.max(0, ...current.map((unit) => Number(unit.unit_number) || 0)) + 1)])}
                className="inline-flex shrink-0 items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-adcet-navy shadow-xs hover:bg-slate-50"
              >
                <Plus className="h-3.5 w-3.5 text-adcet-red" /> Add Unit
              </button>
            </div>

            {units.length === 0 && (
              <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-xs text-slate-500">
                No units added yet. Upload a syllabus file above to extract automatically, or click &quot;Add Unit&quot; to enter manually.
              </p>
            )}

            <div className="space-y-3">
              {units.map((unit, index) => (
                <div key={index} className="rounded-xl border border-slate-200 bg-white p-4 space-y-2 shadow-2xs">
                  <div className="flex items-center gap-2">
                    <label className="w-24 shrink-0 text-[11px] font-bold text-slate-600">Unit no.
                      <input type="number" min="1" value={unit.unit_number} onChange={(e) => updateUnit(index, 'unit_number', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-bold text-adcet-navy text-center" />
                    </label>
                    <label className="min-w-0 flex-1 text-[11px] font-bold text-slate-600">Unit title
                      <input value={unit.title} onChange={(e) => updateUnit(index, 'title', e.target.value)} placeholder="e.g. Linear Regression & Gradient Descent" className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 font-semibold focus:border-adcet-red" />
                    </label>
                    <button type="button" aria-label={`Remove unit ${unit.unit_number}`} onClick={() => setUnits((current) => current.filter((_, i) => i !== index))} className="mt-5 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-rose-600 transition-colors">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="pt-2 border-t border-slate-100 space-y-2">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Topics for Scrutiny Keyword Matching:</span>
                    {unit.topics.map((topic, topicIndex) => (
                      <div key={topicIndex} className="flex gap-2">
                        <input
                          value={topic.topic_name}
                          onChange={(e) => updateTopic(index, topicIndex, e.target.value)}
                          placeholder="e.g. Loss Functions, Bias-Variance Tradeoff"
                          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-1.5 text-xs text-slate-800 focus:bg-white focus:border-adcet-red"
                        />
                        <button type="button" aria-label="Remove topic" onClick={() => setUnits((current) => current.map((u, i) => i === index ? { ...u, topics: u.topics.filter((_, j) => j !== topicIndex) } : u))} className="rounded-lg p-1.5 text-slate-400 hover:text-rose-600">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                    <button type="button" onClick={() => setUnits((current) => current.map((u, i) => i === index ? { ...u, topics: [...u.topics, { topic_name: '' }] } : u))} className="text-xs font-bold text-adcet-red hover:underline inline-flex items-center gap-1">
                      <Plus className="w-3 h-3" /> Add Topic
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 4. COURSE OUTCOMES SECTION */}
          <section className="rounded-2xl border border-slate-200 p-4 space-y-3 bg-slate-50/50">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-700">4</span>
                  <h3 className="text-sm font-bold text-slate-900">
                    Course Outcomes (COs) {outcomes.length > 0 && <span className="font-mono text-adcet-red">({outcomes.length})</span>}
                  </h3>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {syllabusPreview ? 'Review or edit the extracted Course Outcomes below.' : 'Official course outcomes used for Bloom & CO mapping scrutiny.'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOutcomes((current) => [...current, blankOutcome()])}
                className="inline-flex shrink-0 items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-adcet-navy shadow-xs hover:bg-slate-50"
              >
                <Plus className="h-3.5 w-3.5 text-adcet-red" /> Add Outcome
              </button>
            </div>

            {outcomes.length === 0 && (
              <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-xs text-slate-500">
                No outcomes added yet. Upload a syllabus file above to extract automatically, or click &quot;Add Outcome&quot; to enter manually.
              </p>
            )}

            <div className="space-y-2">
              {outcomes.map((outcome, index) => (
                <div key={index} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2.5 shadow-2xs">
                  <input
                    value={outcome.co_code}
                    onChange={(e) => updateOutcome(index, 'co_code', e.target.value)}
                    placeholder="CO1"
                    className="w-20 shrink-0 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs font-mono font-bold text-adcet-navy uppercase text-center"
                  />
                  <input
                    value={outcome.description}
                    onChange={(e) => updateOutcome(index, 'description', e.target.value)}
                    placeholder="Official course outcome description (e.g. Formulate and implement regression models)..."
                    className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 focus:border-adcet-red"
                  />
                  <button
                    type="button"
                    aria-label="Remove course outcome"
                    onClick={() => setOutcomes((current) => current.filter((_, i) => i !== index))}
                    className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-rose-600 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </section>

          {subject && <p className="mt-5 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">Syllabus units, topics, outcomes, and uploaded documents can be edited in the subject workspace after saving these details.</p>}

          <div className="mt-6 flex flex-col-reverse gap-2 border-t border-slate-200 pt-4 sm:flex-row sm:justify-end">
            <button type="button" onClick={close} disabled={loading} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">{createdSubjectId ? 'Close' : 'Cancel'}</button>
            <button type="submit" disabled={loading || previewingSyllabus} className="inline-flex items-center justify-center gap-2 rounded-xl bg-adcet-red px-5 py-2.5 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-50">{loading && <Loader2 className="h-4 w-4 animate-spin" />}{loading ? (createdSubjectId ? 'Retrying import…' : 'Saving subject…') : createdSubjectId ? 'Retry syllabus import' : subject ? 'Save changes' : 'Create subject'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
