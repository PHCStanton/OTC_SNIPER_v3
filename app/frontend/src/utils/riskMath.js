export function normalizeNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function computeRiskMetrics({
  startBalance,
  payoutPercentage,
  riskPercentPerTrade,
  drawdownPercent,
  riskRewardRatio,
  useFixedAmount,
  fixedRiskAmount,
  currentSessionPnl = 0,
}) {
  const safeStartBalance = Math.max(0, normalizeNumber(startBalance));
  const safePayoutPercentage = Math.max(0, normalizeNumber(payoutPercentage));
  const safeRiskPercent = Math.max(0, normalizeNumber(riskPercentPerTrade));
  const safeDrawdownPercent = Math.max(0, normalizeNumber(drawdownPercent));
  const safeRiskRewardRatio = Math.max(0, normalizeNumber(riskRewardRatio));
  const safeFixedRiskAmount = Math.max(0, normalizeNumber(fixedRiskAmount));

  const riskPerTrade = useFixedAmount
    ? safeFixedRiskAmount
    : safeStartBalance * (safeRiskPercent / 100);

  const drawdownAmount = safeStartBalance * (safeDrawdownPercent / 100);
  const takeProfitAmount = drawdownAmount * safeRiskRewardRatio;
  const takeProfitTarget = safeStartBalance + takeProfitAmount;
  const maxDrawdownLimit = Math.max(0, safeStartBalance - drawdownAmount);
  const currentBalance = safeStartBalance + normalizeNumber(currentSessionPnl);
  const distanceToTarget = Math.max(0, takeProfitTarget - currentBalance);
  const distanceToLimit = Math.max(0, currentBalance - maxDrawdownLimit);
  const minimumWinRate = safePayoutPercentage > 0
    ? 100 / (1 + (safePayoutPercentage / 100))
    : 0;

  return {
    startBalance: safeStartBalance,
    payoutPercentage: safePayoutPercentage,
    riskPerTrade,
    drawdownAmount,
    takeProfitAmount,
    takeProfitTarget,
    maxDrawdownLimit,
    currentBalance,
    distanceToTarget,
    distanceToLimit,
    minimumWinRate,
  };
}