'use client';

import { FormEvent, useState } from 'react';
import { MapEngine } from './MapEngine';

type Place = { display_name: string; lat: string; lon: string };

function coordinateQuery(value: string): [number, number] | null {
  const match = value.trim().match(/^(-?\d{1,2}(?:\.\d+)?)\s*[,\s]\s*(-?\d{1,3}(?:\.\d+)?)$/);
  if (!match) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  return Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180 ? [latitude, longitude] : null;
}

export default function MapSearch({ engine }: { engine: MapEngine | null }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Place[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const choose = (place: Place | [number, number]) => {
    const [latitude, longitude] = Array.isArray(place) ? place : [Number(place.lat), Number(place.lon)];
    engine?.setView(latitude, longitude, 16);
    setResults([]);
    setMessage('');
  };

  const search = async (event: FormEvent) => {
    event.preventDefault();
    const value = query.trim();
    if (!value || !engine) return;
    const coordinates = coordinateQuery(value);
    if (coordinates) { choose(coordinates); return; }

    setLoading(true);
    setMessage('');
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(value)}`, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error('Search is temporarily unavailable');
      const places = await response.json() as Place[];
      setResults(places);
      if (places.length === 0) setMessage('No places found. Try a more specific name or coordinates.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Search is temporarily unavailable');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute left-3 top-3 z-[1001] w-[min(360px,calc(100%-76px))]">
      <form onSubmit={search} className="flex overflow-hidden rounded-md bg-white shadow-md">
        <input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search for a place or coordinates" placeholder="Search places or coordinates" className="min-w-0 flex-1 px-3 py-2.5 text-sm text-[#202124] outline-none placeholder:text-[#80868b]" />
        <button type="submit" aria-label="Search" className="px-3 text-lg text-[#5f6368] hover:bg-[#f1f3f4]" disabled={loading}>{loading ? '…' : '⌕'}</button>
      </form>
      {(results.length > 0 || message) && (
        <div className="mt-1 overflow-hidden rounded-md bg-white shadow-md">
          {results.map((place) => <button key={`${place.lat}-${place.lon}`} type="button" onClick={() => choose(place)} className="block w-full border-b border-[#f1f3f4] px-3 py-2 text-left text-xs text-[#3c4043] last:border-0 hover:bg-[#f8f9fa]">{place.display_name}</button>)}
          {message && <p className="px-3 py-2 text-xs text-[#5f6368]">{message}</p>}
        </div>
      )}
    </div>
  );
}
