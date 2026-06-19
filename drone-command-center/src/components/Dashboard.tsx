'use client';

import { useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { useDroneStore } from '@/store/droneStore';
import StatusBar from './layout/StatusBar';
import GlassPanel from './layout/GlassPanel';
import EventConsole from './layout/EventConsole';
import PremiumLineChart from './charts/PremiumLineChart';

// Dynamically import Three.js component (no SSR)
const MissionMapCanvas = dynamic(
  () => import('@/components/3d/MissionMapCanvas'),
  { ssr: false, loading: () => <div className="w-full h-full flex items-center justify-center text-[#4A5A78] text-xs font-mono">Loading 3D Engine...</div> }
);

export default function Dashboard() {
  const {
    telemetry, telemetryHistory, mission, airspace, weather, prediction, health,
    theme, panels, focusedPanel, focusPanel, simulateUpdate, fps,
  } = useDroneStore();

  // Live simulation update loop
  useEffect(() => {
    const interval = setInterval(() => {
      simulateUpdate();
    }, 50); // 20 updates/sec
    return () => clearInterval(interval);
  }, [simulateUpdate]);

  const getGraphData = useCallback((history: { time: number; value: number }[]) => {
    if (!history || history.length === 0) return [];
    return history;
  }, []);

  // Compute status
  const batteryColor = telemetry.battery > 50 ? '#00FF88' : telemetry.battery > 20 ? '#FFC857' : '#FF4D5A';
  const missionStatusColor = mission.state === 'COMPLETE' ? '#00FF88' : mission.state === 'ABORT' ? '#FF4D5A' : '#00D4FF';
  const gpsStatusColor = health.gps_status === 'OK' ? '#00FF88' : health.gps_status === 'WARN' ? '#FFC857' : '#FF4D5A';

  return (
    <div className="h-screen w-screen flex flex-col bg-[#050505] text-white overflow-hidden">
      {/* Status Bar */}
      <StatusBar />

      {/* Main Grid Area */}
      <div className="flex-1 grid grid-cols-18 grid-rows-10 gap-2 p-2 overflow-hidden">
        {/* Row 1: 3D Map + Telemetry Charts + Status */}
        
        {/* 3D Mission Map - spans 6 cols, 4 rows */}
        <div className="col-span-6 row-span-4">
          <GlassPanel
            title="3D Mission Map"
            icon={<span className="text-[8px]">◈</span>}
            status="online"
            isFocused={focusedPanel === 'mission-3d-map'}
            onFocus={() => focusPanel('mission-3d-map')}
          >
            <MissionMapCanvas />
          </GlassPanel>
        </div>

        {/* Speed Chart - 3 cols, 2 rows */}
        <div className="col-span-3 row-span-2">
          <GlassPanel
            title="Speed"
            icon={<span className="text-[8px]">⟐</span>}
            status="online"
            isFocused={focusedPanel === 'telemetry-speed'}
            onFocus={() => focusPanel('telemetry-speed')}
          >
            <PremiumLineChart
              data={getGraphData(telemetryHistory.speed)}
              title="SPEED"
              unit="m/s"
              color="#FF8800"
              gradientFrom="rgba(255, 136, 0, 0.2)"
              gradientTo="rgba(255, 136, 0, 0)"
              live
              height={100}
            />
          </GlassPanel>
        </div>

        {/* Altitude Chart - 3 cols, 2 rows */}
        <div className="col-span-3 row-span-2">
          <GlassPanel
            title="Altitude"
            icon={<span className="text-[8px]">⬍</span>}
            status="online"
            isFocused={focusedPanel === 'telemetry-altitude'}
            onFocus={() => focusPanel('telemetry-altitude')}
          >
            <PremiumLineChart
              data={getGraphData(telemetryHistory.altitude)}
              title="ALTITUDE"
              unit="m"
              color="#00D4FF"
              gradientFrom="rgba(0, 212, 255, 0.2)"
              gradientTo="rgba(0, 212, 255, 0)"
              live
              height={100}
            />
          </GlassPanel>
        </div>

        {/* Drone Status Panel - 3 cols, 2 rows */}
        <div className="col-span-3 row-span-2">
          <GlassPanel
            title="Drone Status"
            icon={<span className="text-[8px]">◉</span>}
            status={telemetry.status === 'EMERGENCY' ? 'error' : telemetry.status === 'NAVIGATE' ? 'online' : 'idle'}
            isFocused={focusedPanel === 'drone-status'}
            onFocus={() => focusPanel('drone-status')}
          >
            <StatusDisplay
              items={[
                { label: 'STATUS', value: telemetry.status, color: batteryColor },
                { label: 'MODE', value: telemetry.flight_mode, color: '#9D6CFF' },
                { label: 'HEADING', value: `${telemetry.heading.toFixed(0)}°`, color: '#06B6D4' },
                { label: 'PITCH/ROLL', value: `${telemetry.pitch.toFixed(1)}°/${telemetry.roll.toFixed(1)}°`, color: '#6B7FA0' },
                { label: 'GPS', value: `${(telemetry.gps_accuracy * 100).toFixed(0)}cm`, color: gpsStatusColor },
                { label: 'SIGNAL', value: `${telemetry.signal_strength}%`, color: telemetry.signal_strength > 80 ? '#00FF88' : '#FFC857' },
                { label: 'TEMP', value: `${telemetry.temperature.toFixed(0)}°C`, color: telemetry.temperature < 60 ? '#00FF88' : '#FFC857' },
                { label: 'INFERENCE', value: `${telemetry.inference_time}ms`, color: '#A78BFA' },
              ]}
            />
          </GlassPanel>
        </div>

        {/* Row 2: Battery + CPU + Mission Timeline + Airspace */}
        
        {/* Battery Chart - 3 cols, 2 rows */}
        <div className="col-span-3 row-span-2 col-start-7 row-start-3">
          <GlassPanel
            title="Battery"
            icon={<span className="text-[8px]">▣</span>}
            status={telemetry.battery > 50 ? 'online' : telemetry.battery > 20 ? 'warning' : 'error'}
            isFocused={focusedPanel === 'telemetry-battery'}
            onFocus={() => focusPanel('telemetry-battery')}
          >
            <div className="h-full flex flex-col gap-2">
              <PremiumLineChart
                data={getGraphData(telemetryHistory.battery)}
                title="BATTERY"
                unit="%"
                color={batteryColor}
                gradientFrom={batteryColor.replace(')', ', 0.2)').replace('rgb', 'rgba')}
                gradientTo={batteryColor.replace(')', ', 0)').replace('rgb', 'rgba')}
                live
                height={60}
                min={0}
                max={100}
              />
              {/* Big battery percentage */}
              <div className="flex items-center justify-center gap-3">
                <div className="text-3xl font-bold font-mono" style={{ color: batteryColor }}>
                  {telemetry.battery.toFixed(0)}
                </div>
                <span className="text-[10px] text-[#4A5A78] font-mono">%</span>
              </div>
            </div>
          </GlassPanel>
        </div>

        {/* CPU Chart - 3 cols, 2 rows */}
        <div className="col-span-3 row-span-2 col-start-10 row-start-3">
          <GlassPanel
            title="CPU Usage"
            icon={<span className="text-[8px]">◈</span>}
            status="online"
            isFocused={focusedPanel === 'telemetry-cpu'}
            onFocus={() => focusPanel('telemetry-cpu')}
          >
            <PremiumLineChart
              data={getGraphData(telemetryHistory.cpu)}
              title="CPU"
              unit="%"
              color="#FFC857"
              gradientFrom="rgba(255, 200, 87, 0.2)"
              gradientTo="rgba(255, 200, 87, 0)"
              live
              height={100}
              min={0}
              max={100}
            />
          </GlassPanel>
        </div>

        {/* Mission Timeline - 3 cols, 2 rows */}
        <div className="col-span-3 row-span-2 col-start-13 row-start-3">
          <GlassPanel
            title="Mission Timeline"
            icon={<span className="text-[8px]">▸</span>}
            status={mission.state === 'COMPLETE' ? 'online' : 'idle'}
            isFocused={focusedPanel === 'mission-timeline'}
            onFocus={() => focusPanel('mission-timeline')}
          >
            <TimelinePanel mission={mission} />
          </GlassPanel>
        </div>

        {/* Airspace - 3 cols, 4 rows */}
        <div className="col-span-3 row-span-4 col-start-16 row-start-1">
          <GlassPanel
            title="Airspace"
            icon={<span className="text-[8px]">◯</span>}
            status={airspace.violations > 0 ? 'error' : airspace.risk_score > 0.3 ? 'warning' : 'online'}
            isFocused={focusedPanel === 'airspace'}
            onFocus={() => focusPanel('airspace')}
          >
            <AirspacePanel airspace={airspace} weather={weather} />
          </GlassPanel>
        </div>

        {/* Row 3: Drone Health + Prediction + Signal + GPS */}
        
        {/* Drone Health - 3 cols, 3 rows */}
        <div className="col-span-3 row-span-3 col-start-1 row-start-5">
          <GlassPanel
            title="Drone Health"
            icon={<span className="text-[8px]">♦</span>}
            status="online"
            isFocused={focusedPanel === 'drone-health'}
            onFocus={() => focusPanel('drone-health')}
          >
            <HealthPanel health={health} />
          </GlassPanel>
        </div>

        {/* Prediction - 3 cols, 3 rows */}
        <div className="col-span-3 row-span-3 col-start-4 row-start-5">
          <GlassPanel
            title="Prediction"
            icon={<span className="text-[8px]">◈</span>}
            status="online"
            isFocused={focusedPanel === 'prediction-panel'}
            onFocus={() => focusPanel('prediction-panel')}
          >
            <PredictionPanel prediction={prediction} />
          </GlassPanel>
        </div>

        {/* Signal Strength - 3 cols, 3 rows */}
        <div className="col-span-3 row-span-3 col-start-7 row-start-5">
          <GlassPanel
            title="Signal Strength"
            icon={<span className="text-[8px]">⟐</span>}
            status={telemetry.signal_strength > 80 ? 'online' : 'warning'}
            isFocused={focusedPanel === 'telemetry-signal'}
            onFocus={() => focusPanel('telemetry-signal')}
          >
            <PremiumLineChart
              data={getGraphData(telemetryHistory.signal)}
              title="SIGNAL"
              unit="%"
              color="#06B6D4"
              gradientFrom="rgba(6, 182, 212, 0.2)"
              gradientTo="rgba(6, 182, 212, 0)"
              live
              height={100}
              min={0}
              max={100}
            />
          </GlassPanel>
        </div>

        {/* GPS Accuracy - 3 cols, 3 rows */}
        <div className="col-span-3 row-span-3 col-start-10 row-start-5">
          <GlassPanel
            title="GPS Accuracy"
            icon={<span className="text-[8px]">◉</span>}
            status={health.gps_status === 'OK' ? 'online' : 'warning'}
            isFocused={focusedPanel === 'telemetry-gps'}
            onFocus={() => focusPanel('telemetry-gps')}
          >
            <PremiumLineChart
              data={getGraphData(telemetryHistory.gps)}
              title="GPS"
              unit="cm"
              color="#00FF88"
              gradientFrom="rgba(0, 255, 136, 0.2)"
              gradientTo="rgba(0, 255, 136, 0)"
              live
              height={100}
            />
          </GlassPanel>
        </div>

        {/* Graph Workspace - 6 cols, 3 rows */}
        <div className="col-span-6 row-span-3 col-start-13 row-start-5">
          <GlassPanel
            title="Graph Workspace"
            icon={<span className="text-[8px]">⬡</span>}
            status="online"
            isFocused={focusedPanel === 'graph-workspace'}
            onFocus={() => focusPanel('graph-workspace')}
          >
            <GraphWorkspace history={telemetryHistory} />
          </GlassPanel>
        </div>

        {/* Row 4: Event Console - full width */}
        <div className="col-span-18 row-span-2 col-start-1 row-start-8">
          <GlassPanel
            title="Event Console"
            icon={<span className="text-[8px]">▤</span>}
            status="online"
            isFocused={focusedPanel === 'event-console'}
            onFocus={() => focusPanel('event-console')}
          >
            <EventConsole />
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────────

function StatusDisplay({ items }: { items: { label: string; value: string; color: string }[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between">
          <span className="text-[9px] uppercase tracking-wider text-[#4A5A78] font-mono">{item.label}</span>
          <span className="text-[11px] font-bold font-mono tabular-nums" style={{ color: item.color }}>
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function TimelinePanel({ mission }: { mission: any }) {
  const states = ['INIT', 'TAKEOFF', 'CRUISE', 'INSPECT', 'RETURN', 'LAND', 'COMPLETE'];
  const currentIdx = states.indexOf(mission.state) >= 0 ? states.indexOf(mission.state) : 2;

  return (
    <div className="flex flex-col gap-2 h-full justify-center">
      {/* Progress bar */}
      <div className="w-full h-1.5 bg-[rgba(26,26,46,0.6)] rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg, #00D4FF, #00FF88)' }}
          initial={{ width: 0 }}
          animate={{ width: `${mission.progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      
      {/* Timeline dots */}
      <div className="flex justify-between mt-1">
        {states.map((state, i) => (
          <div key={state} className="flex flex-col items-center gap-0.5">
            <div
              className={`w-2 h-2 rounded-full ${
                i <= currentIdx ? 'bg-[#00D4FF]' : 'bg-[rgba(26,26,46,0.6)]'
              }`}
              style={i <= currentIdx ? { boxShadow: '0 0 6px rgba(0, 212, 255, 0.5)' } : {}}
            />
            <span className={`text-[6px] font-mono ${
              i === currentIdx ? 'text-[#6B7FA0]' : 'text-[#4A5A78]'
            }`}>
              {state.slice(0, 4)}
            </span>
          </div>
        ))}
      </div>

      {/* Mission info */}
      <div className="flex justify-between text-[9px] font-mono text-[#4A5A78] mt-1">
        <span>{mission.progress.toFixed(1)}%</span>
        <span>ETA {mission.eta}</span>
        <span>WP {mission.current_waypoint}/{mission.waypoints.length}</span>
      </div>
    </div>
  );
}

function AirspacePanel({ airspace, weather }: { airspace: any; weather: any }) {
  return (
    <div className="flex flex-col gap-1.5 h-full">
      <div className="grid grid-cols-2 gap-1">
        {[
          { label: 'Zones Active', value: airspace.zones_active, color: '#FF6600' },
          { label: 'Violations', value: airspace.violations, color: airspace.violations > 0 ? '#FF4D5A' : '#00FF88' },
          { label: 'TFR Active', value: airspace.tfr_active, color: '#9D6CFF' },
          { label: 'Risk Score', value: (airspace.risk_score * 100).toFixed(0) + '%', color: airspace.risk_score > 0.5 ? '#FF4D5A' : airspace.risk_score > 0.2 ? '#FFC857' : '#00FF88' },
        ].map((item) => (
          <div key={item.label} className="flex flex-col">
            <span className="text-[7px] uppercase tracking-wider text-[#4A5A78] font-mono">{item.label}</span>
            <span className="text-[12px] font-bold font-mono" style={{ color: item.color }}>{item.value}</span>
          </div>
        ))}
      </div>
      <div className="w-full h-px bg-[rgba(26,26,46,0.4)] my-1" />
      <div className="flex items-center justify-center gap-2 mt-auto">
        <span
          className="text-[10px] font-bold font-mono tracking-wider"
          style={{ color: airspace.risk_score > 0.3 ? '#FFC857' : '#00FF88' }}
        >
          DECISION: {airspace.decision}
        </span>
      </div>
      <div className="flex justify-between text-[7px] text-[#4A5A78] font-mono">
        <span>WIND: {weather.wind_speed.toFixed(1)} m/s</span>
        <span>VIS: {weather.visibility}km</span>
        <span>TURB: {weather.turbulence.toFixed(1)}</span>
      </div>
    </div>
  );
}

function HealthPanel({ health }: { health: any }) {
  const statusColor = (s: string) => s === 'OK' ? '#00FF88' : s === 'WARN' ? '#FFC857' : '#FF4D5A';
  return (
    <div className="grid grid-cols-2 gap-1.5 h-full">
      {[
        { label: 'IMU', value: health.imu_status, color: statusColor(health.imu_status) },
        { label: 'GPS', value: health.gps_status, color: statusColor(health.gps_status) },
        { label: 'COMPASS', value: health.compass_status, color: statusColor(health.compass_status) },
        { label: 'LIDAR', value: health.lidar_status, color: statusColor(health.lidar_status) },
        { label: 'CAMERA', value: health.camera_status, color: statusColor(health.camera_status) },
        { label: 'BATTERY', value: `${health.battery_health}%`, color: health.battery_health > 80 ? '#00FF88' : '#FFC857' },
        { label: 'MOTOR', value: `${health.motor_temp.toFixed(0)}°C`, color: health.motor_temp < 60 ? '#00FF88' : '#FFC857' },
        { label: 'VIBRATION', value: (health.vibration * 100).toFixed(0), color: health.vibration < 0.1 ? '#00FF88' : '#FFC857' },
      ].map((item) => (
        <div key={item.label} className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: item.color, boxShadow: `0 0 4px ${item.color}` }} />
            <span className="text-[8px] font-mono text-[#4A5A78]">{item.label}</span>
          </div>
          <span className="text-[9px] font-bold font-mono" style={{ color: item.color }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

function PredictionPanel({ prediction }: { prediction: any }) {
  const pctColor = (v: number) => v > 0.8 ? '#00FF88' : v > 0.5 ? '#FFC857' : '#FF4D5A';
  return (
    <div className="grid grid-cols-2 gap-1 h-full">
      {[
        { label: 'Trajectory', value: (prediction.trajectory_confidence * 100).toFixed(0) + '%', color: pctColor(prediction.trajectory_confidence) },
        { label: 'Collision Risk', value: (prediction.collision_probability * 100).toFixed(1) + '%', color: prediction.collision_probability > 0.1 ? '#FFC857' : '#00FF88' },
        { label: 'Path Smooth', value: (prediction.path_smoothness * 100).toFixed(0) + '%', color: pctColor(prediction.path_smoothness) },
        { label: 'Prediction Acc', value: (prediction.prediction_accuracy * 100).toFixed(0) + '%', color: pctColor(prediction.prediction_accuracy) },
        { label: 'Decision Conf', value: (prediction.decision_confidence * 100).toFixed(0) + '%', color: pctColor(prediction.decision_confidence) },
        { label: 'Obstacle Risk', value: (prediction.obstacle_risk * 100).toFixed(0) + '%', color: prediction.obstacle_risk > 0.3 ? '#FF4D5A' : '#00FF88' },
        { label: 'Path Cost', value: prediction.path_cost.toFixed(2), color: prediction.path_cost < 0.5 ? '#00FF88' : '#FFC857' },
      ].map((item) => (
        <div key={item.label} className="flex flex-col">
          <span className="text-[7px] uppercase tracking-wider text-[#4A5A78] font-mono">{item.label}</span>
          <span className="text-[11px] font-bold font-mono tabular-nums" style={{ color: item.color }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

function GraphWorkspace({ history }: { history: any }) {
  return (
    <div className="grid grid-cols-3 gap-1 h-full">
      <PremiumLineChart data={history.temperature} title="Motor Temp" unit="°C" color="#FF4D5A" gradientFrom="rgba(255, 77, 90, 0.2)" gradientTo="rgba(255, 77, 90, 0)" live height={80} />
      <PremiumLineChart data={history.confidence} title="Confidence" unit="%" color="#A78BFA" gradientFrom="rgba(167, 139, 250, 0.2)" gradientTo="rgba(167, 139, 250, 0)" live height={80} />
      <PremiumLineChart data={history.motorTemp} title="Motor RPM" unit="k" color="#FFC857" gradientFrom="rgba(255, 200, 87, 0.2)" gradientTo="rgba(255, 200, 87, 0)" live height={80} />
      <PremiumLineChart data={history.windSpeed} title="Wind Speed" unit="m/s" color="#06B6D4" gradientFrom="rgba(6, 182, 212, 0.2)" gradientTo="rgba(6, 182, 212, 0)" live height={80} />
      <PremiumLineChart data={history.obstacleRisk} title="Obstacle Risk" unit="%" color="#FF4D5A" gradientFrom="rgba(255, 77, 90, 0.2)" gradientTo="rgba(255, 77, 90, 0)" live height={80} />
      <div className="flex flex-col items-center justify-center">
        <span className="text-[8px] text-[#4A5A78] font-mono">CONFIDENCE</span>
        <motion.span
          key={history.confidence[history.confidence.length - 1]?.value.toFixed(1) || '0'}
          initial={{ scale: 0.5 }}
          animate={{ scale: 1 }}
          className="text-[18px] font-bold font-mono text-[#A78BFA]"
        >
          {(history.confidence[history.confidence.length - 1]?.value * 100 || 0).toFixed(0)}%
        </motion.span>
      </div>
    </div>
  );
}