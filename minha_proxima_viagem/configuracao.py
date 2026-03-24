from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from minha_proxima_viagem.modelos import normalizar_nivel_detalhamento


load_dotenv()


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ConfiguracaoAplicacao:
    nome_aplicacao: str
    ambiente: str
    api_backend_url: str
    api_timeout_segundos: int
    planejamento_nivel_detalhamento_padrao: str
    gemini_api_key: str
    gemini_modelo: str
    gemini_modelos_fallback: tuple[str, ...]
    gemini_temperatura: float
    gemini_max_tokens: int
    gemini_timeout_segundos: int
    cache_ttl_segundos: int
    cache_max_entradas: int
    nivel_log: str

    @property
    def gemini_configurado(self) -> bool:
        return _api_key_gemini_valida(self.gemini_api_key)

    @property
    def gemini_modelos_candidatos(self) -> tuple[str, ...]:
        modelos: list[str] = []
        for modelo in (self.gemini_modelo, *self.gemini_modelos_fallback):
            modelo_normalizado = (modelo or "").strip()
            if modelo_normalizado and modelo_normalizado not in modelos:
                modelos.append(modelo_normalizado)
        return tuple(modelos)


def _api_key_gemini_valida(valor: str) -> bool:
    chave = (valor or "").strip()
    placeholders = {"", "sua_chave_aqui", "cole_sua_chave_aqui", "your_api_key_here"}
    return chave not in placeholders


def _obter_modelos_fallback() -> tuple[str, ...]:
    bruto = os.getenv(
        "GEMINI_MODELOS_FALLBACK",
        "models/gemini-2.5-flash,models/gemini-3-flash-preview,models/gemma-3-4b-it",
    ).strip()
    modelos = [item.strip() for item in bruto.split(",") if item.strip()]
    return tuple(modelos)


@lru_cache(maxsize=1)
def obter_configuracao() -> ConfiguracaoAplicacao:
    return ConfiguracaoAplicacao(
        nome_aplicacao=os.getenv("APP_NOME", "Minha Próxima Viagem").strip() or "Minha Próxima Viagem",
        ambiente=os.getenv("APP_AMBIENTE", "desenvolvimento").strip() or "desenvolvimento",
        api_backend_url=os.getenv("APP_API_BACKEND_URL", "http://127.0.0.1:8000").strip() or "http://127.0.0.1:8000",
        api_timeout_segundos=int(os.getenv("APP_API_TIMEOUT_SEGUNDOS", "120")),
        planejamento_nivel_detalhamento_padrao=normalizar_nivel_detalhamento(
            os.getenv("PLANEJAMENTO_NIVEL_DETALHAMENTO_PADRAO", "equilibrado").strip().lower() or "equilibrado"
        ),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_modelo=os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite").strip() or "models/gemini-2.5-flash-lite",
        gemini_modelos_fallback=_obter_modelos_fallback(),
        gemini_temperatura=float(os.getenv("GEMINI_TEMPERATURE", "0.2")),
        gemini_max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "2600")),
        gemini_timeout_segundos=int(os.getenv("GEMINI_TIMEOUT_SEGUNDOS", "90")),
        cache_ttl_segundos=int(os.getenv("CACHE_TTL_SEGUNDOS", "600")),
        cache_max_entradas=int(os.getenv("CACHE_MAX_ENTRADAS", "128")),
        nivel_log=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )

