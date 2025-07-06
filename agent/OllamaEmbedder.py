import requests
from .ollamaEmbedderConfig import OllamaEmbedderConfig

class OllamaEmbedder:
    def __init__(self, config: OllamaEmbedderConfig):
        self.model = config.model
        self.base_url = config.base_url
        self.embedding_dim = config.embedding_dim

    def embed(self, text: str):
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]
