/**
 * HTTP client for Phase 8 AI endpoints.
 */
import { request } from './httpClient.js';

export const getAIStatus = () => request('GET', '/ai/status');

export const chatWithAI = (payload) => request('POST', '/ai/chat', payload);

export const analyzeImageWithAI = (payload) => request('POST', '/ai/analyze-image', payload);