# Windows installer

`OpenRag-Setup.exe` installs Open RAG with everything it needs: the desktop app, a private Python with the engine,
the embedding and reranker models, and a language model served by llama.cpp. After installing, it needs no internet,
no Python and no Ollama.

## What the installer does

- Installs per user, without administrator rights, into `%LOCALAPPDATA%\Programs\Open RAG`.
- Adds a Start menu shortcut and, if you tick the box, a desktop shortcut.
- Keeps your sections, indexes and chats in `%LOCALAPPDATA%\OpenRag` when you uninstall or update.
- Warns you if the Microsoft Edge WebView2 Runtime is missing. Windows 11 always has it; an old Windows 10 may not.

The setup comes as `OpenRag-Setup.exe` plus `.bin` parts, because the language model alone (2.5 GB) is larger than
GitHub's 2 GiB limit per release file. Download all the parts into one folder and run the `.exe`.

## How the app runs the language model

When the app finds `engine/llm/llama-server.exe` and `engine/llm/model.gguf`, it:

1. Picks a free loopback port and a random key.
2. Starts `llama-server` on that port, giving it the key through `LLAMA_API_KEY`.
3. Starts the engine with `--llm-url http://127.0.0.1:<port>/v1`, giving it the same key through `ORE_LLM_API_KEY`.
4. Reports ready once the engine prints `ORE_READY` and `llama-server` answers `/health`.

Both processes run in the app's job object, so they close with it. Their logs are `engine.log` and `llm.log` in
`%LOCALAPPDATA%\OpenRag\logs`.

## Building it

You need:

- Windows with the .NET 10 SDK, Node.js, [uv](https://docs.astral.sh/uv/) and [Inno Setup 6](https://jrsoftware.org/isinfo.php).
- The models on this computer:
  - Run `uv run ore ask` once so the Hugging Face models download.
  - Run `ollama pull qwen3:4b-instruct-2507-q4_K_M` for the language model.

Then, from the repository root:

```
uv run python installer/build.py
```

The script:

1. Publishes the app as self-contained `win-x64`.
2. Copies a uv-managed CPython 3.12.
3. Installs the engine wheel and its locked dependencies into that Python, using CPU-only torch.
4. Copies the models from the Hugging Face and Ollama caches. It checks the GGUF against Ollama's digest.
5. Downloads the pinned llama.cpp CPU build into `installer/.cache` and checks it against its sha256.
6. Checks that the staged engine imports with nothing from the build machine.
7. Runs Inno Setup.

The installer lands in `installer/dist`. To stop after staging (in `installer/build/stage`), run it with `--no-iscc`.

## Checking a build

```
uv run python installer/smoke_test.py
```

This checks the stage end to end without opening the window. It:

1. Starts the bundled `llama-server` and engine the way the app does, with model downloads blocked.
2. Checks that `llama-server` refuses requests without its key.
3. Indexes the example pump manual and asks it a question.
4. Passes only on an answer with sources.

To check an installed app instead of the stage, pass its folder, for example `"%LOCALAPPDATA%\Programs\Open RAG"`.

To update llama.cpp, change `LLAMA_BUILD` and `LLAMA_SHA256` in `build.py`. Take both from the release page on
github.com/ggml-org/llama.cpp.

The setup isn't code-signed, so Windows SmartScreen says the publisher is unknown. Choose *More info*, then *Run anyway*.
