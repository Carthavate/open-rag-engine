# Open RAG (desktop app)

A Windows app for teachers, researchers and students. Organise documents into **categories** (a subject or research
area) and **sections** (a course, session, project or reading list). Ask questions and get cited answers from one section, or
from a whole category. Everything runs on this computer: see [ADR-0007](../docs/adr/0007-desktop-app.md).

It looks like the [AI Engineering Arena](https://carthavate.github.io/ai-engineering-arena): the same "sticker arcade" theme,
in light or dark to match Windows, with the fonts bundled so it looks the same offline.

## How it fits together

```text
OpenRag.exe (WPF)
 ├─ WebView2 ── the React interface (web/), served from the app's folder as https://app.ore
 │                 │  messages: api, ask, cancel, pickFolder, openSource, …
 │                 ▼
 ├─ EngineProxy ── adds the per-launch token, allows only the engine's API paths
 │                 │  HTTP on 127.0.0.1
 │                 ▼
 └─ engine ─────── `ore serve` (Python), started and stopped by the app (job object + --parent-pid)
```

The page never sees the token and never talks to a local port. Answers stream back line by line through the window.

| Folder | What |
|---|---|
| `src/OpenRag.App` | WPF shell: window, WebView2, folder dialog, opening cited files, engine lifetime |
| `src/OpenRag.Core` | Finding and starting the engine, the API proxy, safe file opening (unit-tested) |
| `web/` | React 19 + Tailwind 4 interface, with a mock engine for working in a browser |
| `tools/make_icon.py` | Draws the app icon |

## Develop

You need the .NET 10 SDK, Node 20 and, for the engine, `uv` with the repo's Python setup (see the main README).

```bash
cd desktop
dotnet build OpenRag.slnx        # builds web/ the first time, then the app
dotnet test OpenRag.slnx
```

Run `src/OpenRag.App/bin/Debug/net10.0-windows/OpenRag.exe`. In a checkout it finds the engine by walking up to
`pyproject.toml` and starts it with `uv run ore serve`. `OPENRAG_ENGINE_DIR` points it at another checkout. Its data lives
in `%LOCALAPPDATA%\OpenRag` and the engine's log is in `%LOCALAPPDATA%\OpenRag\logs\engine.log`.

To work on the interface:

```bash
cd desktop/web
npm run dev        # http://localhost:5176 with a mock engine, no Python needed
npm test
```

- **Against a real engine in the browser:** start `ORE_API_TOKEN=<32+ chars> uv run ore serve --origin http://localhost:5176`, then open `http://localhost:5176/?api=http://127.0.0.1:<port>&token=<token>`.
- **Live reload inside the app (Debug builds only):** set `OPENRAG_DEV_URL=http://localhost:5176` before starting `OpenRag.exe`.
