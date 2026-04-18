import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { UploadCloud, Loader2, AlertCircle, CheckCircle2, Image as ImageIcon, X } from 'lucide-react';
import { buildApiUrl } from '../lib/api';

const Diagnosis = () => {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [polling, setPolling] = useState(false);
  const [comprehensiveStatus, setComprehensiveStatus] = useState(null);
  const fileInputRef = useRef(null);

  // Form state
  const [trimester, setTrimester] = useState('1st');
  const [motherAge, setMotherAge] = useState('');
  const [gestationalAge, setGestationalAge] = useState('');
  const [bHcg, setBHcg] = useState('');
  const [pappA, setPappA] = useState('');
  const [previousAffected, setPreviousAffected] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      setFiles((prev) => [...prev, ...droppedFiles]);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length > 0) {
      setFiles((prev) => [...prev, ...selectedFiles]);
    }
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      setError('Please upload at least one ultrasound image.');
      return;
    }
    if (!motherAge || !gestationalAge) {
      setError('Please fill in mother age and gestational age.');
      return;
    }

    setError('');
    setSubmitting(true);
    setResults(null);
    setComprehensiveStatus(null);

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append('images', file));
      formData.append('trimester', trimester);
      formData.append('mother_age', parseInt(motherAge, 10));
      formData.append('gestational_age_weeks', parseFloat(gestationalAge));
      if (bHcg) formData.append('b_hcg', parseFloat(bHcg));
      if (pappA) formData.append('papp_a', parseFloat(pappA));
      formData.append('previous_affected_pregnancy', previousAffected);

      const response = await fetch(buildApiUrl('/api/v1/diagnosis'), {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Diagnosis request failed');
      }

      setResults(data);
      setComprehensiveStatus({
        taskId: data.comprehensive_callback_url?.split('/').pop(),
        status: 'pending',
      });

      // Start polling for comprehensive results
      if (data.comprehensive_pending) {
        pollComprehensiveResults(data.comprehensive_callback_url);
      }
    } catch (err) {
      setError(err.message || 'Failed to submit diagnosis request');
    } finally {
      setSubmitting(false);
    }
  };

  const pollComprehensiveResults = async (callbackUrl) => {
    setPolling(true);
    const taskId = callbackUrl?.split('/').pop();

    const poll = async () => {
      try {
        const response = await fetch(buildApiUrl(`/api/v1/diagnosis/${taskId}/comprehensive`));
        const data = await response.json();

        setComprehensiveStatus((prev) => ({
          ...prev,
          status: data.status,
        }));

        if (data.status === 'completed') {
          setResults((prev) => ({
            ...prev,
            comprehensive: data.results,
          }));
          setPolling(false);
          return;
        }

        if (data.status === 'pending') {
          // Continue polling every 3 seconds
          setTimeout(poll, 3000);
        }
      } catch (err) {
        console.error('Polling error:', err);
        setPolling(false);
      }
    };

    poll();
  };

  const getScoreColor = (score) => {
    if (score >= 0.7) return 'text-red-500';
    if (score >= 0.4) return 'text-yellow-500';
    return 'text-green-500';
  };

  return (
    <div className="max-w-4xl mx-auto py-8 flex flex-col gap-8">
      <div className="text-center">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-5xl font-bold mb-4"
        >
          Prenatal <span className="text-gradient">Diagnosis</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-lg dark:text-gray-400 text-slate-600"
        >
          Upload ultrasound images for AI-powered disease risk assessment
        </motion.p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-8"
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Image Upload */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-2">
              Ultrasound Images
            </label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center gap-4 cursor-pointer transition-colors ${
                dragActive
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-300 dark:border-white/20 hover:border-primary hover:bg-slate-50 dark:hover:bg-white/5'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.dcm"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <UploadCloud className="w-8 h-8 dark:text-gray-400 text-slate-600 group-hover:text-primary transition-colors" />
              </div>
              <div className="text-center">
                <p className="text-slate-900 dark:text-white font-medium mb-1">
                  Click or drag ultrasound images here
                </p>
                <p className="text-sm text-gray-500">Supports .jpg, .png, .dcm</p>
              </div>
            </div>

            {/* File Preview */}
            {files.length > 0 && (
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="relative group glass-card p-2 rounded-lg"
                  >
                    <div className="aspect-square flex items-center justify-center bg-slate-100 dark:bg-white/5 rounded-md overflow-hidden">
                      <ImageIcon className="w-8 h-8 text-slate-400" />
                    </div>
                    <p className="text-xs text-slate-600 dark:text-gray-400 truncate mt-1">
                      {file.name}
                    </p>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Patient Context */}
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
                Trimester
              </label>
              <select
                value={trimester}
                onChange={(e) => setTrimester(e.target.value)}
                className="w-full bg-slate-50 dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              >
                <option value="1st">1st Trimester</option>
                <option value="2nd">2nd Trimester</option>
                <option value="3rd">3rd Trimester</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
                Mother's Age at Due Date
              </label>
              <input
                type="number"
                value={motherAge}
                onChange={(e) => setMotherAge(e.target.value)}
                placeholder="e.g., 30"
                min="18"
                max="60"
                className="w-full bg-slate-50 dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
                Gestational Age (weeks)
              </label>
              <input
                type="number"
                value={gestationalAge}
                onChange={(e) => setGestationalAge(e.target.value)}
                placeholder="e.g., 12.5"
                step="0.1"
                min="1"
                max="42"
                className="w-full bg-slate-50 dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
                Beta-hCG (IU/L) - Optional
              </label>
              <input
                type="number"
                value={bHcg}
                onChange={(e) => setBHcg(e.target.value)}
                placeholder="e.g., 55000"
                step="0.01"
                className="w-full bg-slate-50 dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
                PAPP-A (IU/L) - Optional
              </label>
              <input
                type="number"
                value={pappA}
                onChange={(e) => setPappA(e.target.value)}
                placeholder="e.g., 1200"
                step="0.01"
                className="w-full bg-slate-50 dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              />
            </div>

            <div className="flex items-center">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={previousAffected}
                  onChange={(e) => setPreviousAffected(e.target.checked)}
                  className="w-5 h-5 rounded border-slate-300 dark:border-white/10 text-primary focus:ring-primary"
                />
                <span className="text-sm text-slate-700 dark:text-gray-300">
                  Previous affected pregnancy (chromosomal anomaly)
                </span>
              </label>
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2 text-red-400">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || files.length === 0}
            className="w-full bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white py-4 rounded-xl font-medium transition-colors flex justify-center items-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Submit for Diagnosis'
            )}
          </button>
        </form>
      </motion.div>

      {/* Results Section */}
      {results && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-8"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
              Fast Track Results
            </h2>
            <span className="text-sm text-slate-500 dark:text-gray-400">
              {results.fast_track_ms}ms
            </span>
          </div>

          <div className="space-y-4 mb-6">
            {results.fast_track?.map((result, index) => (
              <div
                key={index}
                className="glass-card p-4 border-l-4 border-l-primary"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-white">
                      {result.disease_name}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-gray-400">
                      {result.disease_id}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`text-2xl font-bold ${getScoreColor(result.final_score)}`}>
                      {(result.final_score * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-slate-500 dark:text-gray-400">
                      CI: [{result.confidence_interval?.[0]?.toFixed(2)}, {result.confidence_interval?.[1]?.toFixed(2)}]
                    </p>
                  </div>
                </div>

                {result.applied_priors?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {result.applied_priors.map((prior, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full"
                      >
                        {prior}
                      </span>
                    ))}
                  </div>
                )}

                <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500 dark:text-gray-400 mb-1">Matching Positive Cases</p>
                    {result.matching_positive_cases?.slice(0, 2).map((c, i) => (
                      <p key={i} className="text-slate-700 dark:text-gray-300">
                        {c.case_id}: {(c.similarity * 100).toFixed(0)}% match
                      </p>
                    ))}
                  </div>
                  <div>
                    <p className="text-slate-500 dark:text-gray-400 mb-1">Matching Negative Cases</p>
                    {result.matching_negative_cases?.slice(0, 2).map((c, i) => (
                      <p key={i} className="text-slate-700 dark:text-gray-300">
                        {c.case_id}: {(c.similarity * 100).toFixed(0)}% match
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Comprehensive Scan Status */}
          <div className="border-t border-slate-200 dark:border-white/10 pt-6">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 dark:text-white">
                Comprehensive Scan
              </h3>
              {comprehensiveStatus?.status === 'pending' && polling && (
                <div className="flex items-center gap-2 text-blue-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Processing...</span>
                </div>
              )}
              {comprehensiveStatus?.status === 'completed' && (
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span className="text-sm">Completed</span>
                </div>
              )}
            </div>
            {results.comprehensive_pending && !comprehensiveStatus?.status && (
              <p className="text-sm text-slate-500 dark:text-gray-400 mt-2">
                Comprehensive scan queued. Results will appear automatically.
              </p>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default Diagnosis;