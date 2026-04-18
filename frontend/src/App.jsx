import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Strategy from './pages/Strategy';
import Chat from './pages/Chat';
import Account from './pages/Account';
import MDS from './pages/MDS';
import Login from './pages/Login';

function App() {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col overflow-x-hidden relative dark:bg-background bg-slate-50 transition-colors duration-300">
        <Navbar theme={theme} toggleTheme={toggleTheme} />
        
        <main className="flex-1 flex flex-col w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 z-10">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/strategy" element={<Strategy />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/account" element={<Account />} />
            <Route path="/mds" element={<MDS />} />
            <Route path="/login" element={<Login />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
