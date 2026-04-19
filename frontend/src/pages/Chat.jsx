import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { apiClient } from '../lib/apiClient';
import logger from '../lib/logger';

const NAMESPACE = 'Chat';

const Chat = () => {
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Hello. I am MedGemma, specialized in prenatal ultrasound analysis. How can I help you?' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const endOfMessagesRef = useRef(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check backend health on mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        // Use apiClient for logging
        const result = await apiClient.get('/api/health');
        setBackendOnline(result.ok);
        logger.debug(NAMESPACE, 'Health check', { status: result.status, ok: result.ok });
      } catch (error) {
        setBackendOnline(false);
        logger.error(NAMESPACE, 'Health check failed', { error: error.message });
      } finally {
        setCheckingStatus(false);
      }
    };
    checkBackendHealth();
    // Check health every 30 seconds
    const interval = setInterval(checkBackendHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    logger.info(NAMESPACE, 'Sending chat request', { message: userMsg });

    try {
      const result = await apiClient.post('/api/llm/chat', { message: userMsg });

      logger.debug(NAMESPACE, 'Chat response', {
        status: result.status,
        ok: result.ok,
        hasData: !!result.data,
        responsePreview: result.data?.response?.substring(0, 100)
      });

      if (!result.ok) {
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${result.data?.detail || 'Unknown error'}` }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: result.data.response }]);
      }
    } catch (error) {
      logger.error(NAMESPACE, 'Chat request failed', { error: error.message });
      setMessages(prev => [...prev, { role: 'assistant', content: 'Backend connection error. Is the Express API server running?' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex-1 flex flex-col glass-card overflow-hidden shadow-2xl h-full">
        <div className="p-4 border-b border-slate-200 dark:border-white/10 dark:bg-white/5 bg-slate-100 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
            <Bot className="text-primary w-6 h-6" />
          </div>
          <div>
            <h2 className="font-semibold  text-slate-900 dark:text-white ">MedGemma LLM</h2>
            <p className={`text-xs flex items-center gap-1 ${backendOnline ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}>
              {checkingStatus ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Checking...</span>
                </>
              ) : backendOnline ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  <span>Online</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  <span>Offline</span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 flex flex-col gap-6">
          {messages.map((msg, i) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              key={i} 
              className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-primary/20' : 'bg-slate-200 dark:bg-white/10'}`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-primary" /> : <Bot className="w-4 h-4 text-primary" />}
              </div>
              <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-primary text-white  rounded-tr-none shadow-md' : 'glass rounded-tl-none text-slate-800 dark:text-gray-200 shadow-sm'}`}>
                {msg.content}
              </div>
            </motion.div>
          ))}
          {loading && (
            <div className="flex gap-4 max-w-[85%]">
               <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-white/10 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="p-4 rounded-2xl glass rounded-tl-none text-slate-800 dark:text-gray-200 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" /> Analyzing...
              </div>
            </div>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        <div className="p-4 border-t border-slate-200 dark:border-white/10 dark:bg-white/5 bg-slate-100">
          <div className="flex gap-2">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question about a pathology or an ultrasound..."
              className="flex-1 bg-white dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3  text-slate-900 dark:text-white  focus:outline-none focus:border-primary transition-colors placeholder:text-slate-400 dark:placeholder:text-gray-500 shadow-sm"
            />
            <button 
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white  w-14 flex items-center justify-center rounded-xl transition-colors shadow-md"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
