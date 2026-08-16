import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  Database, 
  Sparkles, 
  ShieldCheck, 
  AlertTriangle, 
  Download, 
  Upload,
  FileText, 
  CheckCircle2, 
  Layers, 
  Trash2,
  RefreshCw,
  Lock,
  ArrowRight,
  Play,
  BookmarkPlus,
  Activity,
  Zap,
  Info
} from 'lucide-react';

export default function KnowledgeBaseStagingModal({ isOpen, onClose }) {
  // Navigation Tabs: 'queue' | 'protocols'
  const [activeTab, setActiveTab] = useState('queue');

  // Staged Queue State
  const [stagedReports, setStagedReports] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [selectedPatterns, setSelectedPatterns] = useState(new Set());
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitSuccess, setCommitSuccess] = useState(null);
  const [showCommitDialog, setShowCommitDialog] = useState(false);

  // Protocols Library State
  const [protocols, setProtocols] = useState([]);
  const [activeProtocolInfo, setActiveProtocolInfo] = useState(null);
  const [selectedProtocolId, setSelectedProtocolId] = useState(null);
  const [protocolDetails, setProtocolDetails] = useState(null);
  const [protocolLoading, setProtocolLoading] = useState(false);
  const [activateLoading, setActivateLoading] = useState(false);
  const [protocolActionMessage, setProtocolActionMessage] = useState(null);
  const [showActivateDialog, setShowActivateDialog] = useState(false);

  // Save as Protocol Dialog State
  const [showSaveProtocolModal, setShowSaveProtocolModal] = useState(false);
  const [saveProtoName, setSaveProtoName] = useState('');
  const [saveProtoNotes, setSaveProtoNotes] = useState('');
  const [saveProtoHorizon, setSaveProtoHorizon] = useState(60);
  const [saveLoading, setSaveLoading] = useState(false);

  const fileInputRef = useRef(null);

  // -------------------------------------------------------------------------
  // Data Fetching
  // -------------------------------------------------------------------------

  const fetchStagedReports = async () => {
    try {
      const res = await fetch('/api/analysis/staged-reports');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStagedReports(data || []);
      if (data && data.length > 0 && !selectedReportId) {
        setSelectedReportId(data[0].staged_id);
        const allKeys = new Set((data[0].candidate_patterns || []).map((p) => p.pattern_key));
        setSelectedPatterns(allKeys);
      }
    } catch (err) {
      console.error('Failed to fetch staged reports:', err);
    }
  };

  const fetchProtocols = async () => {
    setProtocolLoading(true);
    try {
      const res = await fetch('/api/analysis/protocols');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const list = data.protocols || [];
      setProtocols(list);
      setActiveProtocolInfo(data.active_protocol || null);
      if (list.length > 0 && !selectedProtocolId) {
        setSelectedProtocolId(list[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch protocols:', err);
    } finally {
      setProtocolLoading(false);
    }
  };

  const fetchProtocolDetails = async (protoId) => {
    if (!protoId) return;
    try {
      const res = await fetch(`/api/analysis/protocols/${protoId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProtocolDetails(data);
    } catch (err) {
      console.error('Failed to fetch protocol details:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStagedReports();
      fetchProtocols();
      setCommitSuccess(null);
      setProtocolActionMessage(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (activeTab === 'protocols' && selectedProtocolId) {
      fetchProtocolDetails(selectedProtocolId);
    }
  }, [activeTab, selectedProtocolId]);

  // -------------------------------------------------------------------------
  // Staged Queue Handlers
  // -------------------------------------------------------------------------

  const activeReport = stagedReports.find((r) => r.staged_id === selectedReportId) || stagedReports[0];

  const handleSelectReport = (report) => {
    setSelectedReportId(report.staged_id);
    const allKeys = new Set((report.candidate_patterns || []).map((p) => p.pattern_key));
    setSelectedPatterns(allKeys);
    setCommitSuccess(null);
  };

  const handleTogglePattern = (key) => {
    const next = new Set(selectedPatterns);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setSelectedPatterns(next);
  };

  const handleSelectAllPatterns = () => {
    if (!activeReport) return;
    if (selectedPatterns.size === (activeReport.candidate_patterns || []).length) {
      setSelectedPatterns(new Set());
    } else {
      const allKeys = new Set((activeReport.candidate_patterns || []).map((p) => p.pattern_key));
      setSelectedPatterns(allKeys);
    }
  };

  const handleDeleteStaged = async (stagedId) => {
    try {
      await fetch(`/api/analysis/staged-reports/${stagedId}`, { method: 'DELETE' });
      fetchStagedReports();
    } catch (err) {
      console.error('Failed to delete staged report:', err);
    }
  };

  const handleCommitToKB = async () => {
    if (!activeReport) return;
    setCommitLoading(true);
    try {
      const res = await fetch('/api/analysis/commit-staged-to-knowledge-base', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          staged_id: activeReport.staged_id,
          selected_pattern_keys: Array.from(selectedPatterns),
          commit_bayesian: true,
          commit_kb: true,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCommitSuccess(data);
      setShowCommitDialog(false);
      fetchStagedReports();
      fetchProtocols();
    } catch (err) {
      console.error('Commit failed:', err);
    } finally {
      setCommitLoading(false);
    }
  };

  const handleOpenSaveProtocolModal = () => {
    if (!activeReport) return;
    setSaveProtoName(`Protocol: ${activeReport.session_id}`);
    setSaveProtoNotes(activeReport.user_notes || '');
    setSaveProtoHorizon(60);
    setShowSaveProtocolModal(true);
  };

  const handleSaveProtocolSubmit = async () => {
    if (!activeReport) return;
    setSaveLoading(true);
    try {
      const res = await fetch('/api/analysis/protocols/save-from-staged', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          staged_id: activeReport.staged_id,
          name: saveProtoName,
          notes: saveProtoNotes,
          horizon_seconds: parseInt(saveProtoHorizon, 10) || 60,
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to save protocol');
      }
      const saved = await res.json();
      setShowSaveProtocolModal(false);
      fetchProtocols();
      setActiveTab('protocols');
      setSelectedProtocolId(saved.id);
      setProtocolActionMessage({
        type: 'success',
        text: `Saved snapshot protocol '${saved.name}' (${saved.health}) successfully!`,
      });
    } catch (err) {
      console.error('Save protocol failed:', err);
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaveLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Protocols Library Handlers
  // -------------------------------------------------------------------------

  const handleActivateProtocol = async () => {
    if (!selectedProtocolId) return;
    setActivateLoading(true);
    try {
      const res = await fetch('/api/analysis/protocols/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: selectedProtocolId,
          allow_experimental: true,
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Activation failed');
      }
      const activeData = await res.json();
      setActiveProtocolInfo(activeData);
      setShowActivateDialog(false);
      setProtocolActionMessage({
        type: 'success',
        text: `Activated protocol '${activeData.name}' (${activeData.horizon_seconds}s, ${activeData.health}) as live working priors!`,
      });
      fetchProtocols();
    } catch (err) {
      console.error('Activation failed:', err);
      setProtocolActionMessage({
        type: 'error',
        text: `Activation failed: ${err.message}`,
      });
    } finally {
      setActivateLoading(false);
    }
  };

  const handleDeleteProtocol = async (protoId) => {
    if (!confirm('Are you sure you want to delete this protocol snapshot?')) return;
    try {
      const res = await fetch(`/api/analysis/protocols/${protoId}`, { method: 'DELETE' });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Delete failed');
      }
      fetchProtocols();
      setSelectedProtocolId(null);
      setProtocolDetails(null);
      setProtocolActionMessage({
        type: 'success',
        text: 'Protocol deleted from library.',
      });
    } catch (err) {
      alert(`Failed to delete protocol: ${err.message}`);
    }
  };

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const content = event.target?.result;
        const res = await fetch('/api/analysis/protocols/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: String(content) }),
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Import failed');
        }
        const imported = await res.json();
        fetchProtocols();
        setSelectedProtocolId(imported.id);
        setProtocolActionMessage({
          type: 'success',
          text: `Successfully imported protocol '${imported.name}' (${imported.health}) with ${imported.trade_count} trades.`,
        });
      } catch (err) {
        alert(`Import error: ${err.message}`);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleExportProtocolJSON = (proto) => {
    if (!proto) return;
    const blob = new Blob([JSON.stringify(proto, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bayesian_protocol_${proto.id}_${Date.now()}.json`;
    a.click();
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  if (!isOpen) return null;

  const isSelectedActive = activeProtocolInfo && activeProtocolInfo.id === selectedProtocolId;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in font-sans">
      <div className="relative w-full max-w-6xl h-[88vh] bg-[#101216] border border-amber-500/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Top Header */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-white/5 bg-[#15181f]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner">
              <Database size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-black uppercase tracking-wider text-white">Bayesian Knowledge Base & Protocol Manager</h2>
                <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Transactional Gateway
                </span>
                {activeProtocolInfo && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    <Zap size={10} className="text-cyan-400" />
                    Active: {activeProtocolInfo.name} ({activeProtocolInfo.horizon_seconds}s)
                  </span>
                )}
              </div>
              <p className="text-[10px] text-gray-400">Review staged sessions, manage named Bayesian protocols, and switch live working priors safely.</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Main Body */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Left Sidebar */}
          <div className="w-80 border-r border-white/5 bg-black/30 flex flex-col justify-between overflow-hidden">
            
            {/* Top Tab Selectors */}
            <div className="p-3 border-b border-white/5 bg-[#13151b]">
              <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-black/40 border border-white/5 text-[10px] font-black uppercase">
                <button
                  onClick={() => setActiveTab('queue')}
                  className={`py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                    activeTab === 'queue'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <Layers size={12} />
                  <span>Queue ({stagedReports.length})</span>
                </button>
                <button
                  onClick={() => setActiveTab('protocols')}
                  className={`py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                    activeTab === 'protocols'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <BookmarkPlus size={12} />
                  <span>Protocols ({protocols.length})</span>
                </button>
              </div>
            </div>

            {/* List Scroll Area */}
            <div className="flex-1 p-3 overflow-y-auto custom-scrollbar space-y-2">
              
              {/* TAB 1: STAGED QUEUE */}
              {activeTab === 'queue' && (
                <>
                  <div className="flex items-center justify-between px-1 pb-1 mb-1 border-b border-white/5 text-[9px] font-bold uppercase tracking-wider text-gray-500">
                    <span>Pending Reports</span>
                    <span className="font-mono text-gray-400">{stagedReports.length}</span>
                  </div>

                  {stagedReports.map((r) => {
                    const isSelected = r.staged_id === activeReport?.staged_id;
                    const isCommitted = r.status === 'COMMITTED';

                    return (
                      <div
                        key={r.staged_id}
                        onClick={() => handleSelectReport(r)}
                        className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-amber-500/10 border-amber-500/40 shadow-lg'
                            : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-bold text-white truncate max-w-[140px]">
                            {r.session_id}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[7px] font-black uppercase border ${
                              isCommitted
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                            }`}
                          >
                            {r.status}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[9px] font-mono text-gray-400">
                          <span>{r.total_trades} trades</span>
                          <span className={r.win_rate >= 50 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                            {r.win_rate}% WR
                          </span>
                          <span>${r.net_profit}</span>
                        </div>
                      </div>
                    );
                  })}

                  {stagedReports.length === 0 && (
                    <div className="py-12 text-center text-[10px] text-gray-500">
                      No reports in queue. Stage sessions via Journal AI Briefing.
                    </div>
                  )}
                </>
              )}

              {/* TAB 2: PROTOCOLS LIBRARY */}
              {activeTab === 'protocols' && (
                <>
                  <div className="flex items-center justify-between px-1 pb-1 mb-1 border-b border-white/5">
                    <span className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Saved Protocols</span>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="flex items-center gap-1 px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 text-[8px] font-black uppercase text-amber-400 border border-white/10"
                    >
                      <Upload size={10} />
                      <span>Import JSON</span>
                    </button>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleImportFile}
                      accept=".json"
                      className="hidden"
                    />
                  </div>

                  {protocols.map((p) => {
                    const isSelected = p.id === selectedProtocolId;
                    const isActive = p.is_active;

                    return (
                      <div
                        key={p.id}
                        onClick={() => setSelectedProtocolId(p.id)}
                        className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-amber-500/10 border-amber-500/40 shadow-lg'
                            : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-1.5 truncate max-w-[150px]">
                            {isActive && (
                              <span className="px-1 py-0.2 rounded text-[7px] font-black uppercase bg-emerald-500 text-black">
                                ACTIVE
                              </span>
                            )}
                            <span className="text-[10px] font-bold text-white truncate">
                              {p.name}
                            </span>
                          </div>
                          <span className="px-1.5 py-0.2 rounded text-[7px] font-black font-mono uppercase bg-white/5 text-gray-300 border border-white/10">
                            {p.horizon_seconds}s
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[9px] font-mono mt-1 text-gray-400">
                          <span>N={p.trade_count}</span>
                          <span className={p.win_rate >= 50 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                            {p.win_rate}% WR
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[7px] font-black uppercase ${
                              p.health === 'READY'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : p.health === 'EXPERIMENTAL'
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-rose-500/20 text-rose-300'
                            }`}
                          >
                            {p.health}
                          </span>
                        </div>
                      </div>
                    );
                  })}

                  {protocols.length === 0 && !protocolLoading && (
                    <div className="py-12 text-center text-[10px] text-gray-500">
                      No protocols saved yet. Use "Save as Protocol" from the queue or import a JSON bundle.
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Bottom Refresh Button */}
            <div className="p-3 border-t border-white/5 bg-[#13151b]">
              <button
                onClick={() => {
                  fetchStagedReports();
                  fetchProtocols();
                }}
                className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg bg-white/5 text-[9px] font-bold uppercase tracking-wider text-gray-400 hover:text-white hover:bg-white/10 transition-all border border-white/5"
              >
                <RefreshCw size={11} />
                <span>Refresh Data</span>
              </button>
            </div>
          </div>

          {/* Main Inspection Panel */}
          <div className="flex-1 p-6 overflow-y-auto custom-scrollbar space-y-6">
            
            {/* Status / Action Notification Banner */}
            {protocolActionMessage && (
              <div
                className={`p-3 rounded-xl border flex items-center justify-between text-xs animate-fade-in ${
                  protocolActionMessage.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  {protocolActionMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                  <span>{protocolActionMessage.text}</span>
                </div>
                <button
                  onClick={() => setProtocolActionMessage(null)}
                  className="text-gray-400 hover:text-white text-[10px]"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {commitSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-emerald-300 text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-emerald-400" />
                  <span>{commitSuccess.message} ({commitSuccess.patterns_committed} patterns committed)</span>
                </div>
                <span className="text-[9px] font-mono text-gray-400">Backups: {commitSuccess.backups?.join(', ')}</span>
              </div>
            )}

            {/* ================= VIEW 1: STAGED REPORT QUEUE VIEW ================= */}
            {activeTab === 'queue' && activeReport && (
              <>
                {/* Scope & Significance Bar */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3.5 rounded-xl bg-black/40 border border-white/5 font-mono text-[10px]">
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Session Scope</span>
                    <span className="font-bold text-white text-xs">{activeReport.session_id}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Statistical Significance</span>
                    <span className={`font-bold flex items-center gap-1 ${activeReport.statistical_significance ? 'text-emerald-400' : 'text-amber-400'}`}>
                      <ShieldCheck size={11} />
                      {activeReport.statistical_significance ? 'SUFFICIENT (N >= 25)' : 'LOW SAMPLE (<25)'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Candidate Patterns</span>
                    <span className="font-bold text-cyan-400 text-xs">{selectedPatterns.size} / {(activeReport.candidate_patterns || []).length}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">60s Bayesian Deltas</span>
                    <span className="font-bold text-amber-400">+{activeReport.bayesian_deltas?.total_wins_delta || 0}W / +{activeReport.bayesian_deltas?.total_losses_delta || 0}L</span>
                  </div>
                </div>

                {/* Candidate Condition Patterns Table */}
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-2">
                      <h3 className="text-xs font-black uppercase tracking-wider text-white">Discovered Candidate Patterns</h3>
                      <span className="text-[9px] text-gray-400">({(activeReport.candidate_patterns || []).length} patterns)</span>
                    </div>
                    <button
                      onClick={handleSelectAllPatterns}
                      className="text-[9px] font-bold text-amber-400 hover:underline uppercase"
                    >
                      {selectedPatterns.size === (activeReport.candidate_patterns || []).length ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>

                  <div className="max-h-56 overflow-y-auto border border-white/5 rounded-xl bg-black/20 custom-scrollbar">
                    <table className="w-full text-left text-[10px]">
                      <thead className="sticky top-0 bg-[#171a22] text-gray-400 uppercase text-[8px] tracking-wider border-b border-white/5">
                        <tr>
                          <th className="py-2 px-3 w-8"></th>
                          <th className="py-2">Pattern Key</th>
                          <th className="py-2">Sample</th>
                          <th className="py-2">Win Rate</th>
                          <th className="py-2">Expectancy</th>
                          <th className="py-2">Confidence</th>
                          <th className="py-2 text-right px-3">Classification</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 font-mono">
                        {(activeReport.candidate_patterns || []).map((p) => {
                          const isChecked = selectedPatterns.has(p.pattern_key);
                          return (
                            <tr
                              key={p.pattern_key}
                              onClick={() => handleTogglePattern(p.pattern_key)}
                              className={`cursor-pointer hover:bg-white/[0.03] transition-colors ${
                                isChecked ? 'bg-amber-500/5' : ''
                              }`}
                            >
                              <td className="py-1.5 px-3">
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => {}}
                                  className="rounded border-white/20 bg-black/40 text-amber-500 focus:ring-0"
                                />
                              </td>
                              <td className="py-1.5 text-white font-sans font-bold">{p.pattern_key}</td>
                              <td className="py-1.5 text-gray-400">{p.sample_size}</td>
                              <td className="py-1.5 font-bold">
                                <span className={p.win_rate_pct >= 50 ? 'text-emerald-400' : 'text-rose-400'}>
                                  {p.win_rate_pct.toFixed(1)}%
                                </span>
                              </td>
                              <td className="py-1.5 text-gray-300">${p.expectancy}</td>
                              <td className="py-1.5">
                                <span className="px-1.5 py-0.2 rounded text-[7px] font-black uppercase bg-white/5 text-gray-300">
                                  {p.confidence_tier}
                                </span>
                              </td>
                              <td className="py-1.5 text-right px-3 font-sans">
                                {p.boost_candidate ? (
                                  <span className="px-1.5 py-0.2 rounded text-[7px] font-black uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                    Boost Edge
                                  </span>
                                ) : p.suppression_candidate ? (
                                  <span className="px-1.5 py-0.2 rounded text-[7px] font-black uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                    Suppress Trap
                                  </span>
                                ) : (
                                  <span className="text-gray-600 text-[8px]">Neutral</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Bayesian Priors Diff Preview */}
                <div>
                  <h3 className="text-xs font-black uppercase tracking-wider text-white mb-2">60s Bayesian Prior Deltas Preview</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[9px]">
                    {Object.entries(activeReport.bayesian_deltas?.feature_deltas || {}).slice(0, 12).map(([fkey, counts]) => (
                      <div key={fkey} className="p-2 rounded-lg bg-black/30 border border-white/5 flex items-center justify-between">
                        <span className="text-gray-400 truncate max-w-[120px]">{fkey}</span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-emerald-400 font-bold">+{counts.win}W</span>
                          <span className="text-rose-400 font-bold">+{counts.loss}L</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Commit Confirmation Popup */}
                {showCommitDialog && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/40 space-y-3 animate-fade-in">
                    <div className="flex items-start gap-2.5">
                      <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-xs font-bold text-white uppercase">Confirm Commit to Global Knowledge Base</h4>
                        <p className="text-[10px] text-gray-300 mt-1">
                          This will append {selectedPatterns.size} patterns to <code className="text-amber-300">condition_patterns.json</code> and merge +{activeReport.bayesian_deltas?.total_trades_delta || 0} trades into the live <code className="text-amber-300">bayesian_priors.json</code> working file. An automated timestamped backup (.bak) will be created first.
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-amber-500/20">
                      <button
                        onClick={() => setShowCommitDialog(false)}
                        className="px-3 py-1.5 rounded-lg bg-white/5 text-gray-300 text-[10px] font-bold uppercase hover:bg-white/10"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCommitToKB}
                        disabled={commitLoading}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-500 text-black text-[10px] font-black uppercase hover:bg-emerald-400 transition-all disabled:opacity-50"
                      >
                        {commitLoading ? <RefreshCw size={12} className="animate-spin" /> : <Lock size={12} />}
                        <span>{commitLoading ? 'Committing...' : 'Yes, Commit with Backup'}</span>
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ================= VIEW 2: PROTOCOLS LIBRARY INSPECT VIEW ================= */}
            {activeTab === 'protocols' && protocolDetails && (
              <>
                {/* Protocol Header Card */}
                <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-sm font-black text-white">{protocolDetails.name}</h3>
                      <span className="px-2 py-0.5 rounded text-[8px] font-mono font-bold bg-white/10 text-amber-300 border border-white/10">
                        {protocolDetails.horizon_seconds}s Horizon
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[8px] font-black uppercase ${
                          protocolDetails.health === 'READY'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : protocolDetails.health === 'EXPERIMENTAL'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}
                      >
                        {protocolDetails.health}
                      </span>
                    </div>

                    {isSelectedActive ? (
                      <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] font-black uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm">
                        <CheckCircle2 size={12} />
                        Currently Active Live
                      </span>
                    ) : (
                      <button
                        onClick={() => setShowActivateDialog(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-black text-[9px] font-black uppercase hover:bg-emerald-400 transition-all shadow-md"
                      >
                        <Play size={11} className="fill-black" />
                        <span>Activate Protocol</span>
                      </button>
                    )}
                  </div>

                  <p className="text-[10px] text-gray-400">{protocolDetails.notes || 'No description provided.'}</p>
                </div>

                {/* Metrics Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3.5 rounded-xl bg-black/40 border border-white/5 font-mono text-[10px]">
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Total Trades (N)</span>
                    <span className="font-bold text-white text-xs">{protocolDetails.priors?.total_trades || 0}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Win Rate</span>
                    <span className="font-bold text-emerald-400 text-xs">
                      {protocolDetails.priors?.total_trades > 0
                        ? ((protocolDetails.priors.total_wins / protocolDetails.priors.total_trades) * 100).toFixed(1)
                        : '0.0'}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Wins / Losses</span>
                    <span className="font-bold text-gray-300">
                      {protocolDetails.priors?.total_wins || 0}W / {protocolDetails.priors?.total_losses || 0}L
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[8px] uppercase block font-sans">Distinct Feature Keys</span>
                    <span className="font-bold text-cyan-400">
                      {Object.keys(protocolDetails.priors?.feature_counts || {}).length}
                    </span>
                  </div>
                </div>

                {/* Priors Feature Key Breakdown */}
                <div>
                  <h3 className="text-xs font-black uppercase tracking-wider text-white mb-2.5">Feature Priors Distribution</h3>
                  <div className="max-h-60 overflow-y-auto border border-white/5 rounded-xl bg-black/20 p-2 custom-scrollbar">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 font-mono text-[9px]">
                      {Object.entries(protocolDetails.priors?.feature_counts || {}).map(([fkey, counts]) => (
                        <div key={fkey} className="p-2 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
                          <span className="text-gray-400 truncate max-w-[130px]">{fkey}</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-emerald-400 font-bold">+{counts.win}W</span>
                            <span className="text-rose-400 font-bold">+{counts.loss}L</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Activate Confirmation Dialog */}
                {showActivateDialog && (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40 space-y-3 animate-fade-in">
                    <div className="flex items-start gap-2.5">
                      <Zap size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-xs font-bold text-white uppercase">Confirm Live Protocol Activation</h4>
                        <p className="text-[10px] text-gray-300 mt-1">
                          This will copy the priors from <code className="text-emerald-300">{protocolDetails.name}</code> into the live <code className="text-emerald-300">bayesian_priors.json</code> working file. An automated timestamped backup (.bak) of current priors will be created first.
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-emerald-500/20">
                      <button
                        onClick={() => setShowActivateDialog(false)}
                        className="px-3 py-1.5 rounded-lg bg-white/5 text-gray-300 text-[10px] font-bold uppercase hover:bg-white/10"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleActivateProtocol}
                        disabled={activateLoading}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-500 text-black text-[10px] font-black uppercase hover:bg-emerald-400 transition-all disabled:opacity-50"
                      >
                        {activateLoading ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} className="fill-black" />}
                        <span>{activateLoading ? 'Activating...' : 'Yes, Activate Live'}</span>
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {activeTab === 'protocols' && !protocolDetails && !protocolLoading && (
              <div className="py-24 text-center text-gray-500 text-xs">
                Select a protocol from the left sidebar to inspect details.
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-white/5 bg-[#15181f]">
          
          {/* Left Footer Actions */}
          <div className="flex items-center gap-2">
            {activeTab === 'queue' && activeReport && (
              <>
                <button
                  onClick={() => handleDeleteStaged(activeReport.staged_id)}
                  className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 transition-all mr-2"
                  title="Delete Staged Report"
                >
                  <Trash2 size={13} />
                </button>
                <span className="text-[10px] text-gray-500 font-mono">ID: {activeReport.staged_id}</span>
              </>
            )}

            {activeTab === 'protocols' && protocolDetails && (
              <>
                <button
                  onClick={() => handleExportProtocolJSON(protocolDetails)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-gray-300 text-[10px] font-black uppercase hover:bg-white/10 hover:text-white transition-all"
                >
                  <Download size={12} />
                  <span>Export Protocol JSON</span>
                </button>
                {!isSelectedActive && (
                  <button
                    onClick={() => handleDeleteProtocol(protocolDetails.id)}
                    className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 transition-all ml-1"
                    title="Delete Protocol"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </>
            )}
          </div>

          {/* Right Footer Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-white/5 text-gray-400 text-[10px] font-black uppercase tracking-wider hover:text-white hover:bg-white/10 transition-all"
            >
              Close
            </button>

            {activeTab === 'queue' && activeReport && (
              <>
                {/* Secondary CTA: Commit to Global KB */}
                <button
                  onClick={() => setShowCommitDialog(true)}
                  disabled={commitLoading || selectedPatterns.size === 0}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white/5 border border-amber-500/30 text-amber-300 text-[10px] font-black uppercase tracking-wider hover:bg-amber-500/10 transition-all disabled:opacity-50"
                >
                  <Database size={13} />
                  <span>Commit to KB</span>
                </button>

                {/* Primary CTA: Save as Protocol */}
                <button
                  onClick={handleOpenSaveProtocolModal}
                  disabled={saveLoading}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-emerald-500 text-black text-[10px] font-black uppercase tracking-wider hover:from-amber-400 hover:to-emerald-400 transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                >
                  <BookmarkPlus size={13} />
                  <span>Save as Protocol</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Modal Sub-Dialog: Save as Protocol */}
        {showSaveProtocolModal && (
          <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in font-sans">
            <div className="w-full max-w-md bg-[#161922] border border-amber-500/40 rounded-2xl p-5 shadow-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <BookmarkPlus size={18} className="text-amber-400" />
                  <h3 className="text-xs font-black text-white uppercase tracking-wider">Save as Named Bayesian Protocol</h3>
                </div>
                <button
                  onClick={() => setShowSaveProtocolModal(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-gray-400 mb-1">Protocol Name</label>
                  <input
                    type="text"
                    value={saveProtoName}
                    onChange={(e) => setSaveProtoName(e.target.value)}
                    placeholder="e.g. 60s Range-Bound Night Protocol"
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white focus:border-amber-400 focus:outline-none text-xs font-sans"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold uppercase text-gray-400 mb-1">Horizon Expiry</label>
                    <select
                      value={saveProtoHorizon}
                      onChange={(e) => setSaveProtoHorizon(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white focus:border-amber-400 focus:outline-none text-xs font-mono"
                    >
                      <option value={60}>60s (Standard)</option>
                      <option value={300}>300s (5-Minute)</option>
                      <option value={120}>120s (2-Minute)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase text-gray-400 mb-1">Trades in Snapshot</label>
                    <div className="px-3 py-2 rounded-lg bg-black/20 border border-white/5 text-amber-300 font-mono font-bold text-xs">
                      {activeReport.bayesian_deltas?.total_trades_delta || 0} trades
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase text-gray-400 mb-1">Notes & Description</label>
                  <textarea
                    rows={2}
                    value={saveProtoNotes}
                    onChange={(e) => setSaveProtoNotes(e.target.value)}
                    placeholder="Strategy notes or market conditions observed..."
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white focus:border-amber-400 focus:outline-none text-xs font-sans resize-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/5">
                <button
                  onClick={() => setShowSaveProtocolModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-gray-400 text-[10px] font-black uppercase hover:bg-white/10"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveProtocolSubmit}
                  disabled={saveLoading || !saveProtoName.trim()}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-500 text-black text-[10px] font-black uppercase hover:bg-emerald-400 transition-all disabled:opacity-50"
                >
                  {saveLoading ? <RefreshCw size={12} className="animate-spin" /> : <BookmarkPlus size={12} />}
                  <span>{saveLoading ? 'Saving...' : 'Save Protocol'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
