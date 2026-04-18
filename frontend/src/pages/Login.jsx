import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LogIn, Key, Mail, User, Phone, Building, Component } from 'lucide-react';
import { apiClient } from '../lib/apiClient';
import logger from '../lib/logger';

const InputField = ({ label, icon: Icon, type = "text", ...props }) => (
  <div>
    <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">{label}</label>
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <Icon className="h-5 w-5 text-gray-500" />
      </div>
      <input
        type={type}
        className="block w-full pl-10 pr-3 py-2 border border-slate-300 dark:border-white/10 rounded-lg bg-white dark:bg-white/5 text-slate-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
        required
        {...props}
      />
    </div>
  </div>
);

const Login = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [role, setRole] = useState('personal'); // 'personal' or 'enterprise'

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Personal specific
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');

  // Enterprise specific
  const [managerFirstName, setManagerFirstName] = useState('');
  const [managerLastName, setManagerLastName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyType, setCompanyType] = useState('private'); // 'private' or 'public'

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleAuth = async (e) => {
    e.preventDefault();
    if (isRegister && password !== confirmPassword) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setLoading(true);
    setError('');

    const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
    const namespace = 'Auth';

    const payload = isRegister ? {
      email,
      password,
      role,
      ...(role === 'personal' ? { firstName, lastName, phone } : { managerFirstName, managerLastName, companyName, companyType })
    } : {
      email,
      password
    };

    logger.info(namespace, `Attempting ${isRegister ? 'registration' : 'login'}`, { email, role });

    try {
      const response = await apiClient.post(endpoint, payload);

      if (response.ok) {
        logger.info(namespace, 'Authentication successful', { status: response.status });

        if (isRegister) {
          // Auto-login after register
          const loginResponse = await apiClient.post('/api/auth/login', { email, password });

          if (loginResponse.ok) {
            logger.info(namespace, 'Auto-login after registration successful');
            localStorage.setItem('token', loginResponse.data.access_token);
            localStorage.setItem('role', loginResponse.data.role);
            navigate('/account');
          } else {
            logger.warn(namespace, 'Auto-login failed, showing login form', { status: loginResponse.status });
            setIsRegister(false);
            setError('Compte créé, mais erreur de connexion automatique.');
          }
        } else {
          localStorage.setItem('token', response.data.access_token);
          localStorage.setItem('role', response.data.role);
          logger.info(namespace, 'Login successful, redirecting to account');
          navigate('/account');
        }
      } else {
        const errorMessage = response.data?.detail || (isRegister ? "Erreur lors de l'inscription" : 'Erreur de connexion');
        logger.warn(namespace, 'Authentication failed', { status: response.status, detail: response.data?.detail });
        setError(errorMessage);
      }
    } catch (err) {
      logger.error(namespace, 'Network error during authentication', { error: err.message });
      setError('Impossible de joindre le serveur.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="glass-card p-8">
          <div className="text-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mx-auto mb-4">
              <LogIn className="w-6 h-6 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white ">{isRegister ? 'Créer un compte' : 'Connexion'}</h2>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">

            {/* Role selector for Register */}
            {isRegister && (
              <div className="flex p-1 space-x-1 glass rounded-xl mb-6">
                {['personal', 'enterprise'].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`w-full rounded-lg py-2 text-sm font-medium transition-all ${
                      role === r
                        ? 'bg-primary text-white shadow'
                        : 'text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    {r === 'personal' ? 'Personnel' : 'Entreprise'}
                  </button>
                ))}
              </div>
            )}

            <AnimatePresence mode="popLayout">
              {isRegister && role === 'personal' && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <InputField label="Prénom" icon={User} value={firstName} onChange={e => setFirstName(e.target.value)} placeholder="Jean" />
                    <InputField label="Nom" icon={User} value={lastName} onChange={e => setLastName(e.target.value)} placeholder="Dupont" />
                  </div>
                  <InputField label="Téléphone" icon={Phone} type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="06 12 34 56 78" />
                </motion.div>
              )}

              {isRegister && role === 'enterprise' && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-4">
                  <InputField label="Nom de l'entreprise" icon={Building} value={companyName} onChange={e => setCompanyName(e.target.value)} placeholder="Clinique Pasteur" />

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">Type d'entreprise</label>
                    <select
                      value={companyType}
                      onChange={e => setCompanyType(e.target.value)}
                      className="block w-full px-3 py-2 border border-slate-300 dark:border-white/10 rounded-lg bg-white dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
                    >
                      <option value="private">Privée</option>
                      <option value="public">Publique</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <InputField label="Prénom du responsable" icon={User} value={managerFirstName} onChange={e => setManagerFirstName(e.target.value)} placeholder="Marie" />
                    <InputField label="Nom du responsable" icon={User} value={managerLastName} onChange={e => setManagerLastName(e.target.value)} placeholder="Martin" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Email - Used in both Login & Register */}
            <InputField
              label={isRegister && role === 'enterprise' ? "Email de l'entreprise" : "Email"}
              icon={Mail}
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder={isRegister && role === 'enterprise' ? "contact@entreprise.com" : "email@exemple.com"}
            />

            {/* Password - Used in both Login & Register */}
            <InputField
              label="Mot de passe"
              icon={Key}
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
            />

            {/* Confirm Password - Only Register */}
            {isRegister && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
                <InputField
                  label="Vérification du mot de passe"
                  icon={Key}
                  type="password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </motion.div>
            )}

            {error && (
              <div className="text-red-500 dark:text-red-400 text-sm bg-red-100 dark:bg-red-400/10 p-3 rounded-lg border border-red-200 dark:border-red-400/20">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 transition-colors mt-6"
            >
              {loading ? (isRegister ? 'Inscription...' : 'Connexion...') : (isRegister ? "S'inscrire" : 'Se connecter')}
            </button>

            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => { setIsRegister(!isRegister); setError(''); }}
                className="text-sm text-primary hover:text-primary-hover transition-colors"
              >
                {isRegister ? 'Déjà un compte ? Se connecter' : "Pas de compte ? S'inscrire"}
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </div>
  );
};

export default Login;
