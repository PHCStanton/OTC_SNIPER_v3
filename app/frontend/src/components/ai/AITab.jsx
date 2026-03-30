/**
 * AITab — advisory-only chat and chart screenshot analysis panel.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, ImagePlus, Loader2, RefreshCcw, Send, Trash2, Upload } from 'lucide-react';
import { useAIStore } from '../../stores/useAIStore.js';

function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`rounded-2xl border px-3 py-2 text-xs leading-5 ${isUser ? 'border-[#f5df19]/20 bg-[#f5df19]/10 text-[#f5df19]' : 'border-white/5 bg-[#0f1419] text-[#d7dde0]'}`}>
      <div className="mb-1 flex items-center justify-between gap-2 text-[10px] uppercase tracking-[0.16em] opacity-70">
        <span>{isUser ? 'You' : 'AI'}</span>
        <span>{new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  );
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read image file.'));
    reader.readAsDataURL(file);
  });
}

export default function AITab({ aiStatus, statusLoading, onStatusRefresh }) {
  const { messages, loading, error, draft, setDraft, clearMessages, sendMessage, analyzeImage, imagePreview, setImagePreview, clearImagePreview, setError } = useAIStore();
  const [localPrompt, setLocalPrompt] = useState('Analyze this chart screenshot for structure, trend, support, and risk context.');
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  const enabled = aiStatus?.enabled;
  const disabledMessage = useMemo(() => aiStatus?.reason || 'AI is currently unavailable.', [aiStatus]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    if (aiStatus?.model && !draft) {
      // no-op; keep draft untouched, but this effect ensures a rerender hook for status refresh
    }
  }, [aiStatus, draft]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!enabled) return;
    try {
      await sendMessage({ text: draft });
    } catch (submitError) {
      setError(submitError.message);
    }
  }

  async function handleImageSelected(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      clearImagePreview();
      throw new Error('Only PNG and JPEG images are supported.');
    }

    if (file.size > 20 * 1024 * 1024) {
      clearImagePreview();
      throw new Error('Image exceeds 20 MB limit.');
    }

    const dataUrl = await fileToDataUrl(file);
    setImagePreview(dataUrl);
  }

  async function handleAnalyze() {
    if (!imagePreview || !enabled) return;
    try {
      await analyzeImage({
        imageBase64: imagePreview,
        prompt: localPrompt,
        mimeType: imagePreview.startsWith('data:image/jpeg') ? 'image/jpeg' : 'image/png',
      });
    } catch (analysisError) {
      setError(analysisError.message);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 rounded-2xl border border-white/5 bg-[#0f1419] p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <Bot size={14} className="text-[#f5df19]" />
            <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300">AI Assistant</h3>
          </div>
          <p className="mt-1 text-[10px] leading-4 text-slate-500">
            Advisory only. No trades or settings changes.
          </p>
        </div>

        <button
          type="button"
          onClick={onStatusRefresh}
          className="rounded-lg border border-white/5 bg-white/5 p-1.5 text-slate-400 transition-colors hover:text-slate-200"
          title="Refresh AI status"
        >
          {statusLoading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCcw size={12} />}
        </button>
      </div>

      <div className={`rounded-xl border px-3 py-2 text-[10px] ${enabled ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300' : 'border-amber-400/20 bg-amber-400/10 text-amber-300'}`}>
        <div className="flex items-center justify-between gap-2">
          <span>{enabled ? `Ready • ${aiStatus.model}` : 'AI disabled'}</span>
          <span className="uppercase tracking-[0.16em] opacity-70">{aiStatus.provider}</span>
        </div>
        {!enabled && <p className="mt-1 leading-4 opacity-80">{disabledMessage}</p>}
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-3 py-5 text-center text-[11px] leading-5 text-slate-500">
            Start a chat or upload a chart screenshot for contextual analysis.
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>

      {error && <p className="rounded-xl border border-red-400/20 bg-red-400/10 px-3 py-2 text-[10px] text-red-300">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={!enabled || loading}
          rows={3}
          placeholder="Ask about the market, a trade setup, or a chart pattern..."
          className="w-full resize-none rounded-2xl border border-white/10 bg-[#151a22] px-3 py-2 text-[11px] text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-[#f5df19] disabled:opacity-60"
        />

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            disabled={!enabled || loading || !draft.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#f5df19] px-3 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-black transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
            Send
          </button>

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={!enabled || loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-300 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Upload size={12} />
            Upload
          </button>

          <button
            type="button"
            onClick={clearMessages}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 transition-colors hover:bg-white/10"
          >
            <Trash2 size={12} />
            Clear
          </button>

          <input ref={fileInputRef} type="file" accept="image/png,image/jpeg" className="hidden" onChange={async (event) => {
            try {
              await handleImageSelected(event);
            } catch (uploadError) {
              setError(uploadError.message);
            } finally {
              event.target.value = '';
            }
          }} />
        </div>
      </form>

      {imagePreview && (
        <div className="space-y-2 rounded-2xl border border-white/5 bg-[#151a22] p-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-slate-400">
              <ImagePlus size={12} />
              Screenshot ready
            </div>
            <button type="button" onClick={clearImagePreview} className="text-[10px] text-slate-500 hover:text-slate-300">Remove</button>
          </div>

          <img src={imagePreview} alt="AI upload preview" className="max-h-36 w-full rounded-xl object-contain" />

          <textarea
            value={localPrompt}
            onChange={(event) => setLocalPrompt(event.target.value)}
            rows={2}
            className="w-full resize-none rounded-xl border border-white/10 bg-[#0f1419] px-3 py-2 text-[11px] text-slate-100 outline-none placeholder:text-slate-500 focus:border-[#f5df19]"
          />

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!enabled || loading}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-black transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
            Analyze image
          </button>
        </div>
      )}
    </div>
  );
}