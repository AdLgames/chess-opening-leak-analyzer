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
   (`python3 prepare.py`) and the function settings. Leave the install command
   empty — `prepare.py` only needs the standard library, and the Python runtime
   installs `requirements.txt` into the function itself. A build-stage
   `pip3 install` fails on Vercel with PEP 668 `externally-managed-environment`.
4. Deploy. The build downloads Stockfish 17.1 (`sse41-popcnt`, ~79 MB) and the
   19 MB opening book, so the first build takes a few minutes.

## Deploy from your own machine

```bash
git clone https://github.com/AdLgames/chess-opening-leak-analyzer
cd chess-opening-leak-analyzer/vercel
python prepare.py            # engine + book + front-end (standard library only)
vercel deploy                # first deploy creates the project
```

## The domain

The site is `chessleaklab.co.uk`. Vercel terminates TLS and issues the
certificate; the registrar only has to point the name at it.

1. **Vercel → Project → Settings → Domains → Add**: add `chessleaklab.co.uk`,
   then add `www.chessleaklab.co.uk` and set it to redirect to the apex (Vercel
   offers the redirect when you add the second one). Vercel then shows the exact
   DNS records to create — use those values, not the ones below, if they differ.
2. **At the registrar**, on the `chessleaklab.co.uk` zone:

   | Type | Name | Value |
   | --- | --- | --- |
   | `A` | `@` (the apex) | the address Vercel shows, currently `216.198.79.1` |
   | `CNAME` | `www` | `cname.vercel-dns.com` |

   A `.co.uk` apex cannot be a `CNAME`. If the registrar offers `ALIAS` or
   `ANAME` records, one of those pointed at `cname.vercel-dns.com` is better than
   the `A` record — it follows Vercel if the address ever changes.
3. Delete any parking `A`/`AAAA`/`CNAME` records the registrar left on `@` and
   `www`, or they will keep answering.
4. Wait for propagation (minutes, occasionally an hour or two) and check:

   ```bash
   dig +short chessleaklab.co.uk
   dig +short www.chessleaklab.co.uk
   curl -sSI https://chessleaklab.co.uk | head -1
   ```

   Vercel's Domains panel shows *Valid Configuration* and issues the certificate
   on its own once the records resolve.
5. Set **Settings → Domains → the apex → "Set as production domain"** so
   deployment URLs and the `og:` metadata agree on one home.

Email is separate: adding this site does not touch `MX` records, so mail on the
domain keeps working. If the registrar's default zone had no `MX` at all and you
want mail later, add it then.

## Run the hosted build locally

`prepare.py` leaves a complete bundle behind, and the function also serves
`public/` when it is present, so one command previews exactly what Vercel serves:

```bash
pip install -r requirements.txt   # only needed to run it locally
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

- The CDN serves `/` from `public/index.html` (the front page) and `/app/` from
  `public/app/index.html` (the tool). Nothing needs a rewrite rule: both are
  static directories.
- `public/robots.txt` and `public/sitemap.xml` name the domain, as do the
  `canonical` and `og:` tags in both `index.html` files. If the domain ever
  changes, those four files are the whole list.
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
