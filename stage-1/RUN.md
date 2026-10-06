# Running tablekeeper (stage 1)

Build and start (from this folder):

```sh
docker build -t tablekeeper-stage-1 . && docker run --rm -e PORT=8080 -p 8080:8080 tablekeeper-stage-1
```

Health: `curl http://localhost:8080/health` returns `{"status":"ok"}`.

The image has no runtime dependencies beyond Node.js (standard library only)
and needs no network at run time. State is in memory; seed it with
`POST /_test/reset`.

Without Docker (Node 20+): `PORT=8080 node src/server.js`.
