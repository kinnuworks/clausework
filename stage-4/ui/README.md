# Tablekeeper browser surface (stage 2+)

Plain static files. No build step, no runtime fetch outside the same origin.

## Serving contract
- `GET /`, `/signup`, `/login`, `/lookup` → this directory's `index.html`, `Content-Type: text/html; charset=utf-8`
  (client-side routing; any other unknown non-API path may also return it).
- `GET /static/<path>` → the file at `<path>` in this directory (e.g. `/static/js/app.js`,
  `/static/css/tokens.css`, `/static/fonts/BricolageGrotesque.woff2`, `/static/favicon.svg`).
  Content types: `.js` `text/javascript` (ES modules — must be a JavaScript MIME type),
  `.css` `text/css`, `.woff2` `font/woff2`, `.svg` `image/svg+xml`, `.html` `text/html`, `.txt` `text/plain`.
- The API is called same-origin at the stage-1/2 paths (`/auth/*`, `/restaurants`, `/availability`,
  `/reservations`). No CORS, no other origin.

## API shapes the surface relies on
- Errors `{"error":{"code","message"}}`; 4xx = confirmed refusal, 5xx / network loss / timeout = uncertain.
- `GET /restaurants/{id}` → `tables[{id,label,capacity}]`, optional `combinable[[a,b],...]`.
- `GET /availability` → `slots[{starts_at_local, starts_at, available_table_ids, available_options?}]`.
- `POST /reservations` with `Idempotency-Key`; single table sends `table_id`, a pair sends `table_ids`.
  Response must carry `reference`, `starts_at_local`, `party_size`, `table_ids` (or `table_id`).

## Layout
`index.html` · `css/` tokens, base, search, panel, pages · `js/` app, router, header, api, session,
format, dom, `views/` search, grid, booking, ticket, auth, lookup, missing · `fonts/`.

## Licences
- Bricolage Grotesque — SIL Open Font License 1.1, `fonts/OFL-BricolageGrotesque.txt`
  (subset to Latin, converted to WOFF2; the copyright notice declares no Reserved Font Name).
- Instrument Sans — SIL Open Font License 1.1, `fonts/OFL-InstrumentSans.txt` (subset, WOFF2).
- Icons, favicon, CSS and JS: made for this product.
