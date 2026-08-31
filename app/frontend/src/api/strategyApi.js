import { request } from './httpClient.js';

export const updateRuntimeStrategyConfig = (payload) =>
  request('POST', '/strategy/runtime-config', payload);

export const getRuntimeStrategyConfig = () =>
  request('GET', '/strategy/runtime-config');

export const startCalibration = (payload) =>
  request('POST', '/strategy/calibration/start', payload);

export const stopCalibration = () =>
  request('POST', '/strategy/calibration/stop');

export const getCalibrationStatus = () =>
  request('GET', '/strategy/calibration/status');
