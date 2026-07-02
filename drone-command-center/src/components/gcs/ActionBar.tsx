'use client';

// =============================================================================
// MJN Drone OS - Action Bar
// User action buttons that write to droneEntityStore.
// Every action results in a state change in the single source of truth.
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';

interface ActionButtonProps {
  label: string;
  color: string;
  bgColor: string;
  onClick: () => void;
  disabled?: boolean;
}

function ActionButton({ label, color, bgColor, onClick, disabled }: ActionButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-3 py-1.5 rounded text-xs font-mono font-bold uppercase tracking-wider transition-all duration-200 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
      style={{
        color: disabled ? '#4A5A78' : color,
        backgroundColor: disabled ? 'rgba(74,90,120,0.1)' : bgColor,
        border: `1px solid ${disabled ? 'rgba(74,90,120,0.2)' : color}40`,
      }}
    >
      {label}
    </button>
  );
}

export default function ActionBar() {
  const missionState = useDroneEntityStore((s) => s.drone.missionState);
  const status = useDroneEntityStore((s) => s.drone.status);

  const isFlying = missionState === 'CRUISE' || missionState === 'INSPECT' || missionState === 'HOVER';
  const isLanded = missionState === 'COMPLETE' || missionState === 'INIT';
  const isEmergency = missionState === 'EMERGENCY';
  const isReturning = missionState === 'RETURN';
  const isLanding = missionState === 'LAND';
  const isActive = isFlying || isReturning || isLanding;

  const handleTakeoff = () => {
    useDroneEntityStore.getState().setDrone({
      missionState: 'TAKEOFF',
      status: 'NAVIGATE',
      health: 'OK',
    });
  };

  const handleLand = () => {
    useDroneEntityStore.getState().setDrone({
      missionState: 'LAND',
      status: 'LAND',
      planner: {
        ...useDroneEntityStore.getState().drone.planner,
        decision: 'LAND',
        reason: 'Operator initiated landing',
      },
    });
  };

  const handleReturnHome = () => {
    useDroneEntityStore.getState().setDrone({
      missionState: 'RETURN',
      status: 'RETURN_HOME',
      planner: {
        ...useDroneEntityStore.getState().drone.planner,
        decision: 'RETURN_HOME',
        reason: 'Operator initiated return to home',
      },
    });
  };

  const handlePause = () => {
    useDroneEntityStore.getState().setDrone({
      missionState: 'HOVER',
      status: 'HOLD',
      planner: {
        ...useDroneEntityStore.getState().drone.planner,
        decision: 'HOLD',
        reason: 'Operator paused mission',
      },
    });
  };

  const handleResume = () => {
    useDroneEntityStore.getState().setDrone({
      missionState: 'CRUISE',
      status: 'NAVIGATE',
      planner: {
        ...useDroneEntityStore.getState().drone.planner,
        decision: 'PROCEED',
        reason: 'Operator resumed mission',
      },
    });
  };

  const handleEmergencyStop = () => {
    useDroneEntityStore.getState().setDrone({
      missionState: 'EMERGENCY',
      status: 'EMERGENCY',
      health: 'CRITICAL',
      planner: {
        ...useDroneEntityStore.getState().drone.planner,
        decision: 'EMERGENCY_LAND',
        reason: 'Operator triggered emergency stop',
        confidence: 0.5,
      },
    });
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <ActionButton
        label="TAKEOFF"
        color="#22C55E"
        bgColor="rgba(34,197,94,0.15)"
        onClick={handleTakeoff}
        disabled={isActive || isEmergency}
      />
      <ActionButton
        label="LAND"
        color="#FFC857"
        bgColor="rgba(255,200,87,0.15)"
        onClick={handleLand}
        disabled={!isActive || isEmergency || isLanding}
      />
      <ActionButton
        label="RTH"
        color="#06B6D4"
        bgColor="rgba(6,182,212,0.15)"
        onClick={handleReturnHome}
        disabled={!isActive || isReturning || isEmergency || isLanding}
      />
      <ActionButton
        label="PAUSE"
        color="#EAB308"
        bgColor="rgba(234,179,8,0.15)"
        onClick={handlePause}
        disabled={!isFlying || isEmergency}
      />
      <ActionButton
        label="RESUME"
        color="#06B6D4"
        bgColor="rgba(6,182,212,0.15)"
        onClick={handleResume}
        disabled={isFlying || isActive === false || isEmergency}
      />
      <ActionButton
        label="EM-STOP"
        color="#FF4D5A"
        bgColor="rgba(255,77,90,0.15)"
        onClick={handleEmergencyStop}
        disabled={isEmergency || isLanded}
      />
    </div>
  );
}