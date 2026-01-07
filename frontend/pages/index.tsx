import { useState, useEffect } from 'react';
import Head from 'next/head';
import Navbar from '../components/Navbar';
import {
  uploadBRS,
  uploadCR,
  startConsolidation,
  getJobStatus,
  getStats,
  getDownloadUrl
} from '../src/services/api';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, Download } from 'lucide-react';

interface JobResult {
  brs_id: string;
  version: string;
  sections: number;
  validation_passed: boolean;
  json_output: string;
  markdown_output: string;
  pdf_output: string;
}

interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
  progress?: number;
  result?: JobResult;
  created_at: string;
  updated_at: string;
}

interface Stats {
  vector_store: {
    brs_chunks: number;
    cr_chunks: number;
    total_chunks: number;
  };
  llm_provider: string;
  llm_model: string;
}

interface UploadedDocument {
  doc_id?: string;
  cr_id?: string;
  version?: string;
  sections?: number;
  deltas?: number;
  source_file: string;
}

interface UploadedDocsState {
  brs: UploadedDocument[];
  cr: UploadedDocument[];
}

export default function Home() {
  const [brsFiles, setBrsFiles] = useState<File[]>([]);
  const [crFiles, setCrFiles] = useState<File[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDocsState>({ brs: [], cr: [] });
  const [isUploading, setIsUploading] = useState(false);
  const [consolidationJob, setConsolidationJob] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load stats on mount
  useEffect(() => {
    loadStats();
  }, []);

  // Poll job status
  useEffect(() => {
    if (consolidationJob && jobStatus?.status === 'processing') {
      const interval = setInterval(async () => {
        try {
          const status = await getJobStatus(consolidationJob);
          setJobStatus(status);
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(interval);
            loadStats();
          }
        } catch (err) {
          console.error('Error polling job:', err);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [consolidationJob, jobStatus]);

  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  const handleBRSUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    setIsUploading(true);
    setError(null);
    try {
      for (const file of files) {
        const result = await uploadBRS(file);
        setUploadedDocs(prev => ({
          ...prev,
          brs: [...prev.brs, result.document]
        }));
      }
      setBrsFiles([]);
    } catch (err: any) {
      setError(`Upload failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleCRUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    setIsUploading(true);
    setError(null);
    try {
      for (const file of files) {
        const result = await uploadCR(file);
        setUploadedDocs(prev => ({
          ...prev,
          cr: [...prev.cr, result.change_request]
        }));
      }
      setCrFiles([]);
    } catch (err: any) {
      setError(`Upload failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleConsolidate = async () => {
    setIsUploading(true);
    setError(null);
    try {
      const result = await startConsolidation({
        brs_id: `BRS-FINAL-${Date.now()}`,
        title: 'Consolidated Business Requirements Specification',
        version: 'v1.0'
      });
      setConsolidationJob(result.job_id);
      setJobStatus({
        status: 'pending',
        job_id: result.job_id,
        message: 'Job started...',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Consolidation failed: ${typeof detail === 'object' ? JSON.stringify(detail, null, 2) : detail}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <>
      <Head>
        <title>GenAI BRS Consolidator</title>
        <meta name="description" content="Enterprise-grade BRS consolidation using controlled RAG" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <Navbar />

        <main className="container mx-auto px-4 py-8 max-w-6xl">
          {/* Hero Section */}
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              GenAI BRS Consolidator
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-2">
              Enterprise-grade system for consolidating multiple BRS documents and Change Requests
            </p>
            <p className="text-sm text-gray-500">
              Powered by Ollama qwen2.5 • ChromaDB • Controlled RAG
            </p>
          </div>

          {/* Stats Card */}
          {stats && (
            <div className="bg-white/40 backdrop-blur-md rounded-2xl p-6 border border-white shadow-xl mb-8">
              <div className="grid grid-cols-3 gap-8">
                <div className="text-center border-r border-slate-200/50">
                  <p className="text-3xl font-bold text-blue-600">{stats.vector_store?.brs_chunks || 0}</p>
                  <p className="text-sm text-slate-500 font-medium">BRS Chunks</p>
                </div>
                <div className="text-center border-r border-slate-200/50">
                  <p className="text-3xl font-bold text-emerald-600">{stats.vector_store?.cr_chunks || 0}</p>
                  <p className="text-sm text-slate-500 font-medium">CR Chunks</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-purple-600">{stats.llm_model || '...'}</p>
                  <p className="text-sm text-slate-500 font-medium">LLM Model</p>
                </div>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 mb-8 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              <div>
                <h4 className="font-semibold text-rose-800">Error</h4>
                <p className="text-sm text-rose-700">{error}</p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            <div className="bg-white/40 backdrop-blur-md rounded-2xl p-6 border border-white shadow-xl">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-slate-800">Upload BRS Documents</h2>
              </div>

              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isUploading ? 'border-gray-200 bg-gray-50/50' : 'border-blue-200 hover:border-blue-400 hover:bg-blue-50/30'
                  }`}
              >
                <input
                  type="file"
                  onChange={handleBRSUpload}
                  multiple
                  disabled={isUploading}
                  className="hidden"
                  id="brs-upload"
                  accept=".pdf,.docx,.doc"
                />
                <label htmlFor="brs-upload" className="cursor-pointer group">
                  <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-blue-200 transition-colors">
                    <Upload className="w-6 h-6 text-blue-600" />
                  </div>
                  <p className="text-slate-600 font-medium capitalize">
                    {isUploading ? 'uploading...' : 'choose files'}
                  </p>
                  <p className="text-slate-400 text-sm mt-1">PDF, DOCX formats supported</p>
                </label>
              </div>

              {uploadedDocs.brs.length > 0 && (
                <div className="mt-6">
                  <p className="text-sm font-semibold text-slate-700 mb-3">Uploaded BRS:</p>
                  <ul className="space-y-2">
                    {uploadedDocs.brs.map((doc, idx) => (
                      <li key={idx} className="flex items-center text-sm text-gray-600 bg-white/50 p-2 rounded border border-blue-100">
                        <CheckCircle className="w-4 h-4 text-emerald-500 mr-2" />
                        <span className="font-medium mr-2">{doc.doc_id || doc.source_file}</span>
                        <span className="text-xs text-gray-500">({doc.sections || 0} sections)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="bg-white/40 backdrop-blur-md rounded-2xl p-6 border border-white shadow-xl">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-emerald-50 rounded-lg">
                  <Upload className="w-6 h-6 text-emerald-600" />
                </div>
                <h2 className="text-xl font-bold text-slate-800">Upload Change Requests</h2>
              </div>

              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isUploading ? 'border-gray-200 bg-gray-50/50' : 'border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50/30'
                  }`}
              >
                <input
                  type="file"
                  onChange={handleCRUpload}
                  multiple
                  disabled={isUploading}
                  className="hidden"
                  id="cr-upload"
                  accept=".pdf,.docx,.doc"
                />
                <label htmlFor="cr-upload" className="cursor-pointer group">
                  <div className="mx-auto w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-emerald-200 transition-colors">
                    <Upload className="w-6 h-6 text-emerald-600" />
                  </div>
                  <p className="text-slate-600 font-medium capitalize">
                    {isUploading ? 'uploading...' : 'choose files'}
                  </p>
                  <p className="text-slate-400 text-sm mt-1">PDF, DOCX formats supported</p>
                </label>
              </div>

              {uploadedDocs.cr.length > 0 && (
                <div className="mt-6">
                  <p className="text-sm font-semibold text-slate-700 mb-3">Uploaded CRs:</p>
                  <ul className="space-y-2">
                    {uploadedDocs.cr.map((doc, idx) => (
                      <li key={idx} className="flex items-center text-sm text-gray-600 bg-white/50 p-2 rounded border border-emerald-100">
                        <CheckCircle className="w-4 h-4 text-emerald-500 mr-2" />
                        <span className="font-medium mr-2">{doc.cr_id || doc.source_file}</span>
                        <span className="text-xs text-gray-500">({doc.deltas || 0} deltas)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Consolidate Button */}
          {(uploadedDocs.brs.length > 0 || (stats && stats.vector_store?.brs_chunks > 0)) && (
            <div className="flex justify-center mb-8">
              <button
                onClick={handleConsolidate}
                disabled={isUploading || (jobStatus?.status === 'processing')}
                className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-8 rounded-lg shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {jobStatus?.status === 'processing' ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Consolidating...
                  </>
                ) : (
                  <>
                    <FileText className="w-5 h-5 mr-2" />
                    Start Consolidation
                  </>
                )}
              </button>
            </div>
          )}

          {/* Job Status */}
          {jobStatus && (
            <div className={`rounded-2xl shadow-xl p-6 mb-8 border backdrop-blur-md ${jobStatus.status === 'completed' ? 'bg-emerald-50/50 border-emerald-100' :
              jobStatus.status === 'failed' ? 'bg-rose-50/50 border-rose-100' :
                'bg-blue-50/50 border-blue-100'
              }`}>
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2 text-slate-800">
                {jobStatus.status === 'completed' && <CheckCircle className="w-6 h-6 text-emerald-600" />}
                {jobStatus.status === 'failed' && <AlertCircle className="w-6 h-6 text-rose-600" />}
                {jobStatus.status === 'processing' && <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />}
                Job Status: <span className="capitalize">{jobStatus.status}</span>
              </h3>

              {/* Progress Bar */}
              {jobStatus.status === 'processing' && (
                <div className="mb-6">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium text-blue-700">Progress</span>
                    <span className="text-sm font-medium text-blue-700">{Math.round(jobStatus.progress || 0)}%</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2.5">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${jobStatus.progress || 0}%` }}
                    ></div>
                  </div>
                </div>
              )}

              <p className="text-slate-600 mb-6 font-medium">{jobStatus.message}</p>

              {jobStatus.result && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white/50 rounded-xl p-4 border border-white">
                      <p className="text-xs font-bold text-slate-400 mb-1 uppercase tracking-widest">BRS ID</p>
                      <p className="text-lg font-bold text-slate-700 truncate">{jobStatus.result.brs_id}</p>
                    </div>
                    <div className="bg-white/50 rounded-xl p-4 border border-white">
                      <p className="text-xs font-bold text-slate-400 mb-1 uppercase tracking-widest">Sections Generated</p>
                      <p className="text-lg font-bold text-slate-700">{jobStatus.result.sections}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 bg-white/50 p-4 rounded-xl border border-slate-100">
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Validation:</p>
                    <div className={`flex items-center gap-1.5 font-bold ${jobStatus?.result?.validation_passed ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {jobStatus?.result?.validation_passed ? (
                        <>
                          <CheckCircle className="w-5 h-5" />
                          <span>Passed</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-5 h-5" />
                          <span>Failed</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-4">
                    {jobStatus?.result?.pdf_output && (
                      <a
                        href={getDownloadUrl(jobStatus.result.pdf_output)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-6 rounded-lg transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        Download PDF
                      </a>
                    )}
                    {jobStatus?.result?.json_output && (
                      <a
                        href={getDownloadUrl(jobStatus.result.json_output)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        Download JSON
                      </a>
                    )}
                    {jobStatus?.result?.markdown_output && (
                      <a
                        href={getDownloadUrl(jobStatus.result.markdown_output)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-6 rounded-lg transition-colors shadow-sm"
                      >
                        <Download className="w-4 h-4" />
                        Download Markdown
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Instructions */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4">How to Use</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
              <li>Upload one or more BRS documents (PDF or DOCX format)</li>
              <li>Upload Change Request documents that modify the BRS</li>
              <li>Click "Start Consolidation" to generate the final BRS</li>
              <li>Monitor the job status and download the results when complete</li>
            </ol>
            <div className="mt-4 p-4 bg-blue-50 rounded-md">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> The system uses Evidence Packs to prevent hallucinations.
                Every requirement in the final BRS is traceable to source documents.
              </p>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="bg-gray-800 text-white py-8 mt-16">
          <div className="container mx-auto px-4 text-center">
            <p className="text-gray-300">
              © 2024 GenAI BRS Consolidator. Powered by Ollama qwen2.5, ChromaDB, and Controlled RAG.
            </p>
          </div>
        </footer>
      </div>
    </>
  );
}
