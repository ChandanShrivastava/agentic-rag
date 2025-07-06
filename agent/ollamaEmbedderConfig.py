from dataclasses import dataclass

@dataclass
class OllamaEmbedderConfig:
    model: str
    base_url: str = "http://localhost:11434"
    embedding_dim: int = 768