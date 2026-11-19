'use client';

// =============================================================================
// MJN Drone OS - Action Bar
// User action buttons that write to droneEntityStore.
// Every action results in a state change in the single source of truth.
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';
import { simulationEngine } from '@/store/simulationEngine';

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
      className="command-action-button transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:translate-y-0"
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

  const isFlying = missionState === 'CRUISE' || missionState === 'INSPECT' || missionState === 'HOVER';
  const isLanded = missionState === 'COMPLETE' || missionState === 'INIT';
  const isEmergency = missionState === 'EMERGENCY';
  const isReturning = missionState === 'RETURN';
  const isLanding = missionState === 'LAND';
  const isPaused = missionState === 'HOVER';
  const isActive = isFlying || isReturning || isLanding || missionState === 'TAKEOFF';

  const handleTakeoff = () => {
    simulationEngine.commandTakeoff();
  };

  const handleLand = () => {
    simulationEngine.commandLand();
  };

  const handleReturnHome = () => {
    simulationEngine.commandReturnHome();
  };

  const handlePause = () => {
    simulationEngine.commandPause();
  };

  const handleResume = () => {
    simulationEngine.commandResume();
  };

  const handleEmergencyStop = () => {
    simulationEngine.commandLand(true);
  };

  return (
    <div className="command-action-bar">
      <ActionButton
        label="TAKEOFF"
        color="#22C55E"
        bgColor="rgba(34,197,94,0.15)"
        onClick={handleTakeoff}
        disabled={isFlying || isReturning || isLanding || isEmergency || isLanded}
      />
      <ActionButton
        label="LAND"
        color="#FFC857"
        bgColor="rgba(255,200,87,0.15)"
        onClick={handleLand}
        disabled={!isActive || isEmergency || isLanding || isLanded}
      />
      <ActionButton
        label="RETURN HOME"
        color="#06B6D4"
        bgColor="rgba(6,182,212,0.15)"
        onClick={handleReturnHome}
        disabled={!isActive || isReturning || isEmergency || isLanding || isLanded}
      />
      <ActionButton
        label="PAUSE"
        color="#EAB308"
        bgColor="rgba(234,179,8,0.15)"
        onClick={handlePause}
        disabled={!isFlying || isPaused || isEmergency}
      />
      <ActionButton
        label="RESUME"
        color="#06B6D4"
        bgColor="rgba(6,182,212,0.15)"
        onClick={handleResume}
        disabled={!isPaused || isEmergency}
      />
      <ActionButton
        label="EMERGENCY"
        color="#FF4D5A"
        bgColor="rgba(255,77,90,0.15)"
        onClick={handleEmergencyStop}
        disabled={isEmergency || isLanded}
      />
    </div>
  );
}
