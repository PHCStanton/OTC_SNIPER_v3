import React, { useState, useEffect, useCallback } from 'react';
import { User, ShieldAlert, Key, Check, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_URL } from '../config';

export default function AccountManagementView() {
  const { user, token } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [demoSsid, setDemoSsid] = useState('');
  const [realSsid, setRealSsid] = useState('');
  const [demoConfigured, setDemoConfigured] = useState(false);
  const [realConfigured, setRealConfigured] = useState(false);
  const [demoSaving, setDemoSaving] = useState(false);
  const [realSaving, setRealSaving] = useState(false);

  // Toast state: { type: 'success'|'error', message: string } | null
  const [toast, setToast] = useState(null);

  const showToast = useCallback((type, message) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const fetchCreds = useCallback(async (accountType) => {
    try {
      const res = await fetch(`${API_URL}/auth/credentials/pocket_option/${accountType}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return;
      const data = await res.json();
      if (accountType === 'demo') setDemoConfigured(!!data.configured);
      if (accountType === 'real') setRealConfigured(!!data.configured);
    } catch (e) {
      console.error('fetchCreds error:', e);
    }
  }, [token]);

  useEffect(() => {
    if (isAdmin && token) {
      fetchCreds('demo');
      fetchCreds('real');
    }
  }, [isAdmin, token, fetchCreds]);

  const handleSave = async (accountType, ssidValue) => {
    if (!ssidValue.trim()) return;
    const setSaving = accountType === 'demo' ? setDemoSaving : setRealSaving;

    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/auth/credentials`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          broker_name: 'pocket_option',
          account_type: accountType,
          ssid: ssidValue.trim()
        })
      });

      if (res.ok) {
        // Clear the input field
        if (accountType === 'demo') setDemoSsid('');
        if (accountType === 'real') setRealSsid('');
        // Re-fetch from server to confirm the badge reflects real state
        await fetchCreds(accountType);
        showToast('success', `${accountType === 'demo' ? 'Demo' : 'Real'} SSID saved successfully.`);
      } else {
        let detail = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          detail = errData.detail || detail;
        } catch (_) { /* non-JSON body */ }
        showToast('error', `Save failed: ${detail}`);
      }
    } catch (e) {
      console.error('handleSave error:', e);
      showToast('error', `Save failed: ${e.message || 'Network error'}`);
    } finally {
      setSaving(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center max-w-sm">
          <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20">
            <ShieldAlert className="w-8 h-8 text-red-400" />
          </div>
          <h2 className="text-xl font-semibold text-white">Access Denied</h2>
          <p className="text-slate-400 text-sm">
            You need administrator privileges to access the account management area.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto relative">
      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border text-sm font-medium transition-all
            ${toast.type === 'success'
              ? 'bg-emerald-900/90 border-emerald-500/40 text-emerald-300'
              : 'bg-red-900/90 border-red-500/40 text-red-300'
            }`}
        >
          {toast.type === 'success'
            ? <CheckCircle2 className="w-4 h-4 shrink-0" />
            : <AlertCircle className="w-4 h-4 shrink-0" />
          }
          {toast.message}
        </div>
      )}

      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-white">Account Management</h2>
          <p className="text-slate-400 mt-1">Manage users, roles, and broker credentials.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Users List */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white flex items-center gap-2">
                <User className="w-5 h-5 text-cyan-400" />
                System Users
              </h3>
              <button className="text-xs font-medium bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 px-3 py-1.5 rounded-md transition-colors border border-cyan-500/20">
                + Add User
              </button>
            </div>
            
            <div className="space-y-3">
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400 font-bold">
                    A
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">admin</p>
                    <p className="text-xs text-slate-500">Administrator</p>
                  </div>
                </div>
                <div className="text-xs px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Active
                </div>
              </div>
            </div>
          </div>

          {/* Broker Credentials */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white flex items-center gap-2">
                <Key className="w-5 h-5 text-amber-400" />
                Broker Credentials
              </h3>
            </div>
            
            <p className="text-sm text-slate-400 mb-4">
              Securely store credentials for broker auto-connection. Credentials are encrypted at rest using Fernet symmetric encryption.
            </p>

            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-white">Pocket Option (Demo)</h4>
                  {demoConfigured ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                      <Check className="w-3 h-3" /> Configured
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">Not Configured</span>
                  )}
                </div>
                <div className="flex gap-2 mt-3">
                  <input 
                    type="password" 
                    placeholder="Enter new SSID..." 
                    value={demoSsid}
                    onChange={(e) => setDemoSsid(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded text-sm px-3 py-1.5 text-white focus:outline-none focus:border-cyan-500"
                  />
                  <button 
                    onClick={() => handleSave('demo', demoSsid)}
                    disabled={!demoSsid || demoSaving}
                    className="px-3 py-1.5 text-sm bg-cyan-500 hover:bg-cyan-600 disabled:bg-slate-800 disabled:text-slate-500 text-black font-medium rounded transition-colors"
                  >
                    {demoSaving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-white">Pocket Option (Real)</h4>
                  {realConfigured ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                      <Check className="w-3 h-3" /> Configured
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">Not Configured</span>
                  )}
                </div>
                <div className="flex gap-2 mt-3">
                  <input 
                    type="password" 
                    placeholder="Enter new SSID..." 
                    value={realSsid}
                    onChange={(e) => setRealSsid(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded text-sm px-3 py-1.5 text-white focus:outline-none focus:border-cyan-500"
                  />
                  <button 
                    onClick={() => handleSave('real', realSsid)}
                    disabled={!realSsid || realSaving}
                    className="px-3 py-1.5 text-sm bg-cyan-500 hover:bg-cyan-600 disabled:bg-slate-800 disabled:text-slate-500 text-black font-medium rounded transition-colors"
                  >
                    {realSaving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
