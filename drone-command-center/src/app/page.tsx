'use client';

import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import dynamic from 'next/dynamic';
import {
  Activity,
  Battery,
  BrainCircuit,
  ChevronLeft,
  MapPin,
  Plane,
  Radio,
  Route,
  Satellite,
  ShieldCheck,
  Wind,
} from 'lucide-react';
import { useDroneEntityStore } from '@/store/droneEntityStore';
import { simulationEngine } from '@/store/simulationEngine';
import type { GeneratedMission } from '@/store/missionGenerator';
import { monitorStateChanges } from '@/store/eventEngine';
import { useEventEngine } from '@/hooks/useEventEngine';
import AttitudeIndicator from '@/components/gcs/AttitudeIndicator';
import Compass from '@/components/gcs/Compass';
import AlertPanel from '@/components/gcs/AlertPanel';
import EventConsole from '@/components/gcs/EventConsole';
import ActionBar from '@/components/gcs/ActionBar';

const GISMap = dynamic(() => import('@/components/gis/GISMap'), {
  ssr: false,
  loading: () => <div className="command-map-loading"><span /></div>,
});
const MissionPlanner = dynamic(() => import('@/components/mission/MissionPlanner'), {
  ssr: false,
  loading: () => <div className="h-screen w-screen bg-[#07111f]" />,
});

function LiveUTC() {
  const [utc, setUtc] = useState('--:--:--');

  useEffect(() => {
    const interval = window.setInterval(() => setUtc(new Date().toISOString().slice(11, 19)), 1_000);
    return () => window.clearInterval(interval);
  }, []);

  return <span>{utc}</span>;
}

function formatFlightTime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function statusColor(status: string) {
  if (status === 'OK' || status === 'CRUISE' || status === 'COMPLETE') return '#34d399';
  if (status === 'WARN' || status === 'HOVER' || status === 'RETURN') return '#fbbf24';
  return '#fb7185';
}

export default function Home() {
  const drone = useDroneEntityStore((state) => state.drone);
  const updateRate = useDroneEntityStore((state) => state.updateRate);
  const { unreadCount } = useEventEngine();
  const [showEvents, setShowEvents] = useState(false);
  const [mission, setMission] = useState<GeneratedMission | null>(null);

  useEffect(() => {
    if (!mission) return;
    simulationEngine.start(mission);
    const interval = window.setInterval(monitorStateChanges, 200);
    return () => {
      simulationEngine.stop();
      window.clearInterval(interval);
    };
  }, [mission]);

  if (!mission) return <MissionPlanner onLaunch={setMission} />;

  const batteryColor = drone.battery.percentage > 50 ? '#34d399' : drone.battery.percentage > 20 ? '#fbbf24' : '#fb7185';
  const healthColor = statusColor(drone.health);
  const waypoint = drone.waypoints[drone.currentWaypointIndex];
  const remainingWaypoints = Math.max(0, drone.waypoints.length - drone.currentWaypointIndex - 1);
  const activeMission = !['COMPLETE', 'EMERGENCY'].includes(drone.missionState);

  return (
    <div className="command-shell">
      <AlertPanel />

      <header className="command-header">
        <div className="command-brand">
          <div className="command-brand-mark"><Plane size={18} /></div>
          <div><span>MJN AEROSPACE</span><strong>Command Center</strong></div>
        </div>

        <div className="command-header-divider" />
        <div className="command-mission-id">
          <span>ACTIVE FLIGHT</span>
          <strong>{drone.missionId}</strong>
        </div>
        <div className="command-state-pill" style={{ '--state-color': healthColor } as CSSProperties}>
          <i /> {drone.missionState.replace('_', ' ')}
        </div>
        <div className="command-header-details">
          <HeaderMetric label="Connection" value={drone.connected ? 'Connected' : 'Offline'} color={drone.connected ? '#34d399' : '#fb7185'} />
          <HeaderMetric label="GPS" value={`${drone.gps.satellites} satellites`} color={drone.gps.satellites > 6 ? '#7dd3fc' : '#fbbf24'} />
          <HeaderMetric label="Wind" value={`${drone.weather.windSpeed.toFixed(0)} m/s`} />
        </div>
        <div className="command-header-spacer" />
        <div className="command-clock"><span>FLIGHT</span><strong>{formatFlightTime(drone.telemetry.flightTime)}</strong></div>
        <div className="command-clock command-utc"><span>UTC</span><strong><LiveUTC /></strong></div>
        <button type="button" onClick={() => setMission(null)} className="command-plan-button"><ChevronLeft size={15} /> New plan</button>
        <button type="button" onClick={() => setShowEvents((open) => !open)} className="command-events-button" aria-expanded={showEvents}>
          <Activity size={15} /> Activity
          {unreadCount > 0 && <span>{unreadCount > 9 ? '9+' : unreadCount}</span>}
        </button>
      </header>

      <div className="command-workspace">
        <aside className="command-sidebar command-sidebar-left">
          <section className="command-intro-card">
            <div className="command-section-icon"><Plane size={17} /></div>
            <div>
              <span className="command-kicker">SIMULATED FLIGHT</span>
              <h1>{mission.missionName}</h1>
              <p>{activeMission ? 'The drone is following the route you planned.' : 'This simulated flight has ended. Create a new plan when you are ready.'}</p>
            </div>
          </section>

          <Panel title="Flight at a glance" helper="The essentials, updated live.">
            <div className="command-stat-grid">
              <BigMetric label="Height" value={drone.altitude.toFixed(0)} unit="m" accent="#5dd4ff" />
              <BigMetric label="Speed" value={drone.velocity.toFixed(1)} unit="m/s" accent="#a78bfa" />
              <BigMetric label="Direction" value={drone.heading.toFixed(0)} unit="°" accent="#f7ca69" />
              <BigMetric label="Signal" value={drone.signal.strength.toFixed(0)} unit="%" accent={drone.signal.strength > 60 ? '#55dba2' : '#f7ca69'} />
            </div>
          </Panel>

          <Panel title="System health">
            <ReadinessRow icon={<Battery size={15} />} label="Battery" value={`${drone.battery.percentage.toFixed(0)}% charged`} tone={batteryColor} progress={drone.battery.percentage} />
            <ReadinessRow icon={<Satellite size={15} />} label="Position" value={`${drone.gps.satellites} satellites locked`} tone={drone.gps.satellites > 6 ? '#34d399' : '#fbbf24'} progress={Math.min(100, drone.gps.satellites * 6)} />
            <ReadinessRow icon={<Radio size={15} />} label="Connection" value={drone.connected ? 'Control link is stable' : 'Control link is unavailable'} tone={drone.connected ? '#34d399' : '#fb7185'} progress={drone.connected ? drone.signal.strength : 0} />
          </Panel>

          <Panel title="Local conditions">
            <div className="command-weather">
              <Wind size={23} />
              <div><strong>{drone.weather.windSpeed.toFixed(0)} m/s</strong><span>Wind from {drone.weather.windDirection.toFixed(0)}°</span></div>
              <div className="command-weather-secondary"><strong>{drone.weather.visibility.toFixed(0)} km</strong><span>Visibility</span></div>
            </div>
            <div className="command-mini-row"><span>Temperature</span><strong>{drone.weather.temperature.toFixed(0)}°C</strong></div>
          </Panel>
        </aside>

        <main className="command-map">
          <GISMap />
          <div className="command-map-caption">
            <span className="command-map-caption-dot" />
            <div><strong>Live route view</strong><span>Map follows the drone while it is in motion.</span></div>
          </div>
          <div className="command-map-route">
            <Route size={15} /><span>Next: <strong>{waypoint?.label || 'Mission complete'}</strong></span><i /><span>{remainingWaypoints} waypoint{remainingWaypoints === 1 ? '' : 's'} after this</span>
          </div>
        </main>

        <aside className="command-sidebar command-sidebar-right">
          <Panel title="Mission progress" helper="Your route, one clear step at a time.">
            <div className="command-progress-value"><strong>{drone.missionProgress}%</strong><span>{drone.missionEta === '00:00' ? 'Arriving now' : `${drone.missionEta} remaining`}</span></div>
            <div className="command-progress-track"><span style={{ width: `${Math.min(100, Math.max(0, drone.missionProgress))}%` }} /></div>
            <div className="command-route-next"><MapPin size={16} /><div><span>Up next</span><strong>{waypoint?.label || 'Flight complete'}</strong><small>{drone.telemetry.distanceToTarget.toFixed(0)} m away</small></div></div>
          </Panel>

          <Panel title="AI flight assistant" helper="Plain-language route advice.">
            <div className="command-ai-decision">
              <span style={{ color: drone.planner.decision === 'PROCEED' ? '#34d399' : '#fbbf24' }}><BrainCircuit size={17} /> {drone.planner.decision.replace('_', ' ')}</span>
              <strong>{(drone.planner.confidence * 100).toFixed(0)}% confident</strong>
            </div>
            <p className="command-ai-copy">{drone.planner.reason}</p>
            <div className="command-ai-grid">
              <SmallMetric label="Route risk" value={`${(drone.prediction.obstacleRisk * 100).toFixed(0)}%`} tone={drone.prediction.obstacleRisk < 0.2 ? '#34d399' : '#fbbf24'} />
              <SmallMetric label="Success chance" value={`${(drone.prediction.missionSuccessProbability * 100).toFixed(0)}%`} tone="#5dd4ff" />
              <SmallMetric label="Path check" value={drone.prediction.collisionProbability < 0.05 ? 'Clear' : 'Review'} tone={drone.prediction.collisionProbability < 0.05 ? '#34d399' : '#fbbf24'} />
            </div>
          </Panel>

          <Panel title="Quick controls" helper="These actions control the simulator.">
            <ActionBar />
          </Panel>

          <button type="button" onClick={() => setShowEvents((open) => !open)} className="command-log-toggle">
            <span><Activity size={15} /> Flight activity</span>
            <span>{showEvents ? 'Hide' : `${unreadCount || 'View'}`}</span>
          </button>
          {showEvents && <div className="command-event-console"><EventConsole /></div>}
        </aside>
      </div>

      <footer className="command-footer">
        <div className="command-instruments"><AttitudeIndicator /><span className="command-footer-divider" /><Compass /></div>
        <div className="command-footer-readouts">
          <FooterMetric label="Vertical speed" value={drone.telemetry.verticalSpeed.toFixed(1)} unit="m/s" tone={drone.telemetry.verticalSpeed >= 0 ? '#55dba2' : '#fb7185'} />
          <FooterMetric label="Battery voltage" value={drone.battery.voltage.toFixed(1)} unit="V" tone={batteryColor} />
          <FooterMetric label="Telemetry" value={String(updateRate)} unit="Hz" tone="#5dd4ff" />
        </div>
        <div className="command-footer-spacer" />
        <div className="command-footer-safe"><ShieldCheck size={15} /><span>Simulator safety checks active</span></div>
      </footer>
    </div>
  );
}

function HeaderMetric({ label, value, color = '#b8cee1' }: { label: string; value: string; color?: string }) {
  return <div className="command-header-metric"><span>{label}</span><strong style={{ color }}>{value}</strong></div>;
}

function Panel({ title, helper, children }: { title: string; helper?: string; children: ReactNode }) {
  return <section className="command-panel"><div className="command-panel-heading"><div><h2>{title}</h2>{helper && <p>{helper}</p>}</div></div>{children}</section>;
}

function BigMetric({ label, value, unit, accent }: { label: string; value: string; unit: string; accent: string }) {
  return <div className="command-big-metric"><span>{label}</span><strong style={{ color: accent }}>{value}<small>{unit}</small></strong></div>;
}

function ReadinessRow({ icon, label, value, tone, progress }: { icon: ReactNode; label: string; value: string; tone: string; progress: number }) {
  return <div className="command-readiness-row"><span className="command-readiness-icon" style={{ color: tone }}>{icon}</span><div><strong>{label}</strong><small>{value}</small><span className="command-readiness-track"><i style={{ width: `${Math.min(100, Math.max(0, progress))}%`, background: tone }} /></span></div></div>;
}

function SmallMetric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className="command-small-metric"><span>{label}</span><strong style={{ color: tone }}>{value}</strong></div>;
}

function FooterMetric({ label, value, unit, tone }: { label: string; value: string; unit: string; tone: string }) {
  return <div className="command-footer-metric"><span>{label}</span><strong style={{ color: tone }}>{value}<small>{unit}</small></strong></div>;
}
