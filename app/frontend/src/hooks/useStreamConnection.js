/**
 * Global Socket.IO stream wiring for live tick data and asset focus events.
 */
import { useEffect, useRef } from 'react';
import { initSocket } from '../api/socketClient.js';
import { updateAllowedAssets, watchAssets } from '../api/streamApi.js';
import { useAssetStore } from '../stores/useAssetStore.js';
import { useStreamStore } from '../stores/useStreamStore.js';

const MAX_TICKS = 300;
const CONFIDENCE_BY_LEVEL = {
  HIGH: 85,
  MEDIUM: 65,
  LOW: 40,
};

function normalizeConfidence(payloadConfidence, score) {
  const numericConfidence = Number(payloadConfidence);
  if (Number.isFinite(numericConfidence)) {
    return Math.max(0, Math.min(100, numericConfidence <= 1 ? numericConfidence * 100 : numericConfidence));
  }

  const numericScore = Number(score);
  if (Number.isFinite(numericScore) && numericScore > 0) {
    return Math.max(0, Math.min(100, numericScore));
  }

  const level = typeof payloadConfidence === 'string' ? payloadConfidence.trim().toUpperCase() : '';
  if (level in CONFIDENCE_BY_LEVEL) {
    return CONFIDENCE_BY_LEVEL[level];
  }

  return 0;
}

export function useStreamConnection() {
  const selectedAsset = useAssetStore((state) => state.selectedAsset);
  const multiChartAssets = useAssetStore((state) => state.multiChartAssets);
  const clearAsset = useStreamStore((state) => state.clearAsset);
  const batchUpdate = useStreamStore((state) => state.batchUpdate);
  const setWarmup = useStreamStore((state) => state.setWarmup);
  const setIsStreaming = useStreamStore((state) => state.setIsStreaming);

  const tickBufferRef = useRef({});
  const pendingUpdatesRef = useRef({});
  const rafIdRef = useRef(null);

  useEffect(() => {
    const socket = initSocket();

    const processBatch = () => {
      const updates = pendingUpdatesRef.current;
      const entries = Object.entries(updates);
      if (entries.length > 0) {
        const resolved = {};
        for (const [asset, data] of entries) {
           resolved[asset] = {
             ...data,
             ticks: [...(tickBufferRef.current[asset] || [])],
           };
        }
        batchUpdate(resolved);
        pendingUpdatesRef.current = {};
      }
      rafIdRef.current = null;
    };

    const handleMarketData = (payload = {}) => {
      const asset = typeof payload.asset === 'string' ? payload.asset.trim() : '';
      if (!asset) return;

      const price = Number(payload.price);
      if (!Number.isFinite(price)) return;

      const timestamp = Number(payload.timestamp ?? Date.now() / 1000);
      const bufferMap = tickBufferRef.current;
      const assetBuffer = Array.isArray(bufferMap[asset]) ? bufferMap[asset] : [];

      assetBuffer.push({ price, timestamp });
      if (assetBuffer.length > MAX_TICKS) {
        assetBuffer.splice(0, assetBuffer.length - MAX_TICKS);
      }

      bufferMap[asset] = assetBuffer;

      const recommended = typeof payload.recommended === 'string' ? payload.recommended.trim().toLowerCase() : '';
      const normalizedDirection = recommended === 'call' || recommended === 'put' ? recommended : null;
      const score = Number(payload.oteo_score);
      const confidence = normalizeConfidence(payload.confidence, score);

      const signal = {
        direction: normalizedDirection,
        confidence,
        score: Number.isFinite(score) ? score : confidence,
        label: typeof payload.recommended === 'string' ? payload.recommended : null,
        velocity: Number(payload.velocity ?? 0),
        pressure_pct: Number(payload.pressure_pct ?? 0),
        z_score: Number(payload.z_score ?? 0),
        maturity: Number(payload.maturity ?? 0),
        slow_velocity: Number(payload.slow_velocity ?? 0),
        trend_aligned: Boolean(payload.trend_aligned),
        actionable: Boolean(payload.actionable),
        stretch_alignment: Number(payload.stretch_alignment ?? 0),
        base_oteo_score: Number(payload.base_oteo_score ?? score ?? 0),
        base_confidence: payload.base_confidence ?? null,
        base_actionable: Boolean(payload.base_actionable),
        level2_enabled: Boolean(payload.level2_enabled),
        level2_score_adjustment: Number(payload.level2_score_adjustment ?? 0),
        level2_suppressed_reason: payload.level2_suppressed_reason ?? null,
        marketContext: payload.market_context ?? null,
        regime: payload.market_context?.adx_regime ?? null,
      };

      const manipulationPayload = payload.manipulation;
      let manipulation = null;
      if (manipulationPayload && typeof manipulationPayload === 'object') {
        const keys = Object.keys(manipulationPayload);
        manipulation = {
          detected: keys.length > 0,
          type: keys[0] ?? null,
          flags: manipulationPayload,
        };
      }

      // Queue for batch update
      pendingUpdatesRef.current[asset] = { signal, manipulation };

      if (!rafIdRef.current) {
        rafIdRef.current = requestAnimationFrame(processBatch);
      }

      if (!useStreamStore.getState().isStreaming) {
        setIsStreaming(true);
      }
    };

    const handleWarmupStatus = (payload = {}) => {
      const asset = typeof payload.asset === 'string' ? payload.asset.trim() : '';
      if (!asset) return;

      setWarmup(asset, !Boolean(payload.ready));
    };

    const handleDisconnect = () => {
      setIsStreaming(false);
    };

    socket.on('market_data', handleMarketData);
    socket.on('warmup_status', handleWarmupStatus);
    socket.on('disconnect', handleDisconnect);

    return () => {
      socket.off('market_data', handleMarketData);
      socket.off('warmup_status', handleWarmupStatus);
      socket.off('disconnect', handleDisconnect);
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, [setIsStreaming, setWarmup, batchUpdate]);

  useEffect(() => {
    if (!selectedAsset) return;

    const dedupedAssets = [
      selectedAsset,
      ...((Array.isArray(multiChartAssets) ? multiChartAssets : []).filter((asset) => asset && asset !== selectedAsset)),
    ].slice(0, 9);

    const allowedAssets = new Set(dedupedAssets);
    const bufferMap = tickBufferRef.current;

    for (const asset of Object.keys(bufferMap)) {
      if (!allowedAssets.has(asset)) {
        delete bufferMap[asset];
        clearAsset(asset);
      }
    }

    initSocket();
    setWarmup(selectedAsset, true);
    watchAssets(dedupedAssets);
    updateAllowedAssets(dedupedAssets);
  }, [clearAsset, multiChartAssets, selectedAsset, setWarmup]);
}
