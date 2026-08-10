# Skelly Synchronize — frontend

React (Vite + TypeScript) UI for `skelly_synchronize`, talking to the `skelly_synchronize.api` FastAPI server over HTTP.

## Running

This is a two-process dev setup: the API server and the Vite dev server.

1. From the repo root, install the API extra and start the API server:

   ```
   pip install -e ".[api]"
   skelly-sync-api
   ```

   This runs on `http://127.0.0.1:8000`.

2. In this directory, install dependencies and start the dev server:

   ```
   npm install
   npm run dev
   ```

3. Open the URL Vite prints (typically `http://localhost:5173`).

The API's CORS policy allows any `localhost`/`127.0.0.1` origin, so no dev-server proxy is needed.

## Notes

- `src/api/client.ts` hardcodes the API base URL as `http://127.0.0.1:8000`. There's no environment-variable override yet — add one if/when the frontend needs to be bundled and served from FastAPI as a single process.
- No test runner or linter beyond TypeScript's own checks (`npm run build` runs `tsc -b`) is set up yet.
