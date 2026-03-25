from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from minha_proxima_viagem.configuracao import ConfiguracaoAplicacao
from minha_proxima_viagem.modelos import InteressesViagem, SolicitacaoPlanoViagem
from minha_proxima_viagem.servico_planejamento import ServicoPlanejamentoViagem


class ClienteGeminiFake:
    def __init__(self, resposta: dict[str, Any], configuracao: ConfiguracaoAplicacao) -> None:
        self.resposta = resposta
        self.configuracao = configuracao
        self.quantidade_chamadas = 0

    def gerar_json(self, _: str, __: str) -> dict[str, Any]:
        self.quantidade_chamadas += 1
        return self.resposta


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
        interesses=InteressesViagem(cultural=True, gastronomico=True),
    )


def test_gerar_plano_usa_modo_conservador_quando_resposta_parece_alucinada(
    configuracao_teste: ConfiguracaoAplicacao,
    solicitacao_teste: SolicitacaoPlanoViagem,
) -> None:
    resposta_suspeita = {
        "destino": "Atlantis",
        "resumo_historia": {
            "titulo": "Resumo histórico do destino",
            "resumo": "Não tenho certeza sobre a história local.",
            "itens": ["Talvez existam marcos históricos relevantes."],
        },
        "contexto_periodo": {
            "titulo": "Clima, eventos e contexto do período",
            "resumo": "Pode haver eventos, mas não foi possível confirmar.",
            "itens": [],
        },
        "interesses": [],
        "dicas_seguranca": {
            "titulo": "Segurança no destino",
            "resumo": "Sem informação suficiente.",
            "itens": [],
        },
        "roteiro_dia_a_dia": [
            {
                "dia": 1,
                "data": "10/07/2026",
                "tema_dia": "Dia genérico",
                "manha": "Comece o dia com um café local e reconhecimento da região central do destino.",
                "tarde": "Reserve o período para a principal atração sugerida, respeitando o perfil da viagem e o ritmo do grupo.",
                "noite": "Finalize com uma refeição típica ou passeio leve em região movimentada e segura.",
                "observacoes": "Talvez seja interessante validar depois.",
            }
        ],
        "observacoes_gerais": ["Não encontrei confirmação confiável."],
        "fontes_recomendadas": [],
        "__metadados_resposta": {
            "modelo_utilizado": "models/gemini-2.5-flash-lite",
            "familia_modelo": "Gemini",
        },
    }
    cliente_fake = ClienteGeminiFake(resposta_suspeita, configuracao_teste)
    servico = ServicoPlanejamentoViagem(cliente_gemini=cliente_fake, configuracao=configuracao_teste)

    plano = servico.gerar_plano(solicitacao_teste)
    plano_repetido = servico.gerar_plano(solicitacao_teste)

    assert plano.destino == "Lisboa"
    assert "Não foi possível obter informações precisas sobre o local de destino" in plano.aviso_importante
    assert "Não foi possível obter informações históricas precisas" in plano.resumo_historia.resumo
    assert "portal oficial de turismo" in plano.roteiro_dia_a_dia[0].manha.casefold()
    assert plano.modelo_utilizado == "models/gemini-2.5-flash-lite"
    assert plano.origem_cache is False
    assert plano_repetido.origem_cache is False
    assert cliente_fake.quantidade_chamadas == 2


def test_gerar_plano_preserva_fluxo_normal_quando_resposta_e_confiavel(
    configuracao_teste: ConfiguracaoAplicacao,
    solicitacao_teste: SolicitacaoPlanoViagem,
) -> None:
    resposta_confiavel = {
        "destino": "Lisboa",
        "periodo_viagem": "10/07/2026 a 12/07/2026",
        "total_dias": 3,
        "perfil_viajantes": "2 adulto(s)",
        "resumo_historia": {
            "titulo": "Resumo histórico do destino",
            "resumo": "Lisboa tem formação histórica ligada à expansão marítima portuguesa e a camadas urbanas de diferentes períodos.",
            "itens": [
                "Centro histórico com forte presença patrimonial",
                "Influência marítima e comercial na identidade local",
                "Bairros antigos ajudam a entender a evolução da cidade",
            ],
        },
        "contexto_periodo": {
            "titulo": "Clima, eventos e contexto do período",
            "resumo": "Julho costuma trazer clima quente, dias longos e maior movimento turístico em Lisboa.",
            "itens": [
                "Reservas antecipadas ajudam em atrações concorridas",
                "Passeios ao ar livre funcionam melhor cedo ou no fim da tarde",
                "Vale acompanhar a agenda cultural oficial do período",
            ],
        },
        "interesses": [
            {
                "titulo": "Cultural",
                "resumo": "O perfil cultural combina bem com áreas históricas, museus e caminhadas por bairros tradicionais.",
                "itens": [
                    "Centro histórico e miradouros",
                    "Museus e espaços de interpretação cultural",
                    "Bairros tradicionais com vida local",
                ],
            },
            {
                "titulo": "Gastronômico",
                "resumo": "Há espaço para combinar mercados, cafés e restaurantes tradicionais com bom equilíbrio entre custo e experiência.",
                "itens": [
                    "Mercados e cafés locais",
                    "Restaurantes tradicionais em bairros centrais",
                    "Uma refeição especial para o fim do dia",
                ],
            },
        ],
        "dicas_seguranca": {
            "titulo": "Segurança no destino",
            "resumo": "Cuidados com deslocamentos, pertences e retorno noturno ajudam a manter a viagem mais tranquila.",
            "itens": [
                "Organize retorno noturno antes de sair",
                "Mantenha atenção a pertences em áreas movimentadas",
                "Confirme rotas e horários em canais oficiais",
            ],
        },
        "roteiro_dia_a_dia": [
            {
                "dia": 1,
                "data": "10/07/2026",
                "tema_dia": "Centro histórico e ambientação",
                "manha": "Comece explorando uma área histórica central para entender a dinâmica da cidade com menos movimento.",
                "tarde": "Aprofunde o passeio com um museu ou outro espaço cultural relevante e pause para almoço em região próxima.",
                "noite": "Feche o dia com jantar em bairro tradicional e retorno planejado com tranquilidade.",
                "observacoes": "Chegar cedo ajuda a aproveitar melhor as áreas mais concorridas.",
            },
            {
                "dia": 2,
                "data": "11/07/2026",
                "tema_dia": "Bairros tradicionais e gastronomia",
                "manha": "Dedique a manhã a caminhar por um bairro com identidade local, observando arquitetura e cotidiano.",
                "tarde": "Combine mercado, café e uma refeição típica em áreas com boa concentração de opções.",
                "noite": "Reserve a noite para uma experiência gastronômica mais marcante, mantendo deslocamento simples.",
                "observacoes": "Se algum restaurante for disputado, vale reservar antes.",
            },
            {
                "dia": 3,
                "data": "12/07/2026",
                "tema_dia": "Miradouros, cultura e despedida",
                "manha": "Use a manhã para vistas panorâmicas e um passeio final em ritmo leve.",
                "tarde": "Escolha um último bloco cultural ou uma revisita a uma área favorita antes do encerramento.",
                "noite": "Mantenha a noite leve, com jantar sem pressa e logística fácil para retorno ou saída.",
                "observacoes": "Revise horários e deslocamentos para evitar correria no encerramento da viagem.",
            },
        ],
        "observacoes_gerais": ["Use o roteiro como guia flexível e confirme reservas com antecedência."],
        "fontes_recomendadas": ["Portal oficial de turismo de Lisboa"],
        "aviso_importante": "Confirme horários e disponibilidade em canais oficiais antes da viagem.",
        "__metadados_resposta": {
            "modelo_utilizado": "models/gemini-2.5-flash-lite",
            "familia_modelo": "Gemini",
        },
    }
    cliente_fake = ClienteGeminiFake(resposta_confiavel, configuracao_teste)
    servico = ServicoPlanejamentoViagem(cliente_gemini=cliente_fake, configuracao=configuracao_teste)

    plano = servico.gerar_plano(solicitacao_teste)
    plano_em_cache = servico.gerar_plano(solicitacao_teste)

    assert plano.destino == "Lisboa"
    assert plano.aviso_importante == "Confirme horários e disponibilidade em canais oficiais antes da viagem."
    assert plano.roteiro_dia_a_dia[0].tema_dia == "Centro histórico e ambientação"
    assert plano.origem_cache is False
    assert plano_em_cache.origem_cache is True
    assert cliente_fake.quantidade_chamadas == 1

