# Third-party software in Open RAG

Open RAG is developed by Wadi Touil (https://github.com/TWadi) and Ghassen Jamoussi
(https://github.com/GhassenJamoussi99). It is free software under the GNU Affero General Public License v3.0 (see
`LICENSE.txt`), and its source code is at https://github.com/Carthavate/open-rag-engine.

The installer also brings the components below, each under its own licence.

## Models

| Component | Where | Licence |
| --- | --- | --- |
| Qwen3-4B-Instruct-2507 (Alibaba Qwen team), 4-bit GGUF as published by Ollama | `engine/llm/model.gguf` | Apache-2.0 (`engine/llm/MODEL_LICENSE.txt`) |
| intfloat/multilingual-e5-small | `engine/models/intfloat--multilingual-e5-small` | MIT (model card in that folder) |
| cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | `engine/models/cross-encoder--mmarco-mMiniLMv2-L12-H384-v1` | Apache-2.0 |

## Programs and libraries

| Component | Where | Licence |
| --- | --- | --- |
| llama.cpp `llama-server` (ggml-org) | `engine/llm` | MIT (`engine/llm/LICENSE*`) |
| CPython | `engine/python` | Python Software Foundation License (`engine/python/LICENSE.txt`) |
| Python packages: LangChain, Chroma, PyTorch, sentence-transformers, FastAPI and their dependencies | `engine/python/Lib/site-packages` | Each package's own licence, in its `*.dist-info` folder |
| .NET runtime | the app folder | MIT |
| Microsoft Edge WebView2 SDK | `Microsoft.Web.WebView2.*.dll`, `WebView2Loader.dll` | Microsoft WebView2 SDK licence (BSD-3-Clause style) |
| React, React DOM, Motion | `wwwroot` | MIT |
| Lucide icons | `wwwroot` | ISC |
| Fonts: Lilita One, Atkinson Hyperlegible, IBM Plex Mono | `wwwroot` | SIL Open Font License 1.1 |
