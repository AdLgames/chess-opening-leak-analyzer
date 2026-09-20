# Vendored assets

Everything the dashboard loads is in this repository. The page makes a point of not
phoning home, and previously did so anyway — two font stylesheets from
`fonts.googleapis.com` and 200KB of Chart.js from `cdn.jsdelivr.net`, both of which
told a third party the IP address of everyone who opened it.

| Asset | Version | Licence | Source |
| --- | --- | --- | --- |
| Inter (latin, 400/500/600/700 normal) | 5.0.20 | SIL Open Font License 1.1 | npm `@fontsource/inter` |
| JetBrains Mono (latin, 400/500/700 normal) | 5.0.21 | SIL Open Font License 1.1 | npm `@fontsource/jetbrains-mono` |

Chart.js is gone rather than vendored: the page drew two bar charts with it, which did
not justify 200KB, and a `<canvas>` cannot be read by a screen reader. Both are now
inline SVG in `../charts.js`, each with a real table of the same numbers beneath it.

To refresh a font, `npm pack @fontsource/<name>@<version>`, unpack, and copy the
`files/*-latin-<weight>-normal.woff2` you need into `fonts/`.
