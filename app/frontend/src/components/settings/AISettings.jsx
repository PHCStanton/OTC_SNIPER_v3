/**
 * AISettings — Dedicated AI Settings panel (Phase 1+).
 * Easy to add/remove/manage profiles.
 * Voice settings live here.
 * Profiles control model (fast non-reasoning vs balanced reasoning), KB usage, token limits, and voice playback params.
 * Feature assignments let different parts of the app (confirmation, review loop, analysis, chat, voiceover) use appropriate settings.
 *
 * Reasoning split recommendation (per plan):
 * - Fast non-reasoning ("grok-4.3-fast"): Auto-Ghost confirmations (4s timeout), quick chat.
 * - Balanced/light reasoning ("grok-4.3-balanced"): AI Review Loop, Analysis refinement, Voice-over scripts.
 */

import { useEffect, useState } from 'react';
import { Plus, Trash2, Copy, Play, Save, Zap, Volume2 } from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';

// Default profile template (fast, cheap, good for speed-critical paths)
const DEFAULT_PROFILE = {
  name: 'New Profile',
  modelKey: 'grok-4.3-fast',
  reasoningEffort: 'none', // none | low
  includeKB: true,
  maxTokens: 600,
  voice: {
    voiceName: '', // populated from browser speechSynthesis
    rate: 1.0,
    pitch: 1.0,
    volume: 0.9,
  },
  description: 'Custom profile',
};

const FEATURE_LABELS = {
  confirmation: 'Auto-Ghost / Trade Confirmation',
  review: 'AI Review Loop (periodic)',
  analysis: 'Session Analysis & Refinement',
  chat: 'Direct AI Chat / Image',
  voiceover: 'Voice-Over Script Generation',
};

export default function AISettings() {
  const {
    aiModel,
    setAiModel,
    aiProfiles = {},
    setAiProfiles,
    activeAiProfile = 'default',
    setActiveAiProfile,
    featureProfiles = {},
    setFeatureProfile,
    aiDevMode,
    setAiDevMode,
  } = useSettingsStore();

  const [availableVoices, setAvailableVoices] = useState([]);
  const [testPlaying, setTestPlaying] = useState(null);

  // Load browser voices (for Voice Settings)
  useEffect(() => {
    const loadVoices = () => {
      const voices = window.speechSynthesis?.getVoices?.() || [];
      setAvailableVoices(voices.map(v => ({ name: v.name, lang: v.lang, voiceURI: v.voiceURI })));
    };

    loadVoices();
    if (window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
    return () => {
      if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  const profiles = aiProfiles && Object.keys(aiProfiles).length > 0
    ? aiProfiles
    : {
        default: {
          name: 'Fast Confirmation (Default)',
          modelKey: 'grok-4.3-fast',
          reasoningEffort: 'none',
          includeKB: true,
          maxTokens: 400,
          voice: { voiceName: '', rate: 1.05, pitch: 1.0, volume: 0.85 },
          description: 'Optimized for low-latency binary decisions',
        },
        'deep-review': {
          name: 'Deep Review & Analysis',
          modelKey: 'grok-4.3-balanced',
          reasoningEffort: 'low',
          includeKB: true,
          maxTokens: 1200,
          voice: { voiceName: '', rate: 0.95, pitch: 1.02, volume: 0.9 },
          description: 'Higher quality for periodic reviews and session analysis',
        },
      };

  const currentActive = activeAiProfile || 'default';
  const activeProfile = profiles[currentActive] || profiles.default || DEFAULT_PROFILE;

  function saveProfiles(newProfiles) {
    setAiProfiles(newProfiles);
  }

  function updateActiveProfile(patch) {
    const updated = {
      ...profiles,
      [currentActive]: { ...activeProfile, ...patch },
    };
    saveProfiles(updated);
  }

  function addProfile() {
    const newKey = `profile-${Date.now().toString(36).slice(2, 8)}`;
    const newProfiles = {
      ...profiles,
      [newKey]: {
        ...DEFAULT_PROFILE,
        name: `Custom Profile ${Object.keys(profiles).length + 1}`,
      },
    };
    saveProfiles(newProfiles);
    setActiveAiProfile(newKey);
  }

  function duplicateProfile(key) {
    const source = profiles[key] || activeProfile;
    const newKey = `profile-${Date.now().toString(36).slice(2, 8)}`;
    const newProfiles = {
      ...profiles,
      [newKey]: {
        ...source,
        name: `${source.name} (copy)`,
      },
    };
    saveProfiles(newProfiles);
    setActiveAiProfile(newKey);
  }

  function deleteProfile(key) {
    if (Object.keys(profiles).length <= 1) return; // keep at least one
    const newProfiles = { ...profiles };
    delete newProfiles[key];
    saveProfiles(newProfiles);
    if (currentActive === key) {
      setActiveAiProfile(Object.keys(newProfiles)[0]);
    }
  }

  function setProfileForFeature(feature, profileKey) {
    setFeatureProfile(feature, profileKey);
  }

  // Voice test playback using browser Web Speech (Grok Voices placeholder ready)
  function testVoice(profileKey) {
    const prof = profiles[profileKey] || activeProfile;
    const voiceCfg = prof.voice || {};
    if (!window.speechSynthesis) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(
      `Testing ${prof.name}. This is a sample Grok advisory playback using the selected voice profile.`
    );

    const match = availableVoices.find(v => v.name === voiceCfg.voiceName);
    if (match) {
      // Find the actual SpeechSynthesisVoice object
      const synthVoices = window.speechSynthesis.getVoices();
      const realVoice = synthVoices.find(v => v.name === match.name);
      if (realVoice) utterance.voice = realVoice;
    }

    utterance.rate = voiceCfg.rate ?? 1.0;
    utterance.pitch = voiceCfg.pitch ?? 1.0;
    utterance.volume = voiceCfg.volume ?? 0.9;

    utterance.onend = () => setTestPlaying(null);
    setTestPlaying(profileKey);
    window.speechSynthesis.speak(utterance);
  }

  // Grok Native TTS test — calls backend proxy /api/ai/speak and plays the returned audio
  async function testGrokVoice(profileKey) {
    const prof = profiles[profileKey] || activeProfile;
    const voiceCfg = prof.voice || {};
    const voiceId = voiceCfg.voiceId || voiceCfg.customVoiceId || 'eve';
    const language = voiceCfg.language || 'en';
    const speed = voiceCfg.speed ?? 1.0;

    const textToSpeak = `Testing ${prof.name}. This is a sample using Grok Native TTS voice ${voiceId}. The integration supports speed control and professional delivery.`;

    setTestPlaying(profileKey);
    try {
      const res = await fetch('/api/ai/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToSpeak,
          voice_id: voiceId,
          language,
          speed,
          profile_key: profileKey,
        }),
      });
      if (!res.ok) throw new Error(`TTS error ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setTestPlaying(null);
      };
      await audio.play();
    } catch (err) {
      console.error('Grok TTS test failed:', err);
      // Fallback to browser utterance with a note
      if (window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(`Grok TTS test failed. Falling back. ${textToSpeak}`);
        utterance.onend = () => setTestPlaying(null);
        window.speechSynthesis.speak(utterance);
      } else {
        setTestPlaying(null);
      }
    }
  }

  function updateVoice(patch) {
    updateActiveProfile({
      voice: { ...(activeProfile.voice || {}), ...patch },
    });
  }

  const modelOptions = [
    { key: 'grok-4.3-fast', label: 'Grok 4.3 Fast (Non-Reasoning)' },
    { key: 'grok-4.3-balanced', label: 'Grok 4.3 Balanced (Light Reasoning)' },
    { key: 'grok-4.3', label: 'Grok 4.3 (Default)' },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="rounded-2xl border border-white/5 bg-[#1a1c22] p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ffb800] text-black">
            <Zap size={20} />
          </div>
          <div>
            <h3 className="text-lg font-black uppercase tracking-[1.5px] text-white">AI &amp; Voice Settings</h3>
            <p className="text-[11px] text-gray-500">Manage models, reasoning strategy, knowledge base usage, and voice playback. Add/remove profiles easily.</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-xl bg-white/[0.015] border border-white/5 p-4 text-[11px]">
            <div className="font-black uppercase tracking-widest text-[#ffb800] mb-1">Reasoning Strategy (Recommended)</div>
            <div className="text-gray-400 leading-snug">
              <strong>Fast (none)</strong>: Auto-Ghost confirmations, quick replies (speed &amp; low tokens).<br />
              <strong>Balanced (low)</strong>: Review loop, analysis, voice scripts (better reasoning, higher quality).
            </div>
          </div>
          <div className="rounded-xl bg-white/[0.015] border border-white/5 p-4 text-[11px]">
            <div className="font-black uppercase tracking-widest text-[#ffb800] mb-1">Current Global Default</div>
            <div className="text-white font-mono text-sm">{activeProfile.modelKey} — {activeProfile.reasoningEffort} reasoning</div>
            <button
              onClick={() => setAiModel(activeProfile.modelKey)}
              className="mt-2 text-[10px] px-3 py-1 rounded bg-[#ffb800] text-black font-black uppercase tracking-widest hover:bg-white"
            >
              Apply as Global aiModel
            </button>
          </div>
        </div>
      </div>

      {/* Profiles Manager */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-sm font-black uppercase tracking-[1px] text-white">AI Profiles</div>
            <div className="text-[10px] text-gray-500">Add, remove, duplicate. Each profile defines model, reasoning, KB, and voice.</div>
          </div>
          <button
            onClick={addProfile}
            className="flex items-center gap-2 rounded-lg bg-[#ffb800] px-4 py-2 text-[11px] font-black uppercase tracking-widest text-black hover:bg-white active:scale-[0.985]"
          >
            <Plus size={14} /> Add Profile
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(profiles).map(([key, prof]) => {
            const isActive = key === currentActive;
            const v = prof.voice || {};
            return (
              <div
                key={key}
                className={`rounded-2xl border p-5 transition-all ${isActive ? 'border-[#ffb800]/60 bg-[#1f222b] shadow' : 'border-white/5 bg-[#1a1c22] hover:border-white/20'}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <input
                      className="bg-transparent text-base font-black text-white outline-none w-full"
                      value={prof.name}
                      onChange={(e) => {
                        const updated = { ...profiles, [key]: { ...prof, name: e.target.value } };
                        saveProfiles(updated);
                      }}
                    />
                    <div className="text-[10px] text-gray-500 mt-0.5">{prof.description}</div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => setActiveAiProfile(key)} className={`text-[10px] px-2.5 py-1 rounded font-black uppercase tracking-widest ${isActive ? 'bg-[#ffb800] text-black' : 'bg-white/5 hover:bg-white/10'}`}>
                      {isActive ? 'ACTIVE' : 'USE'}
                    </button>
                    <button onClick={() => duplicateProfile(key)} title="Duplicate" className="p-1.5 text-gray-400 hover:text-white"><Copy size={14} /></button>
                    <button onClick={() => deleteProfile(key)} title="Delete" className="p-1.5 text-gray-400 hover:text-red-400 disabled:opacity-30" disabled={Object.keys(profiles).length === 1}><Trash2 size={14} /></button>
                  </div>
                </div>

                {/* Model + Reasoning */}
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-[9px] font-black uppercase tracking-widest text-gray-500 mb-1">MODEL</div>
                    <select
                      value={prof.modelKey}
                      onChange={(e) => {
                        const updated = { ...profiles, [key]: { ...prof, modelKey: e.target.value } };
                        saveProfiles(updated);
                      }}
                      className="w-full h-10 rounded-lg bg-[#25282f] px-3 text-xs font-black uppercase tracking-widest border border-white/5"
                    >
                      {modelOptions.map(opt => (
                        <option key={opt.key} value={opt.key}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <div className="text-[9px] font-black uppercase tracking-widest text-gray-500 mb-1">REASONING EFFORT</div>
                    <select
                      value={prof.reasoningEffort}
                      onChange={(e) => {
                        const updated = { ...profiles, [key]: { ...prof, reasoningEffort: e.target.value } };
                        saveProfiles(updated);
                      }}
                      className="w-full h-10 rounded-lg bg-[#25282f] px-3 text-xs font-black uppercase tracking-widest border border-white/5"
                    >
                      <option value="none">none — Fast (speed/token efficient)</option>
                      <option value="low">low — Light reasoning (quality)</option>
                    </select>
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-4 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!prof.includeKB}
                      onChange={(e) => {
                        const updated = { ...profiles, [key]: { ...prof, includeKB: e.target.checked } };
                        saveProfiles(updated);
                      }}
                    />
                    <span className="text-gray-400">Include KB Patterns</span>
                  </label>
                  <div className="flex items-center gap-2 text-gray-400">
                    Max tokens
                    <input
                      type="number"
                      className="w-20 h-8 rounded bg-[#25282f] px-2 text-xs border border-white/5"
                      value={prof.maxTokens || 600}
                      onChange={(e) => {
                        const updated = { ...profiles, [key]: { ...prof, maxTokens: parseInt(e.target.value) || 400 } };
                        saveProfiles(updated);
                      }}
                    />
                  </div>
                </div>

                {/* Voice Settings (core request location) */}
                <div className="mt-4 pt-4 border-t border-white/5">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-[#ffb800] mb-2">
                    <Volume2 size={13} /> VOICE SETTINGS — Grok Native TTS supported
                  </div>

                  {/* Voice Provider Toggle */}
                  <div className="mb-3">
                    <div className="text-[9px] text-gray-500 mb-1">Voice Provider</div>
                    <div className="flex rounded-lg bg-[#1a1c22] border border-white/5 p-1">
                      {['browser', 'grok'].map((prov) => (
                        <button
                          key={prov}
                          type="button"
                          onClick={() => {
                            const updated = {
                              ...profiles,
                              [key]: {
                                ...prof,
                                voice: { ...(prof.voice || {}), provider: prov },
                              },
                            };
                            saveProfiles(updated);
                          }}
                          className={`flex-1 rounded-md py-1.5 text-[10px] font-black uppercase tracking-widest transition-all ${
                            (prof.voice?.provider || 'browser') === prov
                              ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/30'
                              : 'text-gray-500 hover:text-white'
                          }`}
                        >
                          {prov === 'browser' ? 'Browser (zero cost)' : 'Grok Native TTS (professional)'}
                        </button>
                      ))}
                    </div>
                  </div>

                  { (prof.voice?.provider || 'browser') === 'grok' ? (
                    /* Grok Native TTS options */
                    <div className="space-y-3">
                      <div>
                        <div className="text-[9px] text-gray-500 mb-1">Grok Voice (built-in or custom voice_id)</div>
                        <select
                          value={prof.voice?.voiceId || 'eve'}
                          onChange={(e) => {
                            const updated = { ...profiles, [key]: { ...prof, voice: { ...(prof.voice || {}), voiceId: e.target.value } } };
                            saveProfiles(updated);
                          }}
                          className="w-full h-9 rounded bg-[#25282f] px-3 text-xs border border-white/5"
                        >
                          <option value="eve">eve — Energetic, upbeat (default)</option>
                          <option value="ara">ara — Warm, friendly</option>
                          <option value="rex">rex — Confident, professional</option>
                          <option value="sal">sal — Smooth, balanced</option>
                          <option value="leo">leo — Authoritative, strong</option>
                          <option value="custom">Custom voice_id…</option>
                        </select>
                        {prof.voice?.voiceId === 'custom' && (
                          <input
                            className="mt-2 w-full h-9 rounded bg-[#25282f] px-3 text-xs border border-white/5 font-mono"
                            placeholder="Enter custom voice_id (e.g. from console or /custom-voices)"
                            value={prof.voice?.customVoiceId || ''}
                            onChange={(e) => {
                              const updated = { ...profiles, [key]: { ...prof, voice: { ...(prof.voice || {}), customVoiceId: e.target.value, voiceId: e.target.value } } };
                              saveProfiles(updated);
                            }}
                          />
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <div className="text-[9px] text-gray-500 mb-1">Speed (0.7–1.5)</div>
                          <input
                            type="range"
                            min={0.7}
                            max={1.5}
                            step={0.05}
                            value={prof.voice?.speed ?? 1.0}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value);
                              const updated = { ...profiles, [key]: { ...prof, voice: { ...(prof.voice || {}), speed: val } } };
                              saveProfiles(updated);
                            }}
                            className="w-full accent-[#ffb800]"
                          />
                          <div className="text-right text-[10px] tabular-nums text-gray-400">{(prof.voice?.speed ?? 1.0).toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-[9px] text-gray-500 mb-1">Language</div>
                          <input
                            className="w-full h-9 rounded bg-[#25282f] px-3 text-xs border border-white/5"
                            value={prof.voice?.language || 'en'}
                            onChange={(e) => {
                              const updated = { ...profiles, [key]: { ...prof, voice: { ...(prof.voice || {}), language: e.target.value } } };
                              saveProfiles(updated);
                            }}
                          />
                        </div>
                      </div>

                      <button
                        onClick={() => testGrokVoice(key)}
                        disabled={testPlaying === key}
                        className="flex items-center gap-2 text-[11px] px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 disabled:opacity-60"
                      >
                        <Play size={13} /> {testPlaying === key ? 'Generating Grok TTS...' : 'Test Grok Native Voice'}
                      </button>
                      <div className="text-[9px] text-gray-500">Grok TTS uses server-side synthesis (billed per character). Proxy is handled by backend /api/ai/speak.</div>
                    </div>
                  ) : (
                    /* Browser voices (existing) */
                    <div className="space-y-3">
                      <div>
                        <div className="text-[9px] text-gray-500 mb-1">Browser Voice (System / Windows voices — zero token cost after text gen)</div>
                        <select
                          value={v.voiceName || ''}
                          onChange={(e) => {
                            const updated = { ...profiles, [key]: { ...prof, voice: { ...(prof.voice || {}), voiceName: e.target.value } } };
                            saveProfiles(updated);
                          }}
                          className="w-full h-9 rounded bg-[#25282f] px-3 text-xs border border-white/5"
                        >
                          <option value="">System Default Voice</option>
                          {availableVoices.map(vc => (
                            <option key={vc.voiceURI || vc.name} value={vc.name}>{vc.name} ({vc.lang})</option>
                          ))}
                        </select>
                      </div>

                      <div className="grid grid-cols-3 gap-3 text-xs">
                        {[
                          { label: 'Rate', field: 'rate', min: 0.5, max: 2, step: 0.05 },
                          { label: 'Pitch', field: 'pitch', min: 0.5, max: 2, step: 0.05 },
                          { label: 'Volume', field: 'volume', min: 0, max: 1, step: 0.05 },
                        ].map(({ label, field, min, max, step }) => (
                          <div key={field}>
                            <div className="text-[9px] text-gray-500 mb-1">{label}</div>
                            <input
                              type="range"
                              min={min}
                              max={max}
                              step={step}
                              value={v[field] ?? (field === 'volume' ? 0.9 : 1)}
                              onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                const updated = { ...profiles, [key]: { ...prof, voice: { ...(prof.voice || {}), [field]: val } } };
                                saveProfiles(updated);
                              }}
                              className="w-full accent-[#ffb800]"
                            />
                            <div className="text-right text-[10px] tabular-nums text-gray-400">{(v[field] ?? (field === 'volume' ? 0.9 : 1)).toFixed(2)}</div>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={() => testVoice(key)}
                        disabled={testPlaying === key}
                        className="flex items-center gap-2 text-[11px] px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 disabled:opacity-60"
                      >
                        <Play size={13} /> {testPlaying === key ? 'Playing...' : 'Test Browser Voice'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Assignments */}
      <div className="rounded-2xl border border-white/5 bg-[#1a1c22] p-6">
        <div className="text-sm font-black uppercase tracking-[1px] text-white mb-1">Feature Assignments</div>
        <div className="text-[10px] text-gray-500 mb-4">Choose which profile each part of the system should use. This enables optimal speed vs quality tradeoffs.</div>

        <div className="space-y-3">
          {Object.keys(FEATURE_LABELS).map((feat) => (
            <div key={feat} className="flex items-center gap-3 rounded-xl bg-white/[0.015] border border-white/5 px-4 py-3">
              <div className="w-52 text-xs font-medium text-gray-300">{FEATURE_LABELS[feat]}</div>
              <select
                value={featureProfiles[feat] || currentActive}
                onChange={(e) => setProfileForFeature(feat, e.target.value)}
                className="flex-1 h-10 rounded-lg bg-[#25282f] px-3 text-xs font-black uppercase tracking-widest border border-white/5"
              >
                {Object.entries(profiles).map(([k, p]) => (
                  <option key={k} value={k}>{p.name}</option>
                ))}
              </select>
            </div>
          ))}
        </div>

        <div className="mt-4 text-[10px] text-gray-500">
          Tip: Map "confirmation" to a fast non-reasoning profile. Map "review" and "analysis" to balanced reasoning profiles.
        </div>
      </div>

      {/* Developer Mode quick toggle (kept for compatibility) */}
      <div className="flex items-center justify-between rounded-xl bg-white/[0.02] border border-white/5 p-4">
        <div>
          <div className="font-black text-sm">Developer Mode</div>
          <div className="text-[10px] text-gray-500">Gives Grok platform/architecture context in chats.</div>
        </div>
        <button
          onClick={() => setAiDevMode(!aiDevMode)}
          className={`h-5 w-10 rounded-full transition-colors shrink-0 ${aiDevMode ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
        >
          <div className={`h-3 w-3 rounded-full bg-white transition-transform ${aiDevMode ? 'translate-x-6' : 'translate-x-1'}`} />
        </button>
      </div>
    </div>
  );
}
