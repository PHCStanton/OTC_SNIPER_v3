import { request } from './httpClient.js';

export const updateRuntimeStrategyConfig = (payload) =>
  request('POST', '/strategy/runtime-config', payload);

export const getRuntimeStrategyConfig = () =>
  request('GET', '/strategy/runtime-config');
