# Running tablekeeper (stage 4)

Build and start (from this folder):

```sh
docker build -t tablekeeper-stage-4 . && docker run --rm -e PORT=8080 -p 8080:8080 tablekeeper-stage-4
```

Health: `curl http://localhost:8080/health` returns `{"status":"ok"}`.
Browser screens: http://localhost:8080/ (also `/signup`, `/login`, `/lookup`).

The image has no runtime dependencies beyond Node.js (standard library only)
and needs no network at run time; fonts, scripts and styles are served from `ui/`. State is in memory; seed it with
`POST /_test/reset`.

Without Docker (Node 20+): `PORT=8080 node src/server.js`.
