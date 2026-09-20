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

## Accounts

The analyser itself is stateless, but a stateless analyser can only ever tell
you what is leaking today — never whether you fixed it. Accounts are what make a
second run mean something: the same leak key (the position EPD plus the move
played) is tracked across runs, with a lifecycle of `open → drilling → fixed →
regressed`.

Accounts switch themselves on when a database is configured, and off when there
is not one — a fork or a local preview still runs the analyser, it just does not
keep anything. On a deployment that *does* have a database, signing in is
required to run: a run has to belong to somebody for its progress to be kept.

### What you need

1. **A Postgres database.** In the Vercel dashboard: *Storage → Create → Postgres
   (Neon)*, then connect it to this project. That injects `POSTGRES_URL` and
   friends; nothing else needs setting up, and the schema is created on the
   first request that needs it.

   The driver is [pg8000](https://pypi.org/project/pg8000/), a pure-Python
   implementation of the Postgres wire protocol, rather than psycopg: this
   function already carries a 79 MB engine and a 19 MB opening book, and
   psycopg's 12 MB of vendored shared libraries is more than the deployment
   will build. The connection is made over TLS unless the URL says
   `sslmode=disable`, which only a plaintext local server should.

2. **Lichess OAuth**, if you want one-tap sign-in for Lichess players. Lichess
   issues public clients no secret, so `LICHESS_CLIENT_ID` is the whole
   configuration; pick any stable string that identifies your deployment, e.g.
   `chessleaklab.co.uk`. The redirect URI is
   `https://your-domain/api/auth/lichess/callback` and is derived from the
   request, or from `LEAKLAB_SITE_URL` if you set it.

3. **Email**, for everyone else — Chess.com has no public OAuth, so its players
   sign in with a single-use link. Set `RESEND_API_KEY` and `MAIL_FROM` (an
   address on a domain verified with [Resend](https://resend.com)).

| Variable | Needed for | Notes |
| --- | --- | --- |
| `POSTGRES_URL` | accounts at all | injected by Vercel Postgres |
| `LICHESS_CLIENT_ID` | Lichess sign-in | no secret: the flow is PKCE |
| `RESEND_API_KEY`, `MAIL_FROM` | email sign-in | |
| `LEAKLAB_SITE_URL` | optional | pins the origin used in redirect URIs |
| `LEAKLAB_CORS_ORIGINS` | optional | a regex; the default allows localhost only |
| `LEAKLAB_DEV_MAGIC_LINKS` | preview only | `1` returns the link instead of mailing it; refused when `VERCEL_ENV=production` |

### Evidence that adds up across runs

A line you meet twice a month never reaches the three-game threshold inside a
single run, so it could never become a leak however long it kept costing you.
With an account it can: the server keeps the evidence per **(decision, game)**
pair rather than as a count.

That distinction is the whole trick. "Your last 120 games" analysed monthly
re-reads most of the same games, and a count would have doubled every time;
re-inserting a pair that is already there does nothing. A decision crosses into
being a leak at three distinct games, on its pooled record against the book.

Two things this deliberately does not claim. There is no engine verdict behind
an accumulated leak — the engine only ever runs on decisions a single run saw
often enough to judge — so it is flagged `underperforming` and nothing else.
And the pooled score is weighted by games, not by runs, so four games at 0% and
one at 100% reads as 20%, not 50%.

The Repertoire view shows these under "Adding up across runs", including the
ones still short of the threshold, so the evidence arriving is visible rather
than appearing from nowhere.

### What is stored, and what is not

The games are not kept. A fetched archive lives in the function's temporary
storage and goes when the instance is recycled, exactly as before.

What is kept is progress: one row per run, one row per leak with its status,
the repertoire decisions, the drill schedule and its attempt log, preferences,
the most recent report so a new device opens on something real, and — for the
accumulation above — which games each run read and which decisions appeared in
which game. That last part is identifiers only: no moves, no results, nothing
that is not already in the public archive the run was built from. Alongside
that sits an email address or a Lichess account id. No passwords are stored,
and neither is the Lichess access token: it is used once, in the callback, to
ask Lichess who just signed in, and then dropped. The scope requested is
`preference:read`, which grants nothing the public API does not, so keeping the
token would be a credential held for a capability the app never uses.

Two endpoints exist from the first migration rather than being promised for
later, and the account menu links to both:

* `GET /api/auth/export` — everything held for the signed-in user, as one JSON
  file.
* `POST /api/auth/delete` with `{"confirm": "DELETE"}` — erases the account.
  Every other table is `ON DELETE CASCADE` from `users`, which is asserted by
  `tests/test_accounts.py` so it cannot quietly stop being true.

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
