import { useEffect } from "react";
import { fetchSquad, type ApiPlayer } from "@/lib/api";
import { useState } from "react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { BorderBeam, CardBeam } from "@/components/ui/BorderBeam";
import { NumberTicker } from "@/components/ui/NumberTicker";
import { RiskRadar } from "@/components/ui/RiskRadar";
import { InjuryTimeline } from "@/components/ui/InjuryTimeline";
import IntelFeed from "@/components/IntelFeed";
import { FootballSVG } from "@/components/ui/PitchBackground";

// ─── Types ─────────────────────────────────────────────────────────────────
type Tier = "Low" | "Medium" | "High";

interface Player {
  id: number;
  name: string;
  position: string;
  age: number;
  minutesLast30: number;
  gamesLast14: number;
  daysSinceInjury: number;
  injuryCount2yr: number;
  riskScore: number;
  tier: Tier;
  subScores: { acl: number; hamstring: number; ankle: number; meniscus: number };
  shapFactors: { label: string; value: number }[];
  nextMatch: { opponent: string; venue: string; surface: string; homeAway: string; date: string };
  injuryHistory: { year: number; type: string; gamesMissed: number }[];
  distance: number;
}



function mapApiPlayerToPlayer(p: ApiPlayer): Player {
  return {
    id: p.id,
    name: p.name,
    position: p.position,
    age: p.age,
    minutesLast30: p.minutesLast30,
    gamesLast14: p.gamesLast14,
    daysSinceInjury: p.daysSinceInjury,
    injuryCount2yr: p.injuryCount2yr,
    riskScore: p.riskScore,
    tier: p.tier,
    subScores: p.subScores,
    shapFactors: p.shapFactors,
    nextMatch: p.nextMatch,
    injuryHistory: p.injuryHistory,
    distance: p.distance ?? 0,
  };
}

// ─── Mock Data Generator ───────────────────────────────────────────────────
function generateMockSquad(): Player[] {
  const pos = ["GK", "DEF", "MID", "FWD"];
  const fn = ["Luca", "James", "Mateo", "Arjun", "Kai", "Sven", "Omar", "Riku", "Diego", "Theo", "Leo", "Finn"];
  const ln = ["Müller", "Torres", "Mbeki", "Tanaka", "Walsh", "Novak", "Eriksen", "Santos", "Osei", "Dubois", "Bianchi", "Ali"];
  const inj = ["ACL", "Hamstring", "Ankle", "Meniscus"];
  const sf = ["Natural Grass", "Artificial Turf"];
  const vn = ["Emirates Stadium", "Camp Nou", "Allianz Arena", "San Siro", "Parc des Princes"];
  
  return Array.from({ length: 18 }, (_, i) => {
    const rs = Math.floor(Math.random() * 100);
    const surface = sf[Math.floor(Math.random() * 2)];
    return {
      id: i + 1,
      name: `${fn[i % fn.length]} ${ln[i % ln.length]}`,
      position: pos[i % 4],
      age: 20 + Math.floor(Math.random() * 17),
      minutesLast30: Math.floor(Math.random() * 900),
      gamesLast14: Math.floor(Math.random() * 6),
      daysSinceInjury: Math.floor(Math.random() * 400),
      injuryCount2yr: Math.floor(Math.random() * 5),
      riskScore: rs,
      tier: (rs < 40 ? "Low" : rs < 70 ? "Medium" : "High") as Tier,
      subScores: {
        acl: Math.round(Math.random() * 60),
        hamstring: Math.round(Math.random() * 70),
        ankle: Math.round(Math.random() * 55),
        meniscus: Math.round(Math.random() * 45),
      },
      shapFactors: [
        { label: surface === "Artificial Turf" ? "Artificial Turf" : "Natural Grass", value: +(Math.random() * 0.3).toFixed(2) },
        { label: "Fixture Congestion", value: +(Math.random() * 0.3).toFixed(2) },
        { label: "Injury History", value: +(Math.random() * 0.25).toFixed(2) },
      ].sort((a, b) => b.value - a.value),
      nextMatch: {
        opponent: `vs. ${ln[Math.floor(Math.random() * ln.length)]} FC`,
        venue: vn[Math.floor(Math.random() * vn.length)],
        surface,
        homeAway: Math.random() > 0.5 ? "Away" : "Home",
        date: `June ${10 + i}, 2026`,
      },
      injuryHistory: Array.from({ length: Math.floor(Math.random() * 5) }, (_, j) => ({
        year: 2020 + j,
        type: inj[Math.floor(Math.random() * inj.length)],
        gamesMissed: 2 + Math.floor(Math.random() * 20),
      })),
      distance: +(Math.random() * 500 + 100).toFixed(1),
    };
  });
}

// ─── Color Constants ───────────────────────────────────────────────────────
const tierClr: Record<Tier, { bg: string; text: string; border: string; dot: string }> = {
  Low: { bg: "rgba(0, 232, 123, 0.1)", text: "#00e87b", border: "rgba(0, 232, 123, 0.3)", dot: "#00e87b" },
  Medium: { bg: "rgba(255, 149, 0, 0.1)", text: "#ff9500", border: "rgba(255, 149, 0, 0.3)", dot: "#ff9500" },
  High: { bg: "rgba(255, 45, 85, 0.1)", text: "#ff2d55", border: "rgba(255, 45, 85, 0.3)", dot: "#ff2d55" },
};
const posClr: Record<string, string> = { GK: "#bf5af2", DEF: "#0a84ff", MID: "#00e87b", FWD: "#ff9500" };

const SF = "'Inter', 'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif";

// ─── Staggered Letter Reveal Component ─────────────────────────────────────
function StaggeredText({ text }: { text: string }) {
  return (
    <span className="inline-flex flex-wrap">
      {text.split("").map((char, i) => (
        <span
          key={i}
          className="inline-block animate-[letterReveal_0.4s_ease-out_both]"
          style={{ animationDelay: `${i * 25}ms` }}
        >
          {char === " " ? "\u00A0" : char}
        </span>
      ))}
    </span>
  );
}

// ─── Sub Components ────────────────────────────────────────────────────────
function RiskDot({ tier, size = 8 }: { tier: Tier; size?: number }) {
  const c = tierClr[tier];
  return (
    <span
      className="inline-block rounded-full shrink-0 animate-pulse"
      style={{
        width: size,
        height: size,
        backgroundColor: c.dot,
        boxShadow: `0 0 8px ${c.dot}`,
      }}
    />
  );
}

function RiskBadge({ tier, score }: { tier: Tier; score?: number }) {
  const c = tierClr[tier];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[0.68rem] font-bold"
      style={{
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        fontFamily: SF,
      }}
    >
      <RiskDot tier={tier} size={6} />
      {tier.toUpperCase()}{score !== undefined && ` · ${score}%`}
    </span>
  );
}

function PosBadge({ pos }: { pos: string }) {
  const cl = posClr[pos] || "#8faa98";
  return (
    <span
      className="text-[0.65rem] font-bold px-2 py-0.5 rounded font-scoreboard uppercase"
      style={{
        background: `${cl}15`,
        color: cl,
        border: `1px solid ${cl}30`,
      }}
    >
      {pos}
    </span>
  );
}

function SurfaceTag({ surface: _surface }: { surface: string }) {
  return null;
}



// ─── Risk Bar Chart ────────────────────────────────────────────────────────
// ─── Risk Bar Chart ────────────────────────────────────────────────────────
function RiskBarChart({ categories }: { categories: { label: string; value: number }[] }) {
  return (
    <div className="flex flex-col gap-2.5">
      {categories.map((cat, i) => {
        const color = cat.value > 70 ? "#ff2d55" : cat.value > 40 ? "#ff9500" : "#00e87b";
        return (
          <div key={i} className="flex items-center gap-3">
            <span
              className="text-[0.62rem] w-28 shrink-0 truncate text-white/50 tracking-wider font-semibold uppercase"
              style={{ fontFamily: SF }}
            >
              {cat.label}
            </span>
            <div className="flex-1 h-2.5 rounded bg-black/40 border border-white/5 overflow-hidden">
              <div
                className="h-full rounded transition-all duration-1000 ease-out"
                style={{
                  width: `${cat.value}%`,
                  background: `linear-gradient(90deg, ${color}99, ${color})`,
                  boxShadow: `0 0 10px ${color}50`,
                  animation: `riskBarGrow 1.2s ease-out ${i * 0.1}s both`,
                  ["--bar-width" as string]: `${cat.value}%`,
                }}
              />
            </div>
            <span
              className="text-[0.7rem] font-bold w-10 text-right font-scoreboard"
              style={{ color }}
            >
              {cat.value}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
// ─── Squad Risk Table ──────────────────────────────────────────────────────
function SquadRiskTable({ players, onSelect }: { players: Player[]; onSelect: (p: Player) => void }) {
  const [posFilter, setPosFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<string>("riskScore");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const filtered = players.filter((p) => {
    const matchesPos = posFilter === "ALL" || p.position === posFilter;
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          p.position.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesPos && matchesSearch;
  });

  const sorted = [...filtered].sort((a, b) => {
    let aVal: any = a[sortField as keyof Player];
    let bVal: any = b[sortField as keyof Player];

    if (sortField === "name") {
      return sortDirection === "asc"
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name);
    }
    
    if (aVal === undefined) return 1;
    if (bVal === undefined) return -1;

    return sortDirection === "asc"
      ? (aVal > bVal ? 1 : -1)
      : (aVal < bVal ? 1 : -1);
  });

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const SortIndicator = ({ field }: { field: string }) => {
    if (sortField !== field) return <span className="text-white/20 ml-1">⇅</span>;
    return sortDirection === "asc"
      ? <span className="text-emerald-400 ml-1">▲</span>
      : <span className="text-emerald-400 ml-1">▼</span>;
  };

  return (
    <GlassPanel corners animationDelay={300} noPadding>
      <div className="p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <span
            className="text-xs font-scoreboard font-bold tracking-[0.15em] uppercase text-emerald-400"
          >
            Squad Risk Overview
          </span>
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 sm:flex-initial">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search squad..."
                className="w-full sm:w-44 px-3 py-1 pl-8 rounded-lg bg-black/40 border border-emerald-500/20 text-xs text-white focus:outline-none focus:border-emerald-400 transition-all"
              />
              <span className="absolute left-2.5 top-1.5 text-white/40 text-[10px]">🔍</span>
            </div>

            {/* Position filter pill toggles */}
            <div className="flex bg-black/40 p-0.5 rounded-lg border border-white/5">
              {["ALL", "GK", "DEF", "MID", "FWD"].map((p) => (
                <button
                  key={p}
                  onClick={() => setPosFilter(p)}
                  className="px-2.5 py-1 rounded-md text-[0.65rem] font-bold transition-all"
                  style={{
                    color: posFilter === p ? "#00e87b" : "rgba(255,255,255,0.4)",
                    background: posFilter === p ? "rgba(0, 232, 123, 0.08)" : "transparent",
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Risk bar chart stats */}
        <RiskBarChart
          categories={[
            { label: "Overall Squad Risk", value: Math.round(players.reduce((s, p) => s + p.riskScore, 0) / players.length) },
            { label: "Turf Exposure Index", value: Math.round(players.filter((p) => p.nextMatch.surface === "Artificial Turf").length / players.length * 100) },
            { label: "Workload Congestion", value: Math.round(players.reduce((s, p) => s + p.gamesLast14, 0) / players.length * 16.6) },
          ]}
        />
      </div>

      {/* Player list table */}
      <div
        className="border-t mt-2 max-h-[380px] overflow-y-auto"
        style={{ borderColor: "rgba(0,232,123,0.15)" }}
      >
        <table className="w-full text-left border-collapse">
          <thead>
            <tr
              className="sticky top-0 z-10 border-b border-emerald-500/10"
              style={{ background: "rgba(10, 26, 18, 0.9)", backdropFilter: "blur(10px)" }}
            >
              <th
                onClick={() => handleSort("id")}
                className="cursor-pointer text-[0.6rem] tracking-wider px-5 py-3 font-scoreboard font-bold text-white/50 hover:text-white transition-colors"
              >
                JERSEY <SortIndicator field="id" />
              </th>
              <th
                onClick={() => handleSort("name")}
                className="cursor-pointer text-[0.6rem] tracking-wider py-3 font-scoreboard font-bold text-white/50 hover:text-white transition-colors"
              >
                PLAYER <SortIndicator field="name" />
              </th>
              <th
                onClick={() => handleSort("position")}
                className="cursor-pointer text-[0.6rem] tracking-wider py-3 font-scoreboard font-bold text-white/50 hover:text-white transition-colors"
              >
                POS <SortIndicator field="position" />
              </th>
              <th
                onClick={() => handleSort("distance")}
                className="cursor-pointer text-right text-[0.6rem] tracking-wider py-3 font-scoreboard font-bold text-white/50 hover:text-white transition-colors"
              >
                DISTANCE <SortIndicator field="distance" />
              </th>
              <th className="py-3 px-2 text-[0.6rem] font-scoreboard font-bold text-white/50 select-none">
                RISK METER
              </th>
              <th
                onClick={() => handleSort("riskScore")}
                className="cursor-pointer text-right text-[0.6rem] tracking-wider py-3 pr-5 font-scoreboard font-bold text-white/50 hover:text-white transition-colors"
              >
                RISK <SortIndicator field="riskScore" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, idx) => {
              const isHighRisk = p.tier === "High";
              const jerseyNum = (p.id * 3) % 97 + 1;
              return (
                <tr
                  key={p.id}
                  onClick={() => onSelect(p)}
                  className={`cursor-pointer transition-all duration-300 relative border-b border-white/5 hover:bg-emerald-500/[0.04] animate-[playerRowIn_0.4s_ease-out_both]`}
                  style={{
                    animationDelay: `${idx * 20}ms`,
                    borderLeft: isHighRisk ? "4px solid #ff2d55" : "4px solid transparent",
                    animationName: isHighRisk ? "riskBreathing 2.5s infinite" : undefined,
                  }}
                >
                  <td className="px-5 py-3">
                    <span className="text-xs font-scoreboard font-semibold text-white/50">
                      #{jerseyNum}
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      {/* Jersey color-coded initials avatar */}
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-[0.7rem] font-scoreboard font-black shrink-0 relative transition-transform duration-300"
                        style={{
                          background: `${posClr[p.position] || "#34d399"}20`,
                          color: posClr[p.position] || "#34d399",
                          border: `2px solid ${posClr[p.position] || "#34d399"}50`,
                          boxShadow: `0 0 6px ${posClr[p.position] || "#34d399"}30`,
                        }}
                      >
                        {p.name.split(" ").map((n) => n[0]).join("")}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-white tracking-wide">
                          {p.name}
                        </span>
                        <span className="text-[9px] text-white/40 tracking-wider">
                          Age {p.age}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="py-3">
                    <PosBadge pos={p.position} />
                  </td>
                  <td className="py-3 text-right">
                    <span className="text-[0.7rem] font-scoreboard font-semibold text-white/60">
                      {p.distance} km
                    </span>
                  </td>
                  <td className="py-3 px-2">
                    {/* Mini inline risk bar */}
                    <div className="w-[60px] h-1 bg-white/5 rounded-full overflow-hidden shrink-0">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${p.riskScore}%`,
                          backgroundColor: tierClr[p.tier].text,
                          boxShadow: `0 0 6px ${tierClr[p.tier].text}80`,
                        }}
                      />
                    </div>
                  </td>
                  <td className="py-3 pr-5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span
                        className="text-xs font-scoreboard font-bold"
                        style={{ color: tierClr[p.tier].text }}
                      >
                        {p.riskScore}%
                      </span>
                      <RiskDot tier={p.tier} size={6} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </GlassPanel>
  );
}

// ─── Speedometer Gauge for Risk ────────────────────────────────────────────
function SpeedometerGauge({ value, size = 160 }: { value: number; size?: number }) {
  const r = size * 0.38;
  const cx = size / 2;
  const cy = size / 2 + 10;
  const circ = Math.PI * r;
  const offset = circ - (value / 100) * circ;
  const color = value < 40 ? "#00e87b" : value < 70 ? "#ff9500" : "#ff2d55";
  
  // Calculate pointer angle (from -180deg to 0deg)
  const angle = -180 + (value / 100) * 180;

  return (
    <div className="relative flex flex-col items-center justify-center" style={{ width: size, height: size * 0.75 }}>
      <svg width={size} height={size * 0.65} className="overflow-visible">
        {/* Track arc */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* Colored Fill */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{
            transition: "stroke-dashoffset 1.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
            filter: `drop-shadow(0 0 8px ${color}80)`,
          }}
        />
        {/* Pointer needle */}
        <g transform={`translate(${cx}, ${cy}) rotate(${angle})`}>
          <line
            x1={0}
            y1={0}
            x2={-r + 10}
            y2={0}
            stroke="#ffffff"
            strokeWidth={2}
            strokeLinecap="round"
            style={{
              transition: "transform 1.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
            }}
          />
          <circle cx={0} cy={0} r={4} fill="#ffffff" />
        </g>
      </svg>
      <div className="absolute bottom-1 flex flex-col items-center">
        <span className="text-3xl font-scoreboard font-black leading-none" style={{ color }}>
          <NumberTicker value={value} suffix="%" duration={1200} />
        </span>
        <span className="text-[8px] text-white/30 tracking-[0.15em] font-semibold mt-1 uppercase">
          Injury Risk index
        </span>
      </div>
    </div>
  );
}

// ─── Player Detail Side Panel ──────────────────────────────────────────────
function PlayerDetail({ player, onClose }: { player: Player; onClose: () => void }) {
  const radarValues = {
    surface: player.nextMatch.surface === "Artificial Turf" ? 85 : 25,
    workload: Math.min(100, Math.round((player.minutesLast30 / 900) * 100)),
    history: Math.min(100, player.injuryCount2yr * 25),
    age: Math.min(100, Math.round(((player.age - 20) / 17) * 100)),
    position: player.position === "FWD" ? 75 : player.position === "MID" ? 65 : player.position === "DEF" ? 55 : 35,
    recovery: Math.max(0, Math.min(100, Math.round(100 - (player.daysSinceInjury / 400) * 100))),
  };

  return (
    <div
      className="fixed top-0 right-0 h-screen overflow-y-auto z-[100] border-l flex flex-col"
      style={{
        width: "min(460px,100vw)",
        boxShadow: "-12px 0 40px rgba(0,0,0,0.7)",
        background: "rgba(6, 15, 8, 0.85)",
        backdropFilter: "blur(32px)",
        borderColor: "rgba(0, 232, 123, 0.2)",
        animation: "panelSlideLeft 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* Header */}
      <div
        className="sticky top-0 z-10 p-6 flex flex-col gap-4 border-b"
        style={{
          background: "rgba(6, 18, 10, 0.9)",
          backdropFilter: "blur(16px)",
          borderColor: "rgba(0, 232, 123, 0.15)",
        }}
      >
        <div className="flex justify-between items-start">
          <div>
            <div className="flex gap-2 items-center mb-1">
              <PosBadge pos={player.position} />
              <span className="text-[10px] text-white/40 font-scoreboard">AGE {player.age}</span>
            </div>
            <h2 className="text-xl font-black text-white tracking-wide uppercase">
              <StaggeredText text={player.name} />
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs transition-all border bg-white/5 border-white/10 hover:border-emerald-500/50 hover:text-emerald-400 cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Speedometer telemetry */}
        <div className="flex items-center justify-around gap-2 py-2">
          <SpeedometerGauge value={player.riskScore} size={150} />
          <div className="flex flex-col gap-2 shrink-0">
            <RiskBadge tier={player.tier} />
            <span className="text-[9px] text-white/40 tracking-wider font-semibold font-scoreboard mt-0.5">
              TIER: {player.tier.toUpperCase()}
            </span>
          </div>
        </div>

      </div>

      {/* Details Scroll Area */}
      <div className="p-6 space-y-6 flex-1 overflow-y-auto">
        
        {/* Next Match — intentionally hidden until fixture data is available */}
        {false && (
          <DetailSection title="NEXT FIXTURE TELEMETRY">
          <GlassPanel>
            <div className="flex justify-between items-start mb-2">
              <span className="text-sm font-bold text-white tracking-wide">
                {player.nextMatch.opponent}
              </span>
              <SurfaceTag surface={player.nextMatch.surface} />
            </div>
            <div className="text-[11px] text-white/50 font-semibold space-y-1">
              <div className="flex justify-between">
                <span>Venue:</span>
                <span>{player.nextMatch.venue} ({player.nextMatch.homeAway})</span>
              </div>
              <div className="flex justify-between">
                <span>Date:</span>
                <span>{player.nextMatch.date}</span>
              </div>
            </div>
          </GlassPanel>
          </DetailSection>
        )}

        {/* Radar Bio-Metrics */}
        <DetailSection title="BIO-METRICS ANALYSIS RISK RADAR">
          <GlassPanel className="flex items-center justify-center py-2">
            <RiskRadar values={radarValues} size={190} />
          </GlassPanel>
        </DetailSection>

        {/* SHAP Indicators */}
        <DetailSection title="SHAP ATTRIBUTION EXPLAINABILITY">
          <GlassPanel>
            <div className="space-y-3">
              {player.shapFactors.map((f, i) => {
                const pct = Math.round(f.value * 100);
                const isPositive = pct > 0;
                const col = isPositive ? "#ff2d55" : "#00e87b";
                return (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-[10px] font-scoreboard shrink-0" style={{ color: col }}>
                      {isPositive ? "▲" : "▼"}
                    </span>
                    <span className="text-[10px] w-28 shrink-0 truncate text-white/60 font-semibold uppercase">{f.label}</span>
                    <div className="flex-1 h-2 rounded bg-black/40 border border-white/5 overflow-hidden">
                      <div
                        className="h-full rounded transition-all duration-700"
                        style={{
                          width: `${Math.min(Math.abs(pct) * 3, 100)}%`,
                          background: col,
                          boxShadow: `0 0 6px ${col}40`,
                        }}
                      />
                    </div>
                    <span className="text-[10px] w-8 text-right font-scoreboard font-bold" style={{ color: col }}>
                      {isPositive ? "+" : ""}{pct}%
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="border-t border-white/5 mt-4 pt-2 flex items-center justify-between text-[8px] text-white/30 font-scoreboard">
              <span>MODEL: XGBOOST REGRESSOR</span>
              <span>SHAP v0.44</span>
            </div>
          </GlassPanel>
        </DetailSection>

        {/* Workload Scoreboard */}
        <DetailSection title="WORKLOAD LED INDEX">
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "MINS/30D", value: player.minutesLast30, suffix: "m" },
              { label: "APPS/14D", value: player.gamesLast14, suffix: "" },
              { label: "CLEAN DAYS", value: player.daysSinceInjury, suffix: "d" },
            ].map((stat) => (
              <GlassPanel key={stat.label} className="text-center p-3 relative">
                <CardBeam colorFrom="#00e87b" duration={4} />
                <span className="block text-[8px] text-white/40 font-scoreboard tracking-wider uppercase mb-1">
                  {stat.label}
                </span>
                <span className="block text-lg font-scoreboard font-bold text-emerald-400">
                  {stat.value}{stat.suffix}
                </span>
              </GlassPanel>
            ))}
          </div>
        </DetailSection>

        {/* Injury Timeline */}
        <DetailSection title="INJURY HISTORY TIMELINE">
          <GlassPanel className="py-4">
            <InjuryTimeline injuries={player.injuryHistory} />
          </GlassPanel>
        </DetailSection>

      </div>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="block text-[0.6rem] font-scoreboard tracking-[0.15em] text-white/40 uppercase font-bold">
        {title}
      </span>
      {children}
    </div>
  );
}



// ─── Squad Summary Cards ───────────────────────────────────────────────────
function SquadSummary({ players }: { players: Player[] }) {
  const h = players.filter((p) => p.tier === "High").length;
  const m = players.filter((p) => p.tier === "Medium").length;
  const l = players.filter((p) => p.tier === "Low").length;
  const avg = Math.round(players.reduce((s, p) => s + p.riskScore, 0) / players.length);
  
  // Calculate next match turf exposure count
  const astroExposure = players.filter((p) => p.nextMatch.surface === "Artificial Turf").length;
  const isAstroNext = astroExposure > players.length / 2;

  const cards = [
    { label: "SQUAD AVERAGE RISK", value: avg, suffix: "%", sub: "Match week average risk", color: "#e2e8f0" },
    { label: "HIGH RISK FLAGGED", value: h, suffix: "", sub: "Critical physical status", color: "#ff2d55", highlight: "high" },
    { label: "MEDIUM REVIEW", value: m, suffix: "", sub: "Physio evaluation advised", color: "#ff9500" },
    { label: "LOW RISK CLEAR", value: l, suffix: "", sub: "Squad eligible to play", color: "#00e87b" },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      {cards.map((card, i) => {
        const isHighHighlight = card.highlight === "high";
        return (
          <div
            key={card.label}
            className="relative rounded-2xl p-5 border flex flex-col justify-between h-[110px] group transition-all duration-300"
            style={{
              background: "rgba(10, 26, 18, 0.45)",
              borderColor: isHighHighlight ? "rgba(255, 45, 85, 0.3)" : "rgba(0, 232, 123, 0.15)",
              boxShadow: isHighHighlight ? "0 0 15px rgba(255, 45, 85, 0.1)" : "0 4px 16px rgba(0,0,0,0.2)",
              animation: `statCardIn 0.6s ease-out ${i * 80}ms forwards`,
              opacity: 0,
            }}
          >
            {/* Animated card border beams */}
            {isHighHighlight ? (
              <div
                className="absolute inset-0 rounded-[inherit] pointer-events-none animate-[riskBreathing_3s_infinite]"
                style={{ borderLeftWidth: "3px" }}
              />
            ) : (
              <BorderBeam size={100} duration={5} delay={i * 0.5} />
            )}

            <span className="block text-[8px] font-scoreboard tracking-[0.15em] text-white/40 uppercase font-bold">
              {card.label}
            </span>

            <span className="block text-3xl font-scoreboard font-black leading-none my-1" style={{ color: card.color }}>
              <NumberTicker value={card.value} suffix={card.suffix} duration={1200} />
            </span>

            <span className="block text-[9px] text-white/30 tracking-wide font-semibold truncate">
              {card.sub}
            </span>
          </div>
        );
      })}

      {/* 5th Card: Next Surface — intentionally hidden until fixture data is available */}
      {false && (
        <div
        className="relative rounded-2xl p-5 border flex flex-col justify-between h-[110px] col-span-2 lg:col-span-1"
        style={{
          background: "rgba(10, 26, 18, 0.45)",
          borderColor: isAstroNext ? "rgba(255, 149, 0, 0.3)" : "rgba(0, 232, 123, 0.15)",
          animation: "statCardIn 0.6s ease-out 320ms forwards",
          opacity: 0,
        }}
      >
        <BorderBeam size={100} duration={6} colorFrom={isAstroNext ? "#ff9500" : "#00e87b"} />
        <span className="block text-[8px] font-scoreboard tracking-[0.15em] text-white/40 uppercase font-bold">
          NEXT MATCH SURFACE
        </span>
        <span
          className="block text-2xl font-scoreboard font-black leading-none my-1 uppercase"
          style={{ color: isAstroNext ? "#ff9500" : "#00e87b" }}
        >
          {isAstroNext ? "ASTRO" : "GRASS"}
        </span>
        <span className="block text-[9px] text-white/30 tracking-wide font-semibold truncate">
          {isAstroNext ? "⚠ High joint load alert" : "✓ Standard safety ratio"}
        </span>
        </div>
      )}
    </div>
  );
}

// ─── Tabbed Navigation ─────────────────────────────────────────────────────
function DashboardTabs({ active, onChange }: { active: string; onChange: (tab: string) => void }) {
  const tabs = ["Dashboard"];
  return (
    <div className="flex items-center gap-1 bg-black/35 p-0.5 rounded-lg border border-white/5 self-start">
      {tabs.map((tab) => {
        const isActive = active === tab;
        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className="relative px-4 py-1.5 rounded-md text-xs font-bold transition-all duration-300 font-scoreboard cursor-pointer"
            style={{
              color: isActive ? "#00e87b" : "rgba(255,255,255,0.4)",
              background: isActive ? "rgba(0, 232, 123, 0.08)" : "transparent",
            }}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}

// ─── Main PitchGuard Dashboard Component ───────────────────────────────────
interface PitchGuardProps {
  league: string;
  club: string;
  onBack: () => void;
}

export default function PitchGuard({ league, club, onBack }: PitchGuardProps) {
  const [squad, setSquad] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSquad(club)
      .then((apiPlayers) => setSquad(apiPlayers.map(mapApiPlayerToPlayer)))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [club]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [activeTab, setActiveTab] = useState("Dashboard");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#040a05" }}>
        <span className="text-emerald-400 font-scoreboard text-sm tracking-widest animate-pulse">
          LOADING SQUAD TELEMETRY...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-3" style={{ background: "#040a05" }}>
        <span className="text-red-400 font-scoreboard text-sm">FAILED TO LOAD SQUAD DATA</span>
        <span className="text-white/40 text-xs">{error}</span>
        <button onClick={onBack} className="text-emerald-400 text-xs underline mt-2">Go back</button>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen relative overflow-hidden flex flex-col justify-between"
      style={{ background: "#040a05", fontFamily: SF, color: "#e8f5ea" }}
    >
      <video autoPlay loop muted playsInline preload="auto"  style={{ position: "fixed", inset: 0, width: "100%", height: "100%",    objectFit: "cover", opacity: 0.345, filter: "brightness(0.6) saturate(0.7)", zIndex: 0 }}  src="/src/assets/vid3.mp4"/>
      <div style={{ position: "fixed", inset: 0, zIndex: 1, pointerEvents: "none",  background: "radial-gradient(ellipse at center, rgba(4,10,5,0.4) 0%, rgba(4,10,5,0.88) 100%)" }} />

      {/* Floating Stadium Ambient Glow Orbs */}
      <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 1 }}>
        <div
          className="absolute top-[10%] left-[15%] w-[450px] h-[450px] rounded-full filter blur-[120px]"
          style={{
            background: "radial-gradient(circle, rgba(10, 132, 255, 0.06) 0%, transparent 70%)",
            animation: "ambientGlow 10s ease-in-out infinite",
          }}
        />
        <div
          className="absolute bottom-[20%] right-[15%] w-[350px] h-[350px] rounded-full filter blur-[100px]"
          style={{
            background: "radial-gradient(circle, rgba(0, 232, 123, 0.05) 0%, transparent 70%)",
            animation: "ambientGlow 12s ease-in-out 3s infinite",
          }}
        />
      </div>

      {/* Top Header / Nav Section */}
      <div className="w-full flex flex-col z-20" style={{ position: "relative", zIndex: 2 }}>
        
        {/* Navbar */}
        <div
          className="w-full h-16 px-8 flex items-center justify-between border-b"
          style={{
            background: "rgba(4, 10, 5, 0.85)",
            backdropFilter: "blur(20px)",
            borderColor: "rgba(0, 232, 123, 0.15)",
          }}
        >
          {/* Left: Breadcrumbs */}
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-scoreboard font-bold border bg-white/5 border-white/10 hover:border-emerald-500/50 hover:text-emerald-400 transition-all cursor-pointer"
            >
              <span>←</span>
              <span>Back</span>
            </button>
            <div className="w-px h-6 bg-white/10" />
            
            <div className="flex items-center gap-2 text-[10px] font-scoreboard text-white/40 tracking-wider select-none">
              <span className="hover:text-white transition-colors cursor-pointer" onClick={onBack}>⚡ PITCHGUARD</span>
              <span>/</span>
              <span className="uppercase">{league}</span>
              <span>/</span>
              <span className="text-emerald-400 font-bold uppercase">{club}</span>
            </div>
          </div>

          {/* Center: Pulsing Model Active Badge */}
          <div className="hidden md:flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/25">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
            <span className="text-[10px] font-scoreboard font-bold text-emerald-400 tracking-wider uppercase">
              MODEL STATUS: ACTIVE · CatBoost v5 · SHAP v0.44 · Season 25/26
            </span>
          </div>

          {/* Right: Search & Animated Football User Avatar */}
          <div className="flex items-center gap-4">
            <span className="text-xs font-scoreboard text-white/50 tracking-wider hidden sm:inline select-none">
              SECURE CONNECT
            </span>
            <div
              className="w-8 h-8 rounded-full border border-emerald-500/30 flex items-center justify-center bg-black/60 shadow-lg cursor-pointer"
              title="Dashboard Account"
            >
              <FootballSVG size={22} spinning={true} />
            </div>
          </div>
        </div>

        {/* Dashboard Title & Tabs Area */}
        <div className="px-8 pt-6 pb-2 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex flex-col">
            <h1
              className="text-3xl font-scoreboard font-black tracking-wider text-white uppercase"
              style={{ textShadow: "0 2px 10px rgba(0,0,0,0.5)" }}
            >
              {club}
            </h1>
            <span className="text-[10px] tracking-[0.2em] font-bold text-white/40 uppercase mt-0.5">
              Squad Bio-Mechanical Telemetry Node
            </span>
          </div>
          <DashboardTabs active={activeTab} onChange={setActiveTab} />
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="px-8 py-4 flex-1 z-10 w-full max-w-7xl mx-auto flex flex-col gap-6" style={{ position: "relative", zIndex: 2 }}>
        
        {/* Squad Cards Summary */}
        <SquadSummary players={squad} />

        <div className="flex flex-col xl:flex-row gap-6 w-full items-start">
          
          {/* Left Table Panel */}
          <div className="flex-1 min-w-0 w-full flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-scoreboard tracking-[0.2em] text-white/40 uppercase font-bold">
                ROSTER TELEMETRY INDEX · SELECT PLAYER FOR FULL DIAGNOSTICS
              </span>
            </div>
            <SquadRiskTable players={squad} onSelect={setSelectedPlayer} />
          </div>

          {/* Right Panel: Intelligence Feed */}
          <div className="w-full xl:w-[380px] shrink-0">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[9px] font-scoreboard tracking-[0.2em] text-white/40 uppercase font-bold">
                STADIUM HAZARD TELEMETRY
              </span>
            </div>
            <IntelFeed players={squad} />
          </div>
        </div>
      </div>

      {/* Side Slide-out Panel Overlay */}
      {selectedPlayer && (
        <>
          <div
            onClick={() => setSelectedPlayer(null)}
            className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm transition-opacity duration-300"
          />
          <PlayerDetail player={selectedPlayer} onClose={() => setSelectedPlayer(null)} />
        </>
      )}

      {/* Footer */}
      <div
        className="w-full px-8 py-5 border-t mt-8 z-10 flex items-center justify-between"
        style={{ borderColor: "rgba(0, 232, 123, 0.15)", background: "rgba(4, 10, 5, 0.85)", position: "relative", zIndex: 2 }}
      >
        <span className="text-[9px] font-scoreboard text-white/30 tracking-wider">
          PITCHGUARD DEPLOYMENT v2.4.1-ALPHA · SYSTEM SECURED BY SSL SHA-256
        </span>
        <span className="text-[9px] font-scoreboard text-white/30 tracking-wider uppercase">
          Confidential Sports Analytics Interface
        </span>
      </div>
    </div>
  );
}