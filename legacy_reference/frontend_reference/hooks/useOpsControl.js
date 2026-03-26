/**
 * useOpsControl — Shared hook for Chrome/Collector ops control
 *
 * FIX ISSUE-7: Extracted from LoginScreen.jsx and TradingPlatform.jsx to
 * eliminate ~100 lines of duplicated code across both components.
 *
 * Usage:
 *   const {
 *     chromeStatus, collectorStatus, opsBusy,
 *     fetchOpsStatus, handleStartChrome, handleStopChrome,
 *     handleStartStream, handleStopStream
 *   } = useOpsControl(STREAM_URL);
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const BASE_POLL_MS = 5000;
const MAX_POLL_MS  = 30000;

export function useOpsControl(streamUrl) {
  const [chromeStatus, setChromeStatus] = useState('disconnected');
  const [collectorStatus, setCollectorStatus] = useState('disconnected');
  const [opsBusy, setOpsBusy] = useState({ chrome: false, stream: false });
  const [isBackendReachable, setIsBackendReachable] = useState(false);  // NEW

  const pollIntervalRef = useRef(BASE_POLL_MS);
  const timeoutRef = useRef(null);

  const fetchOpsStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${streamUrl}/ops/status`);
      if (response.data?.processes) {
        const { chrome, collector } = response.data.processes;
        setChromeStatus(chrome?.running ? 'connected' : 'disconnected');
        setCollectorStatus(collector?.running ? 'streaming' : 'disconnected');
      }
      setIsBackendReachable(true);
      pollIntervalRef.current = BASE_POLL_MS;  // reset on success
    } catch (err) {
      setIsBackendReachable(false);
      // Exponential backoff: double interval, cap at MAX_POLL_MS
      pollIntervalRef.current = Math.min(pollIntervalRef.current * 2, MAX_POLL_MS);
      console.debug('Ops status unavailable (next poll in %dms):', pollIntervalRef.current, err.response?.data?.detail || err.message);
    }
  }, [streamUrl]);

  // NEW: Centralized polling with exponential backoff
  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      await fetchOpsStatus();
      if (!cancelled) {
        timeoutRef.current = setTimeout(poll, pollIntervalRef.current);
      }
    };

    // Initial fetch + start polling loop
    poll();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [fetchOpsStatus]);

  const handleStartChrome = useCallback(async (setSuccess, setError) => {
    setOpsBusy(prev => ({ ...prev, chrome: true }));
    try {
      const response = await axios.post(`${streamUrl}/ops/chrome/start`, { url: null });
      const { ok, status } = response.data;
      if (ok) {
        setChromeStatus('connected');
        setSuccess?.(status === 'already_running' ? 'Chrome already running' : 'Chrome started');
      } else {
        setError?.(response.data.user_message || 'Failed to start Chrome');
      }
    } catch (err) {
      setError?.(err.response?.data?.detail?.user_message || err.response?.data?.detail?.error_message || 'Failed to start Chrome');
    } finally {
      setOpsBusy(prev => ({ ...prev, chrome: false }));
    }
  }, [streamUrl]);

  const handleStopChrome = useCallback(async (setSuccess, setError) => {
    setOpsBusy(prev => ({ ...prev, chrome: true }));
    try {
      const response = await axios.post(`${streamUrl}/ops/chrome/stop`);
      const { ok, status } = response.data;
      if (ok) {
        setChromeStatus('disconnected');
        setSuccess?.(status === 'already_stopped' ? 'Chrome not running' : 'Chrome stopped');
      } else {
        setError?.(response.data.user_message || 'Failed to stop Chrome');
      }
    } catch (err) {
      setError?.(err.response?.data?.detail?.user_message || err.response?.data?.detail?.error_message || 'Failed to stop Chrome');
    } finally {
      setOpsBusy(prev => ({ ...prev, chrome: false }));
    }
  }, [streamUrl]);

  const handleStartStream = useCallback(async (setSuccess, setError) => {
    setOpsBusy(prev => ({ ...prev, stream: true }));
    try {
      const response = await axios.post(`${streamUrl}/ops/stream/start`);
      const { ok, status } = response.data;
      if (ok) {
        setCollectorStatus('streaming');
        setSuccess?.(status === 'already_running' ? 'Collector already running' : 'Collector started');
      } else {
        setError?.(response.data.user_message || 'Failed to start Collector');
      }
    } catch (err) {
      setError?.(err.response?.data?.detail?.user_message || err.response?.data?.detail?.error_message || 'Failed to start Collector');
    } finally {
      setOpsBusy(prev => ({ ...prev, stream: false }));
    }
  }, [streamUrl]);

  const handleStopStream = useCallback(async (setSuccess, setError) => {
    setOpsBusy(prev => ({ ...prev, stream: true }));
    try {
      const response = await axios.post(`${streamUrl}/ops/stream/stop`);
      const { ok, status } = response.data;
      if (ok) {
        setCollectorStatus('disconnected');
        setSuccess?.(status === 'already_stopped' ? 'Collector not running' : 'Collector stopped');
      } else {
        setError?.(response.data.user_message || 'Failed to stop Collector');
      }
    } catch (err) {
      setError?.(err.response?.data?.detail?.user_message || err.response?.data?.detail?.error_message || 'Failed to stop Collector');
    } finally {
      setOpsBusy(prev => ({ ...prev, stream: false }));
    }
  }, [streamUrl]);

  return {
    chromeStatus,
    collectorStatus,
    opsBusy,
    isBackendReachable,
    fetchOpsStatus,
    handleStartChrome,
    handleStopChrome,
    handleStartStream,
    handleStopStream,
  };
}
