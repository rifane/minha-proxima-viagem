from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from pydantic import ValidationError

from minha_proxima_viagem.cliente_gemini import ClienteGemini
from minha_proxima_viagem.configuracao import ConfiguracaoAplicacao
from minha_proxima_viagem.excecoes import ErroIntegracaoIA
from minha_proxima_viagem.modelos import (
    InteressesViagem,
    SolicitacaoPlanoViagem,
    normalizar_nivel_detalhamento,
)
from minha_proxima_viagem.prompts import construir_prompt_usuario
from minha_proxima_viagem.servico_planejamento import ServicoPlanejamentoViagem


class ClienteGeminiFake(ClienteGemini):
    def __init__(self) -> None:
        super().__init__(
            configuracao=ConfiguracaoAplicacao(
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
        )
        self.quantidade_chamadas = 0

    def gerar_json(self, prompt_sistema: str, prompt_usuario: str) -> dict:
        self.quantidade_chamadas += 1
        assert "Retorne somente um JSON válido" in prompt_sistema
        assert "Destino: Gramado" in prompt_usuario
        assert "Gastronômico" in prompt_usuario

        return {
            "destino": "Gramado",
            "periodo_viagem": "10/07/2026 a 12/07/2026",
            "total_dias": 3,
            "perfil_viajantes": "2 adulto(s), 1 criança(s)",
            "resumo_historia": {
                "titulo": "Resumo histórico do destino",
                "resumo": "Gramado tem forte influência europeia e tradição turística na Serra Gaúcha.",
                "itens": ["Colonização europeia", "Turismo consolidado", "Cultura serrana"],
            },
            "contexto_periodo": {
                "titulo": "Clima, eventos e contexto do período",
                "resumo": "Julho costuma ter frio, alta temporada e programação temática de inverno.",
                "itens": ["Levar roupas quentes", "Maior movimento turístico"],
            },
            "interesses": [
                {
                    "titulo": "Gastronômico",
                    "resumo": "Destaque para cafés coloniais, chocolates e fondues.",
                    "itens": ["Opção econômica", "Opção intermediária", "Opção premium"],
                }
            ],
            "dicas_seguranca": {
                "titulo": "Segurança no destino",
                "resumo": "Destino turístico com boa estrutura, mas exige cuidados básicos.",
                "itens": ["Atenção ao trânsito", "Verificar reservas e clima"],
            },
            "roteiro_dia_a_dia": [
                {
                    "dia": 1,
                    "data": "10/07/2026",
                    "tema_dia": "Centro e ambientação",
                    "manha": "Passeio leve no centro.",
                    "tarde": "Atração infantil e cultural.",
                    "noite": "Jantar típico.",
                    "observacoes": "Usar casacos.",
                },
                {
                    "dia": 2,
                    "data": "11/07/2026",
                    "tema_dia": "Parques e chocolate",
                    "manha": "Parque temático.",
                    "tarde": "Chocolate e compras.",
                    "noite": "Fondue.",
                    "observacoes": "Reservar com antecedência.",
                },
                {
                    "dia": 3,
                    "data": "12/07/2026",
                    "tema_dia": "Panoramas e despedida",
                    "manha": "Passeio panorâmico.",
                    "tarde": "Almoço de despedida.",
                    "noite": "Retorno.",
                    "observacoes": "Checar trânsito.",
                },
            ],
            "observacoes_gerais": ["Compre ingressos antes em alta temporada."],
            "fontes_recomendadas": ["Site oficial de turismo de Gramado"],
            "__metadados_resposta": {
                "modelo_utilizado": "models/gemini-2.5-flash-lite",
                "familia_modelo": "Gemini",
            },
            "aviso_importante": "Valide horários e disponibilidade antes da viagem.",
        }


class ErroGeminiQuotaFake(Exception):
    pass


def main() -> int:
    try:
        SolicitacaoPlanoViagem(
            data_inicio=date(2026, 7, 12),
            data_fim=date(2026, 7, 10),
            destino="Lisboa",
        )
        raise AssertionError("A validação de período inválido deveria ter falhado.")
    except ValidationError:
        pass

    try:
        SolicitacaoPlanoViagem(
            data_inicio=date(2026, 7, 10),
            data_fim=date(2026, 7, 12),
            destino=" ",
        )
        raise AssertionError("A validação de destino obrigatório deveria ter falhado.")
    except ValidationError:
        pass

    try:
        SolicitacaoPlanoViagem(
            data_inicio=date(2026, 7, 10),
            data_fim=date(2026, 7, 12),
            destino="Lisboa",
            quantidade_adultos=0,
            quantidade_criancas=0,
        )
        raise AssertionError("A validação de quantidade mínima de viajantes deveria ter falhado.")
    except ValidationError:
        pass

    assert normalizar_nivel_detalhamento("compacto") == "enxuto"
    assert normalizar_nivel_detalhamento("padrao") == "equilibrado"
    assert normalizar_nivel_detalhamento("detalhado") == "detalhado"

    solicitacao_alias = SolicitacaoPlanoViagem(
        data_inicio=date(2026, 9, 10),
        data_fim=date(2026, 9, 12),
        destino="Recife",
        quantidade_adultos=2,
        nivel_detalhe="compacto",
    )
    assert solicitacao_alias.nivel_detalhamento == "enxuto"

    solicitacao = SolicitacaoPlanoViagem(
        data_inicio=date(2026, 7, 10),
        data_fim=date(2026, 7, 12),
        destino="Gramado",
        quantidade_adultos=2,
        quantidade_criancas=1,
        nivel_detalhamento="detalhado",
        interesses=InteressesViagem(gastronomico=True, cultural=True),
    )

    prompt = construir_prompt_usuario(solicitacao)
    bloco_interesses_prompt = prompt.split("Regras de negócio obrigatórias:", maxsplit=1)[0]
    assert "Dia 1: 10/07/2026" in prompt
    assert "Gastronômico" in prompt
    assert "Cultural" in prompt
    assert "Nível de detalhamento do plano: detalhado" in prompt
    assert "Aprofunde o conteúdo com mais contexto" in prompt
    assert "cidades, praias, bairros e regiões próximas" in prompt
    assert "destino principal" in prompt
    assert '"tema_dia": "string"' in prompt
    assert "Relaxamento" not in bloco_interesses_prompt
    assert "Vida noturna" not in bloco_interesses_prompt

    solicitacao_sem_interesses = SolicitacaoPlanoViagem(
        data_inicio=date(2026, 8, 1),
        data_fim=date(2026, 8, 3),
        destino="Curitiba",
        quantidade_adultos=1,
        quantidade_criancas=0,
        nivel_detalhamento="equilibrado",
        interesses=InteressesViagem(),
    )

    prompt_sem_interesses = construir_prompt_usuario(solicitacao_sem_interesses)
    assert "Nenhum interesse foi selecionado." in prompt_sem_interesses
    assert "Aventureiro" in prompt_sem_interesses
    assert "Econômico" in prompt_sem_interesses
    assert "Gastronômico" in prompt_sem_interesses
    assert "Cultural" in prompt_sem_interesses
    assert "Relaxamento" in prompt_sem_interesses
    assert "Vida noturna" in prompt_sem_interesses
    assert "Ecoturismo/Sustentável" in prompt_sem_interesses
    assert "cidade próxima" in prompt_sem_interesses or "regiões próximas" in prompt_sem_interesses

    cliente = ClienteGeminiFake()
    erro_quota = cliente._classificar_erro_integracao(
        ErroGeminiQuotaFake(
            "429 You exceeded your current quota. Please retry in 54.844823623s. "
            "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests"
        )
    )
    assert isinstance(erro_quota, ErroIntegracaoIA)
    assert erro_quota.status_code == 429
    assert erro_quota.codigo_erro == "gemini_quota_excedida"
    assert erro_quota.retry_delay_segundos == 54

    cliente_fake = ClienteGeminiFake()
    configuracao_cache = ConfiguracaoAplicacao(
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
    servico = ServicoPlanejamentoViagem(cliente_gemini=cliente_fake, configuracao=configuracao_cache)
    plano = servico.gerar_plano(solicitacao)
    plano_em_cache = servico.gerar_plano(solicitacao)

    assert plano.destino == "Gramado"
    assert plano.total_dias == 3
    assert len(plano.roteiro_dia_a_dia) == 3
    assert plano.roteiro_dia_a_dia[0].tema_dia == "Centro e ambientação"
    assert plano.interesses[0].titulo == "Gastronômico"
    assert len(plano.interesses[0].itens) >= 3
    assert plano.modelo_utilizado == "models/gemini-2.5-flash-lite"
    assert plano.familia_modelo == "Gemini"
    assert plano.nivel_detalhamento == "detalhado"
    assert plano.origem_cache is False
    assert plano_em_cache.destino == "Gramado"
    assert plano_em_cache.origem_cache is True
    assert cliente_fake.quantidade_chamadas == 1

    solicitacao_roteiro_longo = SolicitacaoPlanoViagem(
        data_inicio=date(2026, 10, 1),
        data_fim=date(2026, 10, 8),
        destino="Fortaleza",
        quantidade_adultos=2,
        quantidade_criancas=1,
        nivel_detalhamento="equilibrado",
        interesses=InteressesViagem(gastronomico=True, cultural=True, relaxamento=True),
    )
    roteiro_fallback = servico._gerar_roteiro_minimo(solicitacao_roteiro_longo)
    assert len(roteiro_fallback) == 8
    assert len({dia["tema_dia"] for dia in roteiro_fallback}) == 8
    assert len({dia["manha"] for dia in roteiro_fallback}) == 8
    assert len({dia["tarde"] for dia in roteiro_fallback}) == 8
    assert len({dia["noite"] for dia in roteiro_fallback}) == 8
    assert any(
        "região próxima" in dia["tema_dia"].casefold()
        or "entorno" in dia["tema_dia"].casefold()
        or "fora do eixo" in dia["tema_dia"].casefold()
        for dia in roteiro_fallback
    )
    assert any(
        "cidade próxima" in dia["manha"].casefold()
        or "praia próxima" in dia["manha"].casefold()
        or "entorno regional" in dia["noite"].casefold()
        for dia in roteiro_fallback
    )

    roteiro_ia_incompleto = [
        {
            "dia": 1,
            "data": "01/10/2026",
            "tema_dia": "Ambientação local",
            "manha": "Comece o dia com um café local e reconhecimento da região central do destino.",
            "tarde": "Reserve o período para a principal atração sugerida, respeitando o perfil da viagem e o ritmo do grupo.",
            "noite": "Finalize com uma refeição típica ou passeio leve em região movimentada e segura.",
            "observacoes": "Chegue cedo.",
        },
        {
            "dia": 2,
            "data": "02/10/2026",
            "tema_dia": "Ambientação local",
            "manha": "Comece o dia com um café local e reconhecimento da região central do destino.",
            "tarde": "Reserve o período para a principal atração sugerida, respeitando o perfil da viagem e o ritmo do grupo.",
            "noite": "Finalize com uma refeição típica ou passeio leve em região movimentada e segura.",
            "observacoes": "Chegue cedo.",
        },
    ]
    roteiro_normalizado = servico._normalizar_roteiro(solicitacao_roteiro_longo, roteiro_ia_incompleto)
    assert len(roteiro_normalizado) == 8
    assert len({dia["tema_dia"] for dia in roteiro_normalizado}) == 8
    assert len({dia["manha"] for dia in roteiro_normalizado}) == 8

    observacoes_gerais = servico._complementar_observacoes_gerais(solicitacao_roteiro_longo, [])
    fontes = servico._complementar_fontes_recomendadas(solicitacao_roteiro_longo, [])
    assert any("regiões próximas" in item or "cidades ou regiões próximas" in item for item in observacoes_gerais)
    assert any("cidades, regiões ou atrativos próximos" in item for item in fontes)

    print("Smoke test concluído com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
