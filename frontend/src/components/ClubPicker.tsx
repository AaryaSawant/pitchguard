import {
  GlassButton,
  StadiumBackground,
} from "./ui/GlassUI";
import { LimelightNav, type NavItem } from "./ui/limelight-nav";

const CLUBS: Record<string, string[]> = {
  "Premier League": ["Arsenal", "Chelsea", "Liverpool", "Manchester City", "Tottenham Hotspur"],
  "La Liga": ["Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla"],
  "Bundesliga": ["Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen"],
  "Serie A": ["Juventus", "AC Milan", "Inter Milan", "AS Roma"],
  "Ligue 1": ["PSG", "Monaco", "Marseille"],
  "Süper Lig": ["Galatasaray", "Fenerbahce", "Besiktas"],
};

const CLUB_EMOJI: Record<string, string> = {
  Arsenal: "🔴", Chelsea: "🔵", Liverpool: "🟡", "Manchester City": "🩵", "Tottenham Hotspur": "⚪",
  "Real Madrid": "👑", Barcelona: "🔵", "Atletico Madrid": "🔴", Sevilla: "⚪",
  "Bayern Munich": "🔴", "Borussia Dortmund": "🟡", "Bayer Leverkusen": "⚫",
  Juventus: "⬛", "AC Milan": "🔴", "Inter Milan": "🔵", "AS Roma": "🟠",
  PSG: "🔵", Monaco: "🔴", Marseille: "⚪",
  Galatasaray: "🟡", Fenerbahce: "💛", Besiktas: "⬛",
};

const CLUB_SHORT: Record<string, string> = {
  Arsenal: "ARS", Chelsea: "CHE", Liverpool: "LIV", "Manchester City": "MCI", "Tottenham Hotspur": "TOT",
  "Real Madrid": "RMA", Barcelona: "FCB", "Atletico Madrid": "ATM", Sevilla: "SEV",
  "Bayern Munich": "BAY", "Borussia Dortmund": "BVB", "Bayer Leverkusen": "B04",
  Juventus: "JUV", "AC Milan": "ACM", "Inter Milan": "INT", "AS Roma": "ROM",
  PSG: "PSG", Monaco: "MON", Marseille: "MAR",
  Galatasaray: "GAL", Fenerbahce: "FEN", Besiktas: "BES",
};

interface ClubPickerProps {
  league: string;
  onSelectClub: (club: string) => void;
  onBack: () => void;
}

export default function ClubPicker({ league, onSelectClub, onBack }: ClubPickerProps) {
  const clubs = CLUBS[league] || [];

  const navItems: NavItem[] = clubs.map((club) => ({
    id: CLUB_SHORT[club] || club.slice(0, 3).toUpperCase(),
    label: club,
    icon: (
      <div className="flex flex-col items-center justify-center gap-0.5 select-none">
        <span className="text-3xl leading-none">{CLUB_EMOJI[club] || "⚽"}</span>
        <span
          className="text-[0.5rem] font-bold tracking-wider text-white/60"
          style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif" }}
        >
          {CLUB_SHORT[club] || club.slice(0, 3).toUpperCase()}
        </span>
      </div>
    ),
    onClick: () => onSelectClub(club),
  }));

  return (
    <StadiumBackground>
      <div className="flex flex-col gap-8 items-center justify-center w-full px-4 py-12">
        {/* Back button */}
        <div
          className="self-start ml-4 md:ml-12"
          style={{
            animation: "fadeInUp 0.5s ease-out forwards",
          }}
        >
          <GlassButton onClick={onBack} className="!px-6 !py-3 !hover:px-7 !hover:py-4">
            <div className="flex items-center gap-2 text-white text-sm">
              <span>←</span>
              <span style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif" }}>Back to leagues</span>
            </div>
          </GlassButton>
        </div>

        {/* League title */}
        <div
          className="text-center"
          style={{
            animation: "fadeInUp 0.6s ease-out 0.15s forwards",
            opacity: 0,
          }}
        >
          <p
            className="text-xs tracking-[0.25em] uppercase text-white/70 mb-2"
            style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif" }}
          >
            Select a club
          </p>
          <h2
            className="text-4xl md:text-5xl font-extrabold text-white tracking-tight"
            style={{
              fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif",
              textShadow: "0 2px 20px rgba(0,0,0,0.4)",
            }}
          >
            {league}
          </h2>
        </div>

        {/* Limelight Club Dock */}
        <div
          style={{
            animation: "fadeInUp 0.7s ease-out 0.3s forwards",
            opacity: 0,
          }}
        >
          <LimelightNav items={navItems} />
        </div>
      </div>
    </StadiumBackground>
  );
}
