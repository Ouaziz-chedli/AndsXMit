import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Activity, MessageSquare, Shield, User, LayoutDashboard, LogIn, LogOut, Sun, Moon } from 'lucide-react';
import { motion } from 'framer-motion';

const Navbar = ({ theme, toggleTheme }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthenticated = !!localStorage.getItem('token');

  const links = [
    { name: 'Home', path: '/', icon: Activity },
    { name: 'Strategy', path: '/strategy', icon: Shield },
    { name: 'MDS', path: '/mds', icon: LayoutDashboard },
    { name: 'Chat LLM', path: '/chat', icon: MessageSquare },
    ...(isAuthenticated ? [{ name: 'Account', path: '/account', icon: User }] : []),
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  return (
    <nav className="glass sticky top-0 z-50 border-b border-white/10 w-full transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold dark:text-white text-slate-800 tracking-tight">Pre<span className="text-primary">Birth</span></span>
          </Link>
          
          <div className="hidden md:flex space-x-1">
            {links.map((link) => {
              const isActive = location.pathname === link.path;
              const Icon = link.icon;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`relative flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive ? 'dark:text-white text-slate-900' : 'text-slate-500 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {link.name}
                  {isActive && (
                    <motion.div
                      layoutId="navbar-indicator"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </Link>
              );
            })}
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={toggleTheme}
              className="p-2 rounded-full bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 transition-colors text-slate-700 dark:text-white"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            
            {isAuthenticated ? (
              <button onClick={handleLogout} className="flex items-center gap-2 px-4 py-2 rounded-md bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 transition-colors text-sm font-medium border border-red-500/20">
                <LogOut className="w-4 h-4" />
                Déconnexion
              </button>
            ) : (
              <Link to="/login" className="flex items-center gap-2 px-4 py-2 rounded-md bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 transition-colors text-sm font-medium text-slate-800 dark:text-white border border-slate-300 dark:border-white/10">
                <LogIn className="w-4 h-4" />
                Connexion
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
