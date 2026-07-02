'use client';

// =============================================================================
// MJN Drone OS - Mission Generator
// Generates unique, realistic missions on every launch.
// Each mission type produces appropriate waypoint patterns.
// =============================================================================

export type MissionType =
  | 'infrastructure-inspection'
  | 'solar-farm-survey'
  | 'power-line-inspection'
  | 'bridge-inspection'
  | 'pipeline-inspection'
  | 'agricultural-survey'
  | 'construction-survey'
  | 'search-and-rescue'
  | 'security-patrol'
  | 'package-delivery'
  | 'mapping-mission'
  | 'environmental-monitoring';

export interface GeneratedMission {
  id: string;
  type: MissionType;
  missionName: string;
  homeLat: number;
  homeLng: number;
  homeAlt: number;
  homeAddress: string;
  takeoffLat: number;
  takeoffLng: number;
  takeoffAlt: number;
  destinationLat: number;
  destinationLng: number;
  destinationAlt: number;
  destinationAddress: string;
  waypoints: Array<{ lat: number; lng: number; alt: number; label: string; type: string; hover?: number }>;
  cruiseAltitude: number;
  missionSpeed: number;
  estimatedFlightTime: number;
  batteryBudget: number;
  objective: string;
  difficulty: 'easy' | 'medium' | 'hard';
  priority: 'low' | 'normal' | 'high' | 'critical';
  boundary: { north: number; south: number; east: number; west: number };
  totalDistance: number;
}

const MISSION_TYPES: Array<{ type: MissionType; name: string; objective: string }> = [
  { type: 'infrastructure-inspection', name: 'Infrastructure Inspection', objective: 'Inspect structural integrity of urban infrastructure assets' },
  { type: 'solar-farm-survey', name: 'Solar Farm Survey', objective: 'Thermal and visual survey of solar panel arrays' },
  { type: 'power-line-inspection', name: 'Power Line Inspection', objective: 'Inspect high-voltage transmission line corridors' },
  { type: 'bridge-inspection', name: 'Bridge Inspection', objective: 'Structural inspection of bridge supports and deck' },
  { type: 'pipeline-inspection', name: 'Pipeline Inspection', objective: 'Monitor pipeline right-of-way and detect anomalies' },
  { type: 'agricultural-survey', name: 'Agricultural Survey', objective: 'Multispectral crop health assessment' },
  { type: 'construction-survey', name: 'Construction Survey', objective: 'Monitor construction progress and stockpile volumes' },
  { type: 'search-and-rescue', name: 'Search and Rescue', objective: 'Grid search for missing person in designated area' },
  { type: 'security-patrol', name: 'Security Patrol', objective: 'Perimeter security patrol of facility boundary' },
  { type: 'package-delivery', name: 'Package Delivery', objective: 'Autonomous delivery of payload to designated drop zone' },
  { type: 'mapping-mission', name: 'Mapping Mission', objective: 'High-resolution orthophoto mapping of survey area' },
  { type: 'environmental-monitoring', name: 'Environmental Monitoring', objective: 'Monitor environmental conditions in protected area' },
];

function randomInRange(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function randomInt(min: number, max: number): number {
  return Math.floor(randomInRange(min, max + 1));
}

// Check if a point is inside any restricted zone
function isInRestrictedZone(lat: number, lng: number, zones: Array<{ lat: number; lng: number; radius: number }>): boolean {
  for (const zone of zones) {
    const dLat = ((lat - zone.lat) * Math.PI) / 180;
    const dLng = ((lng - zone.lng) * Math.PI) / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos((zone.lat * Math.PI) / 180) * Math.cos((lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
    const dist = 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    if (dist < zone.radius) return true;
  }
  return false;
}

// Restricted zones around Bangalore
const RESTRICTED_ZONES = [
  { lat: 13.01, lng: 77.62, radius: 800, name: 'Airport CTR' },
  { lat: 12.99, lng: 77.54, radius: 300, name: 'Military Facility' },
  { lat: 12.95, lng: 77.64, radius: 200, name: 'Government Building' },
];

function haversine(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function generateValidPoint(
  centerLat: number,
  centerLng: number,
  minDist: number,
  maxDist: number,
  existing: Array<{ lat: number; lng: number }>,
  minSeparation: number
): { lat: number; lng: number } | null {
  for (let attempt = 0; attempt < 50; attempt++) {
    const angle = Math.random() * 2 * Math.PI;
    const dist = randomInRange(minDist, maxDist);
    const dLat = (dist / 111320) * Math.cos(angle);
    const dLng = (dist / (111320 * Math.cos((centerLat * Math.PI) / 180))) * Math.sin(angle);
    const lat = centerLat + dLat;
    const lng = centerLng + dLng;

    if (isInRestrictedZone(lat, lng, RESTRICTED_ZONES)) continue;

    let tooClose = false;
    for (const p of existing) {
      if (haversine(lat, lng, p.lat, p.lng) < minSeparation) {
        tooClose = true;
        break;
      }
    }
    if (tooClose) continue;

    return { lat, lng };
  }
  return null;
}

function generateWaypointsForMission(
  type: MissionType,
  homeLat: number,
  homeLng: number,
  cruiseAlt: number
): Array<{ lat: number; lng: number; alt: number; label: string; type: string; hover?: number }> {
  const wps: Array<{ lat: number; lng: number; alt: number; label: string; type: string; hover?: number }> = [];
  const existing = [{ lat: homeLat, lng: homeLng }];
  const minSep = 50; // meters minimum separation
  const maxDist = 2000; // max distance from home

  switch (type) {
    case 'power-line-inspection': {
      // Linear corridor pattern
      const angle = randomInRange(0, Math.PI);
      const corridorLength = randomInRange(500, 1500);
      const numPoles = randomInt(4, 8);
      const spacing = corridorLength / (numPoles - 1);
      for (let i = 0; i < numPoles; i++) {
        const d = i * spacing;
        const lat = homeLat + (d / 111320) * Math.cos(angle);
        const lng = homeLng + (d / (111320 * Math.cos((homeLat * Math.PI) / 180))) * Math.sin(angle);
        if (!isInRestrictedZone(lat, lng, RESTRICTED_ZONES)) {
          wps.push({ lat, lng, alt: cruiseAlt, label: `POLE-${String(i + 1).padStart(2, '0')}`, type: 'inspect', hover: 2 });
          existing.push({ lat, lng });
        }
      }
      break;
    }

    case 'solar-farm-survey':
    case 'agricultural-survey':
    case 'mapping-mission': {
      // Grid pattern
      const gridSize = randomInt(3, 5);
      const spacing = randomInRange(80, 150);
      for (let row = 0; row < gridSize; row++) {
        for (let col = 0; col < gridSize; col++) {
          const dLat = (col * spacing) / 111320;
          const dLng = (row * spacing) / (111320 * Math.cos((homeLat * Math.PI) / 180));
          const lat = homeLat + dLat + randomInRange(-0.0002, 0.0002);
          const lng = homeLng + dLng + randomInRange(-0.0002, 0.0002);
          if (!isInRestrictedZone(lat, lng, RESTRICTED_ZONES)) {
            wps.push({ lat, lng, alt: cruiseAlt, label: `GRID-${row}-${col}`, type: 'survey', hover: 0.5 });
            existing.push({ lat, lng });
          }
        }
      }
      break;
    }

    case 'search-and-rescue': {
      // Expanding spiral search pattern
      const numRings = randomInt(3, 5);
      const ringSpacing = randomInRange(60, 100);
      for (let ring = 0; ring < numRings; ring++) {
        const pointsPerRing = 4 + ring * 2;
        const radius = ringSpacing * (ring + 1);
        for (let pt = 0; pt < pointsPerRing; pt++) {
          const angle = (pt / pointsPerRing) * 2 * Math.PI + ring * 0.5;
          const dLat = (radius / 111320) * Math.cos(angle);
          const dLng = (radius / (111320 * Math.cos((homeLat * Math.PI) / 180))) * Math.sin(angle);
          const lat = homeLat + dLat;
          const lng = homeLng + dLng;
          if (!isInRestrictedZone(lat, lng, RESTRICTED_ZONES)) {
            wps.push({ lat, lng, alt: cruiseAlt - randomInRange(0, 20), label: `SRCH-${ring}-${pt}`, type: 'search', hover: 1 });
            existing.push({ lat, lng });
          }
        }
      }
      break;
    }

    case 'bridge-inspection': {
      // Linear pattern along bridge
      const bridgeAngle = randomInRange(0, Math.PI);
      const bridgeLength = randomInRange(200, 600);
      const numPoints = randomInt(4, 8);
      for (let i = 0; i < numPoints; i++) {
        const d = (i / (numPoints - 1)) * bridgeLength - bridgeLength / 2;
        const lat = homeLat + (d / 111320) * Math.cos(bridgeAngle);
        const lng = homeLng + (d / (111320 * Math.cos((homeLat * Math.PI) / 180))) * Math.sin(bridgeAngle);
        if (!isInRestrictedZone(lat, lng, RESTRICTED_ZONES)) {
          wps.push({ lat, lng, alt: cruiseAlt - 20 + randomInRange(-10, 10), label: `BRG-${String(i + 1).padStart(2, '0')}`, type: 'inspect', hover: 3 });
          existing.push({ lat, lng });
        }
      }
      break;
    }

    case 'security-patrol': {
      // Perimeter rectangle
      const rectW = randomInRange(200, 500);
      const rectH = randomInRange(200, 500);
      const corners = [
        { lat: homeLat - rectW / 2 / 111320, lng: homeLng - rectH / 2 / (111320 * Math.cos((homeLat * Math.PI) / 180)) },
        { lat: homeLat + rectW / 2 / 111320, lng: homeLng - rectH / 2 / (111320 * Math.cos((homeLat * Math.PI) / 180)) },
        { lat: homeLat + rectW / 2 / 111320, lng: homeLng + rectH / 2 / (111320 * Math.cos((homeLat * Math.PI) / 180)) },
        { lat: homeLat - rectW / 2 / 111320, lng: homeLng + rectH / 2 / (111320 * Math.cos((homeLat * Math.PI) / 180)) },
      ];
      for (const c of corners) {
        if (!isInRestrictedZone(c.lat, c.lng, RESTRICTED_ZONES)) {
          wps.push({ lat: c.lat, lng: c.lng, alt: cruiseAlt, label: 'PATROL', type: 'patrol' });
          existing.push({ lat: c.lat, lng: c.lng });
        }
      }
      break;
    }

    case 'package-delivery': {
      // Direct point-to-point
      const dest = generateValidPoint(homeLat, homeLng, 300, 1500, existing, 200);
      if (dest) {
        wps.push({ lat: dest.lat, lng: dest.lng, alt: cruiseAlt, label: 'DROP-ZONE', type: 'land' });
        existing.push(dest);
      }
      break;
    }

    case 'construction-survey': {
      // Random survey points in area
      const numPoints = randomInt(5, 10);
      for (let i = 0; i < numPoints; i++) {
        const pt = generateValidPoint(homeLat, homeLng, 30, 400, existing, minSep);
        if (pt) {
          wps.push({ lat: pt.lat, lng: pt.lng, alt: cruiseAlt + randomInRange(-15, 15), label: `SURVEY-${String(i + 1).padStart(2, '0')}`, type: 'survey', hover: 1 });
          existing.push(pt);
        }
      }
      break;
    }

    default: {
      // Generic waypoint pattern (infrastructure, pipeline, environmental)
      const numWps = randomInt(4, 8);
      for (let i = 0; i < numWps; i++) {
        const pt = generateValidPoint(homeLat, homeLng, 50, maxDist, existing, minSep);
        if (pt) {
          wps.push({ lat: pt.lat, lng: pt.lng, alt: cruiseAlt + randomInRange(-10, 10), label: `WP-${String(i + 1).padStart(2, '0')}`, type: 'inspect', hover: randomInRange(0, 2) });
          existing.push(pt);
        }
      }
      break;
    }
  }

  // Add return-to-home waypoint
  wps.push({ lat: homeLat, lng: homeLng, alt: cruiseAlt, label: 'RTH', type: 'home' });

  return wps;
}

export function generateMission(): GeneratedMission {
  // Random home within Bangalore area with slight variation
  const baseLat = 12.9716 + randomInRange(-0.02, 0.04);
  const baseLng = 77.5946 + randomInRange(-0.02, 0.03);

  // Pick mission type
  const typeIdx = randomInt(0, MISSION_TYPES.length - 1);
  const missionInfo = MISSION_TYPES[typeIdx];

  // Cruise altitude based on mission type
  const altitudeMap: Record<string, number> = {
    'infrastructure-inspection': randomInRange(80, 150),
    'solar-farm-survey': randomInRange(100, 200),
    'power-line-inspection': randomInRange(60, 100),
    'bridge-inspection': randomInRange(40, 80),
    'pipeline-inspection': randomInRange(60, 120),
    'agricultural-survey': randomInRange(100, 200),
    'construction-survey': randomInRange(80, 150),
    'search-and-rescue': randomInRange(80, 120),
    'security-patrol': randomInRange(50, 100),
    'package-delivery': randomInRange(80, 120),
    'mapping-mission': randomInRange(150, 250),
    'environmental-monitoring': randomInRange(100, 200),
  };

  // Speed based on mission type (m/s)
  const speedMap: Record<string, number> = {
    'infrastructure-inspection': randomInRange(8, 14),
    'solar-farm-survey': randomInRange(12, 18),
    'power-line-inspection': randomInRange(8, 12),
    'bridge-inspection': randomInRange(6, 10),
    'pipeline-inspection': randomInRange(10, 15),
    'agricultural-survey': randomInRange(14, 20),
    'construction-survey': randomInRange(8, 14),
    'search-and-rescue': randomInRange(12, 18),
    'security-patrol': randomInRange(10, 15),
    'package-delivery': randomInRange(15, 22),
    'mapping-mission': randomInRange(12, 18),
    'environmental-monitoring': randomInRange(10, 16),
  };

  const cruiseAlt = altitudeMap[missionInfo.type] || 100;
  const missionSpeed = speedMap[missionInfo.type] || 8;

  // Generate waypoints
  const waypoints = generateWaypointsForMission(missionInfo.type, baseLat, baseLng, cruiseAlt);

  // Add home waypoint
  const allWaypoints = [
    { lat: baseLat, lng: baseLng, alt: cruiseAlt, label: 'HOME', type: 'home' },
    ...waypoints,
  ];

  // Calculate total distance
  let totalDist = 0;
  for (let i = 1; i < allWaypoints.length; i++) {
    totalDist += haversine(
      allWaypoints[i - 1].lat, allWaypoints[i - 1].lng,
      allWaypoints[i].lat, allWaypoints[i].lng
    );
  }

  // Calculate estimated flight time (seconds)
  const estimatedFlightTime = totalDist / missionSpeed;

  // Battery budget (rough: 1% per ~80m flown at cruise)
  const batteryPerMeter = 0.012; // percent per meter
  const batteryBudget = Math.min(100, totalDist * batteryPerMeter + 5);

  // Difficulty based on distance and waypoints
  let difficulty: 'easy' | 'medium' | 'hard' = 'easy';
  if (totalDist > 3000 || allWaypoints.length > 8) difficulty = 'medium';
  if (totalDist > 6000 || allWaypoints.length > 12) difficulty = 'hard';

  // Priority
  const priorities: Array<'low' | 'normal' | 'high' | 'critical'> = ['low', 'normal', 'high', 'critical'];
  const priority = priorities[Math.floor(Math.random() * priorities.length)];

  // Boundary
  let minLat = allWaypoints[0].lat, maxLat = allWaypoints[0].lat;
  let minLng = allWaypoints[0].lng, maxLng = allWaypoints[0].lng;
  for (const wp of allWaypoints) {
    minLat = Math.min(minLat, wp.lat);
    maxLat = Math.max(maxLat, wp.lat);
    minLng = Math.min(minLng, wp.lng);
    maxLng = Math.max(maxLng, wp.lng);
  }
  // Add padding
  const pad = 0.002;
  const boundary = {
    north: maxLat + pad,
    south: minLat - pad,
    east: maxLng + pad,
    west: minLng - pad,
  };

  // Destination (last non-home waypoint)
  const destination = allWaypoints[allWaypoints.length - 2];

  return {
    id: `MJN-${String(Math.floor(Math.random() * 9999)).padStart(4, '0')}-${missionInfo.type.substring(0, 4).toUpperCase()}`,
    type: missionInfo.type,
    missionName: missionInfo.name,
    homeLat: baseLat,
    homeLng: baseLng,
    homeAlt: cruiseAlt,
    homeAddress: `${baseLat.toFixed(4)}, ${baseLng.toFixed(4)} · Bangalore, Karnataka, India`,
    takeoffLat: baseLat,
    takeoffLng: baseLng,
    takeoffAlt: cruiseAlt,
    destinationLat: destination?.lat ?? baseLat,
    destinationLng: destination?.lng ?? baseLng,
    destinationAlt: destination?.alt ?? cruiseAlt,
    destinationAddress: `${(destination?.lat ?? baseLat).toFixed(4)}, ${(destination?.lng ?? baseLng).toFixed(4)} · Bangalore, Karnataka, India`,
    waypoints: allWaypoints,
    cruiseAltitude: cruiseAlt,
    missionSpeed,
    estimatedFlightTime: Math.round(estimatedFlightTime),
    batteryBudget: Math.round(batteryBudget),
    objective: missionInfo.objective,
    difficulty,
    priority,
    boundary,
    totalDistance: Math.round(totalDist),
  };
}