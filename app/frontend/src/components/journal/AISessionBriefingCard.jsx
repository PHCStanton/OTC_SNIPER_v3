import React, { useState } from 'react';
import { Cpu, Sparkles, Volume2, VolumeX, UploadCloud, RefreshCw, Check, Layers, AlertCircle } from 'lucide-react';

export default function AISessionBriefingCard({ stats, sessionId, kind, onOpenStagingModal }) {
  const [loading, setLoading] = useState(false);
  const [briefReport, setBriefReport] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [stagingLoading, setStagingLoading] = useState(false);
  const [stagedSuccess, setStagedSuccess] = useState(false);
  const [audioObj, setAudioObj] = useState(null);

  const handleGenerateBrief = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/analysis/generate-brief-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, kind: kind || 'ghost' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setBriefReport(data);
    } catch (err) {
      console.error('Failed to generate AI brief:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleVoice = async () => {
    if (isSpeaking) {
      if (audioObj) {
        audioObj.pause();
        audioObj.currentTime = 0;
      }
      window.speechSynthesis?.cancel();
      setIsSpeaking(false);
      return;
    }

    const scriptToSpeak = briefReport?.voice_script || (
      stats ? `Session summary: ${stats.total_trades} trades, ${stats.win_rate}% win rate, ${stats.total_profit} dollars profit.` : ''
    );
    if (!scriptToSpeak) return;

    setIsSpeaking(true);

    // Try backend speech proxy or fallback to browser speech synthesis
    try {
      const res = await fetch('/api/ai/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: scriptToSpeak, provider: 'grok' }),
      });
      if (res.ok && res.headers.get('content-type')?.includes('audio')) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => setIsSpeaking(false);
        audio.onerror = () => {
          fallbackSpeech(scriptToSpeak);
        };
        audio.play();
        setAudioObj(audio);
        return;
      }
    } catch (e) {
      console.warn('Backend TTS unavailable, falling back to Web Speech API:', e);
    }

    fallbackSpeech(scriptToSpeak);
  };

  const fallbackSpeech = (text) => {
    if (!window.speechSynthesis) {
      setIsSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const handleStageForReview = async () => {
    setStagingLoading(true);
    try {
      const res = await fetch('/api/analysis/stage-for-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, kind: kind || 'ghost', notes: 'Staged via AI Session Briefing' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStagedSuccess(true);
      setTimeout(() => setStagedSuccess(false), 3000);
      if (onOpenStagingModal) {
        onOpenStagingModal();
      }
    } catch (err) {
      console.error('Failed to stage report:', err);
    } finally {
      setStagingLoading(false);
    }
  };

  return (
    <div className="p-5 rounded-xl bg-gradient-to-br from-[#15181e] to-[#12141a] border border-amber-500/20 shadow-xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 mb-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner">
            <Cpu size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-black uppercase tracking-wider text-white">AI Session Briefing & Advisory</h2>
              <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Grok 4.3 Reasoning
              </span>
            </div>
            <p className="text-[10px] text-gray-400">Microstructure pattern analysis, vulnerability detection & staging recommendations</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {briefReport && (
            <button
              onClick={handleToggleVoice}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all border ${
                isSpeaking
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse'
                  : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/10 hover:text-white'
              }`}
            >
              {isSpeaking ? <VolumeX size={13} /> : <Volume2 size={13} />}
              <span>{isSpeaking ? 'Stop Audio' : 'Voice Over'}</span>
            </button>
          )}

          <button
            onClick={handleGenerateBrief}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[10px] font-black uppercase tracking-wider hover:bg-amber-500/20 transition-all disabled:opacity-50"
          >
            {loading ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}
            <span>{loading ? 'Analyzing Session...' : briefReport ? 'Re-Generate Brief' : 'Generate AI Brief'}</span>
          </button>

          <button
            onClick={handleStageForReview}
            disabled={stagingLoading}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all border ${
              stagedSuccess
                ? 'bg-emerald-500 text-black border-emerald-400'
                : 'bg-gradient-to-r from-amber-500/20 to-emerald-500/20 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/30'
            }`}
          >
            {stagedSuccess ? <Check size={13} /> : <UploadCloud size={13} />}
            <span>{stagedSuccess ? 'Staged in Queue' : 'Stage for KB Review'}</span>
          </button>
        </div>
      </div>

      {/* Brief Content Area */}
      {briefReport ? (
        <div className="space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 rounded-lg bg-black/30 border border-white/5 font-mono text-[10px]">
            <div>
              <span className="text-gray-500 text-[8px] uppercase block font-sans">Sample Scope</span>
              <span className="font-bold text-white">{briefReport.stats_summary?.total_trades} Trades ({briefReport.stats_summary?.win_rate}% WR)</span>
            </div>
            <div>
              <span className="text-gray-500 text-[8px] uppercase block font-sans">Profit Factor</span>
              <span className="font-bold text-amber-400">{briefReport.stats_summary?.profit_factor} (${briefReport.stats_summary?.net_profit})</span>
            </div>
            <div>
              <span className="text-gray-500 text-[8px] uppercase block font-sans">Vol / Liq Sweet Spot</span>
              <span className="font-bold text-cyan-400">{briefReport.stats_summary?.sweet_spot_volatility?.split(' ')[0]} / {briefReport.stats_summary?.sweet_spot_liquidity?.split(' ')[0]}</span>
            </div>
            <div>
              <span className="text-gray-500 text-[8px] uppercase block font-sans">Candidate Patterns</span>
              <span className="font-bold text-emerald-400">{briefReport.candidate_patterns_count} ready to stage</span>
            </div>
          </div>

          {/* Markdown Structured Report */}
          <div className="p-4 rounded-lg bg-black/20 border border-white/5 text-gray-300 text-xs leading-relaxed font-sans space-y-3 prose-invert">
            <div className="whitespace-pre-wrap font-sans text-[11px] text-gray-200">
              {briefReport.report}
            </div>
          </div>
        </div>
      ) : (
        <div className="py-8 flex flex-col items-center justify-center text-center space-y-3 bg-black/10 rounded-lg border border-white/5">
          <div className="p-3 rounded-full bg-amber-500/5 text-amber-400/70 border border-amber-500/10">
            <Sparkles size={24} />
          </div>
          <div className="max-w-md">
            <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">No AI Briefing Generated Yet</h4>
            <p className="text-[10px] text-gray-500 mt-1">
              Click &quot;Generate AI Brief&quot; above to synthesize session microstructure findings, identify toxic asset traps, and extract candidate Knowledge Base patterns.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
