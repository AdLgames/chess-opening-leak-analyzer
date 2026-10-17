# Search and measurement setup

The code is ready; account ownership cannot be established from a repository.
No Search Console token or analytics account was supplied during this build.
These are the remaining operator steps after reviewing and deploying the drafts.

## Google Search Console

1. Sign in at <https://search.google.com/search-console>. Add a **Domain**
   property for `chessleaklab.co.uk` if you control its DNS. Add Google’s supplied
   TXT record at your DNS provider, then verify. This covers domain variants.
2. Alternatively, add the **URL-prefix** property `https://chessleaklab.co.uk/`
   and choose the HTML-tag verification method. Copy only the tag’s `content`
   token into the Vercel **Production build environment** variable
   `LEAKLAB_GOOGLE_SITE_VERIFICATION`. Redeploy, check the tag in the homepage
   HTML, then press Verify. Keep this setting for future builds. Do not put a
   whole HTML tag into the variable. The builder rejects invalid token syntax.
3. After the new public pages are live, submit
   `https://chessleaklab.co.uk/sitemap.xml`. Inspect the homepage, each of the
   three course pages and a guide. Their declared canonical should be the
   production HTTPS URL, and the public page should allow indexing.
4. Inspect `/app/`: it should be excluded by `noindex`. Do not add a robots.txt
   disallow for the app, because that would prevent the crawler reading noindex.
   API URLs are blocked in robots.txt and carry a noindex hosting header.
5. Check Pages, Sitemaps and Core Web Vitals after Google has collected data.
   In Performance, compare queries and landing pages for courses and guides.
   A new release may take time to crawl; request indexing for the main pages
   once rather than repeatedly submitting them.

Reference: [Google Search Central essentials](https://developers.google.com/search/docs/essentials),
[verification methods](https://support.google.com/webmasters/answer/9008080),
[sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
and [noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing).

## Optional Plausible usage counts

1. Create or use a Plausible account and add `chessleaklab.co.uk` as the site.
   This is a separate service; the build does not create a subscription.
2. Set Vercel Production build variable `LEAKLAB_ANALYTICS_DOMAIN` to
   `chessleaklab.co.uk` and redeploy. Leave it unset to keep external usage
   measurement disabled. No API key belongs in the public configuration.
3. Do **not** add Plausible’s normal automatic script or restore the old Vercel
   analytics script. This site uses the events API so it can control consent
   and exclude private URLs and fields.
4. In Plausible, add custom-event goals with these exact names:

   | Event | Meaning | Available coarse properties |
   | --- | --- | --- |
   | `Preview started` | First legal move tried in a public example | course, surface |
   | `Preview completed` | Taught move played in the public example | course, surface |
   | `Course opened` | A public course overview opened | course, surface |
   | `Training started` | A new training task created, including daily tasks | course, mode, surface when available |
   | `Training completed` | A lesson/recall task finished or five practical moves completed | course, mode |
   | `Daily completed` | All tasks in a daily plan finished | surface |

   Page views use the normal `pageview` event. Public examples deduplicate their
   starts/completions per opening per page visit. Training events run at the
   actual state transition, not every re-render or recap opening. Resuming a
   checkpoint does not create another task-start event.

5. On the production Privacy page, explicitly allow optional counts. With GPC
   and DNT off, confirm events in the provider dashboard and browser Network
   panel. A fresh browser must send none until allowed. Turn counts off and
   verify subsequent events stop. GPC/DNT must suppress them even if allowed.
6. Provider failures must leave lessons working. Localhost and preview URLs
   never send events, even when the build is configured.

These are aggregate, consented counts, not a complete census of users. Search
Console supplies organic-search queries and clicks; optional usage counts show
which public pages lead to useful interactions. The implementation intentionally
does not send full referrers or build personal cross-site attribution.

Reference: [Plausible events API](https://plausible.io/docs/events-api),
[custom-event goals](https://plausible.io/docs/custom-event-goals)
and [data policy](https://plausible.io/data-policy).

## Publishing and ongoing content

- Merge/deploy the reviewed daily-session dependency and this public-site change
  in order. Until then, the new pages are preview content, not the live website.
- Confirm HTTPS, preferred-domain redirects, 404 status, production canonical
  URLs, sitemap URLs and the absence of production-wide noindex. Preview builds
  intentionally contain noindex. Keep preview URLs out of Search Console.
- Check the site on a real phone. Lab Lighthouse scores are useful diagnostics;
  production Core Web Vitals need real visitor data and cannot be certified by
  a local score.
- Improve guides when real questions or corrections appear. Preserve useful URLs,
  link new material from the course and guide hub, and update article dates only
  when content changes. The opening-statistics generator retains its 400-game,
  three-reply and 25-games-per-reply thresholds; do not lower them merely to
  inflate the page count.
- Maintain the real project contact route and data policy as the service changes.
  Confirm the appropriate operator/contact details before introducing paid
  services. The current site names the actual project maintainer and issue route.

## Rebuild and checks

```sh
python chess_opening_analyzer/tools/build_public_diagrams.py  # python-chess required
python chess_opening_analyzer/tools/build_public_site.py      # standard library
python chess_opening_analyzer/tools/build_opening_pages.py    # standard library + book
python vercel/prepare.py
python -m pytest chess_opening_analyzer/tests/test_public_site_seo.py -q
python -m pytest chess-dashboard/tests -q
```

Authored copy lives in `tools/public_content.py`; shared presentation lives in
`tools/public_site.py`. Public HTML is built and committed for local use. The
hosted build repeats generation from the same source and settings. Static board
SVGs are compiled from legal positions and committed, so hosting needs no chess
engine or Python chess package to build the public site.
