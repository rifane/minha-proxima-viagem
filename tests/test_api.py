from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.api import app
from backend.minha_proxima_viagem.modelos import SolicitacaoPlanoViagem


class ServicoPlanejamentoFake:
    def __init__(self) -> None:
        self.quantidade_chamadas = 0

    def gerar_plano(self, solicitacao: SolicitacaoPlanoViagem) -> dict[str, Any]:
        self.quantidade_chamadas += 1
        return {
            "destino": solicitacao.destino,
            "periodo_viagem": solicitacao.periodo_formatado,
            "total_dias": solicitacao.quantidade_dias,
            "perfil_viajantes": solicitacao.perfil_viajantes,
            "resumo_historia": {
                "titulo": "Resumo histórico do destino",
                "resumo": "Resumo validado em teste.",
                "itens": ["Origem local", "Marcos importantes", "Identidade cultural"],
            },
            "contexto_periodo": {
                "titulo": "Clima, eventos e contexto do período",
                "resumo": "Contexto sazonal do período informado.",
                "itens": ["Clima esperado", "Movimento turístico", "Eventos plausíveis"],
            },
            "interesses": [
                {
                    "titulo": "Cultural",
                    "resumo": "Sugestões alinhadas ao perfil cultural.",
                    "itens": ["Centro histórico", "Museu local", "Bairro tradicional"],
                }
            ],
            "dicas_seguranca": {
                "titulo": "Segurança no destino",
                "resumo": "Cuidados básicos para a viagem.",
                "itens": ["Rotas conhecidas", "Checar clima", "Usar canais oficiais"],
            },
            "roteiro_dia_a_dia": [
                {
                    "dia": 1,
                    "data": solicitacao.data_inicio.strftime("%d/%m/%Y"),
                    "tema_dia": "Centro e arredores",
                    "manha": "Passeio pelo centro do destino-base.",
                    "tarde": "Exploração de bairro próximo ou região vizinha plausível.",
                    "noite": "Jantar e retorno com logística simples.",
                    "observacoes": "Validar deslocamento e clima.",
                }
            ],
            "observacoes_gerais": ["Use o roteiro como guia flexível."],
            "fontes_recomendadas": ["Portal oficial de turismo do destino"],
            "modelo_utilizado": "fake-model",
            "familia_modelo": "Fake",
            "nivel_detalhamento": solicitacao.nivel_detalhamento,
            "origem_cache": False,
            "aviso_importante": "Confirme dados em fontes oficiais.",
        }


class ServicoPlanejamentoComErro:
    def gerar_plano(self, _: SolicitacaoPlanoViagem) -> dict[str, Any]:
        raise RuntimeError("erro inesperado de teste")


@pytest.fixture(autouse=True)
def restaurar_servico_planejamento_original():
    servico_original = app.state.servico_planejamento
    yield
    app.state.servico_planejamento = servico_original



def _payload_valido() -> dict[str, Any]:
    return {
        "data_inicio": date(2026, 7, 10).isoformat(),
        "data_fim": date(2026, 7, 10).isoformat(),
        "destino": "Lisboa",
        "quantidade_adultos": 2,
        "quantidade_criancas": 0,
        "nivel_detalhamento": "equilibrado",
        "interesses": {"cultural": True},
    }


def test_get_teste_retorna_status_operacional() -> None:
    cliente = TestClient(app)
    resposta = cliente.get("/teste")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["ok"] is True
    assert dados["rota_principal"] == "/planejar-viagem"
    assert dados["streaming_disponivel"] is True


def test_post_planejar_viagem_retorna_plano_estruturado() -> None:
    servico_fake = ServicoPlanejamentoFake()
    app.state.servico_planejamento = servico_fake
    cliente = TestClient(app)

    resposta = cliente.post("/planejar-viagem", json=_payload_valido())

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["destino"] == "Lisboa"
    assert dados["roteiro_dia_a_dia"][0]["tema_dia"] == "Centro e arredores"
    assert servico_fake.quantidade_chamadas == 1


def test_post_planejar_viagem_valida_campos_obrigatorios() -> None:
    cliente = TestClient(app)

    resposta = cliente.post("/planejar-viagem", json={"destino": "Lisboa"})

    assert resposta.status_code == 422
    dados = resposta.json()
    assert "detalhe" in dados


def test_post_planejar_viagem_stream_retorna_eventos_ndjson() -> None:
    app.state.servico_planejamento = ServicoPlanejamentoFake()
    cliente = TestClient(app)

    with cliente.stream("POST", "/planejar-viagem/stream", json=_payload_valido()) as resposta:
        linhas = [linha for linha in resposta.iter_lines() if linha]

    eventos = [json.loads(linha) for linha in linhas]
    assert resposta.status_code == 200
    assert eventos[0]["tipo"] == "status"
    assert eventos[1]["tipo"] == "resultado"
    assert eventos[1]["plano"]["destino"] == "Lisboa"
    assert eventos[-1]["tipo"] == "fim"


def test_post_planejar_viagem_trata_erro_inesperado() -> None:
    app.state.servico_planejamento = ServicoPlanejamentoComErro()
    cliente = TestClient(app, raise_server_exceptions=False)

    resposta = cliente.post("/planejar-viagem", json=_payload_valido())

    assert resposta.status_code == 500
    assert resposta.json()["detalhe"] == "Ocorreu um erro interno ao gerar o planejamento."

