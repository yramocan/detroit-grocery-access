import Link from "next/link";
import { Summary } from "@/lib/types";
import fs from "fs";
import path from "path";

export const dynamic = "force-static";

function readSummary(): Summary | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "summary.json");
    return JSON.parse(fs.readFileSync(filePath, "utf8")) as Summary;
  } catch {
    return null;
  }
}

export default function MethodologyPage() {
  const summary = readSummary();

  return (
    <article className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-lake">
        Transparency
      </p>
      <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight text-ink">
        Methodology
      </h1>
      <p className="mt-4 text-lg text-ink/70">
        This MVP estimates geographic pedestrian access to manually reviewed
        qualifying grocery stores across the City of Detroit. It measures who
        can walk to good groceries within 15 minutes—not total food security.
      </p>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">Core question</h2>
        <p className="text-ink/80">
          What percentage of Detroit residents can reach a qualifying grocery
          store within 15 minutes on foot, and where are the largest access
          gaps?
        </p>
        {summary && (
          <p className="rounded-xl bg-white/80 px-4 py-3 text-sm shadow-panel">
            Current estimate: <strong>{summary.pct_within_15.toFixed(1)}%</strong>{" "}
            within 15 minutes (
            {summary.residents_within_15.toLocaleString()} of{" "}
            {summary.total_population.toLocaleString()} residents), based on{" "}
            {summary.qualifying_grocery_stores} qualifying stores. Retrieval
            date: {summary.retrieval_date}.
          </p>
        )}
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">Geographic scope</h2>
        <p className="text-ink/80">
          Primary statistics use City of Detroit municipal boundaries only
          (U.S. Census place GEOID 2622000). The broader metro area is excluded
          from headline metrics. The configuration allows near-boundary stores
          outside the city to be added later.
        </p>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">
          Qualifying grocery stores
        </h2>
        <p className="text-ink/80">
          Stores are manually reviewed against the rubric in{" "}
          <code className="rounded bg-mist px-1.5 py-0.5 text-sm">
            data/manual/classification_rubric.md
          </code>
          . A qualifying store should support a normal grocery trip with
          meaningful access to produce, protein, dairy/substitutes,
          grains/staples, frozen foods, and basic household needs.
        </p>
        <p className="text-ink/80">
          Excluded formats include liquor stores, gas stations, convenience
          stores, pharmacies, limited-assortment dollar stores, and specialty
          shops that cannot reasonably support a full grocery trip. V1 does not
          use automated AI classification. Candidate locations are assembled
          from OpenStreetMap, then screened by name and store tag.
        </p>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">Population</h2>
        <p className="text-ink/80">
          U.S. Census / ACS 5-year total population (B01003) at block-group
          resolution, joined to TIGER/Line block groups intersecting Detroit.
          Uninhabited block groups are excluded from accessibility weighting.
          Origins use each inhabited block group’s representative point.
        </p>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">
          Walking network and routing
        </h2>
        <ul className="list-disc space-y-2 pl-5 text-ink/80">
          <li>
            Pedestrian network from OpenStreetMap via OSMnx (
            <code className="text-sm">network_type=walk</code>)
          </li>
          <li>
            Multi-source Dijkstra (NetworkX) from all qualifying store nodes,
            weighted by edge length
          </li>
          <li>
            Default walking speed:{" "}
            <strong>
              {summary?.walking_speed_mph ?? 3.0} mph / 4.8 km/h
            </strong>{" "}
            (configurable in <code className="text-sm">config.yaml</code>)
          </li>
          <li>
            Straight-line radius buffers are not used as the primary measure
          </li>
        </ul>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">Thresholds</h2>
        <p className="text-ink/80">
          Reported bins: ≤5, ≤10, ≤15, ≤20, and &gt;20 minutes. The headline
          metric uses 15 minutes.
        </p>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">
          Place-a-store scenario
        </h2>
        <p className="text-ink/80">
          The interactive placement tool estimates newly served residents using
          an approximate walk time (Euclidean distance × circuity factor of
          1.35) compared with each block group’s precomputed network baseline.
          It is a planning sketch, not an engineered siting study.
        </p>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">Known limitations</h2>
        <p className="text-ink/80">This MVP does not measure:</p>
        <ul className="list-disc space-y-1 pl-5 text-ink/80">
          <li>grocery prices</li>
          <li>inventory quality in real time</li>
          <li>cultural appropriateness of inventory</li>
          <li>transit accessibility</li>
          <li>disability-specific travel times</li>
          <li>sidewalk quality or curb ramps</li>
          <li>personal safety</li>
          <li>snow / weather impacts</li>
          <li>grocery delivery</li>
          <li>store capacity</li>
          <li>reliable store hours beyond basic metadata</li>
        </ul>
        <p className="font-medium text-ink">
          The MVP measures geographic pedestrian accessibility, not total food
          security.
        </p>
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="font-display text-2xl font-semibold">Reproduce</h2>
        <pre className="overflow-x-auto rounded-xl bg-ink px-4 py-3 text-sm text-paper">
{`python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make analyze
cd web && npm install && npm run dev`}
        </pre>
        <p className="text-sm text-ink/60">
          Full write-up also lives in{" "}
          <code className="text-sm">analysis/methodology.md</code>.
        </p>
      </section>

      <p className="mt-12">
        <Link href="/" className="font-medium text-canopy hover:underline">
          ← Back to map
        </Link>
      </p>
    </article>
  );
}
