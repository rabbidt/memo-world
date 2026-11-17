// The real sky and seasons for the Keeper's part of the world (London by default).
// Pure maths, no dependencies, so the server and the browser share it.
export const PLACE = { lat: 51.5, lon: -0.13 };
const RAD = Math.PI / 180, DAY = 86400000;
const julian = (date) => date.getTime() / DAY + 2440587.5;

// Where the sun is: elevation and azimuth in degrees (azimuth clockwise from north).
export function sunPosition(date, place = PLACE) {
  const n = julian(date) - 2451545.0;
  const L = (280.46 + 0.9856474 * n) % 360, g = ((357.528 + 0.9856003 * n) % 360) * RAD;
  const lambda = (L + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * RAD;
  const eps = (23.439 - 0.0000004 * n) * RAD;
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lambda), Math.cos(lambda));
  const dec = Math.asin(Math.sin(eps) * Math.sin(lambda));
  const gmst = (18.697374558 + 24.06570982441908 * n) % 24;
  const ha = (gmst * 15 + place.lon) * RAD - ra, lat = place.lat * RAD;
  const elevation = Math.asin(Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(ha));
  const azimuth = Math.atan2(-Math.sin(ha), Math.tan(dec) * Math.cos(lat) - Math.sin(lat) * Math.cos(ha));
  return { elevation: elevation / RAD, azimuth: ((azimuth / RAD) + 360) % 360, declination: dec / RAD };
}

// Sunrise and sunset for the day that holds `date`, as Dates (null in a polar day or night).
export function sunTimes(date, place = PLACE) {
  const noonish = new Date(Math.floor(date.getTime() / DAY) * DAY + DAY / 2 - (place.lon / 360) * DAY);
  const cross = (dir) => {
    let a = noonish.getTime(), b = a + dir * DAY / 2;
    if (sunPosition(new Date(a), place).elevation < -0.83 || sunPosition(new Date(b), place).elevation > -0.83) return null;
    for (let i = 0; i < 30; i++) { const m = (a + b) / 2; if (sunPosition(new Date(m), place).elevation > -0.83) a = m; else b = m; }
    return new Date(a);
  };
  return { sunrise: cross(-1), sunset: cross(1), noon: noonish };
}

// The moon: phase 0 new, 0.5 full, back to 1; and how much of its face is lit.
const PHASES = ['new moon', 'waxing crescent', 'first quarter', 'waxing gibbous', 'full moon', 'waning gibbous', 'last quarter', 'waning crescent'];
export function moon(date) {
  const phase = ((((date.getTime() - Date.UTC(2000, 0, 6, 18, 14)) / DAY) / 29.530588853) % 1 + 1) % 1;
  return { phase, lit: (1 - Math.cos(phase * 2 * Math.PI)) / 2, name: PHASES[Math.round(phase * 8) % 8] };
}

// The season by date, northern hemisphere, with smooth amounts the world can draw from.
const bump = (x, from, peak, to) => (x <= from || x >= to ? 0 : x < peak ? (x - from) / (peak - from) : (to - x) / (to - peak));
const hash = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
export function season(date) {
  const start = Date.UTC(date.getUTCFullYear(), 0, 1), doy = Math.floor((date.getTime() - start) / DAY) + 1; // 1..366
  const month = date.getUTCMonth();
  const name = ['winter', 'winter', 'spring', 'spring', 'spring', 'summer', 'summer', 'summer', 'autumn', 'autumn', 'autumn', 'winter'][month];
  const part = ['mid', 'late', 'early', 'mid', 'late', 'early', 'mid', 'late', 'early', 'mid', 'late', 'early'][month];
  const winterDepth = Math.max(bump(doy, 325, 380, 440), bump(doy + 365, 325, 380, 440)); // peaks mid January
  const dayNo = Math.floor(date.getTime() / DAY);
  const cold = winterDepth > 0.35;
  return {
    name, part, label: `${part} ${name}`, doy,
    blossom: bump(doy, 80, 110, 140),              // pink and white blossom, peaking mid to late April
    green: Math.min(1, bump(doy, 60, 150, 320) * 1.6), // how lush the grass and leaves are
    autumn: bump(doy, 258, 310, 345),              // leaf colour, peaking early November
    falling: bump(doy, 275, 318, 350),             // leaves in the air
    bare: Math.max(Math.min(1, Math.max(0, (doy - 318) / 22)), doy < 75 ? 1 : Math.max(0, 1 - (doy - 75) / 25)), // leafless trees
    flowers: Math.max(0.04, bump(doy, 55, 165, 300)),
    frost: cold && hash(dayNo) < 0.45 ? 1 : winterDepth > 0.15 && hash(dayNo) < 0.2 ? 0.6 : 0, // frosty mornings
    snow: cold && hash(dayNo + 0.5) < 0.14,       // an occasional snowy day
    rain: hash(dayNo + 0.25) < (name === 'summer' ? 0.25 : 0.4), // UK-ish odds of a wet day
  };
}

export const clockTime = (d, tz = 'Europe/London') => d ? d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: tz }) : 'never';
