import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { papersAPI, subjectsAPI } from '../services/api';
import { Upload, FileText, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

export default function PaperUploadPage() {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [title, setTitle] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [examType, setExamType] = useState('End-Sem');
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [processingStep, setProcessingStep] = useState(0); // 0: Idle, 1..7 Pipeline
  const navigate = useNavigate();

  useEffect(() => {
    const loadSubjects = async () => {
      try {
        const res = await subjectsAPI.list();
        setSubjects(res.data);
        if (res.data.length > 0) {
          setSelectedSubject(res.data[0].id);
          setAcademicYear(res.data[0].academic_year || '');
          setTitle(`${res.data[0].code} ${res.data[0].name} Question Paper`);
        }
      } catch (err) {
        console.error("Failed to load subjects", err);
      }
    };
    loadSubjects();
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF or DOCX question paper file to upload.');
      return;
    }
    setError('');
    setProcessingStep(1);

    const formData = new FormData();
    formData.append('title', title);
    formData.append('subject_id', selectedSubject);
    formData.append('academic_year', academicYear);
    formData.append('exam_type', examType);
    formData.append('file', file);

    try {
      // Step 1: Uploading & Extraction
      const uploadRes = await papersAPI.upload(formData);
      const paperId = uploadRes.data.id;
      setProcessingStep(3); // Extracted & Parsed

      // Step 2: Trigger AI Analysis & Rule Validation
      setProcessingStep(4);
      await papersAPI.analyze(paperId);
      setProcessingStep(7); // Completed

      setTimeout(() => {
        navigate(`/papers/${paperId}`);
      }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process question paper upload');
      setProcessingStep(0);
    }
  };

  const pipelineSteps = [
    "Uploading Document",
    "Extracting Text (PyMuPDF / DOCX)",
    "Parsing Question Structures",
    "AI Analysis (Bloom & CO Mapping)",
    "Executing Deterministic Rule Engine",
    "Checking Semantic Similarity",
    "Generating Scrutiny Report"
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Upload Question Paper for Scrutiny</h1>
        <p className="text-sm text-slate-500">Upload PDF/DOCX paper to trigger AI scrutiny, rule validation & similarity analysis</p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {processingStep > 0 ? (
          <div className="py-12 text-center space-y-6">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 text-blue-600 mb-2">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">Automated Scrutiny Pipeline Running</h3>
            
            <div className="max-w-md mx-auto space-y-3 text-left">
              {pipelineSteps.map((step, idx) => {
                const isDone = processingStep > idx + 1;
                const isCurrent = processingStep === idx + 1;
                return (
                  <div key={idx} className="flex items-center space-x-3 text-sm">
                    {isDone ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="w-5 h-5 text-blue-600 animate-spin shrink-0" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-slate-300 shrink-0" />
                    )}
                    <span className={isDone ? "text-slate-900 font-medium" : isCurrent ? "text-blue-600 font-semibold" : "text-slate-400"}>
                      {step}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">Subject</label>
                <select
                  value={selectedSubject}
                  onChange={(e) => setSelectedSubject(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg shadow-xs text-sm"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Paper Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg shadow-xs text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Academic Year</label>
                <input
                  type="text"
                  required
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg shadow-xs text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Exam Type</label>
                <select
                  value={examType}
                  onChange={(e) => setExamType(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg shadow-xs text-sm"
                >
                  <option value="End-Sem">End-Sem Examination</option>
                  <option value="Mid-Sem">Mid-Sem Examination</option>
                  <option value="Makeup">Makeup Examination</option>
                </select>
              </div>
            </div>

            {/* Drag & Drop File Upload Area */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Question Paper File (PDF / DOCX)</label>
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                  dragActive ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'
                }`}
              >
                <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                <p className="text-sm font-medium text-slate-700">
                  {file ? file.name : "Drag and drop your question paper file here, or click to browse"}
                </p>
                <p className="text-xs text-slate-500 mt-1">Supports PDF (.pdf) and Word Document (.docx)</p>
                
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => e.target.files && setFile(e.target.files[0])}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="mt-4 inline-flex items-center px-4 py-2 text-xs font-semibold rounded-lg bg-white border border-slate-300 shadow-2xs hover:bg-slate-50 cursor-pointer text-slate-700"
                >
                  Browse Computer
                </label>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm text-sm transition-colors"
            >
              Start Automated Question Paper Scrutiny
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
