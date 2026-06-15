import { useState } from "react";
import {
  GlassButton,
  StadiumBackground,
} from "./ui/GlassUI";
import { LimelightNav, type NavItem } from "./ui/limelight-nav";

const LEAGUES = [
  { name: "Premier League", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", short: "PL" },
  { name: "La Liga", flag: "🇪🇸", short: "LL" },
  { name: "Bundesliga", flag: "🇩🇪", short: "BL" },
  { name: "Serie A", flag: "🇮🇹", short: "SA" },
  { name: "Ligue 1", flag: "🇫🇷", short: "L1" },
  { name: "Süper Lig", flag: "🇹🇷", short: "SL" },
];

interface LeagueDockProps {
  onSelectLeague: (league: string) => void;
}

export default function LeagueDock({ onSelectLeague }: LeagueDockProps) {
  const [hoveredLeague, setHoveredLeague] = useState<string | null>(null);

  const navItems: NavItem[] = LEAGUES.map((league) => ({
    id: league.short,
    label: league.name,
    icon: (
      <div className="flex flex-col items-center justify-center gap-0.5 select-none">
        <span className="text-3xl leading-none">{league.flag}</span>
        <span
          className="text-[0.5rem] font-bold tracking-wider text-white/60"
          style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif" }}
        >
          {league.short}
        </span>
      </div>
    ),
    onClick: () => onSelectLeague(league.name),
  }));

  return (
    <StadiumBackground>
      <div className="flex flex-col gap-10 items-center justify-center w-full px-4">
        {/* Limelight Dock with League Icons */}
        <div
          style={{
            animation: "fadeInUp 0.8s ease-out 0.2s forwards",
            opacity: 0,
          }}
        >
          <LimelightNav
            items={navItems}
            onHoverItem={(item) => setHoveredLeague(item?.label ?? null)}
          />
        </div>

        {/* CTA Button */}
        <div
          style={{
            animation: "fadeInUp 0.8s ease-out 0.4s forwards",
            opacity: 0,
          }}
        >
          <GlassButton>
            <div className="text-xl text-white">
              <p style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 600 }}>
                {hoveredLeague
                  ? `Open ${hoveredLeague}`
                  : "Select a league to begin"}
              </p>
            </div>
          </GlassButton>
        </div>
      </div>
    </StadiumBackground>
  );
}
