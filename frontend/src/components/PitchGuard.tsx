import { useState } from "react";
import { ShimmerText } from "@/components/ui/shimmer-text";
import { GlassPanel, GlassBadge } from "@/components/ui/GlassPanel";
import { DottedSurface } from "@/components/ui/dotted-surface";
import { cn } from "@/lib/utils";
import { AnimatedPitch } from "@/components/ui/AnimatedPitch";

// ─── Types ─────────────────────────────────────────────────────────────────
type Tier = "Low" | "Medium" | "High";
interface Player {
  id: number; name: string; position: string; age: number;
  minutesLast30: number; gamesLast14: number; daysSinceInjury: number;
  injuryCount2yr: number; riskScore: number; tier: Tier;
  subScores: { acl: number; hamstring: number; ankle: number; meniscus: number };
  shapFactors: { label: string; value: number }[];
  nextMatch: { opponent: string; venue: string; surface: string; homeAway: string; date: string };
  injuryHistory: { year: number; type: string; gamesMissed: number }[];
  distance: number;
}

// ─── Mock Data Generator ───────────────────────────────────────────────────
function generateMockSquad(): Player[] {
  const pos = ["GK","DEF","MID","FWD"];
  const fn = ["Luca","James","Mateo","Arjun","Kai","Sven","Omar","Riku","Diego","Theo","Leo","Finn"];
  const ln = ["Müller","Torres","Mbeki","Tanaka","Walsh","Novak","Eriksen","Santos","Osei","Dubois","Bianchi","Ali"];
  const inj = ["ACL","Hamstring","Ankle","Meniscus"];
  const sf = ["Natural Grass","Artificial Turf"];
  const vn = ["Emirates Stadium","Camp Nou","Allianz Arena","San Siro","Parc des Princes"];
  return Array.from({length:18},(_,i)=>{
    const rs=Math.floor(Math.random()*100);
    const surface=sf[Math.floor(Math.random()*2)];
    return {
      id:i+1, name:`${fn[i%fn.length]} ${ln[i%ln.length]}`, position:pos[i%4],
      age:20+Math.floor(Math.random()*17), minutesLast30:Math.floor(Math.random()*900),
      gamesLast14:Math.floor(Math.random()*6), daysSinceInjury:Math.floor(Math.random()*400),
      injuryCount2yr:Math.floor(Math.random()*5), riskScore:rs,
      tier:(rs<40?"Low":rs<70?"Medium":"High") as Tier,
      subScores:{acl:Math.round(Math.random()*60),hamstring:Math.round(Math.random()*70),ankle:Math.round(Math.random()*55),meniscus:Math.round(Math.random()*45)},
      shapFactors:[
        {label:surface==="Artificial Turf"?"Artificial Turf":"Natural Grass",value:+(Math.random()*0.3).toFixed(2)},
        {label:"Fixture Congestion",value:+(Math.random()*0.3).toFixed(2)},
        {label:"Injury History",value:+(Math.random()*0.25).toFixed(2)},
      ].sort((a,b)=>b.value-a.value),
      nextMatch:{opponent:`vs. ${ln[Math.floor(Math.random()*ln.length)]} FC`,venue:vn[Math.floor(Math.random()*vn.length)],surface,homeAway:Math.random()>0.5?"Away":"Home",date:`June ${10+i}, 2026`},
      injuryHistory:Array.from({length:Math.floor(Math.random()*5)},(_,j)=>({year:2020+j,type:inj[Math.floor(Math.random()*inj.length)],gamesMissed:2+Math.floor(Math.random()*20)})),
      distance: +(Math.random()*500 + 100).toFixed(1),
    };
  });
}

// ─── Color Constants ───────────────────────────────────────────────────────
const tierClr: Record<Tier,{bg:string;text:string;border:string;dot:string}> = {
  Low:{bg:"rgba(0, 232, 123, 0.1)",text:"#00e87b",border:"rgba(0, 232, 123, 0.3)",dot:"#00e87b"},
  Medium:{bg:"rgba(255, 149, 0, 0.1)",text:"#ff9500",border:"rgba(255, 149, 0, 0.3)",dot:"#ff9500"},
  High:{bg:"rgba(255, 45, 85, 0.1)",text:"#ff2d55",border:"rgba(255, 45, 85, 0.3)",dot:"#ff2d55"},
};
const posClr: Record<string,string> = {GK:"#bf5af2",DEF:"#0a84ff",MID:"#00e87b",FWD:"#ff9500"};

const SF = "'Inter', 'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif";

// ─── Sub Components ────────────────────────────────────────────────────────

function RiskDot({ tier, size = 8 }: { tier: Tier; size?: number }) {
  const c = tierClr[tier];
  return (
    <span
      className="inline-block rounded-full shrink-0"
      style={{
        width: size, height: size,
        backgroundColor: c.dot,
        boxShadow: `0 0 6px ${c.dot}60`,
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
      className="text-[0.65rem] font-bold px-2 py-0.5 rounded"
      style={{
        background: `${cl}15`,
        color: cl,
        border: `1px solid ${cl}30`,
        fontFamily: SF,
      }}
    >
      {pos}
    </span>
  );
}

// ─── Risk Bar Chart ────────────────────────────────────────────────────────
function RiskBarChart({ categories }: { categories: { label: string; value: number }[] }) {
  return (
    <div className="flex flex-col gap-2.5">
      {categories.map((cat, i) => {
        const color = cat.value > 70 ? "#ef4444" : cat.value > 40 ? "#f59e0b" : "#34d399";
        return (
          <div key={i} className="flex items-center gap-3">
            <span
              className="text-[0.62rem] w-28 shrink-0 truncate"
              style={{ color: "var(--color-muted-foreground)", fontFamily: SF }}
            >
              {cat.label}
            </span>
            <div className="flex-1 h-5 rounded-sm overflow-hidden" style={{ background: "rgba(255,255,255,0.04)" }}>
              <div
                className="h-full rounded-sm transition-all duration-1000 ease-out"
                style={{
                  width: `${cat.value}%`,
                  background: `linear-gradient(90deg, ${color}cc, ${color})`,
                  boxShadow: `0 0 8px ${color}40`,
                  animation: `riskBarGrow 1s ease-out ${i * 0.1}s both`,
                  ["--bar-width" as string]: `${cat.value}%`,
                }}
              />
            </div>
            <span
              className="text-[0.65rem] font-bold w-8 text-right"
              style={{ color, fontFamily: SF }}
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
  const sorted = [...players]
    .filter(p => posFilter === "ALL" || p.position === posFilter)
    .sort((a, b) => b.riskScore - a.riskScore);

  return (
    <GlassPanel corners animationDelay={300} noPadding>
      <div className="p-4 pb-2">
        <div className="flex items-center justify-between mb-4">
          <span
            className="text-[0.65rem] font-bold tracking-[0.12em] uppercase"
            style={{ color: "var(--color-accent)", fontFamily: SF }}
          >
            Squad Risk Table
          </span>
          <div className="flex gap-1">
            {["ALL", "GK", "DEF", "MID", "FWD"].map(p => (
              <button
                key={p}
                onClick={() => setPosFilter(p)}
                className="px-2.5 py-1 rounded-md text-[0.6rem] font-bold transition-all duration-300 border"
                style={{
                  fontFamily: SF,
                  color: posFilter === p ? (posClr[p] || "#34d399") : "var(--color-muted)",
                  borderColor: posFilter === p ? `${posClr[p] || "#34d399"}40` : "transparent",
                  background: posFilter === p ? `${posClr[p] || "#34d399"}10` : "transparent",
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Risk bar chart */}
        <RiskBarChart
          categories={[
            { label: "Playability Risks", value: Math.round(players.reduce((s,p) => s + p.subScores.acl, 0) / players.length * 1.5) },
            { label: "Grassed Terrain", value: Math.round(players.filter(p => p.nextMatch.surface === "Natural Grass").length / players.length * 100) },
            { label: "Match Fatigue", value: Math.round(players.reduce((s,p) => s + p.gamesLast14, 0) / players.length * 20) },
          ]}
        />
      </div>

      {/* Player list */}
      <div
        className="border-t mt-2 max-h-[320px] overflow-y-auto"
        style={{ borderColor: "var(--glass-border)" }}
      >
        <table className="w-full">
          <thead>
            <tr
              className="sticky top-0 z-10"
              style={{ background: "var(--glass-bg)" }}
            >
              <th className="text-left text-[0.55rem] tracking-wider px-4 py-2 font-semibold" style={{ color: "var(--color-muted)", fontFamily: SF }}>#</th>
              <th className="text-left text-[0.55rem] tracking-wider py-2 font-semibold" style={{ color: "var(--color-muted)", fontFamily: SF }}>PLAYER</th>
              <th className="text-left text-[0.55rem] tracking-wider py-2 font-semibold" style={{ color: "var(--color-muted)", fontFamily: SF }}>POS</th>
              <th className="text-right text-[0.55rem] tracking-wider py-2 font-semibold" style={{ color: "var(--color-muted)", fontFamily: SF }}>DIST</th>
              <th className="text-right text-[0.55rem] tracking-wider py-2 pr-4 font-semibold" style={{ color: "var(--color-muted)", fontFamily: SF }}>RISK</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, idx) => (
              <tr
                key={p.id}
                onClick={() => onSelect(p)}
                className="cursor-pointer transition-colors duration-200 group"
                style={{ borderBottom: "1px solid rgba(0, 232, 123, 0.05)" }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(0, 232, 123, 0.06)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >
                <td className="px-4 py-2.5">
                  <span
                    className="text-[0.65rem] font-bold w-5 h-5 rounded-full flex items-center justify-center"
                    style={{
                      background: tierClr[p.tier].bg,
                      color: tierClr[p.tier].text,
                      border: `1px solid ${tierClr[p.tier].border}`,
                      fontFamily: SF,
                    }}
                  >
                    {idx + 1}
                  </span>
                </td>
                <td className="py-2.5">
                  <div className="flex items-center gap-2">
                    {/* Avatar circle */}
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-[0.55rem] font-bold shrink-0"
                      style={{
                        background: `${posClr[p.position] || "#34d399"}20`,
                        color: posClr[p.position] || "#34d399",
                        border: `1px solid ${posClr[p.position] || "#34d399"}30`,
                        fontFamily: SF,
                      }}
                    >
                      {p.name.split(" ").map(n => n[0]).join("")}
                    </div>
                    <span
                      className="text-xs font-semibold truncate"
                      style={{ color: "#e2e8f0", fontFamily: SF }}
                    >
                      {p.name}
                    </span>
                  </div>
                </td>
                <td className="py-2.5">
                  <PosBadge pos={p.position} />
                </td>
                <td className="py-2.5 text-right">
                  <span className="text-[0.65rem]" style={{ color: "var(--color-muted-foreground)", fontFamily: SF }}>
                    {p.distance}km
                  </span>
                </td>
                <td className="py-2.5 pr-4">
                  <div className="flex items-center justify-end gap-2">
                    <span
                      className="text-xs font-bold"
                      style={{ color: tierClr[p.tier].text, fontFamily: SF }}
                    >
                      {p.riskScore}%
                    </span>
                    <RiskDot tier={p.tier} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassPanel>
  );
}

// ─── Player Detail Side Panel ──────────────────────────────────────────────
function PlayerDetail({ player, onClose }: { player: Player; onClose: () => void }) {
  const c = tierClr[player.tier];
  return (
    <div
      className="fixed top-0 right-0 h-screen overflow-y-auto z-[100]"
      style={{
        width: "min(440px,100vw)",
        boxShadow: "-20px 0 60px rgba(0,0,0,0.6)",
        background: "var(--glass-bg)",
        backdropFilter: "blur(30px)",
        borderLeft: "1px solid var(--glass-border)",
        animation: "panelSlideLeft 0.4s ease-out",
      }}
    >
      {/* Header */}
      <div
        className="sticky top-0 z-10 p-6"
        style={{
          background: `${c.bg}`,
          backdropFilter: "blur(12px)",
          borderBottom: `1px solid ${c.border}`,
        }}
      >
        <div className="flex justify-between items-start">
          <div>
            <div className="flex gap-2 items-center mb-1">
              <PosBadge pos={player.position} />
              <span className="text-xs" style={{ color: "var(--color-muted)", fontFamily: SF }}>Age {player.age}</span>
            </div>
            <ShimmerText className="text-xl font-extrabold" style={{ color: "#f0f4f1", fontFamily: SF }}>{player.name}</ShimmerText>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-sm transition-colors"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#8faa98",
            }}
          >
            ✕
          </button>
        </div>
        <div className="mt-4 flex items-center gap-4">
          <span className="text-5xl font-bold" style={{ color: c.text, fontFamily: SF }}>{player.riskScore}%</span>
          <div>
            <RiskBadge tier={player.tier} />
            <span className="block text-[0.6rem] mt-1" style={{ color: "var(--color-muted)", fontFamily: SF }}>INJURY RISK SCORE</span>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <ActionButton label="Flag Player" />
          <ActionButton label="Full Report" primary />
        </div>
      </div>

      {/* Sections */}
      <div className="p-6 space-y-5">
        <DetailSection title="NEXT MATCH">
          <GlassPanel>
            <ShimmerText className="text-sm font-bold mb-1.5" style={{ color: "#f0f4f1", fontFamily: SF }}>{player.nextMatch.opponent}</ShimmerText>
            <div className="flex gap-2 flex-wrap items-center">
              <SurfaceTag surface={player.nextMatch.surface} />
              <span className="text-[0.65rem]" style={{ color: "var(--color-muted)", fontFamily: SF }}>
                {player.nextMatch.homeAway} · {player.nextMatch.venue}
              </span>
            </div>
            <span className="block text-[0.6rem] mt-1" style={{ color: "var(--color-muted)", fontFamily: SF }}>{player.nextMatch.date}</span>
          </GlassPanel>
        </DetailSection>

        <DetailSection title="WHY THIS SCORE (SHAP)">
          <GlassPanel>
            {player.shapFactors.map((f, i) => {
              const pct = Math.round(f.value * 100);
              const col = pct > 20 ? "#ef4444" : pct > 10 ? "#f59e0b" : "#22c55e";
              return (
                <div key={i} className="flex items-center gap-2 mb-2">
                  <span className="text-[0.62rem] w-28 shrink-0 truncate" style={{ color: "var(--color-muted-foreground)", fontFamily: SF }}>{f.label}</span>
                  <div className="flex-1 h-1.5 rounded overflow-hidden" style={{ background: "rgba(255,255,255,0.04)" }}>
                    <div className="h-full rounded transition-all duration-700" style={{ width: `${Math.min(pct * 3, 100)}%`, background: col }} />
                  </div>
                  <span className="text-[0.62rem] w-8 text-right font-bold" style={{ color: col, fontFamily: SF }}>+{pct}%</span>
                </div>
              );
            })}
            <span className="block text-[0.55rem] mt-2" style={{ color: "var(--color-muted)", fontFamily: SF }}>Model: XGBoost · SHAP v0.44</span>
          </GlassPanel>
        </DetailSection>

        <DetailSection title="INJURY TYPE RISK">
          <GlassPanel>
            {([
              ["ACL", player.subScores.acl, "#ef4444"],
              ["Hamstring", player.subScores.hamstring, "#f59e0b"],
              ["Ankle", player.subScores.ankle, "#3b82f6"],
              ["Meniscus", player.subScores.meniscus, "#8b5cf6"],
            ] as [string, number, string][]).map(([label, value, color]) => (
              <div key={label} className="mb-2.5">
                <div className="flex justify-between mb-1">
                  <span className="text-[0.62rem]" style={{ color: "var(--color-muted-foreground)", fontFamily: SF }}>{label}</span>
                  <span className="text-[0.62rem] font-bold" style={{ color: "#d4e4d9", fontFamily: SF }}>{value}%</span>
                </div>
                <div className="h-1.5 rounded overflow-hidden" style={{ background: "rgba(255,255,255,0.04)" }}>
                  <div className="h-full rounded transition-all duration-700" style={{ width: `${value}%`, background: color }} />
                </div>
              </div>
            ))}
          </GlassPanel>
        </DetailSection>

        <DetailSection title="WORKLOAD">
          <div className="flex gap-2">
            {([
              ["MINS/30D", player.minutesLast30],
              ["GAMES/14D", player.gamesLast14],
              ["INJURIES/2YR", player.injuryCount2yr],
            ] as [string, number][]).map(([l, v]) => (
              <GlassPanel key={l} className="flex-1">
                <span className="block text-[0.55rem] tracking-wider uppercase mb-1" style={{ color: "var(--color-muted)", fontFamily: SF }}>{l}</span>
                <span className="block text-lg font-bold" style={{ color: "#f0f4f1", fontFamily: SF }}>{v}</span>
              </GlassPanel>
            ))}
          </div>
        </DetailSection>

        <DetailSection title="INJURY HISTORY">
          <GlassPanel>
            {player.injuryHistory.length === 0 ? (
              <span className="block text-xs" style={{ color: "var(--color-muted)", fontFamily: SF }}>No recorded injuries</span>
            ) : (
              player.injuryHistory.map((inj, i) => (
                <div
                  key={i}
                  className="flex justify-between items-center py-2"
                  style={{ borderBottom: i < player.injuryHistory.length - 1 ? "1px solid rgba(0, 232, 123,0.08)" : "none" }}
                >
                  <div>
                    <span className="text-xs font-bold" style={{ color: "#d4e4d9", fontFamily: SF }}>{inj.type}</span>
                    <span className="text-[0.6rem] ml-1" style={{ color: "var(--color-muted)", fontFamily: SF }}>· {inj.year}</span>
                  </div>
                  <span className="text-[0.6rem]" style={{ color: "var(--color-muted)", fontFamily: SF }}>{inj.gamesMissed} missed</span>
                </div>
              ))
            )}
          </GlassPanel>
        </DetailSection>

        <div className="flex gap-2 pt-2">
          <ActionButton label="Rest Player" />
          <ActionButton label="Adjust Load" />
        </div>
      </div>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <span
        className="block text-[0.6rem] tracking-[0.12em] uppercase font-semibold mb-2"
        style={{ color: "var(--color-muted)", fontFamily: SF }}
      >
        {title}
      </span>
      {children}
    </div>
  );
}

function ActionButton({ label, primary, onClick }: { label: string; primary?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300 border"
      style={{
        fontFamily: SF,
        background: primary ? "rgba(0, 232, 123,0.15)" : "rgba(255,255,255,0.04)",
        borderColor: primary ? "rgba(0, 232, 123,0.35)" : "rgba(255,255,255,0.08)",
        color: primary ? "#00e87b" : "#7a9ab8",
      }}
    >
      {label}
    </button>
  );
}

function SurfaceTag({ surface }: { surface: string }) {
  const a = surface === "Artificial Turf";
  return (
    <span
      className="text-[0.6rem] font-bold px-2 py-0.5 rounded"
      style={{
        color: a ? "#ff9500" : "#00e87b",
        background: a ? "rgba(255,149,0,0.1)" : "rgba(0,232,123,0.1)",
        border: `1px solid ${a ? "rgba(255,149,0,0.25)" : "rgba(0,232,123,0.25)"}`,
        fontFamily: SF,
      }}
    >
      {a ? "⚠ ASTRO" : "✓ GRASS"}
    </span>
  );
}

// ─── Squad Summary Cards ───────────────────────────────────────────────────
function SquadSummary({ players }: { players: Player[] }) {
  const h = players.filter(p => p.tier === "High").length;
  const m = players.filter(p => p.tier === "Medium").length;
  const l = players.filter(p => p.tier === "Low").length;
  const avg = Math.round(players.reduce((s, p) => s + p.riskScore, 0) / players.length);

  const cards: { label: string; value: string | number; sub: string; color: string }[] = [
    { label: "SQUAD AVG", value: `${avg}%`, sub: "match week risk", color: "#f0f4f1" },
    { label: "HIGH RISK", value: h, sub: "players flagged", color: "#ef4444" },
    { label: "MEDIUM", value: m, sub: "physio review", color: "#f59e0b" },
    { label: "LOW RISK", value: l, sub: "clear to play", color: "#22c55e" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      {cards.map((card, i) => (
        <GlassPanel key={card.label} animationDelay={100 + i * 80}>
          <span
            className="block text-[0.55rem] tracking-[0.12em] uppercase font-semibold mb-1"
            style={{ color: "var(--color-muted)", fontFamily: SF }}
          >
            {card.label}
          </span>
          <ShimmerText
            className="text-2xl font-bold"
            style={{ color: card.color, fontFamily: SF }}
          >
            {card.value}
          </ShimmerText>
          <span
            className="block text-[0.55rem] mt-0.5"
            style={{ color: "var(--color-muted)", fontFamily: SF }}
          >
            {card.sub}
          </span>
        </GlassPanel>
      ))}
    </div>
  );
}

// ─── Tabbed Navigation ─────────────────────────────────────────────────────
function DashboardTabs({ active, onChange }: { active: string; onChange: (tab: string) => void }) {
  const tabs = ["Dashboard", "Settings", "Dosely & Bones", "Atops"];
  return (
    <div className="flex items-center gap-1 mt-3">
      {tabs.map(tab => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className="px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-300 border"
          style={{
            fontFamily: SF,
            color: active === tab ? "#00e87b" : "var(--color-muted)",
            background: active === tab ? "rgba(0, 232, 123,0.08)" : "transparent",
            borderColor: active === tab ? "rgba(0, 232, 123,0.2)" : "transparent",
          }}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

// ─── Main PitchGuard Component ─────────────────────────────────────────────

interface PitchGuardProps {
  league: string;
  club: string;
  onBack: () => void;
}

export default function PitchGuard({ league, club, onBack }: PitchGuardProps) {
  const [squad] = useState<Player[]>(() => generateMockSquad());
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [activeTab, setActiveTab] = useState("Dashboard");

  return (
    <div
      className="min-h-screen relative overflow-hidden"
      style={{ background: "var(--color-background)", fontFamily: SF, color: "var(--color-foreground)" }}
    >
      {/* Particle background */}
      <DottedSurface className="size-full" />

      {/* Ambient blue/purple glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(10, 132, 255,0.06) 0%, transparent 70%)",
            animation: "ambientGlow 8s ease-in-out infinite",
          }}
        />
        <div
          className="absolute bottom-0 right-1/4 w-[400px] h-[400px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(191, 90, 242,0.04) 0%, transparent 70%)",
            animation: "ambientGlow 10s ease-in-out 2s infinite",
          }}
        />
      </div>

      {/* Radial center glow */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute -top-10 left-1/2 size-full -translate-x-1/2 rounded-full",
            "bg-[radial-gradient(ellipse_at_center,rgba(10, 132, 255,0.03),transparent_50%)]",
            "blur-[30px]",
          )}
        />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* NAV BAR */}
        <div
          className="sticky top-0 z-50 flex items-center justify-between h-14 px-8 border-b"
          style={{
            background: "rgba(3, 13, 26, 0.85)",
            backdropFilter: "blur(20px)",
            borderColor: "var(--glass-border)",
          }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-300 border"
              style={{
                fontFamily: SF,
                background: "rgba(255,255,255,0.04)",
                borderColor: "rgba(255,255,255,0.08)",
                color: "#7a9ab8",
              }}
            >
              ← Back
            </button>
            <div className="w-px h-6" style={{ background: "var(--glass-border)" }} />
            {/* Logo */}
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center text-sm font-bold"
              style={{
                background: "linear-gradient(135deg, #00e87b, #0a84ff)",
                color: "#fff",
                boxShadow: "0 0 12px rgba(0, 232, 123, 0.3)",
              }}
            >
              ⚡
            </div>
            <ShimmerText className="text-lg font-extrabold">PitchGuard</ShimmerText>
            <GlassBadge style={{ color: "#00e87b", borderColor: "rgba(0, 232, 123, 0.3)" }}>BETA</GlassBadge>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <button
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all duration-300"
              style={{
                fontFamily: SF,
                background: "rgba(0, 232, 123,0.12)",
                border: "1px solid rgba(0, 232, 123,0.3)",
                color: "#00e87b",
              }}
            >
              <span>🔍</span>
              Search Reports
              <span
                className="w-4 h-4 rounded-full flex items-center justify-center text-[0.5rem]"
                style={{ background: "rgba(0, 232, 123, 0.25)" }}
              >
                ✓
              </span>
            </button>
            {/* User avatar placeholder */}
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
              style={{
                background: "linear-gradient(135deg, #00e87b, #0a84ff)",
                color: "#fff",
              }}
            >
              M
            </div>
          </div>
        </div>

        {/* Dashboard Header + Tabs */}
        <div className="px-8 pt-5">
          <div className="flex items-start justify-between">
            <div>
              <span
                className="block text-[0.65rem] font-semibold tracking-[0.12em] uppercase mb-1"
                style={{ color: "var(--color-muted)", fontFamily: SF }}
              >
                {league.toUpperCase()} · INJURY RISK DASHBOARD
              </span>
              <ShimmerText
                className="text-3xl font-bold leading-none"
                style={{ fontFamily: "'Syne', sans-serif" }}
              >
                {club}
              </ShimmerText>
              <DashboardTabs active={activeTab} onChange={setActiveTab} />
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="px-8 py-5">
          <SquadSummary players={squad} />

          <div className="flex gap-5 w-full">
            {/* Left: Squad Risk Table */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-[0.62rem] font-semibold tracking-wider uppercase"
                  style={{ color: "var(--color-muted)", fontFamily: SF }}
                >
                  SQUAD RISK TABLE · click any player for detail
                </span>
                <div className="flex gap-2">
                  <ActionButton label="Export CSV" />
                  <ActionButton label="Run Analysis" primary />
                </div>
              </div>
              <SquadRiskTable players={squad} onSelect={setSelectedPlayer} />
            </div>

            {/* Right: Live Telemetry */}
            <div className="hidden xl:block w-[380px] shrink-0">
              <AnimatedPitch />
            </div>
          </div>
        </div>
      </div>

      {/* Player detail overlay */}
      {selectedPlayer && (
        <>
          <div
            onClick={() => setSelectedPlayer(null)}
            className="fixed inset-0 z-[90]"
            style={{ background: "rgba(3, 13, 26, 0.6)", backdropFilter: "blur(4px)" }}
          />
          <PlayerDetail player={selectedPlayer} onClose={() => setSelectedPlayer(null)} />
        </>
      )}

      {/* Footer */}
      <div
        className="relative z-10 px-8 py-4 border-t mt-8"
        style={{ borderColor: "var(--glass-border)" }}
      >
        <div className="text-[0.55rem]" style={{ color: "var(--color-muted)", fontFamily: SF }}>
          PitchGuard v0.1 · Confidential · Internal use only
        </div>
      </div>
    </div>
  );
}
