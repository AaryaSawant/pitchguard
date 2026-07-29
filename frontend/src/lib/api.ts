// PitchGuard — API Client
// File: frontend/src/lib/api.ts
//
// Talks to the FastAPI backend (src/api/main.py). Adjust API_BASE if your
// backend runs on a different host/port.

const API_BASE = "http://localhost:8000";

export interface ApiPlayer {
  id: number;
  player_tm_id: string;
  name: string;
  position: string;
  age: number;
  minutesLast30: number;
  gamesLast14: number;
  daysSinceInjury: number;
  injuryCount2yr: number;
  riskScore: number;
  tier: "Low" | "Medium" | "High";
  subScores: { acl: number; hamstring: number; ankle: number; meniscus: number };
  shapFactors: { label: string; value: number }[];
  nextMatch: { opponent: string; venue: string; surface: string; homeAway: string; date: string };
  injuryHistory: { year: number; type: string; gamesMissed: number }[];
  distance: number | null;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

export async function fetchClubs(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/clubs`);
  const data = await handleResponse<{ clubs: string[] }>(res);
  return data.clubs;
}

export async function fetchSquad(clubName: string): Promise<ApiPlayer[]> {
  const res = await fetch(`${API_BASE}/squad/${encodeURIComponent(clubName)}`);
  const data = await handleResponse<{ club: string; players: ApiPlayer[] }>(res);
  return data.players;
}

export async function fetchPlayer(playerTmId: string): Promise<ApiPlayer> {
  const res = await fetch(`${API_BASE}/player/${encodeURIComponent(playerTmId)}`);
  return handleResponse<ApiPlayer>(res);
}