import AccessMap from "@/components/AccessMap";
import { ScenarioBase, Summary } from "@/lib/types";
import fs from "fs";
import path from "path";

export const dynamic = "force-static";

function readPublicJson<T>(filename: string): T {
  const filePath = path.join(process.cwd(), "public", "data", filename);
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
}

export default function HomePage() {
  const summary = readPublicJson<Summary>("summary.json");
  const scenario = readPublicJson<ScenarioBase>("scenario_base.json");

  return (
    <div>
      <div className="mx-auto max-w-[1400px] px-4 pt-6 sm:px-6">
        <p className="animate-rise max-w-2xl text-base text-ink/70 sm:text-lg">
          of Detroit residents can reach an assortment-qualified grocery store
          within a 15-minute walk — not necessarily a good or affordable one.
        </p>
      </div>
      <AccessMap summary={summary} scenario={scenario} />
      <footer className="mx-auto max-w-[1400px] px-4 pb-10 pt-2 text-xs text-ink/50 sm:px-6">
        Pedestrian-network analysis at ~{summary.walking_speed_mph} mph. Data
        retrieved {summary.retrieval_date}. See{" "}
        <a href="/methodology" className="underline hover:text-canopy">
          methodology
        </a>{" "}
        for assumptions and limitations. OSM © OpenStreetMap contributors.
      </footer>
    </div>
  );
}
