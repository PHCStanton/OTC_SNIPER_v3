/**
 * AI store — advisory chat, image analysis, and UI state.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { analyzeImageWithAI, chatWithAI, getAIStatus } from '../api/aiApi.js';
import { useSettingsStore } from './useSettingsStore.js';
import { useRiskStore } from './useRiskStore.js';
import { useOpsStore } from './useOpsStore.js';

const MAX_MESSAGES = 20;

function normalizeMessage(message) {
  return {
    id: message.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role: message.role,
    content: String(message.content || '').trim(),
    createdAt: message.createdAt || new Date().toISOString(),
    kind: message.kind || 'text',
  };
}

function trimMessages(messages) {
  return messages.slice(-MAX_MESSAGES);
}

function buildContext() {
  const risk = useRiskStore.getState();
  const ops = useOpsStore.getState();

  return {
    balance: ops.balance || risk.currentBalance || null,
    accountType: ops.accountType || null,
    sessionPnl: risk.sessionPnl,
    winRate: risk.winRate,
    currentStreak: risk.currentStreak,
    totalTrades: risk.totalTrades,
    asset: null,
  };
}

export const useAIStore = create()(
  persist(
    (set, get) => ({
      messages: [],
      loading: false,
      status: { enabled: false, provider: 'xai', model: '', has_api_key: false, reason: '' },
      error: null,
      draft: '',
      imagePreview: null,

      loadStatus: async () => {
        const status = await getAIStatus();
        set({ status, error: null });
        return status;
      },

      setDraft: (draft) => set({ draft }),
      setImagePreview: (imagePreview) => set({ imagePreview }),
      clearImagePreview: () => set({ imagePreview: null }),
      clearMessages: () => set({ messages: [], error: null }),
      setError: (error) => set({ error }),

      setStatus: (status) => set({ status }),

      sendMessage: async ({ text, context, model } = {}) => {
        const content = String(text || get().draft || '').trim();
        if (!content) {
          throw new Error('Message cannot be empty.');
        }

        const settings = useSettingsStore.getState();
        const requestContext = context || buildContext();
        const userMessage = normalizeMessage({ role: 'user', content });
        const nextMessages = trimMessages([...get().messages, userMessage]);

        set({ messages: nextMessages, loading: true, error: null, draft: '' });

        try {
          const response = await chatWithAI({
            messages: nextMessages.map(({ role, content }) => ({ role, content })),
            context: requestContext,
            model: model || settings.aiModel,
          });

          const assistantMessage = normalizeMessage({ role: 'assistant', content: response.response, kind: 'text' });
          set((state) => ({
            messages: trimMessages([...state.messages, assistantMessage]),
            loading: false,
          }));
          return response;
        } catch (error) {
          set({ loading: false, error: error.message });
          throw error;
        }
      },

      analyzeImage: async ({ imageBase64, prompt, context, mimeType, model } = {}) => {
        if (!imageBase64) {
          throw new Error('Image is required for analysis.');
        }

        const settings = useSettingsStore.getState();
        set({ loading: true, error: null });

        try {
          const response = await analyzeImageWithAI({
            image_base64: imageBase64,
            prompt,
            context: context || buildContext(),
            mime_type: mimeType,
            model: model || settings.aiModel,
          });

          const assistantMessage = normalizeMessage({ role: 'assistant', content: response.analysis, kind: 'image' });
          set((state) => ({
            messages: trimMessages([...state.messages, assistantMessage]),
            loading: false,
          }));
          return response;
        } catch (error) {
          set({ loading: false, error: error.message });
          throw error;
        }
      },
    }),
    {
      name: 'otc-sniper-ai-storage',
      partialize: (state) => ({ messages: trimMessages(state.messages), draft: state.draft }),
    }
  )
);