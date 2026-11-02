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
