import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.services.wikidata.fetch import fetch_players
from app.services.wikidata.snapshot import write_snapshot

# Repo inspection (Feb 8, 2026): player seed data comes from backend/data/players_seed.json
# via app.scripts.seed_players, Player/PlayerAlias models live in app/models/entities.py,
# and API list/get endpoints are in app/api/routes.py.




def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch NBA players from Wikidata and write a snapshot JSON.")
    parser.add_argument("--output", default=None, help="Output path for snapshot JSON")
    parser.add_argument("--limit", type=int, default=500, help="Rows per batch")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between batches")
    parser.add_argument("--max-rows", type=int, default=None, help="Stop after fetching this many rows")
    parser.add_argument("--denylist", default=None, help="Alias denylist path")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    output_path = Path(args.output) if args.output else base_dir / "data" / "wikidata_players_snapshot.json"
    denylist_path = Path(args.denylist) if args.denylist else base_dir / "data" / "alias_denylist.txt"

    players = fetch_players(limit=args.limit, sleep_s=args.sleep, max_rows=args.max_rows, denylist_path=denylist_path)

    write_snapshot(players, output_path)
    print(f"Wrote {len(players)} players to {output_path} at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
