/**
 * Debug Panel Component
 * Floating panel to display API logs in the browser
 */

import { useState, useEffect, useRef } from 'react';
import { Bug, X, Trash2, Download, ChevronDown, ChevronUp } from 'lucide-react';

const MAX_LOGS = 100;

const LogEntry = ({ log }) => {
  const [expanded, setExpanded] = useState(false);
  const isError = log.type === 'error' || log.status >= 400;
  const isWarning = log.type === 'warn' || log.status >= 300;

  const getIcon = () => {
    if (isError) return '❌';
    if (isWarning) return '⚠️';
    if (log.type === 'request') return '📤';
    if (log.type === 'response') return '📥';
    return '📋';
  };

  const getColor = () => {
    if (isError) return 'text-red-400';
    if (isWarning) return 'text-yellow-400';
    return 'text-gray-300';
  };

  return (
    <div className={`border-b border-white/10 ${getColor()}`}>
      <div
        className="flex items-center gap-2 p-2 cursor-pointer hover:bg-white/5"
        onClick={() => setExpanded(!expanded)}
      >
        <span>{getIcon()}</span>
        <span className="text-xs opacity-70">{log.timestamp}</span>
        <span className="text-xs font-mono">{log.method || log.type}</span>
        <span className="text-xs font-mono flex-1 truncate">{log.url || log.message}</span>
        {log.duration && <span className="text-xs opacity-50">({log.duration}ms)</span>}
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </div>
      {expanded && (
        <div className="p-2 bg-black/30 text-xs font-mono overflow-auto max-h-40">
          {log.details && (
            <pre className="whitespace-pre-wrap">{JSON.stringify(log.details, null, 2)}</pre>
          )}
          {log.error && (
            <div className="text-red-400">{log.error}</div>
          )}
        </div>
      )}
    </div>
  );
};

const DebugPanel = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState('all');
  const logsRef = useRef(logs);
  const bottomRef = useRef(null);

  // Keep logs ref in sync
  useEffect(() => {
    logsRef.current = logs;
  }, [logs]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Listen for custom log events
  useEffect(() => {
    const handleLog = (event) => {
      const newLog = {
        ...event.detail,
        id: Date.now() + Math.random(),
        timestamp: new Date().toLocaleTimeString(),
      };

      setLogs((prev) => {
        const updated = [newLog, ...prev];
        return updated.slice(0, MAX_LOGS);
      });
    };

    window.addEventListener('api-log', handleLog);
    return () => window.removeEventListener('api-log', handleLog);
  }, []);

  const clearLogs = () => setLogs([]);

  const exportLogs = () => {
    const data = JSON.stringify(logs, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `api-logs-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = logs.filter((log) => {
    if (filter === 'all') return true;
    if (filter === 'errors') return log.type === 'error' || log.status >= 400;
    if (filter === 'api') return log.type === 'request' || log.type === 'response';
    return true;
  });

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-50 p-3 bg-gray-800 text-white rounded-full shadow-lg hover:bg-gray-700 transition-colors"
        title="Open Debug Panel"
      >
        <Bug size={20} />
        {logs.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {logs.length > 99 ? '99+' : logs.length}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-h-[70vh] bg-gray-900 text-white rounded-lg shadow-2xl flex flex-col overflow-hidden border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Bug size={16} />
          <span className="font-medium">API Debug Panel</span>
          <span className="text-xs text-gray-400">({logs.length} logs)</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportLogs}
            className="p-1 hover:bg-gray-700 rounded"
            title="Export Logs"
          >
            <Download size={14} />
          </button>
          <button
            onClick={clearLogs}
            className="p-1 hover:bg-gray-700 rounded"
            title="Clear Logs"
          >
            <Trash2 size={14} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-gray-700 rounded"
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 p-2 bg-gray-800/50 border-b border-gray-700">
        {['all', 'errors', 'api'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-xs rounded ${
              filter === f ? 'bg-primary text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Log List */}
      <div className="flex-1 overflow-auto">
        {filteredLogs.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            No logs yet. Make API requests to see them here.
          </div>
        ) : (
          filteredLogs.map((log) => <LogEntry key={log.id} log={log} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default DebugPanel;
