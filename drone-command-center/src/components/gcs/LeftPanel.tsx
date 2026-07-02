'use client';

import { useDroneEntityStore } from '@/store/droneEntityStore';
import { getSystemStatus } from '@/store/droneSelectors';

const SC = {
  ok: '#00FF88',
  warn: '#FFC857',
  fail: '#FF4D5A',
};

function StatusDot({ status }: { status: string }) {
  const color = status === 'OK' ? SC.ok : status === 'WARN' ? SC.warn : SC.fail;
  return <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: color, boxShadow: `0 0 4px ${color}` }} />;
}

function UsageBar({ value, max = 100, color }: { value: number; max?: number; color?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  const resolved = color || (pct > 80 ? SC.fail : pct > 60 ? SC.warn : SC.ok);
  return (
    <div className="w-full h-1 bg-[rgba(26,26,46,0.6)] rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all duration-300" style={{ width: `${pct}%`, background: resolved }} />
    </div>
  );
}

function SensorCard({ label, value, status }: { label: string; value: string; status: string }) {
  return (
    <div className="flex items-center gap-2 bg-[rgba(26,26,46,0.3)] rounded px-2 py-1">
      <StatusDot status={status} />
      <span className="text-[8px] font-mono text-[#4A5A78] w-12">{label}</span>
      <span className="text-[9px] font-mono text-[#8A9BB5] ml-auto">{value}</span>
    </div>
  );
}

function SysBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[8px] text-[#4A5A78] w-8">{label}</span>
      <UsageBar value={value} />
      <span className="text-[8px] text-[#4A5A78] w-6 text-right">{value}%</span>
    </div>
  );
}

export default function LeftPanel() {
  const battery = useDroneEntityStore((s) => s.drone.battery);
  const system = useDroneEntityStore((s) => s.drone.system);
  const sensors = useDroneEntityStore((s) => s.drone.sensors);
  const gps = useDroneEntityStore((s) => s.drone.gps);
  const imu = useDroneEntityStore((s) => s.drone.imu);
  const altitude = useDroneEntityStore((s) => s.drone.altitude);
  const heading = useDroneEntityStore((s) => s.drone.heading);

  const batteryColor = battery.percentage > 50 ? SC.ok : battery.percentage > 20 ? SC.warn : SC.fail;
  const systemStatus = getSystemStatus(system);

  return (
    <div className="h-full overflow-y-auto px-3 py-2 space-y-3 font-mono select-none">
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Battery</span>
          <span className="text-[16px] font-bold" style={{ color: batteryColor }}>{battery.percentage.toFixed(0)}<span className="text-[9px] text-[#4A5A78]">%</span></span>
        </div>
        <UsageBar value={battery.percentage} color={batteryColor} />
        <div className="grid grid-cols-4 gap-1 mt-1">
          <div className="flex flex-col items-center"><span className="text-[7px] text-[#4A5A78]">V</span><span className="text-[9px] text-[#8A9BB5]">{battery.voltage.toFixed(1)}</span></div>
          <div className="flex flex-col items-center"><span className="text-[7px] text-[#4A5A78]">A</span><span className="text-[9px] text-[#8A9BB5]">{battery.current.toFixed(1)}</span></div>
          <div className="flex flex-col items-center"><span className="text-[7px] text-[#4A5A78]">C</span><span className="text-[9px] text-[#8A9BB5]">{battery.temperature.toFixed(0)}</span></div>
          <div className="flex flex-col items-center"><span className="text-[7px] text-[#4A5A78]">W</span><span className="text-[9px] text-[#8A9BB5]">{battery.power.toFixed(0)}</span></div>
        </div>
        <div className="flex gap-1 mt-1">
          {battery.cells.map((cell, index) => (
            <div key={index} className="flex-1 h-1.5 rounded-full bg-[rgba(26,26,46,0.6)] overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${(cell / 4.2) * 100}%`, background: cell < 3.7 ? SC.warn : SC.ok }} />
            </div>
          ))}
        </div>
        <div className="text-[7px] text-[#4A5A78] mt-0.5">Health {battery.health}% · {battery.cycles} cycles</div>
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Motors</span>
        <div className="grid grid-cols-2 gap-1 mt-1">
          {system.motorRpm.map((rpm, index) => (
            <div key={index} className="bg-[rgba(26,26,46,0.3)] rounded px-1.5 py-1">
              <div className="flex items-center gap-1">
                <StatusDot status={system.motorTemperature[index] > 80 ? 'FAIL' : system.motorTemperature[index] > 60 ? 'WARN' : 'OK'} />
                <span className="text-[7px] text-[#4A5A78]">M{index + 1}</span>
                <span className="text-[8px] text-[#8A9BB5] ml-auto">{(rpm / 1000).toFixed(1)}k</span>
              </div>
              <div className="text-[7px] text-[#4A5A78] mt-0.5">{system.motorTemperature[index].toFixed(0)}C · ESC {system.escTemperature[index]}C</div>
            </div>
          ))}
        </div>
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">Sensors</span>
        <div className="grid grid-cols-2 gap-1 mt-1">
          <SensorCard label="GPS" value={`${gps.satellites}sat HDOP ${gps.hdop.toFixed(1)}`} status={gps.fixType === 'NO_FIX' ? 'FAIL' : gps.fixType === '2D' ? 'WARN' : 'OK'} />
          <SensorCard label="IMU" value={`${imu.accelerationZ.toFixed(1)} m/s²`} status="OK" />
          <SensorCard label="COMPASS" value={`${imu.compassHeading.toFixed(0)}°`} status="OK" />
          <SensorCard label="BARO" value={`${altitude.toFixed(0)}m`} status="OK" />
          <SensorCard label="LIDAR" value={`${sensors.detectionCount} objs`} status={sensors.lidar} />
          <SensorCard label="CAMERA" value={`${sensors.trackingIds.length} tracks`} status={sensors.camera} />
          <SensorCard label="RADAR" value={`${sensors.detectionCount} tgts`} status={sensors.radar} />
          <SensorCard label="FLOW" value={`${heading.toFixed(0)}°`} status={sensors.opticalFlow} />
        </div>
      </div>

      <div className="h-px bg-[rgba(26,26,46,0.4)]" />

      <div>
        <span className="text-[9px] uppercase tracking-wider text-[#6B7FA0]">System</span>
        <div className="space-y-1 mt-1">
          <SysBar label="CPU" value={system.cpuUsage} />
          <SysBar label="GPU" value={system.gpuUsage} />
          <SysBar label="RAM" value={system.ramUsage} />
          <SysBar label="DISK" value={system.diskUsage} />
        </div>
        <div className="flex justify-between text-[7px] text-[#4A5A78] mt-1">
          <span>RX {system.networkRx.toFixed(1)}Mb</span>
          <span>TX {system.networkTx.toFixed(1)}Mb</span>
          <span>TEL {system.telemetryRate}Hz</span>
          <span>{systemStatus}</span>
        </div>
      </div>
    </div>
  );
}
