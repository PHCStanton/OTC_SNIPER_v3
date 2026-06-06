export function toTitleCase(value) {
  return String(value ?? '')
    .replaceAll('_', ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getManipulationLabels(manipulation) {
  if (!manipulation || typeof manipulation !== 'object') return [];

  const flags = manipulation.flags && typeof manipulation.flags === 'object'
    ? manipulation.flags
    : manipulation;

  const labels = Object.entries(flags)
    .filter(([, active]) => Boolean(active))
    .map(([key]) => {
      if (key === 'push_snap') return 'Push & Snap';
      if (key === 'pinning') return 'Pinning';
      return toTitleCase(key);
    });

  if (labels.length > 0) return labels;
  if (manipulation.type) return [toTitleCase(manipulation.type)];
  return [];
}

export function getConfluenceItems(signal, direction) {
  if (!signal || typeof signal !== 'object') return [];

  const marketContext = signal.market_context && typeof signal.market_context === 'object'
    ? signal.market_context
    : {};

  const items = [];
  const velocity = Number(signal.velocity ?? 0);
  const pressurePct = Number(signal.pressure_pct ?? 0);
  const zScore = Number(signal.z_score ?? 0);
  const maturity = Number(signal.maturity ?? 0);
  const level2Adjustment = Number(signal.level2_score_adjustment ?? 0);

  if (direction === 'call' && velocity < 0) items.push('Sell Exhaustion');
  if (direction === 'put' && velocity > 0) items.push('Buy Exhaustion');
  if (Math.abs(zScore) >= 0.35) items.push(`Z-Score ${zScore > 0 ? 'High' : 'Low'}`);
  if (Math.abs(pressurePct) >= 12) items.push(`Pressure ${pressurePct > 0 ? 'Up' : 'Down'}`);
  if (signal.trend_aligned) items.push('Trend Aligned');
  if (direction === 'call' && marketContext.support_alignment) items.push('Support Align');
  if (direction === 'put' && marketContext.resistance_alignment) items.push('Resistance Align');
  if (marketContext.reversal_friendly) items.push('Reversal Friendly');
  if (marketContext.cci_state) items.push(`CCI ${toTitleCase(marketContext.cci_state)}`);
  if (marketContext.adx_regime) items.push(`ADX ${toTitleCase(marketContext.adx_regime)}`);
  if (maturity >= 0.5) items.push(`Maturity ${Math.round(maturity * 100)}%`);
  if (signal.level2_enabled && level2Adjustment !== 0) items.push(`L2 ${level2Adjustment > 0 ? '+' : ''}${level2Adjustment.toFixed(1)}`);
  if (signal.actionable) items.push('Actionable');

  return items.slice(0, 8);
}

export function extractNumericSeries(ticks) {
  if (!Array.isArray(ticks)) return [];

  const series = [];
  for (const tick of ticks) {
    if (typeof tick === 'number' && Number.isFinite(tick)) {
      series.push(tick);
      continue;
    }

    if (!tick || typeof tick !== 'object') continue;

    const candidates = [tick.price, tick.value, tick.close, tick.last, tick.mid, tick.bid, tick.ask];
    let parsed = null;

    for (const candidate of candidates) {
      const numeric = Number(candidate);
      if (Number.isFinite(numeric)) {
        parsed = numeric;
        break;
      }
    }

    if (parsed !== null) series.push(parsed);
  }

  return series;
}

export function buildChartPoints(series, width = 1000, height = 360, padding = 28, paddingRight = null) {
  if (!Array.isArray(series) || series.length === 0) return [];

  let min = series[0];
  let max = series[0];
  for (let i = 1; i < series.length; i++) {
    if (series[i] < min) min = series[i];
    if (series[i] > max) max = series[i];
  }
  const range = max - min || 1;
  const padRight = paddingRight !== null ? paddingRight : padding;
  const usableWidth = Math.max(1, width - padding - padRight);
  const usableHeight = Math.max(1, height - padding * 2);

  return series.map((value, index) => {
    const x = series.length === 1
      ? padding + usableWidth / 2
      : padding + (usableWidth * index) / (series.length - 1);
    const normalized = (value - min) / range;
    const y = padding + usableHeight - normalized * usableHeight;
    return { x, y, value };
  });
}

export function pointsToPath(points) {
  if (!Array.isArray(points) || points.length === 0) return '';
  return points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(' ');
}

export function formatPrice(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';

  const abs = Math.abs(numeric);
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 5 : 6;
  return numeric.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatAssetLabel(asset) {
  if (typeof asset !== 'string' || asset.length === 0) return '—';
  return asset.replace(/_otc$/i, ' OTC').replace(/_/g, '/');
}

export function getSignalDirection(signal) {
  if (!signal || typeof signal !== 'object') return null;

  const raw = [signal.direction, signal.side, signal.bias, signal.action]
    .find((value) => typeof value === 'string' && value.length > 0);

  if (!raw) return null;

  const normalized = raw.toLowerCase();
  if (normalized === 'call' || normalized === 'buy' || normalized === 'up' || normalized === 'long') return 'call';
  if (normalized === 'put' || normalized === 'sell' || normalized === 'down' || normalized === 'short') return 'put';
  return null;
}

export function getSignalLabel(signal) {
  if (!signal || typeof signal !== 'object') return 'WARMING UP';

  const direction = getSignalDirection(signal);
  if (direction === 'call') return 'STRONG BUY';
  if (direction === 'put') return 'STRONG SELL';

  if (typeof signal.recommended === 'string' && signal.recommended.length > 0) {
    return signal.recommended.toUpperCase();
  }
  if (typeof signal.label === 'string' && signal.label.length > 0) return signal.label.toUpperCase();
  if (typeof signal.status === 'string' && signal.status.length > 0) return signal.status.toUpperCase();
  return 'NEUTRAL';
}

export function getSignalConfidence(signal) {
  if (!signal || typeof signal !== 'object') return 0;

  const candidates = [signal.confidence, signal.oteo_score, signal.score, signal.strength, signal.ratio, signal.probability];
  for (const candidate of candidates) {
    const numeric = Number(candidate);
    if (Number.isFinite(numeric)) {
      const value = numeric <= 1 ? numeric * 100 : numeric;
      return Math.max(0, Math.min(100, value));
    }
  }

  return 0;
}

export function getTrendPercent(series) {
  if (!Array.isArray(series) || series.length < 2) return 0;

  const first = Number(series[0]);
  const last = Number(series[series.length - 1]);
  if (!Number.isFinite(first) || !Number.isFinite(last) || first === 0) return 0;

  return ((last - first) / Math.abs(first)) * 100;
}
