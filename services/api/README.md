# DreamNav API

FastAPI service for the PDF-defined scene API boundary.

Install dependencies from the repo root:

```bash
npm run api:install
```

Run tests:

```bash
npm run api:test
```

Start the local API:

```bash
npm run api:dev
```

Primary routes:

```txt
GET /health
GET /demo-scenes
GET /scene/{scene_id}
GET /quality/{scene_id}
GET /scenes/{scene_id}/{asset}
```
