from open_rag_engine.config import EngineConfig
from open_rag_engine.factory import LocalModels


def test_ollama_is_the_default_llm_runtime():
    llm = LocalModels(EngineConfig()).llm
    assert type(llm).__name__ == "ChatOllama" and llm.reasoning is False


def test_an_openai_compatible_server_can_replace_ollama(monkeypatch):
    monkeypatch.delenv("ORE_LLM_API_KEY", raising=False)
    cfg = EngineConfig().updated("llm", provider="openai", base_url="http://127.0.0.1:8090/v1", model="qwen3-4b")
    llm = LocalModels(cfg).llm
    assert type(llm).__name__ == "ChatOpenAI" and llm.model_name == "qwen3-4b"
    assert str(llm.openai_api_base) == "http://127.0.0.1:8090/v1"


def test_each_model_loads_once_even_when_asked_for_at_the_same_time(monkeypatch):
    import threading
    import time

    models = LocalModels(EngineConfig())
    builds = []

    def slow_build():
        builds.append(1)
        time.sleep(0.2)
        return object()

    monkeypatch.setattr(models, "_embeddings", slow_build)
    results = []
    threads = [threading.Thread(target=lambda: results.append(models.embeddings)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(builds) == 1 and len({id(r) for r in results}) == 1
