# Vercel deployment (Opening Leak Lab, hosted)

This folder deploys the dashboard to Vercel as a static front-end plus one Python
serverless function that carries **both** a Stockfish build and the SQLite opening
book inside the function bundle. Nothing calls out to the Lichess API at runtime.

```
api/index.py     FastAPI app, one synchronous /api/analyze call per run
prepare.py       assembles the bundle (package, demo PGNs, front-end, book, engine)
vercel.json      runtime, memory, duration, includeFiles, /api/* rewrite
requirements.txt fastapi, python-chess, python-multipart
```

`chessopening/`, `public/`, `sample_pgns/` and `engine/` are **generated** by
`prepare.py` and are not committed.

## Deploy from the dashboard (recommended)

1. Vercel → Add New → Project → import `AdLgames/chess-opening-leak-analyzer`.
2. Set **Root Directory** to `vercel`.
3. Leave the framework preset as Other. `vercel.json` supplies the build command
   (`python3 prepare.py`), install command and function settings.
4. Deploy. The build downloads Stockfish 17.1 (`sse41-popcnt`, ~79 MB) and the
   19 MB opening book, so the first build takes a few minutes.

## Deploy from your own machine

```bash
git clone https://github.com/AdLgames/chess-opening-leak-analyzer
cd chess-opening-leak-analyzer/vercel
pip install -r requirements.txt
python prepare.py            # engine + book + front-end
vercel deploy                # first deploy creates the project
```

## Run the hosted build locally

`prepare.py` leaves a complete bundle behind, and the function also serves
`public/` when it is present, so one command previews exactly what Vercel serves:

```bash
python -m uvicorn api.index:app --port 8011
# open http://localhost:8011
```

## Hosted limits

The function is capped so a run always fits inside Vercel's execution window:

| Limit | Value |
| --- | --- |
| Engine depth | 14 |
| Games per run | 120 |
| Upload size | 8 MB |
| Engine time budget | 42 s |
| Function duration | 60 s (Hobby maximum) |
| Function memory | 2048 MB (Hobby maximum) |

`GET /api/meta` reports these as `limits`, and the dashboard applies them to the
controls and shows a notice. When the engine budget runs out the remaining
positions are judged on database statistics alone and the run log says so.
Local runs through `python -m chessopening` or `chess-dashboard/api_server.py`
have none of these caps.

## Notes

- Vercel's git clone does not fetch Git LFS objects, so `prepare.py` detects an
  LFS pointer in place of `openings.sqlite` and pulls the real file from
  `media.githubusercontent.com`, which serves LFS content directly. Override with
  `LEAKLAB_DB_URL`, or point at a fork with `LEAKLAB_REPO` / `LEAKLAB_REF`.
- The engine is copied to `/tmp/leaklab-engine/stockfish` and made executable on
  the first request of each cold start; the read-only bundle cannot be exec'd in
  place.
- `LEAKLAB_ENGINE_BUILD` picks the Stockfish build (default `sse41-popcnt`, which
  runs on Vercel's CPUs; `avx2` is faster where supported).
- The bundle is close to Vercel's 250 MB unzipped function limit — the engine is
  ~79 MB and the book ~19 MB. Keep new dependencies small.
