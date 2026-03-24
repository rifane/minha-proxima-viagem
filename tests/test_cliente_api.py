from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from minha_proxima_viagem.cliente_api import ClienteAPIPlanejamento
from minha_proxima_viagem.configuracao import ConfiguracaoAplicacao
from minha_proxima_viagem.excecoes import ErroPlanejamentoViagem
from minha_proxima_viagem.modelos import InteressesViagem, PlanoViagemGerado, SolicitacaoPlanoViagem


@pytest.fixture
def configuracao_teste() -> ConfiguracaoAplicacao:
    return ConfiguracaoAplicacao(
        nome_aplicacao="Minha Próxima Viagem",
        ambiente="teste",
        api_backend_url="http://teste.local",
        api_timeout_segundos=10,
        planejamento_nivel_detalhamento_padrao="equilibrado",
        gemini_api_key="fake-key",
        gemini_modelo="models/gemini-2.5-flash-lite",
        gemini_modelos_fallback=(),
        gemini_temperatura=0.2,
        gemini_max_tokens=1200,
        gemini_timeout_segundos=30,
        cache_ttl_segundos=600,
        cache_max_entradas=16,
        nivel_log="INFO",
    )


@pytest.fixture
def solicitacao_teste() -> SolicitacaoPlanoViagem:
    return SolicitacaoPlanoViagem(
        data_inicio=date(2026, 7, 10),
        data_fim=date(2026, 7, 12),
        destino="Lisboa",
        quantidade_adultos=2,
        interesses=InteressesViagem(cultural=True),
    )


@pytest.fixture
def resposta_plano() -> dict:
    return {
        "destino": "Lisboa",
        "periodo_viagem": "10/07/2026 a 12/07/2026",
        "total_dias": 3,
        "perfil_viajantes": "2 adulto(s)",
        "resumo_historia": {
            "titulo": "Resumo histórico do destino",
            "resumo": "Resumo histórico validado em teste.",
            "itens": ["Marco 1", "Marco 2", "Marco 3"],
        },
        "contexto_periodo": {
            "titulo": "Clima, eventos e contexto do período",
            "resumo": "Contexto do período informado.",
            "itens": ["Clima", "Fluxo", "Eventos"],
        },
        "interesses": [
            {
                "titulo": "Cultural",
                "resumo": "Sugestões culturais.",
                "itens": ["Museu", "Centro", "Feira"],
            }
        ],
        "dicas_seguranca": {
            "titulo": "Segurança no destino",
            "resumo": "Cuidados básicos.",
            "itens": ["Rotas", "Documentos", "Canais oficiais"],
        },
        "roteiro_dia_a_dia": [
            {
                "dia": 1,
                "data": "10/07/2026",
                "tema_dia": "Centro e arredores",
                "manha": "Passeio no destino-base.",
                "tarde": "Bairro ou região próxima.",
                "noite": "Jantar e retorno.",
                "observacoes": "Validar deslocamento.",
            }
        ],
        "observacoes_gerais": ["Use como guia flexível."],
        "fontes_recomendadas": ["Portal oficial de turismo"],
        "modelo_utilizado": "fake-model",
        "familia_modelo": "Fake",
        "nivel_detalhamento": "equilibrado",
        "origem_cache": False,
        "aviso_importante": "Confirme em fontes oficiais.",
    }


def _cliente_http_mock(handler) -> httpx.Client:
    transporte = httpx.MockTransport(handler)
    return httpx.Client(transport=transporte, base_url="http://teste.local")


def test_cliente_api_planeja_viagem_com_backend_http(
    configuracao_teste: ConfiguracaoAplicacao,
    solicitacao_teste: SolicitacaoPlanoViagem,
    resposta_plano: dict,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/planejar-viagem"
        corpo = json.loads(request.content.decode("utf-8"))
        assert corpo["destino"] == "Lisboa"
        return httpx.Response(status_code=200, json=resposta_plano)

    cliente = ClienteAPIPlanejamento(
        configuracao=configuracao_teste,
        cliente_http=_cliente_http_mock(handler),
    )

    plano = cliente.planejar_viagem(solicitacao_teste)

    assert isinstance(plano, PlanoViagemGerado)
    assert plano.destino == "Lisboa"
    assert plano.roteiro_dia_a_dia[0].tema_dia == "Centro e arredores"


def test_cliente_api_informa_backend_indisponivel(configuracao_teste: ConfiguracaoAplicacao) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("falha de conexão")

    cliente = ClienteAPIPlanejamento(
        configuracao=configuracao_teste,
        cliente_http=_cliente_http_mock(handler),
    )

    with pytest.raises(ErroPlanejamentoViagem) as erro:
        cliente.obter_health()

    assert "Não foi possível alcançar o backend" in str(erro.value)

