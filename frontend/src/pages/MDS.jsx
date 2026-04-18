import { motion } from 'framer-motion';
import { HardDrive, ServerCog, Database, Lock } from 'lucide-react';

const MDS = () => {
  return (
    <div className="max-w-4xl mx-auto py-12 flex flex-col items-center justify-center text-center">
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", bounce: 0.5 }}
        className="w-24 h-24 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center mb-8 relative"
      >
        <div className="absolute inset-0 rounded-full border border-primary/50 animate-ping opacity-20"></div>
        <Database className="w-10 h-10 text-primary" />
      </motion.div>
      
      <motion.h1 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-4xl md:text-5xl font-bold mb-4"
      >
        Medical Data Space (<span className="text-gradient">MDS</span>)
      </motion.h1>
      
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-sm font-medium mb-8"
      >
        <ServerCog className="w-4 h-4" />
        Under Development
      </motion.div>
      
      <motion.p 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="dark:text-gray-400 text-slate-600 max-w-2xl text-lg mb-12"
      >
        This section will host the public collaborative contribution interface. Once completed, it will allow institutions to share irreversibly anonymized data to power European research.
      </motion.p>
      
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="grid md:grid-cols-2 gap-6 w-full"
      >
        <div className="glass-card p-6 flex items-start gap-4 text-left opacity-60">
          <HardDrive className="w-8 h-8 text-gray-500 shrink-0" />
          <div>
            <h3 className="text-slate-900 dark:text-white  font-medium mb-1">Decentralized Storage</h3>
            <p className="text-sm dark:text-gray-400 text-slate-600">Ready for EHDS exchange architecture.</p>
          </div>
        </div>
        <div className="glass-card p-6 flex items-start gap-4 text-left opacity-60">
          <Lock className="w-8 h-8 text-gray-500 shrink-0" />
          <div>
            <h3 className="text-slate-900 dark:text-white  font-medium mb-1">Advanced Anonymization</h3>
            <p className="text-sm dark:text-gray-400 text-slate-600">"Privacy by Design" process before sharing.</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default MDS;
