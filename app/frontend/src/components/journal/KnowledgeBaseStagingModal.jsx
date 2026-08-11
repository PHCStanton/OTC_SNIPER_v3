import React, { useState, useEffect } from 'react';
import { 
  X, 
  Database, 
  Sparkles, 
  ShieldCheck, 
  AlertTriangle, 
  Download, 
  FileText, 
  CheckCircle2, 
  Layers, 
  Trash2,
  RefreshCw,
  Lock,
  ArrowRight
} from 'lucide-react';

export default function KnowledgeBaseStagingModal({ isOpen, onClose }) {
  const [stagedReports, setStagedReports] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedPatterns, setSelectedPatterns] = useState(new Set());
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitSuccess, setCommitSuccess] = useState(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const fetchStagedReports = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/analysis/staged-reports');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStagedReports(data || []);
      if (data && data.length > 0 && !selectedReportId) {
        setSelectedReportId(data[0].staged_id);
        // Select all patterns by default
        const allKeys = new Set((data[0].candidate_patterns || []).map((p) => p.pattern_key));
        setSelectedPatterns(allKeys);
      }
    } catch (err) {
      console.error('Failed to fetch staged reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStagedReports();
      setCommitSuccess(null);
    }
  }, [isOpen]);

  const activeReport = stagedReports.find((r) => r.staged_id === selectedReportId) || stagedReports[0];

  const handleSelectReport = (report) => {
    setSelectedReportId(report.staged_id);
    const allKeys = new Set((report.candidate_patterns || []).map((p) => p.pattern_key));
    setSelectedPatterns(allKeys);
    setCommitSuccess(null);
  };

  const handleTogglePattern = (key) => {
    const next = new Set(selectedPatterns);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
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

  const handleCommit = async () => {
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
      setShowConfirmDialog(false);
      fetchStagedReports();
    } catch (err) {
      console.error('Commit failed:', err);
    } finally {
      setCommitLoading(false);
    }
  };

  const handleExportMarkdown = () => {
    if (!activeReport) return;
    const content = `# Knowledge Base Session Update Report
Date: ${activeReport.created_utc}
Session: ${activeReport.session_id} (${activeReport.kind})
Total Trades: ${activeReport.total_trades} | Win Rate: ${activeReport.win_rate}% | Net Profit: $${activeReport.net_profit}
Statistical Significance: ${activeReport.statistical_significance ? 'YES (N >= 25)' : 'NO (Small sample)'}

## Selected Candidate Patterns (${selectedPatterns.size} patterns)
${(activeReport.candidate_patterns || [])
  .filter((p) => selectedPatterns.has(p.pattern_key))
  .map(
    (p) => `- ${p.pattern_key} | N=${p.sample_size}, WR=${p.win_rate_pct}%, Exp=$${p.expectancy} (Tier: ${p.confidence_tier})`
  )
  .join('\n')}

## Bayesian Priors Delta
Total Wins: +${activeReport.bayesian_deltas?.total_wins_delta || 0}
Total Losses: +${activeReport.bayesian_deltas?.total_losses_delta || 0}
`;

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kb_staging_report_${activeReport.session_id}_${Date.now()}.md`;
    a.click();
  };

  const handleExportJSON = () => {
    if (!activeReport) return;
    const exportData = {
      staged_id: activeReport.staged_id,
      timestamp: activeReport.created_utc,
      session_id: activeReport.session_id,
      metrics: {
        total_trades: activeReport.total_trades,
        win_rate: activeReport.win_rate,
        net_profit: activeReport.net_profit,
      },
      selected_patterns: (activeReport.candidate_patterns || []).filter((p) => selectedPatterns.has(p.pattern_key)),
      bayesian_deltas: activeReport.bayesian_deltas,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kb_staging_bundle_${activeReport.session_id}_${Date.now()}.json`;
    a.click();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-5xl h-[85vh] bg-[#12141a] border border-amber-500/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-[#171a22]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner">
              <Database size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-black uppercase tracking-wider text-white">Knowledge Base & Bayesian Priors Staging</h2>
                <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  User Verification Gate
                </span>
              </div>
              <p className="text-[10px] text-gray-400">Review multi-session candidate patterns before manual transactional commit</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Left Sidebar: Staged Reports List */}
          <div className="w-72 border-r border-white/5 bg-black/20 p-4 flex flex-col justify-between overflow-y-auto custom-scrollbar">
            <div>
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-white/5">
                <span className="text-[9px] font-bold uppercase tracking-wider text-gray-400">Staged Reports Queue</span>
                <span className="px-1.5 py-0.2 rounded text-[8px] font-mono bg-white/5 text-gray-400">
                  {stagedReports.length}
                </span>
              </div>

              <div className="space-y-2">
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
                        <span className={r.win_rate >= 50 ? 'text-emerald-400' : 'text-rose-400'}>
                          {r.win_rate}% WR
                        </span>
                        <span>${r.net_profit}</span>
                      </div>
                    </div>
                  );
                })}

                {stagedReports.length === 0 && !loading && (
                  <div className="py-8 text-center text-[10px] text-gray-500">
                    No staged reports in queue. Stage a session from the AI Briefing card.
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={fetchStagedReports}
              className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg bg-white/5 text-[9px] font-bold uppercase tracking-wider text-gray-400 hover:text-white hover:bg-white/10 transition-all border border-white/5"
            >
              <RefreshCw size={11} />
              <span>Refresh Queue</span>
            </button>
          </div>

          {/* Main Inspection Panel */}
          {activeReport ? (
            <div className="flex-1 p-6 overflow-y-auto custom-scrollbar space-y-6">
              
              {/* Commit Notification Banner */}
              {commitSuccess && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-emerald-300 text-xs">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-400" />
                    <span>{commitSuccess.message} ({commitSuccess.patterns_committed} patterns committed)</span>
                  </div>
                  <span className="text-[9px] font-mono text-gray-400">Backups: {commitSuccess.backups?.join(', ')}</span>
                </div>
              )}

              {/* Scope & Significance Bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 rounded-xl bg-black/30 border border-white/5 font-mono text-[10px]">
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
                  <span className="text-gray-500 text-[8px] uppercase block font-sans">Selected Patterns</span>
                  <span className="font-bold text-cyan-400 text-xs">{selectedPatterns.size} / {(activeReport.candidate_patterns || []).length}</span>
                </div>
                <div>
                  <span className="text-gray-500 text-[8px] uppercase block font-sans">Bayesian Deltas</span>
                  <span className="font-bold text-amber-400">+{activeReport.bayesian_deltas?.total_wins_delta || 0}W / +{activeReport.bayesian_deltas?.total_losses_delta || 0}L</span>
                </div>
              </div>

              {/* Candidate Condition Patterns Table */}
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-black uppercase tracking-wider text-white">Candidate Condition Patterns</h3>
                    <span className="text-[9px] text-gray-400">({(activeReport.candidate_patterns || []).length} discovered)</span>
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
                <h3 className="text-xs font-black uppercase tracking-wider text-white mb-2">Bayesian Prior Deltas Preview</h3>
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

              {/* Confirmation Dialog Popup */}
              {showConfirmDialog && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/40 space-y-3 animate-fade-in">
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-bold text-white uppercase">Confirm Transactional Update</h4>
                      <p className="text-[10px] text-gray-300 mt-1">
                        This will write {selectedPatterns.size} patterns to <code className="text-amber-300">condition_patterns.json</code> and merge +{activeReport.bayesian_deltas?.total_trades_delta || 0} trades into <code className="text-amber-300">bayesian_priors.json</code>. An automated timestamped backup (.bak) will be created first.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-amber-500/20">
                    <button
                      onClick={() => setShowConfirmDialog(false)}
                      className="px-3 py-1.5 rounded-lg bg-white/5 text-gray-300 text-[10px] font-bold uppercase hover:bg-white/10"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCommit}
                      disabled={commitLoading}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-500 text-black text-[10px] font-black uppercase hover:bg-emerald-400 transition-all disabled:opacity-50"
                    >
                      {commitLoading ? <RefreshCw size={12} className="animate-spin" /> : <Lock size={12} />}
                      <span>{commitLoading ? 'Committing...' : 'Yes, Commit with Backup'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-xs">
              No report selected.
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-white/5 bg-[#171a22]">
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportMarkdown}
              disabled={!activeReport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-gray-300 text-[10px] font-black uppercase hover:bg-white/10 hover:text-white transition-all disabled:opacity-50"
            >
              <FileText size={12} />
              <span>Export Markdown</span>
            </button>

            <button
              onClick={handleExportJSON}
              disabled={!activeReport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-gray-300 text-[10px] font-black uppercase hover:bg-white/10 hover:text-white transition-all disabled:opacity-50"
            >
              <Download size={12} />
              <span>Export JSON Package</span>
            </button>

            {activeReport && (
              <button
                onClick={() => handleDeleteStaged(activeReport.staged_id)}
                className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 transition-all ml-2"
                title="Delete from Queue"
              >
                <Trash2 size={13} />
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-white/5 text-gray-400 text-[10px] font-black uppercase tracking-wider hover:text-white hover:bg-white/10 transition-all"
            >
              Close
            </button>

            {activeReport && activeReport.status !== 'COMMITTED' && (
              <button
                onClick={() => setShowConfirmDialog(true)}
                disabled={commitLoading || selectedPatterns.size === 0}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-emerald-500 text-black text-[10px] font-black uppercase tracking-wider hover:from-amber-400 hover:to-emerald-400 transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
              >
                <Database size={13} />
                <span>Commit {selectedPatterns.size} Patterns to KB</span>
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
