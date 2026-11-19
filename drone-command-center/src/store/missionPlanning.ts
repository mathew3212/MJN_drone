import { GeneratedMission } from './missionGenerator';

export interface PlannedLocation {
  latitude: number;
  longitude: number;
  label: string;
}

export interface MissionPlan {
  name: string;
  start: PlannedLocation | null;
  destination: PlannedLocation | null;
  stops: PlannedLocation[];
  cruiseAltitude: number;
  speed: number;
}

export interface PlanValidation {
  distance: number;
  batteryBudget: number;
  errors: string[];
}

const EARTH_RADIUS_METERS = 6_371_000;
const MAX_ROUTE_DISTANCE_METERS = 6_500;
const MIN_POINT_SEPARATION_METERS = 20;
const MIN_BATTERY_RESERVE_PERCENT = 15;

// Demonstration operational constraints for the built-in Bangalore simulator.
// A production controller must replace these with authoritative airspace data.
const RESTRICTED_AREAS = [
  { latitude: 13.01, longitude: 77.62, radius: 800, name: 'Airport controlled airspace' },
  { latitude: 12.99, longitude: 77.54, radius: 300, name: 'Military facility exclusion zone' },
  { latitude: 12.95, longitude: 77.64, radius: 200, name: 'Government building exclusion zone' },
];

export function haversineDistance(a: PlannedLocation, b: PlannedLocation): number {
  const dLat = ((b.latitude - a.latitude) * Math.PI) / 180;
  const dLng = ((b.longitude - a.longitude) * Math.PI) / 180;
  const latA = (a.latitude * Math.PI) / 180;
  const latB = (b.latitude * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(latA) * Math.cos(latB) * Math.sin(dLng / 2) ** 2;
  return EARTH_RADIUS_METERS * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function isValidLocation(location: PlannedLocation): boolean {
  return Number.isFinite(location.latitude) && Number.isFinite(location.longitude)
    && Math.abs(location.latitude) <= 90 && Math.abs(location.longitude) <= 180;
}

function segmentDistanceToPoint(a: PlannedLocation, b: PlannedLocation, point: PlannedLocation): number {
  // Local equirectangular projection is accurate enough for the short routes
  // accepted by this simulator and lets us validate the entire route segment.
  const latitudeScale = 111_320;
  const longitudeScale = latitudeScale * Math.cos((a.latitude * Math.PI) / 180);
  const bx = (b.longitude - a.longitude) * longitudeScale;
  const by = (b.latitude - a.latitude) * latitudeScale;
  const px = (point.longitude - a.longitude) * longitudeScale;
  const py = (point.latitude - a.latitude) * latitudeScale;
  const lengthSquared = bx * bx + by * by;
  const fraction = lengthSquared === 0 ? 0 : Math.max(0, Math.min(1, (px * bx + py * by) / lengthSquared));
  return Math.hypot(px - fraction * bx, py - fraction * by);
}

export function validateMissionPlan(plan: MissionPlan): PlanValidation {
  const errors: string[] = [];
  if (!plan.start) errors.push('Choose a starting point.');
  if (!plan.destination) errors.push('Choose a destination point.');
  if (!Number.isFinite(plan.cruiseAltitude) || plan.cruiseAltitude < 30 || plan.cruiseAltitude > 400) errors.push('Cruise altitude must be between 30 m and 400 m.');
  if (!Number.isFinite(plan.speed) || plan.speed < 2 || plan.speed > 25) errors.push('Cruise speed must be between 2 m/s and 25 m/s.');

  const points = [plan.start, ...plan.stops, plan.destination].filter((point): point is PlannedLocation => point !== null);
  points.forEach((point, index) => {
    if (!isValidLocation(point)) errors.push(`Route point ${index + 1} has invalid coordinates.`);
  });

  let distance = 0;
  for (let index = 1; index < points.length; index++) {
    const segment = haversineDistance(points[index - 1], points[index]);
    distance += segment;
    if (segment < MIN_POINT_SEPARATION_METERS) errors.push('Each route point must be at least 20 m apart.');
    for (const area of RESTRICTED_AREAS) {
      const clearance = segmentDistanceToPoint(points[index - 1], points[index], { ...area, label: area.name });
      if (clearance < area.radius) errors.push(`Route enters ${area.name}. Choose a different route.`);
    }
  }

  if (distance > MAX_ROUTE_DISTANCE_METERS) errors.push('Route exceeds the simulator’s 6.5 km safe operating range.');
  const batteryBudget = Math.ceil(5 + distance * 0.012);
  if (batteryBudget > 100 - MIN_BATTERY_RESERVE_PERCENT) errors.push(`Route needs ${batteryBudget}% battery; keep at least ${MIN_BATTERY_RESERVE_PERCENT}% reserve.`);
  return { distance, batteryBudget, errors: [...new Set(errors)] };
}

export function createMissionFromPlan(plan: MissionPlan): GeneratedMission {
  const validation = validateMissionPlan(plan);
  if (validation.errors.length > 0 || !plan.start || !plan.destination) {
    throw new Error(validation.errors[0] || 'The mission plan is incomplete.');
  }
  const route = [plan.start, ...plan.stops, plan.destination];
  const waypoints = route.map((location, index) => ({
    lat: location.latitude,
    lng: location.longitude,
    alt: plan.cruiseAltitude,
    label: index === 0 ? 'START' : index === route.length - 1 ? 'DESTINATION' : `STOP ${index}`,
    type: index === 0 ? 'home' : index === route.length - 1 ? 'land' : 'waypoint',
    hover: index === route.length - 1 ? 0 : 1,
  }));
  const latitudes = route.map((location) => location.latitude);
  const longitudes = route.map((location) => location.longitude);
  const idSuffix = Math.random().toString(36).slice(2, 7).toUpperCase();
  return {
    id: `MJN-${idSuffix}-PLAN`,
    type: 'package-delivery',
    missionName: plan.name.trim() || 'Operator Planned Mission',
    homeLat: plan.start.latitude,
    homeLng: plan.start.longitude,
    homeAlt: plan.cruiseAltitude,
    homeAddress: plan.start.label,
    takeoffLat: plan.start.latitude,
    takeoffLng: plan.start.longitude,
    takeoffAlt: plan.cruiseAltitude,
    destinationLat: plan.destination.latitude,
    destinationLng: plan.destination.longitude,
    destinationAlt: plan.cruiseAltitude,
    destinationAddress: plan.destination.label,
    waypoints,
    cruiseAltitude: plan.cruiseAltitude,
    missionSpeed: plan.speed,
    estimatedFlightTime: Math.max(1, Math.ceil(validation.distance / plan.speed)),
    batteryBudget: validation.batteryBudget,
    objective: `Fly the operator-planned route with ${plan.stops.length} scheduled stop${plan.stops.length === 1 ? '' : 's'}.`,
    difficulty: validation.distance > 3_000 ? 'medium' : 'easy',
    priority: 'normal',
    boundary: {
      north: Math.max(...latitudes) + 0.002,
      south: Math.min(...latitudes) - 0.002,
      east: Math.max(...longitudes) + 0.002,
      west: Math.min(...longitudes) - 0.002,
    },
    totalDistance: Math.round(validation.distance),
  };
}
