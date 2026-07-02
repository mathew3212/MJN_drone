'use client';

import { useDroneEntityStore } from '@/store/droneEntityStore';
import {
  formatDuration,
  getCurrentWaypoint,
  getEmergencyStatus,
  getMissionName,
  getObjectiveLabel,
  getObstacleCount,
  getRemainingWaypoints,
  getReturnHomeActive,
  getRiskScore,
} from '@/store/droneSelectors';

const SC = {
  ok: '#00FF88',
  warn: '#FFC857',
  fail: '#FF4D5A',
  info: '#00D4FF',
  purple: '#9D6CFF',
  dim: '#4A5A78',
};

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
      <span className="text-[8px] font-mono text-[#4A5A78] uppercase tracking-wider">{label}</span>
      <span className="text-[10px] font-mono font-bold tabular-nums" style={{ color: color || '#8A9BB5' }}>{value}</span>
    </div>
  );
}

export default function RightPanel() {
  const drone = useDroneEntityStore((s) => s.drone);
  const currentWaypoint = getCurrentWaypoint(drone);
  const remainingWaypoints = getRemainingWaypoints(drone);
  const obstacleCount = getObstacleCount(drone);
  const riskScore = getRiskScore(drone);
  const emergencyStatus = getEmergencyStatus(drone);
  const returnHomeActive = getReturnHomeActive(drone);

  const confidenceColor = drone.planner.confidence > 0.8 ? SC.ok : drone.planner.confidence > 0.5 ? SC.warn : SC.fail;
  const riskColor = riskScore < 0.2 ? SC.ok : riskScore < 0.5 ? SC.warn : SC.fail;
  const emergencyColor = emergencyStatus === 'NONE' ? SC.ok : emergencyStatus === 'LOW_BATTERY' ? SC.warn : SC.fail;

  return (
    <div className="h-full overflow-y-auto px-3 py-2 space-y-3 font-mono select-none">
      <div>
        <div className="flex items-center justify-between">
          <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Mission</span>
          <span className="text-[8px] text-[#4A5A78]">{drone.missionId}</span>
        </div>
        <div className="text-[10px] text-[#8A9BB5] mb-1">{getMissionName(drone)}</div>

        <div className="flex items-center gap-2 mb-1">
          <span className="text-[20px] font-bold" style={{ color: SC.info }}>{drone.missionProgress.toFixed(1)}</span>
          <span className="text-[9px] text-[#4A5A78]">%</span>
        </div>
        <PctBar value={drone.missionProgress / 100} color={SC.info} height={6} />

        <MetricRow label="ETA" value={drone.missionEta} color={SC.info} />
        <MetricRow label="Waypoint" value={currentWaypoint ? `${drone.currentWaypointIndex + 1} / ${drone.waypoints.length}` : `${drone.waypoints.length} / ${drone.waypoints.length}`} color={SC.purple} />
        <MetricRow label="Distance Remaining" value={`${drone.telemetry.distanceToTarget.toFixed(0)} m`} />
        <MetricRow label="Time Remaining" value={formatDuration(drone.telemetry.timeToTarget)} />
        <MetricRow label="Objective" value={getObjectiveLabel(drone)} color={SC.info} />
        <MetricRow label="Remaining WPs" value={remainingWaypoints.length.toString()} />
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Planner</span>
          <span className="text-[8px] text-[#9D6CFF]">{drone.planner.type}</span>
        </div>
        <div className="text-[14px] font-bold" style={{ color: drone.planner.decision === 'PROCEED' ? SC.ok : SC.warn }}>{drone.planner.decision}</div>
        <div className="text-[8px] text-[#6B7FA0] mb-1">{drone.planner.reason}</div>

        <div className="space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="text-[7px] text-[#4A5A78] uppercase">Confidence</span>
            <span className="text-[9px] font-bold" style={{ color: confidenceColor }}>{(drone.planner.confidence * 100).toFixed(0)}%</span>
          </div>
          <PctBar value={drone.planner.confidence} color={confidenceColor} height={3} />

          <div className="flex items-center justify-between">
            <span className="text-[7px] text-[#4A5A78] uppercase">Prediction</span>
            <span className="text-[9px] text-[#8A9BB5]">{(drone.planner.predictionConfidence * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[7px] text-[#4A5A78] uppercase">Localization</span>
            <span className="text-[9px] text-[#8A9BB5]">{(drone.planner.localizationQuality * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Risk Assessment</span>
        <MetricRow label="Obstacles" value={obstacleCount.toString()} color={obstacleCount > 5 ? SC.fail : SC.ok} />

        <div className="flex items-center justify-between">
          <span className="text-[7px] text-[#4A5A78] uppercase">Risk Score</span>
          <span className="text-[9px] font-bold" style={{ color: riskColor }}>{(riskScore * 100).toFixed(0)}%</span>
        </div>
        <PctBar value={riskScore} color={riskColor} height={3} />

        <div className="flex items-center justify-between mt-1">
          <span className="text-[7px] text-[#4A5A78] uppercase">Success Prob</span>
          <span className="text-[9px] font-bold" style={{ color: drone.prediction.missionSuccessProbability > 0.8 ? SC.ok : SC.warn }}>{(drone.prediction.missionSuccessProbability * 100).toFixed(0)}%</span>
        </div>
        <PctBar value={drone.prediction.missionSuccessProbability} height={3} />
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Status</span>
        <MetricRow label="Return Home" value={returnHomeActive ? 'ACTIVE' : 'STANDBY'} color={returnHomeActive ? SC.warn : SC.dim} />
        <div className="flex items-center justify-between py-0.5">
          <span className="text-[8px] font-mono text-[#4A5A78] uppercase tracking-wider">Emergency</span>
          <span className="px-1.5 py-0.5 rounded text-[8px] font-bold font-mono" style={{ background: `${emergencyColor}20`, color: emergencyColor, border: `1px solid ${emergencyColor}40` }}>
            {emergencyStatus}
          </span>
        </div>
        <MetricRow label="AI Latency" value={`${drone.planner.inferenceTime}ms`} />
        <MetricRow label="Inference" value={`${drone.planner.inferenceTime}ms`} />
      </div>
    </div>
  );
}
