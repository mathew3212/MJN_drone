'use client';

import { useDroneEntityStore } from '@/store/droneEntityStore';
import { getObstacleCount, getRiskScore } from '@/store/droneSelectors';

const SC = { ok: '#00FF88', warn: '#FFC857', fail: '#FF4D5A', info: '#00D4FF', dim: '#4A5A78' };

function PctBar({ value, color, height = 4 }: { value: number; color?: string; height?: number }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  const resolved = color || (pct > 80 ? SC.fail : pct > 60 ? SC.warn : SC.ok);
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ height, background: 'rgba(26,26,46,0.6)' }}>
      <div className="h-full rounded-full transition-all duration-300" style={{ width: `${pct}%`, background: resolved }} />
    </div>
  );
}

function MetricRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[7px] font-mono text-[#4A5A78] uppercase tracking-wider">{label}</span>
      <span className="text-[9px] font-mono font-bold tabular-nums" style={{ color: color || '#8A9BB5' }}>{value}</span>
    </div>
  );
}

export default function AIPanel() {
  const planner = useDroneEntityStore((s) => s.drone.planner);
  const prediction = useDroneEntityStore((s) => s.drone.prediction);
  const drone = useDroneEntityStore((s) => s.drone);
  const obstacleCount = getObstacleCount(drone);
  const riskScore = getRiskScore(drone);
  const predictedLandingZone = drone.overlays.safeLandingZones[0] ?? null;

  return (
    <div className="h-full overflow-y-auto px-3 py-2 space-y-3 font-mono select-none">
      <div className="flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-[#9D6CFF]" style={{ boxShadow: '0 0 6px #9D6CFF' }} />
        <span className="text-[10px] font-bold text-[#9D6CFF]">{planner.type}</span>
      </div>

      <div>
        <span className="text-[8px] uppercase tracking-wider text-[#6B7FA0]">Decision</span>
        <div className="text-[16px] font-bold" style={{ color: planner.decision === 'PROCEED' ? SC.ok : SC.warn }}>{planner.decision}</div>
        <div className="text-[8px] text-[#6B7FA0] mt-0.5">{planner.reason}</div>
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[8px] uppercase text-[#6B7FA0]">Confidence</span>
          <span className="text-[10px] font-bold" style={{ color: planner.confidence > 0.8 ? SC.ok : SC.warn }}>{(planner.confidence * 100).toFixed(0)}%</span>
        </div>
        <PctBar value={planner.confidence} height={5} />
      </div>

      <div className="grid grid-cols-2 gap-x-2">
        <MetricRow label="Obstacles" value={obstacleCount.toString()} color={obstacleCount > 5 ? SC.fail : SC.ok} />
        <MetricRow label="Collision Time" value={prediction.predictedCollisionTime ? `${prediction.predictedCollisionTime}s` : 'N/A'} color={prediction.predictedCollisionTime ? SC.warn : SC.dim} />
        <MetricRow label="Risk Score" value={`${(riskScore * 100).toFixed(0)}%`} color={riskScore < 0.2 ? SC.ok : riskScore < 0.5 ? SC.warn : SC.fail} />
        <MetricRow label="Success Prob" value={`${(prediction.missionSuccessProbability * 100).toFixed(0)}%`} color={prediction.missionSuccessProbability > 0.8 ? SC.ok : SC.warn} />
        <MetricRow label="Path Cost" value={prediction.pathCost.toFixed(2)} />
        <MetricRow label="Planner Latency" value={`${planner.inferenceTime}ms`} color={planner.inferenceTime < 20 ? SC.ok : SC.warn} />
        <MetricRow label="Inference Time" value={`${planner.inferenceTime}ms`} color={planner.inferenceTime < 15 ? SC.ok : SC.warn} />
        <MetricRow label="Prediction Acc" value={`${(prediction.predictionAccuracy * 100).toFixed(0)}%`} color={prediction.predictionAccuracy > 0.8 ? SC.ok : SC.warn} />
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <div className="flex items-center justify-between">
          <span className="text-[7px] uppercase text-[#4A5A78]">Risk Score</span>
          <span className="text-[8px] font-bold" style={{ color: riskScore < 0.2 ? SC.ok : SC.warn }}>{(riskScore * 100).toFixed(0)}%</span>
        </div>
        <PctBar value={riskScore} color={riskScore < 0.2 ? SC.ok : riskScore < 0.5 ? SC.warn : SC.fail} />
      </div>
      <div>
        <div className="flex items-center justify-between">
          <span className="text-[7px] uppercase text-[#4A5A78]">Success Probability</span>
          <span className="text-[8px] font-bold" style={{ color: prediction.missionSuccessProbability > 0.8 ? SC.ok : SC.warn }}>{(prediction.missionSuccessProbability * 100).toFixed(0)}%</span>
        </div>
        <PctBar value={prediction.missionSuccessProbability} color={prediction.missionSuccessProbability > 0.8 ? SC.ok : SC.warn} />
      </div>

      {predictedLandingZone && (
        <div className="bg-[rgba(26,26,46,0.3)] rounded px-2 py-1">
          <span className="text-[7px] uppercase text-[#4A5A78]">Predicted Landing Zone</span>
          <div className="text-[8px] text-[#8A9BB5] mt-0.5">
            {predictedLandingZone.latitude.toFixed(5)}, {predictedLandingZone.longitude.toFixed(5)}
          </div>
        </div>
      )}
    </div>
  );
}
