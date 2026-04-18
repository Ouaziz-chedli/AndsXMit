import { motion } from 'framer-motion';
import { Shield, Lock, Share2, Scale } from 'lucide-react';

const Strategy = () => {
  return (
    <div className="max-w-4xl mx-auto py-8 flex flex-col gap-12">
      <div className="text-center">
        <motion.h1 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-5xl font-bold mb-4"
        >
          Strategy & <span className="text-gradient">Transparency</span>
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="text-lg dark:text-gray-400 text-slate-600"
        >
          Open Source Health Project for the European Evaluation Committee
        </motion.p>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-card p-8">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white  mb-4 flex items-center gap-3">
          <Scale className="text-primary" /> Vision and Value Proposition
        </h2>
        <p className="text-gray-300 leading-relaxed mb-6">
          The goal is to create a <strong>European Health Standard</strong> based on transparency and accessibility. By removing the financial barriers of proprietary licenses, the project enables:
        </p>
        <ul className="space-y-4 text-gray-300">
          <li className="flex gap-3"><div className="w-1.5 h-1.5 rounded-full bg-accent mt-2" /> <span><strong>Democratization:</strong> Universal access to state-of-art tools for all facilities.</span></li>
          <li className="flex gap-3"><div className="w-1.5 h-1.5 rounded-full bg-accent mt-2" /> <span><strong>Sovereignty:</strong> Total technological independence from non-European solutions.</span></li>
          <li className="flex gap-3"><div className="w-1.5 h-1.5 rounded-full bg-accent mt-2" /> <span><strong>Trust:</strong> Radical code transparency to guarantee ethics and security.</span></li>
        </ul>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass-card p-8">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white  mb-4 flex items-center gap-3">
            <Lock className="text-primary" /> Technical Architecture
          </h2>
          <div className="space-y-4 text-gray-300">
            <p><strong>Core Engine (Open Source):</strong> Transparency and auditability. Interoperability with European standards (HL7 FHIR, MDS).</p>
            <p><strong>Local Usage:</strong> "On-Premise" deployment. Closed loop without data leakage.</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass-card p-8">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white  mb-4 flex items-center gap-3">
            <Shield className="text-primary" /> European Standards
          </h2>
          <div className="space-y-4 text-gray-300">
            <p><strong>GDPR:</strong> Local data sovereignty, strict anonymization.</p>
            <p><strong>EU AI Act:</strong> Algorithm transparency (Open Source).</p>
            <p><strong>EHDS:</strong> Ready for the European Health Data Space.</p>
          </div>
        </motion.div>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="glass-card p-8 border-primary/20 bg-primary/5">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white  mb-4 flex items-center gap-3">
          <Share2 className="text-primary" /> Economic Model & Viability
        </h2>
        <p className="text-gray-300 leading-relaxed mb-4">
          Viability relies on strategic partnerships, TCO (Total Cost of Ownership) reduction for hospitals, and European community maintenance.
        </p>
        <blockquote className="border-l-4 border-primary pl-4 italic dark:text-gray-400 text-slate-600 mt-6">
          "Health is a common good. Code transparency is not a security weakness, it is a guarantee of clinical trust."
        </blockquote>
      </motion.div>
    </div>
  );
};

export default Strategy;
