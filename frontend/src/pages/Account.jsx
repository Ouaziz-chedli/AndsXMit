import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { UploadCloud, CheckCircle2, AlertCircle, Building2, UserCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const InputField = ({ label, type, value, onChange, placeholder }) => (
  <div>
    <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
      {label}
    </label>
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full bg-slate-50 dark:bg-white/5 border border-slate-300 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
    />
  </div>
);

const Account = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle');
  const [user, setUser] = useState(null);
  const [vectorDb, setVectorDb] = useState({ status: 'Loading...', documents: 0 });
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [updateStatus, setUpdateStatus] = useState('');

  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role') || 'personal';

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    
    const fetchUser = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';
        const res = await fetch(`${baseUrl}/user/me`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setUser(data.user);
          setFormData(data.user);
          setVectorDb(data.vectorDb || { status: 'Unknown', documents: 0 });
        } else {
          localStorage.removeItem('token');
          localStorage.removeItem('role');
          navigate('/login');
        }
      } catch (error) {
        console.error('Failed to fetch user', error);
      }
    };
    
    fetchUser();
  }, [token, navigate]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setStatus('uploading');
    const uploadData = new FormData();
    uploadData.append('file', file);
    uploadData.append('description', 'Context file for RAG');

    try {
      const baseUrl = import.meta.env.VITE_AI_API_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/api/rag/upload-context`, {
        method: 'POST',
        body: uploadData,
      });
      if (res.ok) {
        setStatus('success');
        setTimeout(() => setStatus('idle'), 3000);
      } else {
        setStatus('error');
      }
    } catch (error) {
      setStatus('error');
    }
  };

  const handleUpdateAccount = async (e) => {
    e.preventDefault();
    setUpdateStatus('updating');
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';
      const res = await fetch(`${baseUrl}/user/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
        setUpdateStatus('success');
        setIsEditing(false);
        setTimeout(() => setUpdateStatus(''), 3000);
      } else {
        setUpdateStatus('error');
      }
    } catch (error) {
      setUpdateStatus('error');
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  if (!user) return <div className="text-center py-20 dark:text-white text-slate-900">Loading profile...</div>;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-8">Account Management</h1>
      
      <div className="grid md:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="col-span-1 glass-card p-6 h-fit">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              {role === 'enterprise' ? <Building2 className="text-slate-900 dark:text-white" /> : <UserCircle className="text-slate-900 dark:text-white" />}
            </div>  
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white capitalize">{role} Account</h3>
              <p className="text-sm dark:text-gray-400 text-slate-600">{user.email}</p>
            </div>
          </div>
          <div className="space-y-3 text-sm text-slate-800 dark:text-gray-300">
            <p className="flex justify-between"><span>Vector DB Status:</span> <span className={vectorDb.status === 'Active' ? "text-green-500" : "text-yellow-500"}>{vectorDb.status}</span></p>
            <p className="flex justify-between"><span>RAG Documents:</span> <span>{vectorDb.documents} files</span></p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="col-span-2 flex flex-col gap-6">
          <div className="glass-card p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Profile Information</h2>
              {!isEditing && (
                <button onClick={() => setIsEditing(true)} className="text-sm text-primary hover:text-accent font-medium">Edit Profile</button>
              )}
            </div>

            {isEditing ? (
              <form onSubmit={handleUpdateAccount} className="space-y-4">
                {role === 'personal' ? (
                  <div className="grid grid-cols-2 gap-4">
                    <InputField label="First Name" type="text" value={formData.firstName || ''} onChange={(e) => setFormData({...formData, firstName: e.target.value})} placeholder="John" />
                    <InputField label="Last Name" type="text" value={formData.lastName || ''} onChange={(e) => setFormData({...formData, lastName: e.target.value})} placeholder="Doe" />
                    <div className="col-span-2">
                      <InputField label="Phone" type="text" value={formData.phone || ''} onChange={(e) => setFormData({...formData, phone: e.target.value})} placeholder="+1 234 567 890" />
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <InputField label="Company Name" type="text" value={formData.companyName || ''} onChange={(e) => setFormData({...formData, companyName: e.target.value})} placeholder="Acme Corp" />
                    <InputField label="Company Type" type="text" value={formData.companyType || ''} onChange={(e) => setFormData({...formData, companyType: e.target.value})} placeholder="Public / Private" />
                    <InputField label="Manager First Name" type="text" value={formData.managerFirstName || ''} onChange={(e) => setFormData({...formData, managerFirstName: e.target.value})} placeholder="Jane" />
                    <InputField label="Manager Last Name" type="text" value={formData.managerLastName || ''} onChange={(e) => setFormData({...formData, managerLastName: e.target.value})} placeholder="Smith" />
                  </div>
                )}
                
                <div className="flex justify-end gap-3 mt-4">
                  <button type="button" onClick={() => setIsEditing(false)} className="px-4 py-2 border border-slate-300 dark:border-gray-600 rounded-lg text-slate-700 dark:text-gray-300 hover:bg-slate-100 dark:hover:bg-white/10">Cancel</button>
                  <button type="submit" disabled={updateStatus === 'updating'} className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg">
                    {updateStatus === 'updating' ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
                {updateStatus === 'success' && <p className="text-green-500 text-sm mt-2">Profile updated successfully!</p>}
                {updateStatus === 'error' && <p className="text-red-500 text-sm mt-2">Failed to update profile.</p>}
              </form>
            ) : (
              <div className="grid grid-cols-2 gap-y-4 text-sm">
                {role === 'personal' ? (
                  <>
                    <div><p className="text-slate-500 dark:text-gray-400">First Name</p><p className="text-slate-900 dark:text-white font-medium">{user.firstName || 'Not set'}</p></div>
                    <div><p className="text-slate-500 dark:text-gray-400">Last Name</p><p className="text-slate-900 dark:text-white font-medium">{user.lastName || 'Not set'}</p></div>
                    <div><p className="text-slate-500 dark:text-gray-400">Phone</p><p className="text-slate-900 dark:text-white font-medium">{user.phone || 'Not set'}</p></div>
                  </>
                ) : (
                  <>
                    <div><p className="text-slate-500 dark:text-gray-400">Company Name</p><p className="text-slate-900 dark:text-white font-medium">{user.companyName || 'Not set'}</p></div>
                    <div><p className="text-slate-500 dark:text-gray-400">Company Type</p><p className="text-slate-900 dark:text-white font-medium">{user.companyType || 'Not set'}</p></div>
                    <div><p className="text-slate-500 dark:text-gray-400">Manager</p><p className="text-slate-900 dark:text-white font-medium">{user.managerFirstName} {user.managerLastName}</p></div>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="glass-card p-8">
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">Add to Context (RAG Vectorization)</h2>
            <p className="dark:text-gray-400 text-slate-600 mb-6">Upload protocols, anonymized medical histories, or guidelines to enrich the local AI knowledge base.</p>

            <form onSubmit={handleUpload} className="flex flex-col gap-4">
              <div className="relative border-2 border-dashed border-slate-300 dark:border-white/20 rounded-xl p-10 flex flex-col items-center justify-center gap-4 hover:bg-slate-100 dark:bg-white/5 hover:border-primary transition-colors cursor-pointer group">
                <input 
                  type="file" 
                  onChange={(e) => setFile(e.target.files[0])}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
                />
                <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                  <UploadCloud className="w-8 h-8 dark:text-gray-400 text-slate-600 group-hover:text-primary transition-colors" />
                </div>
                <div className="text-center">
                  <p className="text-slate-900 dark:text-white font-medium mb-1">
                    {file ? file.name : "Click or drag a file here"}
                  </p>
                  <p className="text-sm text-gray-500">Supports .pdf, .txt, .md</p>
                </div>
              </div>

              <button 
                type="submit" 
                disabled={!file || status === 'uploading'}
                className="bg-primary hover:bg-primary-hover text-white py-3 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
              >
                {status === 'uploading' ? (
                  <>Vectorization in progress...</>
                ) : (
                  <>Add to knowledge base</>
                )}
              </button>

              {status === 'success' && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="p-4 bg-green-500/10 border border-green-500/20 text-green-400 rounded-xl flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" /> File vectorized and added to RAG context successfully.
                </motion.div>
              )}
              
              {status === 'error' && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" /> Error during vectorization. Is the backend running?
                </motion.div>
              )}
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Account;
