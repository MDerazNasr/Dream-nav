# DreamNav Remote Dense Worker

Local stub provider for the remote dense handoff flow.

It accepts the DreamNav bundle zip, generates a dense point cloud `.ply`, and posts the result back to the configured DreamNav callback route.

Run tests:

```bash
npm run remote-dense:test
```

Start the worker:

```bash
npm run remote-dense:dev
```

Default local address:

```txt
http://127.0.0.1:8010
```
