'use client';

import { useEffect, useRef, useState } from 'react';
import { useDroneEntityStore } from '@/store/droneEntityStore';
import { simulationEngine } from '@/store/simulationEngine';
import { monitorStateChanges } from '@/store/eventEngine';
import { useEventEngine } from '@/hooks/useEventEngine';
import dynamic from 'next/dynamic';

function LiveUTC() {
  const [mounted, setMounted] = useState(false);
  const [utc, setUtc] = useState('');
  useEffect(() => {
    setMounted(true);
    setUtc(new Date().toISOString().slice(11, 19));
    const i = setInterval(() => setUtc(new Date().toISOString().slice(11, 19)), 1000);
    return () => clearInterval(i);
  }, []);
  if (!mounted) return <span>--:--:--</span>;
  return <span>{utc}</span>;
}

const GISMap = dynamic(() => import('@/components/gis/GISMap'), { ssr: false, loading: () => <div className="h-full w-full flex items-center justify-center bg-[#111]" /> });

import AttitudeIndicator from '@/components/gcs/AttitudeIndicator';
import Compass from '@/components/gcs/Compass';
import AlertPanel from '@/components/gcs/AlertPanel';
import EventConsole from '@/components/gcs/EventConsole';
import AIPanel from '@/components/gcs/AIPanel';
import MarkerInfoPanel from '@/components/gcs/MarkerInfoPanel';

export default function Home() {
  const d = useDroneEntityStore((s) => s.drone);
  const rate = useDroneEntityStore((s) => s.updateRate);
  const { unreadCount } = useEventEngine();
  const [showE, setShowE] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (!started.current) { simulationEngine.start(); started.current = true; }
    const i = setInterval(monitorStateChanges, 200);
    return () => { simulationEngine.stop(); clearInterval(i); };
  }, []);

  const bat = d.battery.percentage > 50 ? '#22C55E' : d.battery.percentage > 20 ? '#EAB308' : '#EF4444';
  const hlth = d.health === 'OK' ? '#22C55E' : d.health === 'WARN' ? '#EAB308' : '#EF4444';

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#0D0D0D] text-[#E8E8E8] flex flex-col select-none">
      <AlertPanel />
      <header className="h-11 bg-[#161616] border-b border-[#222] flex items-center px-4 gap-4 text-[11px] shrink-0">
        <div className="flex items-center gap-2 mr-2"><div className="w-1.5 h-1.5 rounded-full bg-[#06B6D4]" /><span className="font-semibold tracking-wider text-[12px]">MJN</span></div>
        <div className="flex items-center gap-3 px-3 py-1 bg-[#1A1A1A] rounded"><span className="text-[#888] tracking-wider text-[9px]">Mission</span><span className="text-[#E8E8E8] font-mono text-[11px]">{d.missionId}</span></div>
        <div className="flex items-center gap-2 px-3 py-1 bg-[#1A1A1A] rounded"><div className="w-1.5 h-1.5 rounded-full" style={{backgroundColor:hlth}} /><span className="text-[#888] tracking-wider text-[9px]">Mode</span><span className="text-[#E8E8E8] font-mono text-[11px]">{d.missionState}</span></div>
        <div className="w-px h-5 bg-[#222]" />
        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{backgroundColor:d.connected?'#22C55E':'#EF4444'}} /><span className="text-[#888] text-[9px]">{d.connected?'ONLINE':'OFFLINE'}</span></div>
        <div className="w-px h-5 bg-[#222]" />
        <span className="text-[#888] text-[9px]">GPS</span><span className="font-mono text-[11px]" style={{color:d.gps.satellites>6?'#22C55E':'#EAB308'}}>{d.gps.satellites}</span>
        <span className="text-[#888] text-[9px]">WIND</span><span className="font-mono text-[11px] text-[#06B6D4]">{d.weather.windSpeed.toFixed(0)}</span>
        <span className="text-[#888] text-[9px]">BAT</span><span className="font-mono text-[11px]" style={{color:bat}}>{d.battery.percentage.toFixed(0)}%</span>
        <div className="flex-1" />
        <div className="font-mono text-[11px] text-[#888]">{String(Math.floor(d.telemetry.flightTime/3600)).padStart(2,'0')}:{String(Math.floor((d.telemetry.flightTime%3600)/60)).padStart(2,'0')}:{String(d.telemetry.flightTime%60).padStart(2,'0')}</div>
        <div className="text-[#555] text-[10px]"><LiveUTC /> UTC</div>
        <button onClick={()=>setShowE(!showE)} className="relative px-2 py-1 rounded bg-[#1A1A1A] text-[10px] tracking-wider">Events{unreadCount>0&&<span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#EF4444] text-white text-[7px] flex items-center justify-center font-bold">{unreadCount>9?'9+':unreadCount}</span>}</button>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-[220px] bg-[#111] border-r border-[#222] flex flex-col overflow-y-auto shrink-0">
          <div className="p-2 space-y-1.5">
            <Card title="Drone"><R label="ID" v={d.id}/><R label="Status" v={d.status} c={hlth}/><R label="Health" v={d.health} c={hlth}/><R label="Speed" v={`${d.velocity.toFixed(1)}m/s`}/><R label="Alt" v={`${d.altitude.toFixed(0)}m`}/><R label="Heading" v={`${d.heading.toFixed(0)}°`}/></Card>
            <Card title="Battery"><div className="h-1.5 bg-[#222] rounded-full overflow-hidden mb-1"><div className="h-full rounded-full transition-all" style={{width:`${d.battery.percentage}%`,backgroundColor:bat}}/></div><R label="Charge" v={`${d.battery.percentage.toFixed(0)}%`} c={bat}/><R label="Voltage" v={`${d.battery.voltage.toFixed(1)}V`}/><R label="Current" v={`${d.battery.current.toFixed(1)}A`}/><R label="Temp" v={`${d.battery.temperature.toFixed(0)}°C`}/></Card>
            <Card title="GPS"><R label="Sats" v={String(d.gps.satellites)} c={d.gps.satellites>6?'#22C55E':'#EAB308'}/><R label="HDOP" v={d.gps.hdop.toFixed(2)}/><R label="Fix" v={d.gps.fixType} c={d.gps.fixType.includes('RTK')?'#22C55E':'#06B6D4'}/><R label="Lat" v={d.latitude.toFixed(5)}/><R label="Lng" v={d.longitude.toFixed(5)}/></Card>
            <Card title="Signal"><R label="Strength" v={`${d.signal.strength.toFixed(0)}%`} c={d.signal.strength>60?'#22C55E':'#EAB308'}/><R label="RSSI" v={`${d.signal.rssi.toFixed(0)}dBm`}/><R label="SNR" v={`${d.signal.snr.toFixed(0)}dB`}/></Card>
            <Card title="System"><R label="CPU" v={`${d.system.cpuUsage}%`}/><R label="RAM" v={`${d.system.ramUsage}%`}/><R label="GPU" v={`${d.system.gpuUsage}%`}/><R label="Hz" v={`${rate}`}/></Card>
            <Card title="Weather"><R label="Wind" v={`${d.weather.windSpeed.toFixed(0)}m/s`}/><R label="Vis" v={`${d.weather.visibility.toFixed(0)}km`}/><R label="Temp" v={`${d.weather.temperature.toFixed(0)}°C`}/></Card>
          </div>
        </aside>
        <main className="flex-1 relative bg-[#0D0D0D]"><GISMap /></main>
        <aside className="w-[240px] bg-[#111] border-l border-[#222] flex flex-col overflow-y-auto shrink-0">
          <div className="p-2 space-y-1.5">
            <Card title="Mission"><R label="ID" v={d.missionId}/><R label="State" v={d.missionState} c={hlth}/><R label="Progress" v={`${d.missionProgress}%`}/><R label="ETA" v={d.missionEta}/><R label="Planner" v={d.planner.type}/><R label="Decision" v={d.planner.decision} c={d.planner.decision==='PROCEED'?'#22C55E':'#06B6D4'}/><R label="Confidence" v={`${(d.planner.confidence*100).toFixed(0)}%`}/></Card>
            <Card title="Waypoint"><R label="Current" v={d.waypoints[d.currentWaypointIndex]?.label||'N/A'}/><R label="Dist" v={`${d.telemetry.distanceToTarget.toFixed(0)}m`}/><R label="Remaining" v={`${d.waypoints.length-d.currentWaypointIndex-1}WPs`}/><R label="To Home" v={`${d.telemetry.distanceToHome.toFixed(0)}m`}/><R label="ETA Home" v={`${d.telemetry.timeToHome.toFixed(0)}s`}/></Card>
            <Card title="Prediction"><R label="Collision" v={`${(d.prediction.collisionProbability*100).toFixed(0)}%`} c={d.prediction.collisionProbability>0.05?'#EAB308':'#22C55E'}/><R label="Success" v={`${(d.prediction.missionSuccessProbability*100).toFixed(0)}%`}/><R label="Risk" v={`${(d.prediction.obstacleRisk*100).toFixed(0)}%`} c={d.prediction.obstacleRisk>0.2?'#EAB308':'#22C55E'}/></Card>
            <AIPanel />
            <button onClick={()=>setShowE(!showE)} className="w-full px-2 py-1.5 rounded bg-[#1A1A1A] text-[10px] text-left flex items-center justify-between"><span className="tracking-wider text-[#888]">Event Log</span>{unreadCount>0&&<span className="px-1 py-0.5 rounded text-[8px] font-bold" style={{backgroundColor:'rgba(239,68,68,0.2)',color:'#EF4444'}}>{unreadCount}</span>}</button>
            {showE&&<EventConsole />}
          </div>
        </aside>
      </div>
      <footer className="h-16 bg-[#161616] border-t border-[#222] flex items-center px-4 gap-4 shrink-0">
        <AttitudeIndicator /><div className="w-px h-8 bg-[#222]" /><Compass /><div className="w-px h-8 bg-[#222]" />
        <IV label="ALT" v={d.altitude.toFixed(0)} u="m" c="#06B6D4" />
        <IV label="SPD" v={d.velocity.toFixed(1)} u="m/s" c="#06B6D4" />
        <IV label="V/S" v={d.telemetry.verticalSpeed.toFixed(1)} u="m/s" c={d.verticalSpeed>=0?'#22C55E':'#EF4444'} />
        <div className="w-px h-8 bg-[#222]" />
        <div className="flex flex-col items-center min-w-[40px]"><span className="text-[8px] text-[#666] tracking-wider">SIG</span><div className="w-8 h-1.5 bg-[#222] rounded-full overflow-hidden mt-0.5"><div className="h-full rounded-full transition-all" style={{width:`${d.signal.strength}%`,backgroundColor:d.signal.strength>60?'#22C55E':'#EAB308'}}/></div></div>
        <div className="flex flex-col items-center min-w-[50px]"><span className="text-[8px] text-[#666] tracking-wider">BAT</span><div className="flex items-center gap-1.5 mt-0.5"><div className="w-10 h-2 bg-[#222] rounded-full overflow-hidden border border-[#333]"><div className="h-full rounded-full transition-all" style={{width:`${d.battery.percentage}%`,backgroundColor:bat}}/></div><span className="text-xs font-mono" style={{color:bat}}>{d.battery.percentage.toFixed(0)}</span></div></div>
        <div className="flex-1" />
        <span className="text-[9px] text-[#555]">{d.missionProgress}% · {d.waypoints.length-d.currentWaypointIndex-1} WP remaining</span>
      </footer>
    </div>
  );
}

function Card({title,children}:{title:string;children:React.ReactNode}){return(<div className="rounded-lg bg-[#1A1A1A] p-2.5"><div className="text-[8px] text-[#666] tracking-widest mb-2 font-semibold">{title}</div><div className="space-y-0.5">{children}</div></div>);}
function R({label,v,c}:{label:string;v:string;c?:string}){return(<div className="flex items-center justify-between"><span className="text-[10px] text-[#888]">{label}</span><span className="text-[10px] font-mono" style={{color:c||'#C8C8C8'}}>{v}</span></div>);}
function IV({label,v,u,c}:{label:string;v:string;u:string;c:string}){return(<div className="flex flex-col items-center min-w-[48px]"><span className="text-[8px] text-[#666] tracking-wider">{label}</span><span className="text-sm font-mono font-semibold leading-tight" style={{color:c}}>{v}</span><span className="text-[7px] text-[#555]">{u}</span></div>);}