// What the real sky and season over the Keeper's home mean for Ash, in words and small effects.
import { sunPosition, sunTimes, moon, season, clockTime } from '../web/js/almanac.js';

export { sunPosition, season };
export const isDark = (d = new Date()) => sunPosition(d).elevation < -6;      // stars are out
export const isDusk = (d = new Date()) => sunPosition(d).elevation < 3;       // low sun, evening or night

const FINDS = {
  spring: ['blossom', 'catkin', 'eggshell'], summer: ['wild berry', 'daisy', 'warm pebble'],
  autumn: ['fallen leaf', 'acorn', 'conker'], winter: ['holly sprig', 'bare twig', 'pine needle'],
};
const GARDEN_FINDS = { spring: ['seedling'], summer: ['ripe berry', 'pea pod'], autumn: ['pumpkin seed', 'windfall apple'], winter: [] };
const GARDEN = {
  spring: 'Seedlings are pushing up in the beds. It is planting time.',
  summer: 'The beds are in full growth and there is plenty to pick.',
  autumn: 'The last of the harvest is in the beds, with pumpkins fattening and seeds to save.',
  winter: 'The beds are resting under the cold. Nothing grows now, but it is a good time to plan the spring.',
};
const AIR = {
  spring: 'The trees are in new leaf and blossom.', summer: 'The trees are full and green and the days are long.',
  autumn: 'The leaves have turned gold and red and are coming down.', winter: 'The leafy trees are bare and the days are short.',
};

// Extra things that can be found anywhere on land at this time of year (and a few only in the garden).
export function seasonalFinds(zone, d = new Date()) {
  const s = season(d);
  return [...FINDS[s.name], ...(zone?.id === 'garden' ? GARDEN_FINDS[s.name] : [])];
}

// The lines Ash perceives about the sky and season.
export function skyLines(zone, d = new Date()) {
  const s = season(d), t = sunTimes(d), m = moon(d), up = sunPosition(d).elevation > -0.83;
  const weather = s.snow ? ' Snow is falling today.' : s.frost && d.getHours() < 10 ? ' There is frost on the grass this morning.' : '';
  return [
    `It is ${s.label}. ${AIR[s.name]}${weather}`,
    `The sun ${up ? 'is up' : 'is down'}: it rose at ${clockTime(t.sunrise)} and sets at ${clockTime(t.sunset)} today. Tonight's moon is a ${m.name}.`,
    zone?.id === 'garden' ? GARDEN[s.name] : null,
  ];
}

// Cold, dark days are a little more tiring to be out in.
export const outdoorCost = (d = new Date()) => (season(d).name === 'winter' ? 1 : 0);
