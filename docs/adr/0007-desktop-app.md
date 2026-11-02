# ADR-0007: A Windows desktop app over a local engine API

- **Status:** Proposed
- **Date:** 2026-11-02
- **Deciders:** Wadi, Ghassen
- **Requirements:** D-01, D-02, D-06, D-10, C-03, C-04

## Context and problem

Teachers, researchers and students want to ask questions about their own study material without sending it anywhere. They organise it in **categories** (a subject or research area) and **sections** (a course, session, project or reading list). Each section has its own folders, and an answer must come only from the section, or the category, they choose. Many of their laptops are offline or locked down, so the app must work with no network and ship as one self-contained installer.

How do we build that app on top of the engine?

## Decision drivers

- Fully offline after installation, with nothing to configure (D-02, C-03).
- Runs on ordinary Windows laptops without a GPU (C-04).
- A modern, friendly interface: most users are not technical.
- Answers stay grounded and cited (D-06), and every source can be opened.
- The engine stays the single implementation of retrieval and answering (D-01).

## Considered options

1. **WPF shell with WebView2 and a React interface; the engine runs as a hidden child process with a loopback HTTP API.**
2. **Native WPF (XAML)**, calling the engine the same way.
3. **Electron or Tauri.**
4. **No app:** `ore serve` plus the user's browser.

## Decision

Option 1, the same structure as our Duet app.

- **Shell (.NET, WPF).** It owns the window, the native dialogs (pick a folder, open a source file) and the engine's lifetime:
  - It starts `ore serve` with a fresh random token in `ORE_API_TOKEN`, and reads the `ORE_READY port=<n>` line.
  - It ties the engine to a job object, so the engine dies with the app. `--parent-pid` is the backstop.
- **Interface (React and Tailwind, in WebView2).**
  - It is served from the app's own files on a virtual host (`https://app.ore`), so it needs no network.
  - It calls the engine's API directly, with the token the shell hands it, and streams answers as newline-delimited JSON.
- **Engine API (FastAPI, `ore serve`).** It is reachable only from this machine, through three guards:
  1. It binds to `127.0.0.1` and rejects any non-loopback `Host` header, which blocks DNS rebinding.
  2. Every request needs the per-launch bearer token.
  3. CORS allows only `https://app.ore`.

  Errors are problem details (RFC 9457) without stack traces or document content.
- **One index per section.** A section is one collection: a Chroma index plus BM25 chunks.
  - A **category** question searches each section, fuses the lists with reciprocal rank fusion, and reranks the fused candidates once.
  - Indexing runs in the background, one job at a time, and drops files that were deleted from the folders.
  - It keeps the documents of folders that are temporarily missing, such as an unplugged USB drive.
- **Offline by construction.**
  - When every model is on disk, the engine sets `HF_HUB_OFFLINE`, and telemetry is off.
  - The self-contained installer bundles llama.cpp's `llama-server` with a GGUF build of the default model (Qwen3 4B Instruct, Apache-2.0). The engine reaches it through `provider = "openai"`, because the OpenAI-compatible API is what `llama-server` speaks.
  - Ollama remains the default for developers, and it is too large to bundle.

### Consequences

- **Good:**
  - The interface can look modern without fighting XAML.
  - The engine stays one Python code path, tested once.
  - The same API serves a future web UI or MCP server.
- **Bad:**
  - Two runtimes ship together, .NET and Python, which makes the installer large (several GB, mostly models).
  - **Mitigation:** the packaging work keeps models and runtimes in separate, cacheable folders, and compresses what compresses.
- **Bad:**
  - A local HTTP port is an attack surface.
  - **Mitigation:** the three guards above, all covered by tests.

### Confirmation

`tests/test_api.py` checks the token, the loopback-host rule and the CORS origin. `tests/test_library.py` checks that a section answers only from its own documents and that a category answers from all of its sections.

## Pros and cons of the options

### WPF + WebView2 + React

- Good, because it uses the stack and patterns we already proved in Duet: virtual-host assets, the job object and Mica.
- Good, because WebView2 is preinstalled on Windows 11.
- Bad, because there are two UI technologies to know.

### Native WPF

- Good, because it is one technology with no web layer.
- Bad, because a polished, friendly interface takes much longer to build.

### Electron or Tauri

- Good, because they are cross-platform.
- Bad, because Electron adds another large runtime, and Tauri adds Rust. Neither buys us anything for a Windows-first app.

### Browser plus `ore serve`

- Good, because there is nothing to build.
- Bad, because it gives no folder picker and no way to open source files, and users would have to start a server themselves.

## More information

[ADR-0006](0006-python-and-langchain.md) (engine stack), [interfaces](../architecture/05-interfaces.md) (error categories and problem details).
