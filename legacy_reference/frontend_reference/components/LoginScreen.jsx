import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Key, AlertCircle, LogIn } from 'lucide-react';

export default function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // login() in AuthContext handles the fetch and sets token/user state
      const success = await login(username, password);
      if (!success) {
        setError('Invalid username or password. Check credentials and ensure backend is running on port 8001.');
      }
    } catch (err) {
      if (err.message?.includes('Failed to fetch')) {
        setError('Cannot reach backend server (port 8001). Is it running?');
      } else {
        setError(err.message || 'Login failed');
      }
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-16 h-16 bg-cyan-500/10 rounded-xl flex items-center justify-center border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.15)]">
            <Shield className="w-8 h-8 text-cyan-400" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
          OTC Sniper <span className="text-cyan-400">v2</span>
        </h2>
        <p className="mt-2 text-center text-sm text-slate-400">
          Sign in to access your trading dashboard
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 py-8 px-4 shadow-xl sm:rounded-lg sm:px-10 border border-slate-800 relative overflow-hidden">
          
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500/0 via-cyan-500 to-cyan-500/0"></div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                <p className="text-sm text-red-200">{error}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-300">
                Username
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="block w-full bg-slate-950 border border-slate-800 rounded-lg pl-3 pr-10 py-2 text-white focus:ring-cyan-500 focus:border-cyan-500 sm:text-sm"
                  placeholder="admin"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Key className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-3 py-2 text-white focus:ring-cyan-500 focus:border-cyan-500 sm:text-sm"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-black bg-cyan-400 hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin" />
              ) : (
                <div className="flex items-center gap-2">
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </div>
              )}
            </button>
          </form>
          
          <div className="mt-6 text-center text-xs text-slate-500">
            Default credentials: admin / admin
          </div>
        </div>
      </div>
    </div>
  );
}
