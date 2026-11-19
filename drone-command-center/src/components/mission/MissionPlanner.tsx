'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  AlertTriangle,
  Battery,
  CheckCircle2,
  ChevronRight,
  Circle,
  Gauge,
  MapPin,
  Mountain,
  Navigation,
  Plane,
  Plus,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import type { GeneratedMission } from '@/store/missionGenerator';
import { MissionPlan, PlannedLocation, createMissionFromPlan, validateMissionPlan } from '@/store/missionPlanning';

type SelectMode = 'start' | 'destination' | 'stop';
type SearchPlace = { display_name: string; lat: string; lon: string };

const DEFAULT_CENTER: L.LatLngExpression = [12.9716, 77.5946];
const DEMO_START: PlannedLocation = { latitude: 12.9716, longitude: 77.5946, label: 'Bengaluru city centre' };
const DEMO_DESTINATION: PlannedLocation = { latitude: 12.9764, longitude: 77.6031, label: 'Ulsoor route destination' };

function coordinateLabel(latitude: number, longitude: number): string {
  return `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
}

function formatDistance(distance: number): string {
  return distance >= 1_000 ? `${(distance / 1_000).toFixed(2)} km` : `${Math.round(distance)} m`;
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '—';
  const minutes = Math.ceil(seconds / 60);
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function parseCoordinates(value: string): PlannedLocation | null {
  const match = value.trim().match(/^(-?\d{1,2}(?:\.\d+)?)\s*[,\s]\s*(-?\d{1,3}(?:\.\d+)?)$/);
  if (!match) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return null;
  return { latitude, longitude, label: coordinateLabel(latitude, longitude) };
}

function locationIcon(color: string, text: string): L.DivIcon {
  return L.divIcon({
    className: 'mission-planner-marker',
    html: `<span style="display:grid;place-items:center;width:30px;height:30px;border-radius:12px 12px 12px 2px;transform:rotate(-45deg);background:${color};border:2px solid rgba(255,255,255,.88);box-shadow:0 6px 16px rgba(0,0,0,.35)"><b style="transform:rotate(45deg);font:700 10px sans-serif;color:#fff">${text}</b></span>`,
    iconSize: [32, 32],
    iconAnchor: [16, 29],
  });
}

export default function MissionPlanner({ onLaunch }: { onLaunch: (mission: GeneratedMission) => void }) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routeLayerRef = useRef<L.LayerGroup | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [selectMode, setSelectMode] = useState<SelectMode>('start');
  const [start, setStart] = useState<PlannedLocation | null>(null);
  const [destination, setDestination] = useState<PlannedLocation | null>(null);
  const [stops, setStops] = useState<PlannedLocation[]>([]);
  const [name, setName] = useState('My first flight');
  const [cruiseAltitude, setCruiseAltitude] = useState(120);
  const [speed, setSpeed] = useState(12);
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<SearchPlace[]>([]);
  const [searchMessage, setSearchMessage] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const plan = useMemo<MissionPlan>(() => ({ name, start, destination, stops, cruiseAltitude, speed }), [name, start, destination, stops, cruiseAltitude, speed]);
  const validation = useMemo(() => validateMissionPlan(plan), [plan]);
  const routePoints = [start, ...stops, destination].filter((point): point is PlannedLocation => point !== null);
  const estimatedDuration = validation.distance > 0 ? validation.distance / speed : 0;
  const completedSteps = Number(Boolean(start)) + Number(Boolean(destination));

  const selectLocation = useCallback((location: PlannedLocation) => {
    if (selectMode === 'start') {
      setStart(location);
      setSelectMode(destination ? 'stop' : 'destination');
    } else if (selectMode === 'destination') {
      setDestination(location);
      setSelectMode('stop');
    } else {
      setStops((current) => [...current, { ...location, label: location.label || `Stop ${current.length + 1}` }]);
    }
    mapRef.current?.flyTo([location.latitude, location.longitude], Math.max(mapRef.current.getZoom(), 15), { duration: 0.35 });
  }, [destination, selectMode]);

  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container || mapRef.current) return;
    const map = L.map(container, { center: DEFAULT_CENTER, zoom: 13, zoomControl: false, attributionControl: true });
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    const routeLayer = L.layerGroup().addTo(map);
    mapRef.current = map;
    routeLayerRef.current = routeLayer;
    setMapReady(true);
    return () => {
      map.remove();
      mapRef.current = null;
      routeLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const onClick = (event: L.LeafletMouseEvent) => selectLocation({ latitude: event.latlng.lat, longitude: event.latlng.lng, label: coordinateLabel(event.latlng.lat, event.latlng.lng) });
    map.off('click');
    map.on('click', onClick);
    return () => { map.off('click', onClick); };
  }, [selectLocation]);

  useEffect(() => {
    if (!mapReady || !routeLayerRef.current) return;
    const layer = routeLayerRef.current;
    layer.clearLayers();
    if (routePoints.length > 1) {
      L.polyline(routePoints.map((point) => [point.latitude, point.longitude] as L.LatLngExpression), { color: '#38bdf8', weight: 4, opacity: 0.92, dashArray: '10 9', lineCap: 'round' }).addTo(layer);
    }
    if (start) L.marker([start.latitude, start.longitude], { icon: locationIcon('#10b981', 'S') }).bindTooltip(`Start: ${start.label}`).addTo(layer);
    stops.forEach((stop, index) => L.marker([stop.latitude, stop.longitude], { icon: locationIcon('#f59e0b', String(index + 1)) }).bindTooltip(`Stop ${index + 1}: ${stop.label}`).addTo(layer));
    if (destination) L.marker([destination.latitude, destination.longitude], { icon: locationIcon('#f43f5e', 'D') }).bindTooltip(`Destination: ${destination.label}`).addTo(layer);
  }, [destination, mapReady, routePoints, start, stops]);

  const searchPlaces = async (event: FormEvent) => {
    event.preventDefault();
    if (!search.trim()) return;
    const coordinates = parseCoordinates(search);
    if (coordinates) {
      setResults([]);
      setSearchMessage('');
      selectLocation(coordinates);
      return;
    }
    setIsSearching(true);
    setSearchMessage('');
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(search.trim())}`, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error('Place search is unavailable. You can still click the map to choose a point.');
      const places = await response.json() as SearchPlace[];
      setResults(places);
      if (!places.length) setSearchMessage('No matching place found. Try a fuller name or click directly on the map.');
    } catch (error) {
      setSearchMessage(error instanceof Error ? error.message : 'Place search is unavailable. You can still click the map.');
    } finally {
      setIsSearching(false);
    }
  };

  const chooseSearchResult = (place: SearchPlace) => {
    setResults([]);
    setSearchMessage('');
    selectLocation({ latitude: Number(place.lat), longitude: Number(place.lon), label: place.display_name });
  };

  const loadDemoRoute = () => {
    setStart(DEMO_START);
    setDestination(DEMO_DESTINATION);
    setStops([]);
    setSelectMode('stop');
    mapRef.current?.fitBounds([[DEMO_START.latitude, DEMO_START.longitude], [DEMO_DESTINATION.latitude, DEMO_DESTINATION.longitude]], { padding: [72, 72], maxZoom: 15 });
  };

  const launch = () => {
    if (validation.errors.length) return;
    onLaunch(createMissionFromPlan(plan));
  };

  return (
    <main className="mission-planner">
      <aside className="planner-sidebar">
        <header className="planner-brand">
          <div className="planner-brand-mark"><Plane size={18} strokeWidth={2.4} /></div>
          <div>
            <p className="planner-eyebrow">MJN AEROSPACE</p>
            <h1>Flight Studio</h1>
          </div>
          <span className="planner-demo-badge">SIMULATOR</span>
        </header>

        <div className="planner-scroll">
          <section className="planner-intro">
            <div className="planner-intro-icon"><Sparkles size={19} /></div>
            <div>
              <p className="planner-eyebrow">GUIDED SETUP</p>
              <h2>Build a safe route in three simple steps.</h2>
              <p>Choose where the drone starts, where it should finish, and any optional stops in between.</p>
            </div>
          </section>

          <form onSubmit={searchPlaces} className="planner-search">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find a place or paste coordinates" aria-label="Find a place or paste coordinates" />
            <button type="submit" disabled={isSearching} aria-label="Search for a place">{isSearching ? '…' : 'Search'}</button>
            {(results.length > 0 || searchMessage) && <div className="planner-search-results">
              {results.map((place) => <button key={`${place.lat}-${place.lon}`} type="button" onClick={() => chooseSearchResult(place)}>{place.display_name}</button>)}
              {searchMessage && <p>{searchMessage}</p>}
            </div>}
          </form>

          <div className="planner-progress" aria-label={`${completedSteps} of 2 required route points selected`}>
            <span style={{ width: `${(completedSteps / 2) * 100}%` }} />
          </div>

          <section className="planner-section">
            <div className="planner-section-heading">
              <span>Route points</span>
              <button type="button" onClick={loadDemoRoute} className="planner-text-button"><Sparkles size={13} /> Use demo route</button>
            </div>
            <div className="planner-steps">
              <RoutePoint step="1" title="Starting point" hint="Where your drone takes off" value={start} tone="start" active={selectMode === 'start'} onSelect={() => setSelectMode('start')} onClear={() => setStart(null)} />
              <RoutePoint step="2" title="Destination" hint="Where your drone lands" value={destination} tone="destination" active={selectMode === 'destination'} onSelect={() => setSelectMode('destination')} onClear={() => setDestination(null)} />
              {stops.map((stop, index) => <RoutePoint key={`${stop.latitude}-${stop.longitude}-${index}`} step={String(index + 3)} title={`Optional stop ${index + 1}`} hint="A point to visit on the way" value={stop} tone="stop" active={false} onSelect={() => setSelectMode('stop')} onClear={() => setStops((current) => current.filter((_, stopIndex) => stopIndex !== index))} />)}
              <button type="button" onClick={() => setSelectMode('stop')} className={`planner-add-stop ${selectMode === 'stop' ? 'is-active' : ''}`}><Plus size={16} /> Add an optional stop</button>
            </div>
          </section>

          <section className="planner-section">
            <div className="planner-section-heading"><span>Flight settings</span><span className="planner-section-note">Adjust if needed</span></div>
            <label className="planner-field"><span>Mission name</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Name this flight" /></label>
            <div className="planner-field-grid">
              <label className="planner-field"><span><Mountain size={13} /> Height</span><input value={cruiseAltitude} onChange={(event) => setCruiseAltitude(Number(event.target.value))} type="number" min="30" max="400" /><small>30–400 metres</small></label>
              <label className="planner-field"><span><Gauge size={13} /> Speed</span><input value={speed} onChange={(event) => setSpeed(Number(event.target.value))} type="number" min="2" max="25" /><small>2–25 m/s</small></label>
            </div>
          </section>

          <section className="planner-section">
            <div className="planner-section-heading"><span>Flight check</span><span className={validation.errors.length ? 'planner-check-pending' : 'planner-check-ready'}>{validation.errors.length ? 'Needs attention' : 'Ready to fly'}</span></div>
            <div className="planner-summary-grid">
              <SummaryMetric icon={<Route size={16} />} label="Route length" value={formatDistance(validation.distance)} />
              <SummaryMetric icon={<Navigation size={16} />} label="Flight time" value={formatDuration(estimatedDuration)} />
              <SummaryMetric icon={<Battery size={16} />} label="Battery used" value={`${validation.batteryBudget}%`} />
            </div>
            <div className={`planner-validation ${validation.errors.length ? 'has-errors' : 'is-clear'}`}>
              {validation.errors.length ? <><AlertTriangle size={17} /><div><strong>Finish these items</strong><ul>{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul></div></> : <><ShieldCheck size={18} /><div><strong>Route passed the simulator checks</strong><p>Estimated landing reserve: {100 - validation.batteryBudget}%.</p></div></>}
            </div>
          </section>
        </div>

        <footer className="planner-footer">
          <p><ShieldCheck size={14} /> This is a simulator. Always use approved local procedures before operating a real aircraft.</p>
          <button type="button" onClick={launch} disabled={validation.errors.length > 0} className="planner-launch-button"><Plane size={17} /> Start this simulated flight <ChevronRight size={17} /></button>
        </footer>
      </aside>

      <section className="planner-map" aria-label="Mission planning map">
        <div ref={mapContainerRef} className="h-full w-full" />
        <div className="planner-map-shade" />
        <div className="planner-map-topbar">
          <span className="planner-map-live-dot" /> <strong>Route builder</strong><span>•</span><span>{routePoints.length} point{routePoints.length === 1 ? '' : 's'} selected</span>
        </div>
        <div className="planner-map-instruction">
          <div className={`planner-mode-icon ${selectMode}`}><MapPin size={18} /></div>
          <div><span>Next action</span><strong>{selectMode === 'start' ? 'Click the map to place your starting point' : selectMode === 'destination' ? 'Click the map to place your destination' : 'Click the map to add an optional stop'}</strong></div>
        </div>
        <div className="planner-map-legend"><span className="legend-start"><Circle size={10} fill="currentColor" /> Start</span><span className="legend-stop"><Circle size={10} fill="currentColor" /> Stop</span><span className="legend-destination"><Circle size={10} fill="currentColor" /> Destination</span></div>
      </section>
    </main>
  );
}

function RoutePoint({ step, title, hint, value, tone, active, onSelect, onClear }: { step: string; title: string; hint: string; value: PlannedLocation | null; tone: 'start' | 'destination' | 'stop'; active: boolean; onSelect: () => void; onClear: () => void }) {
  const complete = Boolean(value);
  return <div className={`planner-route-point ${tone} ${active ? 'is-active' : ''} ${complete ? 'is-complete' : ''}`}>
    <span className="planner-step-number">{complete ? <CheckCircle2 size={15} /> : step}</span>
    <button type="button" onClick={onSelect} className="planner-route-main"><span>{title}</span><small>{value?.label || hint}</small></button>
    {value ? <button type="button" onClick={onClear} className="planner-clear-point" aria-label={`Clear ${title}`} title={`Clear ${title}`}><X size={15} /></button> : <button type="button" onClick={onSelect} className="planner-place-point">Place</button>}
  </div>;
}

function SummaryMetric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="planner-summary-metric"><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></div>;
}
