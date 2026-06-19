'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useDroneStore } from '@/store/droneStore';

/**
 * Drone model with direct Three.js imperative updates every frame.
 * No React props for position/rotation — uses useFrame + groupRef
 * to achieve 60fps smooth interpolation.
 */
export default function DroneModel() {
  const groupRef = useRef<THREE.Group>(null!);
  const posRef = useRef(new THREE.Vector3(0, 3, 0));
  const yawRef = useRef(0);

  // Rotor refs
  const r1 = useRef<THREE.Mesh>(null!);
  const r2 = useRef<THREE.Mesh>(null!);
  const r3 = useRef<THREE.Mesh>(null!);
  const r4 = useRef<THREE.Mesh>(null!);
  const gimbalRef = useRef<THREE.Mesh>(null!);

  // Read fresh state every frame — no stale closures
  useFrame(({ clock }) => {
    const t = useDroneStore.getState().telemetry;
    const target = new THREE.Vector3(
      t.position.x - 50,
      (t.altitude || 45) / 6, // higher altitude for visibility
      t.position.y - 50,
    );
    const targetYaw = -((t.heading || 0) * Math.PI) / 180 + Math.PI / 2;

    // Smooth interpolation
    posRef.current.lerp(target, 0.15);
    yawRef.current += (targetYaw - yawRef.current) * 0.15;

    // Direct Three.js imperative update on the group — bypasses React reconciliation
    if (groupRef.current) {
      groupRef.current.position.copy(posRef.current);
      groupRef.current.rotation.y = yawRef.current;
    }

    // Rotors
    const speed = 45;
    if (r1.current) r1.current.rotation.y = clock.elapsedTime * speed;
    if (r2.current) r2.current.rotation.y = -clock.elapsedTime * speed;
    if (r3.current) r3.current.rotation.y = clock.elapsedTime * speed;
    if (r4.current) r4.current.rotation.y = -clock.elapsedTime * speed;

    // Gimbal stabilization
    if (gimbalRef.current) {
      gimbalRef.current.rotation.x = -t.pitch * 0.02;
      gimbalRef.current.rotation.z = -t.roll * 0.02;
    }
  });

  return (
    <group ref={groupRef} position={[0, 3, 0]} rotation={[0, 0, 0]}>
      {/* Carbon fiber body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.8, 0.15, 0.5]} />
        <meshStandardMaterial color="#1a1a1a" metalness={0.8} roughness={0.2} />
      </mesh>

      {/* Central dome */}
      <mesh position={[0, 0.1, 0]}>
        <sphereGeometry args={[0.25, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#222" metalness={0.6} roughness={0.3} />
      </mesh>

      {/* Arms */}
      {([[-0.45, -0.05, -0.35], [0.45, -0.05, -0.35], [-0.45, -0.05, 0.35], [0.45, -0.05, 0.35]] as const).map((pos, i) => (
        <group key={`arm-${i}`} position={pos as unknown as THREE.Vector3}>
          <mesh rotation={[0, 0, 0]}>
            <cylinderGeometry args={[0.025, 0.035, 0.5, 6]} />
            <meshStandardMaterial color="#333" metalness={0.7} roughness={0.3} />
          </mesh>
          <mesh position={[0, 0.05, 0]}>
            <cylinderGeometry args={[0.06, 0.08, 0.08, 12]} />
            <meshStandardMaterial color="#444" metalness={0.9} roughness={0.2} />
          </mesh>
        </group>
      ))}

      {/* Propellers */}
      <mesh ref={r1} position={[-0.45, 0.08, -0.35]}>
        <cylinderGeometry args={[0.3, 0.3, 0.015, 4]} />
        <meshStandardMaterial color="#555" transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={r2} position={[0.45, 0.08, -0.35]}>
        <cylinderGeometry args={[0.3, 0.3, 0.015, 4]} />
        <meshStandardMaterial color="#555" transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={r3} position={[-0.45, 0.08, 0.35]}>
        <cylinderGeometry args={[0.3, 0.3, 0.015, 4]} />
        <meshStandardMaterial color="#555" transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={r4} position={[0.45, 0.08, 0.35]}>
        <cylinderGeometry args={[0.3, 0.3, 0.015, 4]} />
        <meshStandardMaterial color="#555" transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>

      {/* Camera gimbal */}
      <group ref={gimbalRef} position={[0, -0.05, -0.3]}>
        <mesh><sphereGeometry args={[0.04, 12, 12]} /><meshStandardMaterial color="#111" metalness={0.9} roughness={0.1} /></mesh>
        <mesh position={[0, 0, -0.05]}><cylinderGeometry args={[0.02, 0.03, 0.02, 12]} /><meshStandardMaterial color="#1a3a6a" metalness={0.3} roughness={0.5} /></mesh>
      </group>

      {/* GPS/Compass */}
      <mesh position={[0, 0.18, 0.15]}>
        <boxGeometry args={[0.12, 0.02, 0.08]} />
        <meshStandardMaterial color="#2a2a2a" metalness={0.5} roughness={0.4} />
      </mesh>

      {/* LiDAR */}
      <mesh position={[0, -0.05, -0.25]}>
        <cylinderGeometry args={[0.03, 0.05, 0.06, 12]} />
        <meshStandardMaterial color="#1a3a2a" metalness={0.6} roughness={0.3} />
      </mesh>

      {/* Landing gear */}
      {([[-0.2, -0.12, -0.2], [0.2, -0.12, -0.2], [-0.2, -0.12, 0.2], [0.2, -0.12, 0.2]] as const).map((pos, i) => (
        <mesh key={`leg-${i}`} position={pos as unknown as THREE.Vector3}>
          <cylinderGeometry args={[0.015, 0.02, 0.06, 6]} />
          <meshStandardMaterial color="#555" metalness={0.4} roughness={0.6} />
        </mesh>
      ))}

      {/* Status LEDs */}
      <mesh position={[-0.45, 0.02, -0.5]}><sphereGeometry args={[0.02, 8, 8]} /><meshBasicMaterial color="#00FF88" /></mesh>
      <mesh position={[0.45, 0.02, -0.5]}><sphereGeometry args={[0.02, 8, 8]} /><meshBasicMaterial color="#00FF88" /></mesh>
      <mesh position={[-0.45, 0.02, 0.5]}><sphereGeometry args={[0.02, 8, 8]} /><meshBasicMaterial color="#FF3333" /></mesh>
      <mesh position={[0.45, 0.02, 0.5]}><sphereGeometry args={[0.02, 8, 8]} /><meshBasicMaterial color="#FF3333" /></mesh>

      {/* Glow aura */}
      <mesh><sphereGeometry args={[0.6, 16, 16]} /><meshBasicMaterial color="#FF6600" transparent opacity={0.04} /></mesh>

      {/* Heading indicator */}
      <mesh position={[0, 0, -0.8]}>
        <boxGeometry args={[0.01, 0.01, 0.4]} />
        <meshBasicMaterial color="#FF5500" transparent opacity={0.4} />
      </mesh>
    </group>
  );
}