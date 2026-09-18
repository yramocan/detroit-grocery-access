export type Summary = {
  retrieval_date: string;
  walking_speed_mph: number;
  headline_threshold_minutes: number;
  total_population: number;
  residents_within_15: number;
  residents_outside_15: number;
  pct_within_15: number;
  qualifying_grocery_stores: number;
  median_walk_minutes_pop_weighted: number | null;
  metric_definition?: string;
  qualifying_definition?: string;
  lowest_access_tract: {
    tract: string;
    pct_within_15: number;
    population: number;
  } | null;
  highest_access_tract: {
    tract: string;
    pct_within_15: number;
    population: number;
  } | null;
  bins: { bin: string; population: number; block_groups: number }[];
  assumptions: Record<string, string>;
  limitations: string[];
};

export type ScenarioPoint = {
  GEOID: string;
  population: number;
  walk_minutes: number | null;
  within_15: boolean;
  origin_node: number | null;
  lat: number;
  lon: number;
};

export type ScenarioBase = {
  speed_mpm: number;
  headline_minutes: number;
  total_population: number;
  residents_within_15: number;
  pct_within_15: number;
  points: ScenarioPoint[];
};

export function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-US").format(Math.round(n));
}

/** Approximate network walk minutes using Euclidean distance × circuity factor. */
export function estimateWalkMinutes(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
  speedMpm: number,
  circuity = 1.35
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const R = 6371000;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  const meters = 2 * R * Math.asin(Math.sqrt(a));
  return (meters * circuity) / speedMpm;
}
