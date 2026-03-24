from __future__ import annotations

from types import SimpleNamespace

import pytest

from minha_proxima_viagem.cliente_gemini import ClienteGemini
from minha_proxima_viagem.configuracao import ConfiguracaoAplicacao
from minha_proxima_viagem.excecoes import ErroIntegracaoIA


@pytest.fixture
def configuracao_teste() -> ConfiguracaoAplicacao:
    return ConfiguracaoAplicacao(
        nome_aplicacao="Minha Próxima Viagem",
        ambiente="teste",
        api_backend_url="http://127.0.0.1:8000",
        api_timeout_segundos=30,
        planejamento_nivel_detalhamento_padrao="equilibrado",
        gemini_api_key="fake-key",
        gemini_modelo="models/gemini-2.5-flash-lite",
        gemini_modelos_fallback=("models/gemini-2.5-flash", "models/gemini-3-flash-preview", "models/gemma-3-4b-it"),
        gemini_temperatura=0.3,
        gemini_max_tokens=2600,
        gemini_timeout_segundos=90,
        cache_ttl_segundos=600,
        cache_max_entradas=128,
        nivel_log="INFO",
    )


@pytest.fixture
def cliente(configuracao_teste: ConfiguracaoAplicacao) -> ClienteGemini:
    return ClienteGemini(configuracao=configuracao_teste)


def test_converter_json_aceita_json_valido(cliente: ClienteGemini) -> None:
    dados = cliente._converter_json('{"destino":"Fortaleza","total_dias":5}')
    assert dados["destino"] == "Fortaleza"
    assert dados["total_dias"] == 5


def test_converter_json_extrai_json_de_markdown(cliente: ClienteGemini) -> None:
    texto = 'Resposta:\n```json\n{"destino":"Fortaleza","total_dias":5}\n```'
    dados = cliente._converter_json(texto)
    assert dados["destino"] == "Fortaleza"


def test_converter_json_recupera_json_truncado_simples(cliente: ClienteGemini) -> None:
    texto = '{"destino":"Fortaleza","total_dias":5,"observacoes_gerais":["Leve água"]'
    dados = cliente._converter_json(texto)
    assert dados["destino"] == "Fortaleza"
    assert dados["observacoes_gerais"] == ["Leve água"]


def test_converter_json_recupera_json_com_texto_extra(cliente: ClienteGemini) -> None:
    texto = 'Aqui está o plano: {"destino":"Fortaleza","total_dias":5} Obrigado.'
    dados = cliente._converter_json(texto)
    assert dados["total_dias"] == 5


def test_converter_json_falha_quando_irrecuperavel(cliente: ClienteGemini) -> None:
    with pytest.raises(ErroIntegracaoIA) as erro:
        cliente._converter_json('Resposta inesperada sem objeto JSON estruturado aproveitável.')

    assert erro.value.codigo_erro == "gemini_json_nao_encontrado"


def test_extrair_texto_da_resposta_lendo_candidates(cliente: ClienteGemini) -> None:
    resposta = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text="{"), SimpleNamespace(text='"destino":"Fortaleza"}')]
                )
            )
        ]
    )

    texto = cliente._extrair_texto_da_resposta(resposta)
    assert '"destino":"Fortaleza"' in texto


def test_ordem_modelos_candidatos_prioriza_gemini(configuracao_teste: ConfiguracaoAplicacao) -> None:
    assert configuracao_teste.gemini_modelos_candidatos == (
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.5-flash",
        "models/gemini-3-flash-preview",
        "models/gemma-3-4b-it",
    )

