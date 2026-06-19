'use client';

import { useMemo, useRef, useEffect, useState, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line as DreiLine, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useDroneStore } from '@/store/droneStore';
import { ThreeErrorBoundary } from './ErrorBoundary';
import { WorldGenerator, type TreeData, type RoadData, type WaterBody } from '@/lib/world/world-generator';
import TerrainMesh from '@/components/3d/digital-twin/TerrainMesh';
import Buildings from '@/components/3d/digital-twin/Buildings';
import DroneModel from '@/components/3d/digital-twin/DroneModel';

// ─── Fallback Grid ────────────────────────────────────────────
function GridFallback() {
  const lines = useMemo(() => {
    const items: { points: THREE.Vector3[]; color: string }[] = [];
    for (let i = 0; i <= 20; i++) {
      const pos = -50 + i * 5;
      const c = i % 2 === 0 ? '#1A1A2E' : '#0F0F1A';
      items.push({ points: [new THREE.Vector3(-50, 0, pos), new THREE.Vector3(50, 0, pos)], color: c });
      items.push({ points: [new THREE.Vector3(pos, 0, -50), new THREE.Vector3(pos, 0, 50)], color: c });
    }
    return items;
  }, []);
  return (
    <group>
      {lines.map((l, i) => <DreiLine key={i} points={l.points} color={l.color} lineWidth={0.5} />)}
      <DreiLine points={[new THREE.Vector3(-50,0,-50), new THREE.Vector3(50,0,-50), new THREE.Vector3(50,0,50), new THREE.Vector3(-50,0,50), new THREE.Vector3(-50,0,-50)]} color="#00D4FF" lineWidth={1} transparent opacity={0.3} />
    </group>
  );
}

// ─── Debug Overlay (Html portal) ─────────────────────────────
function DebugOverlay() {
  const { gl, camera } = useThree();
  const [fps, setFps] = useState(0);
  const [draws, setDraws] = useState(0);
  const [tris, setTris] = useState(0);
  const cnt = useRef(0); const lt = useRef(0);
  useFrame(({ clock }) => {
    cnt.current++;
    if (clock.elapsedTime - lt.current > 1) {
      setFps(Math.round(cnt.current / (clock.elapsedTime - lt.current)));
      setDraws(gl.info.render.calls);
      setTris(gl.info.render.triangles);
      cnt.current = 0; lt.current = clock.elapsedTime;
    }
  });
  const t = useDroneStore(s => s.telemetry);
  return (
    <Html position={[-49, 0.5, -49]} zIndexRange={[100,0]} occlude={false}>
      <div className="font-mono text-[8px] leading-tight pointer-events-none select-none" style={{ background:'rgba(5,5,5,0.7)', padding:'3px 6px', borderRadius:'4px', border:'1px solid rgba(26,26,46,0.6)', backdropFilter:'blur(4px)' }}>
        <div style={{ color: fps > 50 ? '#4A5A78' : fps > 20 ? '#FFC857' : '#FF4D5A' }}>{fps || '--'} FPS | {draws} DC | {tris}T</div>
        <div style={{ color: '#4A5A78' }}>BRAIN | NAV | SENSE | PRED</div>
        <div style={{ color: '#6B7FA0' }}>{t.status} | HDG {t.heading.toFixed(0)}° | ALT {t.altitude.toFixed(0)}m</div>
      </div>
    </Html>
  );
}

// ─── Water ────────────────────────────────────────────────────
function WaterSystem({ water }: { water: WaterBody[] }) {
  if (!water?.length) return null;
  return (<group>{water.map((w, i) => {
    if (w.type === 'river') {
      const pts = w.vertices.map(v => new THREE.Vector3(v[0]-50, 0, v[1]-50));
      return (<group key={i}><DreiLine points={pts} color="#1A5C8A" lineWidth={3} transparent opacity={0.4} /><DreiLine points={pts} color="#2A6A9C" lineWidth={6} transparent opacity={0.15} /></group>);
    }
    if (w.type === 'lake') {
      const shape = new THREE.Shape(); w.vertices.forEach((v, idx) => { const x=v[0]-50, z=v[1]-50; idx===0 ? shape.moveTo(x,z) : shape.lineTo(x,z); });
      return (<mesh key={i} rotation={[-Math.PI/2,0,0]} position={[0,-0.2,0]}><shapeGeometry args={[shape]} /><meshStandardMaterial color="#1A5C8A" transparent opacity={0.35} metalness={0.3} roughness={0.4} /></mesh>);
    }
    return null;
  })}</group>);
}

// ─── Trees (GPU Instanced) ───────────────────────────────────
function TreeInstances({ trees, terrainRes, worldSize }: { trees: TreeData[]; terrainRes: number; worldSize: number }) {
  const scale = worldSize / terrainRes;
  const ref = useRef<THREE.InstancedMesh>(null!);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colors = ['#2D5A1E','#3A6B2E','#4A7C34','#1E4A0E'];
  useEffect(() => {
    const m = ref.current; if (!m || !trees.length) return;
    for (let i = 0; i < trees.length; i++) {
      const x = (trees[i].x / terrainRes) * worldSize - worldSize / 2;
      const z = (trees[i].z / terrainRes) * worldSize - worldSize / 2;
      const s = trees[i].scale * scale;
      dummy.position.set(x, s * 0.5, z); dummy.scale.set(s, s, s); dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
      if (m.instanceColor) m.setColorAt(i, new THREE.Color(colors[i % colors.length]));
    }
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }, [trees, scale, dummy]);
  if (!trees.length) return null;
  return (<instancedMesh ref={ref} args={[undefined, undefined, trees.length]} frustumCulled>
    <coneGeometry args={[0.4*scale, 1.2*scale, 6]} />
    <meshStandardMaterial metalness={0} roughness={1} />
  </instancedMesh>);
}

// ─── Roads ───────────────────────────────────────────────────
function RoadNetwork({ roads, terrainRes, worldSize }: { roads: RoadData[]; terrainRes: number; worldSize: number }) {
  const scale = worldSize / terrainRes;
  if (!roads?.length) return null;
  return (<group>{roads.map((r, i) => {
    const pts = r.points.map(p => new THREE.Vector3((p[0]/terrainRes)*worldSize - worldSize/2, 0.02, (p[1]/terrainRes)*worldSize - worldSize/2));
    return <DreiLine key={i} points={pts} color="#666677" lineWidth={r.width * scale * 0.3} transparent opacity={0.6} />;
  })}</group>);
}

// ─── Waypoints ───────────────────────────────────────────────
function Waypoints() {
  const waypoints = useDroneStore(s => s.mission.waypoints);
  const telemetry = useDroneStore(s => s.telemetry);
  if (!waypoints?.length) return null;
  return (<group>{waypoints.map((wp, i) => {
    const isActive = i === 0 || (i > 0 && i <= waypoints.length - 1);
    const color = i === 0 ? '#00FF88' : isActive ? '#FFC857' : '#4A5A78';
    return (<group key={i} position={[wp.x-50, 0.1, wp.y-50]}>
      <mesh rotation={[-Math.PI/2,0,0]}><ringGeometry args={[0.6, 0.9, 32]} /><meshBasicMaterial color={color} transparent opacity={0.7} side={THREE.DoubleSide} /></mesh>
      <DreiLine points={[new THREE.Vector3(0,0,0), new THREE.Vector3(0,3,0)]} color={color} lineWidth={1} transparent opacity={0.3} />
      <mesh position={[0,3,0]}><sphereGeometry args={[0.2,8,8]} /><meshBasicMaterial color={color} /></mesh>
    </group>);
  })}</group>);
}

// ─── Flight Paths ────────────────────────────────────────────
function FlightPath() {
  const visited = useDroneStore(s => s.mission.visited_path);
  const predicted = useDroneStore(s => s.mission.predicted_path);
  const telemetry = useDroneStore(s => s.telemetry);
  const vPts = useMemo(() => visited?.map(p => new THREE.Vector3(p.x-50, 0.05, p.y-50)) || [], [visited]);
  const pPts = useMemo(() => predicted?.map(p => new THREE.Vector3(p.x-50, 0.1, p.y-50)) || [], [predicted]);
  return (<group>
    {vPts.length > 1 && <DreiLine points={vPts} color="#FF6633" lineWidth={2} transparent opacity={0.6} />}
    {pPts.length > 1 && <DreiLine points={pPts} color="#00D4FF" lineWidth={1.5} transparent opacity={0.5} dashed dashSize={0.5} gapSize={0.3} />}
    {/* Safety corridor */}
    {pPts.length > 1 && <DreiLine points={pPts.map(p => new THREE.Vector3(p.x, p.y-0.05, p.z))} color="#00FF88" lineWidth={4} transparent opacity={0.06} />}
    {/* Path from home */}
    {vPts.length > 1 && <DreiLine points={[new THREE.Vector3(5-50,0.02,5-50), vPts[0]]} color="#9D6CFF" lineWidth={1} transparent opacity={0.3} />}
  </group>);
}

// ─── LiDAR Point Cloud ───────────────────────────────────────
function LidarCloud() {
  const t = useDroneStore(s => s.telemetry);
  const ref = useRef<THREE.Points>(null!);
  const positions = useMemo(() => new Float32Array(800 * 3), []);
  const rng = useMemo(() => {
    let s = 12345 % 2147483647; return () => { s = (s * 16807) % 2147483647; return (s-1)/2147483646; };
  }, []);

  useFrame(() => {
    if (!ref.current) return;
    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    const dx = t.position.x - 50; const dz = t.position.y - 50;
    const heading = (t.heading || 0) * Math.PI / 180;
    const y = (t.altitude || 45) / 8;
    for (let i = 0; i < 800; i++) {
      const angle = heading + (rng() - 0.5) * 1.8;
      const dist = 1 + rng() * 10;
      const ht = (rng() - 0.5) * 5;
      pos[i*3] = dx + Math.cos(angle) * dist;
      pos[i*3+1] = ht + y - 2;
      pos[i*3+2] = dz + Math.sin(angle) * dist;
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (<points ref={ref}>
    <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
    <pointsMaterial size={0.06} color="#00FF88" transparent opacity={0.3} sizeAttenuation />
  </points>);
}

// ─── Camera Frustum ──────────────────────────────────────────
function CameraFrustum() {
  const t = useDroneStore(s => s.telemetry);
  const dx = t.position.x - 50; const dz = t.position.y - 50;
  const heading = (t.heading || 0) * Math.PI / 180;
  const y = (t.altitude || 45) / 8;
  const fov = 0.8; const range = 6;
  const pts = [
    new THREE.Vector3(dx, y-0.1, dz),
    new THREE.Vector3(dx + Math.cos(heading - fov/2) * range, y - 0.3, dz + Math.sin(heading - fov/2) * range),
    new THREE.Vector3(dx + Math.cos(heading + fov/2) * range, y - 0.3, dz + Math.sin(heading + fov/2) * range),
  ];
  const pts2 = [
    new THREE.Vector3(dx, y+0.1, dz),
    new THREE.Vector3(dx + Math.cos(heading - fov/2) * range, y + 0.1, dz + Math.sin(heading - fov/2) * range),
    new THREE.Vector3(dx + Math.cos(heading + fov/2) * range, y + 0.1, dz + Math.sin(heading + fov/2) * range),
  ];
  const corners = [
    new THREE.Vector3(dx + Math.cos(heading - fov/2) * range, y - 0.3, dz + Math.sin(heading - fov/2) * range),
    new THREE.Vector3(dx + Math.cos(heading - fov/2) * range, y + 0.1, dz + Math.sin(heading - fov/2) * range),
    new THREE.Vector3(dx + Math.cos(heading + fov/2) * range, y + 0.1, dz + Math.sin(heading + fov/2) * range),
    new THREE.Vector3(dx + Math.cos(heading + fov/2) * range, y - 0.3, dz + Math.sin(heading + fov/2) * range),
  ];
  return (<group>
    <DreiLine points={pts} color="#00D4FF" lineWidth={2} transparent opacity={0.15} />
    <DreiLine points={pts2} color="#00D4FF" lineWidth={2} transparent opacity={0.15} />
    {corners.length === 4 && <DreiLine points={[corners[0], corners[1], corners[2], corners[3], corners[0]]} color="#00D4FF" lineWidth={1} transparent opacity={0.08} />}
  </group>);
}

// ─── No-Fly Zones ───────────────────────────────────────────
function NoFlyZones() {
  return (<group>
    <mesh position={[10,0.5,15]} rotation={[-Math.PI/2,0,0]}><ringGeometry args={[4,5,32]} /><meshBasicMaterial color="#FF4D5A" transparent opacity={0.15} side={THREE.DoubleSide} /></mesh>
    <DreiLine points={[new THREE.Vector3(6,0.05,11), new THREE.Vector3(14,0.05,11), new THREE.Vector3(14,0.05,19), new THREE.Vector3(6,0.05,19), new THREE.Vector3(6,0.05,11)]} color="#FF4D5A" lineWidth={1} transparent opacity={0.3} />
  </group>);
}

// ─── Wind Indicator ──────────────────────────────────────────
function WindIndicator() {
  const w = useDroneStore(s => s.weather);
  const dir = (w.wind_direction || 0) * Math.PI / 180;
  return (<group position={[-45, 8, -45]}>
    <DreiLine points={[new THREE.Vector3(0,0,0), new THREE.Vector3(Math.cos(dir)*4, 0, Math.sin(dir)*4)]} color="#06B6D4" lineWidth={2} transparent opacity={0.4} />
    <mesh position={[Math.cos(dir)*4, 0, Math.sin(dir)*4]}><sphereGeometry args={[0.2,8,8]} /><meshBasicMaterial color="#06B6D4" transparent opacity={0.6} /></mesh>
    <Html position={[0,1,0]} zIndexRange={[100,0]} occlude={false}>
      <div className="text-[8px] font-mono text-[#4A5A78] whitespace-nowrap">WIND {w.wind_speed.toFixed(1)} m/s</div>
    </Html>
  </group>);
}

// ─── GPS Uncertainty Circle ──────────────────────────────────
function GpsUncertainty() {
  const t = useDroneStore(s => s.telemetry);
  const x = t.position.x - 50; const z = t.position.y - 50; const y = (t.altitude || 45) / 8;
  const radius = 0.5 + t.gps_accuracy * 2;
  return (<mesh position={[x, y-0.2, z]} rotation={[-Math.PI/2, 0, 0]}>
    <ringGeometry args={[0, radius, 24]} />
    <meshBasicMaterial color="#00FF88" transparent opacity={0.08} side={THREE.DoubleSide} />
  </mesh>);
}

// ─── Pure world data generator ───────────────────────────────
function generateWorldData() {
  const gen = new WorldGenerator({ size: 100, seed: 42, urbanDensity: 0.6, vegetationDensity: 0.7, waterLevel: 0.4, hilliness: 0.5 });
  const terrainRes = 128;
  const heightmap = gen.generateHeightmap(terrainRes);
  const mesh = gen.generateTerrainMesh(heightmap, terrainRes);
  const buildings = gen.generateBuildings(heightmap, terrainRes);
  const trees = gen.generateTrees(heightmap, terrainRes, buildings);
  const roads = gen.generateRoads(terrainRes);
  const water = gen.generateWater(terrainRes);
  return { mesh, buildings, trees, roads, water, terrainRes, worldSize: 100 };
}
type WorldData = ReturnType<typeof generateWorldData>;

// ─── Lighting ────────────────────────────────────────────────
function SceneLighting() {
  return (<>
    <ambientLight intensity={0.5} color="#6688CC" />
    <directionalLight position={[60, 80, 40]} intensity={1.0} color="#FFEECC" />
    <directionalLight position={[-40, 30, -60]} intensity={0.3} color="#8899FF" />
    <hemisphereLight args={['#6688CC', '#0A0A1A', 0.6]} />
  </>);
}

// ─── Scene Content ───────────────────────────────────────────
function SceneContent({ worldData }: { worldData: WorldData | null }) {
  return (<>
    <SceneLighting />
    <fog attach="fog" args={['#0A0A1A', 80, 150]} />

    {/* World */}
    {worldData ? (
      <>
        <TerrainMesh mesh={worldData.mesh} />
        <WaterSystem water={worldData.water} />
        <RoadNetwork roads={worldData.roads} terrainRes={worldData.terrainRes} worldSize={worldData.worldSize} />
        <Buildings buildings={worldData.buildings} terrainRes={worldData.terrainRes} worldSize={worldData.worldSize} />
        <TreeInstances trees={worldData.trees} terrainRes={worldData.terrainRes} worldSize={worldData.worldSize} />
      </>
    ) : <GridFallback />}

    {/* Sensors */}
    <LidarCloud />
    <CameraFrustum />
    <GpsUncertainty />
    <WindIndicator />

    {/* Navigation */}
    <Waypoints />
    <FlightPath />
    <NoFlyZones />

    {/* Drone */}
    <DroneModel />

    {/* Overlay */}
    <DebugOverlay />

    <OrbitControls
      enablePan enableZoom enableRotate
      minDistance={3} maxDistance={180}
      maxPolarAngle={Math.PI / 2.05}
      target={[0, 0, 0]}
      dampingFactor={0.12}
      enableDamping
    />
  </>);
}

// ─── Canvas Inner ────────────────────────────────────────────
function CanvasInner({ worldData }: { worldData: WorldData | null }) {
  return (<Suspense fallback={null}><SceneContent worldData={worldData} /></Suspense>);
}

// ─── Main Export ─────────────────────────────────────────────
export default function MissionMapCanvas() {
  const [worldData, setWorldData] = useState<WorldData | null>(null);
  const [worldError, setWorldError] = useState<string | null>(null);
  const [webglOk, setWebglOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    try {
      const c = document.createElement('canvas');
      const gl = c.getContext('webgl2') || c.getContext('webgl');
      if (!gl) { if (!cancelled) setWebglOk(false); return; }
      if (!cancelled) setWebglOk(true);
      const data = generateWorldData();
      if (!cancelled) setWorldData(data);
    } catch (e) {
      if (!cancelled) setWorldError(e instanceof Error ? `${e.message} [${e.stack?.split('\n')[1]?.trim()}]` : String(e));
    }
    return () => { cancelled = true; };
  }, []);

  if (webglOk === false) return <div className="w-full h-full flex items-center justify-center bg-[#080810] text-[#FF4D5A] text-xs font-mono">WebGL unavailable</div>;
  if (worldError) return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-[#080810] p-4">
      <div className="text-[#FF4D5A] text-xs font-mono mb-1">⚠ 3D ENGINE</div>
      <pre className="text-[#6B7FA0] text-[8px] font-mono max-w-md text-center">{worldError}</pre>
      <button onClick={() => window.location.reload()} className="mt-2 px-3 py-1 text-[10px] font-mono bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.3)] text-[#00D4FF] rounded">RELOAD</button>
    </div>
  );

  return (
    <ThreeErrorBoundary>
      <div className="w-full h-full" style={{ background: '#0A0A1A' }}>
        {!worldData && <div className="absolute top-2 left-1/2 -translate-x-1/2 z-10 text-[#4A5A78] text-[9px] font-mono">Generating Digital Twin...</div>}
        <Canvas
          camera={{ position: [60, 40, 60], fov: 50, near: 0.1, far: 200 }}
          gl={{ antialias: true, alpha: false, powerPreference: 'high-performance', toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.0 }}
          dpr={[1, 2]}
          style={{ width: '100%', height: '100%' }}
          onCreated={(s) => console.log('[DT] Canvas ready:', s.gl.capabilities)}
        >
          <CanvasInner worldData={worldData} />
        </Canvas>
      </div>
    </ThreeErrorBoundary>
  );
}