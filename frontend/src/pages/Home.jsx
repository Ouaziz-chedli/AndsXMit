import { motion } from 'framer-motion';
import { ArrowRight, Activity, ShieldCheck, Database, BrainCircuit } from 'lucide-react';
import { Link } from 'react-router-dom';

const Home = () => {
  const features = [
    { icon: BrainCircuit, title: 'AI-Powered Detection', desc: 'MedGemma integration for non-invasive prenatal disease detection using ultrasound images.' },
    { icon: ShieldCheck, title: 'Privacy by Design', desc: 'Local-first architecture ensuring patient data never leaves the hospital unless explicitly shared.' },
    { icon: Database, title: 'Vector DB Aggregation', desc: 'Per-disease vector databases combining positive and negative examples across trimesters.' },
    { icon: Activity, title: 'Community Driven', desc: 'European Standard Health approach, completely open-source and transparent for scientific audit.' },
  ];

  return (
    <div className="flex flex-col gap-16 py-8">
      {/* Hero Section */}
      <section className="flex flex-col items-center text-center max-w-4xl mx-auto gap-6 pt-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          PreBirth Project
        </motion.div>
        
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-5xl md:text-7xl font-bold tracking-tight"
        >
          AI-Powered <span className="text-gradient">Prenatal</span><br />Disease Detection
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg md:text-xl dark:text-gray-400 text-slate-600 max-w-2xl"
        >
          A non-invasive diagnostic platform utilizing advanced LLMs and Vector Databases to reduce unnecessary invasive procedures while ensuring absolute data sovereignty.
        </motion.p>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex gap-4 mt-4"
        >
          <Link to="/chat" className="px-6 py-3 rounded-lg bg-primary hover:bg-primary-hover text-white  font-medium flex items-center gap-2 transition-all shadow-[0_0_20px_rgba(59,130,246,0.3)]">
            Try the LLM Chat
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/strategy" className="px-6 py-3 rounded-lg glass hover:bg-white/10 text-slate-900 dark:text-white  font-medium transition-all">
            Read the Strategy
          </Link>
        </motion.div>
      </section>
      
      {/* Features Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        {features.map((feature, i) => {
          const Icon = feature.icon;
          return (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 + i * 0.1 }}
              className="glass-card p-6 flex flex-col gap-4"
            >
              <div className="w-12 h-12 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center">
                <Icon className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-white ">{feature.title}</h3>
              <p className="dark:text-gray-400 text-slate-600">{feature.desc}</p>
            </motion.div>
          );
        })}
      </section>
    </div>
  );
};

export default Home;
