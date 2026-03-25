import sys
from html import escape
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

from minha_proxima_viagem.cliente_api import instanciar_cliente_api_planejamento
from minha_proxima_viagem.configuracao import obter_configuracao
from minha_proxima_viagem.excecoes import ErroIntegracaoIA, ErroPlanejamentoViagem
from minha_proxima_viagem.modelos import (
    InteressesViagem,
    PlanoViagemGerado,
    SolicitacaoPlanoViagem,
    normalizar_nivel_detalhamento,
    obter_parametros_detalhamento,
)


configuracao = obter_configuracao()
cliente_api = instanciar_cliente_api_planejamento()


_MAPA_ICONES_INTERESSES = {
    "Aventureiro": "🧗",
    "Econômico": "💸",
    "Gastronômico": "🍽️",
    "Cultural": "🏛️",
    "Relaxamento": "🧘",
    "Vida noturna": "🌃",
    "Ecoturismo/Sustentável": "🌿",
}

_NIVEIS_DETALHAMENTO = ["enxuto", "equilibrado", "detalhado"]

_MENSAGEM_MODO_CONSERVADOR = "não foi possível obter informações precisas sobre o local de destino"


def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(251, 191, 36, 0.18), transparent 24%),
                    radial-gradient(circle at top left, rgba(14, 165, 233, 0.18), transparent 28%),
                    linear-gradient(180deg, #fffaf2 0%, #fffdf8 42%, #f8fbff 100%);
            }
            .bloco-hero {
                background: linear-gradient(135deg, #f97316 0%, #fb7185 45%, #0ea5e9 100%);
                border-radius: 22px;
                padding: 1.8rem 1.9rem;
                color: white;
                margin-bottom: 1.2rem;
                box-shadow: 0 20px 48px rgba(249, 115, 22, 0.20);
                position: relative;
                overflow: hidden;
            }
            .bloco-hero::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.10) 100%);
            }
            .bloco-hero::after {
                content: "";
                position: absolute;
                width: 240px;
                height: 240px;
                border-radius: 50%;
                right: -70px;
                top: -90px;
                background: rgba(255,255,255,0.12);
            }
            .bloco-hero h1 {
                margin: 0 0 0.45rem 0;
                font-size: 2.15rem;
                font-weight: 800;
                position: relative;
                z-index: 1;
            }
            .bloco-hero p {
                margin: 0;
                font-size: 1rem;
                line-height: 1.55;
                opacity: 0.96;
                max-width: 760px;
                position: relative;
                z-index: 1;
            }
            .hero-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 0.55rem;
                margin-top: 1rem;
                position: relative;
                z-index: 1;
            }
            .hero-badge {
                background: rgba(255,255,255,0.18);
                border: 1px solid rgba(255,255,255,0.24);
                color: #fff;
                padding: 0.38rem 0.72rem;
                border-radius: 999px;
                font-size: 0.86rem;
                font-weight: 600;
            }
            .bloco-inspiracao {
                background: rgba(255,255,255,0.92);
                border: 1px solid #fde7cf;
                border-radius: 22px;
                padding: 1rem 1rem 0.4rem 1rem;
                box-shadow: 0 16px 32px rgba(15, 23, 42, 0.05);
                margin-bottom: 1rem;
            }
            .grade-inspiracao {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.85rem;
                margin-top: 0.7rem;
            }
            .card-inspiracao {
                background: linear-gradient(180deg, #fffdf9 0%, #fff7ed 100%);
                border: 1px solid #fed7aa;
                border-radius: 18px;
                padding: 1rem;
            }
            .card-inspiracao h4 {
                margin: 0 0 0.35rem 0;
                color: #9a3412;
                font-size: 1rem;
            }
            .card-inspiracao p {
                margin: 0;
                color: #475569;
                font-size: 0.93rem;
                line-height: 1.5;
            }
            .bloco-formulario {
                background: #ffffff;
                border: 1px solid #fde7cf;
                border-radius: 20px;
                padding: 1.15rem 1.15rem 0.5rem 1.15rem;
                box-shadow: 0 18px 32px rgba(148, 163, 184, 0.10);
                margin-bottom: 1rem;
            }
            .bloco-secao {
                background: linear-gradient(180deg, #fffdfa 0%, #fff8ef 100%);
                border: 1px solid #fde7cf;
                border-radius: 18px;
                padding: 0.9rem 1rem 0.6rem 1rem;
                margin-bottom: 0.9rem;
            }
            .bloco-secao h3 {
                margin-top: 0;
                margin-bottom: 0.35rem;
                color: #7c2d12;
                font-size: 1rem;
            }
            .texto-apoio {
                color: #475569;
                font-size: 0.95rem;
                margin-bottom: 0.6rem;
            }
            .bloco-guia {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 18px;
                padding: 1rem 1rem 0.85rem 1rem;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
                margin-bottom: 1rem;
            }
            .grade-resumo {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.85rem;
                margin: 1rem 0 0.6rem 0;
            }
            .card-resumo {
                background: linear-gradient(180deg, #ffffff 0%, #fffaf5 100%);
                border: 1px solid #fde7cf;
                border-radius: 18px;
                padding: 1rem;
                box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
            }
            .card-resumo-topo {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                margin-bottom: 0.55rem;
            }
            .card-resumo-icone {
                width: 2.2rem;
                height: 2.2rem;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border-radius: 999px;
                background: linear-gradient(135deg, #fff7ed 0%, #dbeafe 100%);
                font-size: 1.05rem;
                box-shadow: inset 0 0 0 1px #fde7cf;
            }
            .card-resumo-label {
                color: #9a3412;
                font-size: 0.82rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 0.35rem;
            }
            .card-resumo-valor {
                color: #0f172a;
                font-size: 1.05rem;
                font-weight: 700;
                line-height: 1.45;
                word-break: break-word;
            }
            .barra-status {
                background: linear-gradient(90deg, #fff7ed 0%, #eff6ff 100%);
                border: 1px solid #fed7aa;
                border-radius: 16px;
                padding: 0.9rem 1rem;
                margin-bottom: 1rem;
                color: #0f172a;
            }
            .barra-status strong {
                color: #c2410c;
            }
            .faixa-destaque-destino {
                background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 35%, #0ea5e9 100%);
                border-radius: 22px;
                padding: 1.2rem 1.25rem;
                margin: 0.35rem 0 1rem 0;
                color: white;
                box-shadow: 0 18px 36px rgba(30, 58, 138, 0.18);
            }
            .faixa-destaque-destino small {
                display: block;
                opacity: 0.85;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }
            .faixa-destaque-destino strong {
                display: block;
                font-size: 1.35rem;
                font-weight: 800;
                margin-bottom: 0.25rem;
            }
            .faixa-destaque-destino span {
                display: block;
                line-height: 1.55;
                opacity: 0.96;
            }
            .faixa-destaque-destino em {
                display: block;
                margin-top: 0.55rem;
                font-style: normal;
                opacity: 0.92;
                color: #dbeafe;
            }
            .linha-metadados {
                display: flex;
                flex-wrap: wrap;
                gap: 0.65rem;
                margin: 0.55rem 0 1rem 0;
            }
            .badge-meta {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                border-radius: 999px;
                padding: 0.45rem 0.8rem;
                font-size: 0.88rem;
                font-weight: 700;
                border: 1px solid #e2e8f0;
                background: #ffffff;
                color: #334155;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
            }
            .badge-meta.modelo {
                border-color: #bae6fd;
                background: linear-gradient(90deg, #f0f9ff 0%, #eef2ff 100%);
                color: #0f172a;
            }
            .badge-meta.cache {
                border-color: #bbf7d0;
                background: linear-gradient(90deg, #f0fdf4 0%, #ecfeff 100%);
                color: #166534;
            }
            .badge-meta.ao-vivo {
                border-color: #fed7aa;
                background: linear-gradient(90deg, #fff7ed 0%, #fffbeb 100%);
                color: #9a3412;
            }
            .badge-meta.conservador {
                border-color: #fcd34d;
                background: linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%);
                color: #92400e;
            }
            .banner-conservador {
                background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 45%, #fef3c7 100%);
                border: 1px solid #fdba74;
                border-left: 6px solid #f59e0b;
                border-radius: 18px;
                padding: 1rem 1.1rem;
                margin: 0.2rem 0 1rem 0;
                box-shadow: 0 14px 28px rgba(245, 158, 11, 0.10);
            }
            .banner-conservador-topo {
                display: flex;
                align-items: center;
                gap: 0.55rem;
                margin-bottom: 0.4rem;
                color: #92400e;
                font-weight: 800;
                font-size: 1rem;
            }
            .banner-conservador-texto {
                color: #78350f;
                line-height: 1.55;
                font-size: 0.95rem;
            }
            .banner-conservador ul {
                margin: 0.7rem 0 0 1.1rem;
                color: #78350f;
            }
            .banner-conservador li {
                margin-bottom: 0.28rem;
            }
            .linha-interesses {
                display: flex;
                flex-wrap: wrap;
                gap: 0.55rem;
                margin: 0.8rem 0 0.15rem 0;
            }
            .chip-interesse {
                border-radius: 999px;
                padding: 0.38rem 0.78rem;
                font-size: 0.88rem;
                font-weight: 600;
                border: 1px solid #cbd5e1;
                background: #ffffff;
                color: #475569;
            }
            .chip-interesse.ativo {
                border-color: #fdba74;
                background: linear-gradient(90deg, #fff7ed 0%, #fffbeb 100%);
                color: #9a3412;
                box-shadow: 0 8px 18px rgba(249, 115, 22, 0.10);
            }
            .chip-interesse.sugestao {
                border-style: dashed;
                border-color: #cbd5e1;
                background: #f8fafc;
            }
            .grid-interesses-resultado {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.9rem;
            }
            .grade-insights {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.9rem;
                margin: 0.2rem 0 1rem 0;
            }
            .card-insight {
                background: linear-gradient(180deg, #ffffff 0%, #fffaf5 100%);
                border: 1px solid #fde7cf;
                border-radius: 18px;
                padding: 1rem;
                box-shadow: 0 12px 22px rgba(15, 23, 42, 0.04);
            }
            .card-insight-titulo {
                color: #9a3412;
                font-size: 0.82rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.4rem;
            }
            .card-insight-valor {
                color: #0f172a;
                font-size: 1.02rem;
                font-weight: 800;
                line-height: 1.45;
                margin-bottom: 0.25rem;
            }
            .card-insight-texto {
                color: #475569;
                line-height: 1.55;
                font-size: 0.93rem;
            }
            .card-interesse-resultado {
                background: linear-gradient(180deg, #ffffff 0%, #fffaf5 100%);
                border: 1px solid #fde7cf;
                border-radius: 18px;
                padding: 1rem;
                box-shadow: 0 12px 22px rgba(15, 23, 42, 0.04);
            }
            .card-interesse-topo {
                display: flex;
                align-items: center;
                gap: 0.7rem;
                margin-bottom: 0.55rem;
            }
            .card-interesse-icone {
                width: 2.3rem;
                height: 2.3rem;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border-radius: 999px;
                background: linear-gradient(135deg, #fff7ed 0%, #fef3c7 100%);
                font-size: 1.05rem;
                box-shadow: inset 0 0 0 1px #fde7cf;
            }
            .card-interesse-titulo {
                color: #9a3412;
                font-size: 1rem;
                font-weight: 800;
            }
            .stExpander {
                border: 1px solid #fde7cf !important;
                border-radius: 16px !important;
                overflow: hidden;
            }
            .cartao-roteiro {
                background: linear-gradient(180deg, #ffffff 0%, #fffaf5 100%);
                border: 1px solid #fde7cf;
                border-radius: 18px;
                padding: 0.95rem 1rem 0.15rem 1rem;
                margin-bottom: 0.7rem;
                box-shadow: 0 10px 20px rgba(15, 23, 42, 0.04);
            }
            .sidebar-card {
                background: linear-gradient(180deg, #ffffff 0%, #fff8ef 100%);
                border: 1px solid #fde7cf;
                border-radius: 18px;
                padding: 0.9rem 0.95rem;
                margin-bottom: 0.85rem;
                box-shadow: 0 10px 18px rgba(15, 23, 42, 0.04);
            }
            .sidebar-card h4 {
                margin: 0 0 0.5rem 0;
                color: #9a3412;
                font-size: 0.98rem;
            }
            .sidebar-card p,
            .sidebar-card li {
                color: #475569;
                font-size: 0.92rem;
                line-height: 1.45;
            }
            .cartao-roteiro h4 {
                margin: 0 0 0.6rem 0;
                color: #9a3412;
                font-size: 1rem;
            }
            .cartao-roteiro-topo {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
                flex-wrap: wrap;
                margin-bottom: 0.75rem;
            }
            .pill-tema-dia {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                border-radius: 999px;
                padding: 0.45rem 0.78rem;
                background: linear-gradient(90deg, #eff6ff 0%, #fff7ed 100%);
                border: 1px solid #c7d2fe;
                color: #1e3a8a;
                font-size: 0.88rem;
                font-weight: 700;
            }
            .bloco-observacao-dia {
                margin-top: 0.55rem;
                padding: 0.7rem 0.85rem;
                border-radius: 14px;
                border: 1px solid #fed7aa;
                background: linear-gradient(90deg, #fff7ed 0%, #fffbeb 100%);
                color: #7c2d12;
                line-height: 1.5;
            }
            .timeline-roteiro {
                position: relative;
                margin-top: 0.2rem;
                padding-left: 1.4rem;
            }
            .timeline-roteiro::before {
                content: "";
                position: absolute;
                left: 0.35rem;
                top: 0.4rem;
                bottom: 0.5rem;
                width: 2px;
                background: linear-gradient(180deg, #fdba74 0%, #7dd3fc 100%);
            }
            .timeline-item {
                position: relative;
                padding: 0 0 1rem 0.55rem;
            }
            .timeline-item:last-child {
                padding-bottom: 0.35rem;
            }
            .timeline-item::before {
                content: "";
                position: absolute;
                left: -0.75rem;
                top: 0.22rem;
                width: 0.75rem;
                height: 0.75rem;
                border-radius: 999px;
                background: #fff;
                border: 2px solid #fb923c;
                box-shadow: 0 0 0 3px #fff7ed;
            }
            .timeline-titulo {
                color: #9a3412;
                font-weight: 800;
                margin-bottom: 0.18rem;
            }
            .timeline-texto {
                color: #334155;
                line-height: 1.55;
            }
            .bloco-carregando {
                background: linear-gradient(90deg, #fff7ed 0%, #eff6ff 100%);
                border: 1px solid #fed7aa;
                border-radius: 18px;
                padding: 0.95rem 1rem;
                margin: 0.75rem 0 1rem 0;
                color: #7c2d12;
                font-weight: 600;
                animation: pulsarViagem 1.6s ease-in-out infinite;
            }
            @keyframes pulsarViagem {
                0% { transform: scale(1); box-shadow: 0 8px 16px rgba(249, 115, 22, 0.05); }
                50% { transform: scale(1.01); box-shadow: 0 12px 22px rgba(14, 165, 233, 0.08); }
                100% { transform: scale(1); box-shadow: 0 8px 16px rgba(249, 115, 22, 0.05); }
            }
            .mini-aba-texto {
                color: #475569;
                margin-bottom: 0.75rem;
            }
            @media (max-width: 1100px) {
                .grade-resumo {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .grade-inspiracao {
                    grid-template-columns: 1fr;
                }
                .grid-interesses-resultado {
                    grid-template-columns: 1fr;
                }
                .grade-insights {
                    grid-template-columns: 1fr;
                }
            }
            @media (max-width: 700px) {
                .grade-resumo {
                    grid-template-columns: 1fr;
                }
                .grade-inspiracao {
                    grid-template-columns: 1fr;
                }
                .grid-interesses-resultado {
                    grid-template-columns: 1fr;
                }
                .grade-insights {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def formatar_data_br(data_valor: date) -> str:
    return data_valor.strftime("%d/%m/%Y")


def formatar_rotulo_nivel_detalhamento(nivel: str) -> str:
    parametros = obter_parametros_detalhamento(normalizar_nivel_detalhamento(nivel))
    return str(parametros["rotulo"])


def obter_descricao_nivel_detalhamento(nivel: str) -> str:
    parametros = obter_parametros_detalhamento(normalizar_nivel_detalhamento(nivel))
    return str(parametros["descricao"])


def renderizar_chips_interesses(interesses: dict[str, bool]) -> None:
    selecionados = [nome for nome, ativo in interesses.items() if ativo]
    chips: list[str] = []
    for nome, ativo in interesses.items():
        classes = "chip-interesse ativo" if ativo else "chip-interesse"
        chips.append(f'<span class="{classes}">{nome}</span>')

    if not selecionados:
        chips = [
            f'<span class="chip-interesse sugestao">{nome}</span>'
            for nome in interesses.keys()
        ]

    st.markdown(f'<div class="linha-interesses">{"".join(chips)}</div>', unsafe_allow_html=True)


def renderizar_chips_interesses_resultado(plano: PlanoViagemGerado) -> None:
    if not plano.interesses:
        return

    chips = [
        f'<span class="chip-interesse ativo">{_MAPA_ICONES_INTERESSES.get(grupo.titulo, "✨")} {escape(grupo.titulo)}</span>'
        for grupo in plano.interesses
    ]
    st.markdown(
        '<div class="mini-aba-texto"><strong>Interesses considerados no plano:</strong></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="linha-interesses">{"".join(chips)}</div>', unsafe_allow_html=True)


def _obter_resumo_interesses_resultado(plano: PlanoViagemGerado) -> str:
    if not plano.interesses:
        return "Sem interesses destacados."
    if len(plano.interesses) <= 3:
        return ", ".join(grupo.titulo for grupo in plano.interesses)
    primeiros = ", ".join(grupo.titulo for grupo in plano.interesses[:3])
    return f"{primeiros} e mais {len(plano.interesses) - 3}"


def renderizar_painel_visao_geral(plano: PlanoViagemGerado) -> None:
    nivel_rotulo = formatar_rotulo_nivel_detalhamento(plano.nivel_detalhamento)
    nivel_descricao = obter_descricao_nivel_detalhamento(plano.nivel_detalhamento)
    interesses_resumo = _obter_resumo_interesses_resultado(plano)
    total_fontes = len(plano.fontes_recomendadas)
    total_observacoes = len(plano.observacoes_gerais)
    st.markdown(
        f"""
        <div class="grade-insights">
            <div class="card-insight">
                <div class="card-insight-titulo">🧭 Leitura rápida</div>
                <div class="card-insight-valor">Guia para {escape(plano.destino)}</div>
                <div class="card-insight-texto">Resumo pensado para {escape(plano.periodo_viagem)}, com roteiro distribuído ao longo de {plano.total_dias} dia(s).</div>
            </div>
            <div class="card-insight">
                <div class="card-insight-titulo">✨ Detalhamento escolhido</div>
                <div class="card-insight-valor">{escape(nivel_rotulo)}</div>
                <div class="card-insight-texto">{escape(nivel_descricao.capitalize())}.</div>
            </div>
            <div class="card-insight">
                <div class="card-insight-titulo">🎯 Foco do plano</div>
                <div class="card-insight-valor">{len(plano.interesses)} interesse(s)</div>
                <div class="card-insight-texto">{escape(interesses_resumo)}. {total_fontes} fonte(s) recomendada(s) e {total_observacoes} observação(ões) geral(is).</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_grupo(titulo: str, resumo: str, itens: list[str]) -> None:
    st.markdown('<div class="bloco-guia">', unsafe_allow_html=True)
    st.markdown(f"### {titulo}")
    st.write(resumo)
    if itens:
        for item in itens:
            st.markdown(f"- {item}")
    st.markdown("</div>", unsafe_allow_html=True)


def formatar_modelo_exibicao(plano: PlanoViagemGerado) -> str | None:
    if not plano.modelo_utilizado:
        return plano.familia_modelo

    nome_curto = plano.modelo_utilizado.replace("models/", "")
    if plano.familia_modelo:
        return f"{plano.familia_modelo} · {nome_curto}"
    return nome_curto


def plano_em_modo_conservador(plano: PlanoViagemGerado) -> bool:
    aviso = (plano.aviso_importante or "").strip().casefold()
    return _MENSAGEM_MODO_CONSERVADOR in aviso


def renderizar_banner_modo_conservador(plano: PlanoViagemGerado) -> None:
    if not plano_em_modo_conservador(plano):
        return

    st.markdown(
        f"""
        <div class="banner-conservador">
            <div class="banner-conservador-topo">⚠️ Plano em modo conservador</div>
            <div class="banner-conservador-texto">
                {escape(plano.aviso_importante)}
                <ul>
                    <li>Priorize atrações, bairros e deslocamentos confirmados em canais oficiais.</li>
                    <li>Use este plano como guia provisório até validar clima, funcionamento e reservas.</li>
                    <li>Evite assumir como confirmadas sugestões muito específicas sem checagem final.</li>
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_metadados_resultado(plano: PlanoViagemGerado) -> None:
    badges: list[str] = []
    modelo_exibicao = formatar_modelo_exibicao(plano)
    if modelo_exibicao:
        badges.append(
            f'<span class="badge-meta modelo">🤖 Modelo: {escape(modelo_exibicao)}</span>'
        )

    badges.append(
        f'<span class="badge-meta">🧭 Detalhamento: {escape(formatar_rotulo_nivel_detalhamento(plano.nivel_detalhamento))}</span>'
    )

    if plano.origem_cache:
        badges.append('<span class="badge-meta cache">⚡ Resultado vindo do cache</span>')
    else:
        badges.append('<span class="badge-meta ao-vivo">🌐 Consulta gerada ao vivo</span>')

    if plano_em_modo_conservador(plano):
        badges.append('<span class="badge-meta conservador">⚠️ Modo conservador</span>')

    st.markdown(f'<div class="linha-metadados">{"".join(badges)}</div>', unsafe_allow_html=True)


def renderizar_bloco_inspiracao() -> None:
    st.markdown(
        """
        <div class="bloco-inspiracao">
            <div class="texto-apoio"><strong>Inspiração para sua próxima experiência:</strong> escolha o clima da viagem e deixe a IA transformar preferências em um mini guia prático.</div>
            <div class="grade-inspiracao">
                <div class="card-inspiracao">
                    <h4>🏖️ Sol e mar</h4>
                    <p>Perfeito para destinos litorâneos, com foco em praias, gastronomia regional, pôr do sol e passeios leves.</p>
                </div>
                <div class="card-inspiracao">
                    <h4>🏙️ Cultura e cidade</h4>
                    <p>Ideal para quem quer explorar centros históricos, museus, feiras, cafés e a identidade local de cada lugar.</p>
                </div>
                <div class="card-inspiracao">
                    <h4>🌿 Natureza e descanso</h4>
                    <p>Ótimo para viagens com trilhas leves, ecoturismo, calmaria, experiências autênticas e ritmo mais tranquilo.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_faixa_destaque_destino(plano: PlanoViagemGerado) -> None:
    st.markdown(
        f"""
        <div class="faixa-destaque-destino">
            <small>🌍 Seu próximo destino em foco</small>
            <strong>Seu guia para {escape(plano.destino)}</strong>
            <span>{escape(plano.periodo_viagem)} • {plano.total_dias} dia(s) planejados • {escape(plano.perfil_viajantes)}</span>
            <em>Planejamento em nível {escape(formatar_rotulo_nivel_detalhamento(plano.nivel_detalhamento).lower())}, com histórico, contexto do período, interesses, segurança e roteiro dia a dia.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_card_interesse(grupo: PlanoViagemGerado | object, titulo: str, resumo: str, itens: list[str]) -> None:
    icone = _MAPA_ICONES_INTERESSES.get(titulo, "✨")
    itens_html = "".join(f"<li>{escape(item)}</li>" for item in itens)
    st.markdown(
        f"""
        <div class="card-interesse-resultado">
            <div class="card-interesse-topo">
                <div class="card-interesse-icone">{icone}</div>
                <div class="card-interesse-titulo">{escape(titulo)}</div>
            </div>
            <div class="timeline-texto">{escape(resumo)}</div>
            {'<ul>' + itens_html + '</ul>' if itens_html else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_timeline_dia(dia: object) -> None:
    tema_dia = escape(getattr(dia, "tema_dia", "") or "Roteiro do dia")
    observacoes = escape(getattr(dia, "observacoes", "") or "")
    st.markdown(
        f"""
        <div class="cartao-roteiro">
            <div class="cartao-roteiro-topo">
                <div class="pill-tema-dia">🗺️ Tema do dia: {tema_dia}</div>
            </div>
            <div class="timeline-roteiro">
                <div class="timeline-item">
                    <div class="timeline-titulo">☀️ Manhã</div>
                    <div class="timeline-texto">{escape(getattr(dia, 'manha'))}</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-titulo">🌤️ Tarde</div>
                    <div class="timeline-texto">{escape(getattr(dia, 'tarde'))}</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-titulo">🌙 Noite</div>
                    <div class="timeline-texto">{escape(getattr(dia, 'noite'))}</div>
                </div>
            </div>
            {f'<div class="bloco-observacao-dia"><strong>Observação prática:</strong> {observacoes}</div>' if observacoes else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_resultado(plano: PlanoViagemGerado) -> None:
    st.success("Planejamento gerado com sucesso!")
    renderizar_faixa_destaque_destino(plano)
    renderizar_banner_modo_conservador(plano)

    st.markdown(
        f"""
        <div class="grade-resumo">
            <div class="card-resumo">
                <div class="card-resumo-topo">
                    <div class="card-resumo-icone">📍</div>
                    <div class="card-resumo-label">Destino</div>
                </div>
                <div class="card-resumo-valor">{escape(plano.destino)}</div>
            </div>
            <div class="card-resumo">
                <div class="card-resumo-topo">
                    <div class="card-resumo-icone">🗓️</div>
                    <div class="card-resumo-label">Período da viagem</div>
                </div>
                <div class="card-resumo-valor">{escape(plano.periodo_viagem)}</div>
            </div>
            <div class="card-resumo">
                <div class="card-resumo-topo">
                    <div class="card-resumo-icone">⏳</div>
                    <div class="card-resumo-label">Total de dias</div>
                </div>
                <div class="card-resumo-valor">{plano.total_dias}</div>
            </div>
            <div class="card-resumo">
                <div class="card-resumo-topo">
                    <div class="card-resumo-icone">👥</div>
                    <div class="card-resumo-label">Perfil</div>
                </div>
                <div class="card-resumo-valor">{escape(plano.perfil_viajantes)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="barra-status">
            <strong>Resumo do planejamento:</strong> confira abaixo a história do destino, o contexto do período,
            os interesses sugeridos, as orientações de segurança e o roteiro dia a dia.
        </div>
        """,
        unsafe_allow_html=True,
    )

    renderizar_metadados_resultado(plano)
    renderizar_painel_visao_geral(plano)
    renderizar_chips_interesses_resultado(plano)

    abas = st.tabs(["🏛️ História", "🌦️ Período", "🎯 Interesses", "🛡️ Segurança", "🗓️ Roteiro", "📝 Observações"])

    with abas[0]:
        st.markdown('<div class="mini-aba-texto">Contexto histórico e identidade cultural do destino.</div>', unsafe_allow_html=True)
        renderizar_grupo(
            plano.resumo_historia.titulo,
            plano.resumo_historia.resumo,
            plano.resumo_historia.itens,
        )

    with abas[1]:
        st.markdown('<div class="mini-aba-texto">Clima, movimento turístico e panorama do período selecionado.</div>', unsafe_allow_html=True)
        renderizar_grupo(
            plano.contexto_periodo.titulo,
            plano.contexto_periodo.resumo,
            plano.contexto_periodo.itens,
        )

    with abas[2]:
        st.markdown('<div class="mini-aba-texto">Sugestões alinhadas ao estilo de viagem informado.</div>', unsafe_allow_html=True)
        st.markdown('<div class="grid-interesses-resultado">', unsafe_allow_html=True)
        for grupo in plano.interesses:
            renderizar_card_interesse(grupo, grupo.titulo, grupo.resumo, grupo.itens)
        st.markdown('</div>', unsafe_allow_html=True)

    with abas[3]:
        st.markdown('<div class="mini-aba-texto">Cuidados úteis para uma viagem mais tranquila e segura.</div>', unsafe_allow_html=True)
        renderizar_grupo(
            plano.dicas_seguranca.titulo,
            plano.dicas_seguranca.resumo,
            plano.dicas_seguranca.itens,
        )

    with abas[4]:
        st.markdown('<div class="mini-aba-texto">Uma jornada sugerida do amanhecer até a noite para cada dia da viagem.</div>', unsafe_allow_html=True)
        for dia in plano.roteiro_dia_a_dia:
            with st.expander(f"Dia {dia.dia} - {dia.data} • {dia.tema_dia}", expanded=dia.dia == 1):
                renderizar_timeline_dia(dia)

    with abas[5]:
        st.markdown('<div class="mini-aba-texto">Notas finais para conferência e preparação antes da viagem.</div>', unsafe_allow_html=True)
        st.markdown(f"**Perfil de viajantes:** {plano.perfil_viajantes}")
        st.markdown(f"**Aviso importante:** {plano.aviso_importante}")

        if plano.observacoes_gerais:
            st.markdown("### Observações gerais")
            for observacao in plano.observacoes_gerais:
                st.markdown(f"- {observacao}")

        if plano.fontes_recomendadas:
            st.markdown("### Fontes recomendadas para validação final")
            for fonte in plano.fontes_recomendadas:
                st.markdown(f"- {fonte}")


st.set_page_config(page_title=configuracao.nome_aplicacao, layout="wide")
aplicar_estilos()

st.markdown(
    """
    <div class="bloco-hero">
        <h1>🧳 Minha Próxima Viagem</h1>
        <p>
            Transforme sua pesquisa de viagem em um roteiro inspirador: informe o destino, o período e seu estilo,
            e receba um guia prático com clima, cultura, gastronomia, segurança e programação dia a dia para o destino e arredores quando isso fizer sentido.
        </p>
        <div class="hero-badges">
            <span class="hero-badge">☀️ Clima e contexto</span>
            <span class="hero-badge">🍽️ Gastronomia local</span>
            <span class="hero-badge">🗺️ Roteiro dia a dia</span>
            <span class="hero-badge">🔎 Dicas por interesse</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-card">
            <h4>✈️ Como funciona</h4>
            <p>1. Informe o destino e o período da viagem.<br>2. Ajuste o perfil dos viajantes e seus interesses.<br>3. Clique em <strong>Buscar</strong> para receber um mini planejamento completo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="sidebar-card">
            <h4>💡 Dicas rápidas</h4>
            <p>• Sem interesses marcados, a aplicação sugere todos brevemente.<br>• Com crianças, o roteiro considera um ritmo mais adequado.<br>• O plano pode incluir cidades e regiões próximas quando isso enriquecer a viagem.<br>• Confirme horários, clima e valores em canais oficiais.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## 🔌 Backend e IA")
    backend_ok, mensagem_backend, health_backend = cliente_api.verificar_backend()
    if not backend_ok:
        st.error(mensagem_backend)
        st.caption(f"URL configurada do backend: {configuracao.api_backend_url}")
    else:
        st.success("Backend FastAPI disponível.")
        st.caption(f"URL do backend: {configuracao.api_backend_url}")
        if health_backend and health_backend.get("gemini_configurado"):
            st.success("Integração com Gemini pronta para uso no backend.")
        else:
            st.warning("O backend está ativo, mas a chave do Gemini parece não estar configurada corretamente.")


data_inicio_padrao = date.today() + timedelta(days=30)
data_fim_padrao = data_inicio_padrao + timedelta(days=4)
nivel_detalhamento_padrao = normalizar_nivel_detalhamento(configuracao.planejamento_nivel_detalhamento_padrao)

renderizar_bloco_inspiracao()

st.markdown('<div class="bloco-formulario">', unsafe_allow_html=True)
with st.form("form_planejamento"):
    st.markdown('<div class="bloco-secao">', unsafe_allow_html=True)
    st.markdown("### 📅 Informações obrigatórias")
    st.markdown(
        '<div class="texto-apoio">Escolha o período da viagem e informe o destino desejado. O planejamento pode considerar arredores e bate-voltas plausíveis sem perder o foco do destino principal.</div>',
        unsafe_allow_html=True,
    )
    col_data_inicio, col_data_fim, col_destino = st.columns([1, 1, 2])
    data_inicio = col_data_inicio.date_input("Data início", value=data_inicio_padrao, format="DD/MM/YYYY")
    data_fim = col_data_fim.date_input("Data fim", value=data_fim_padrao, format="DD/MM/YYYY")
    destino = col_destino.text_input("Destino", placeholder="Ex.: Lisboa, Portugal")
    st.caption(f"Período selecionado: {formatar_data_br(data_inicio)} até {formatar_data_br(data_fim)}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="bloco-secao">', unsafe_allow_html=True)
    st.markdown("### 👨‍👩‍👧 Perfil dos viajantes")
    st.markdown('<div class="texto-apoio">Preencha quantos adultos e crianças participarão da viagem.</div>', unsafe_allow_html=True)
    col_adultos, col_criancas = st.columns(2)
    quantidade_adultos = int(col_adultos.number_input("Quantidade de adultos", min_value=0, value=2, step=1))
    quantidade_criancas = int(col_criancas.number_input("Quantidade de crianças", min_value=0, value=0, step=1))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="bloco-secao">', unsafe_allow_html=True)
    st.markdown("### 🎯 Interesses")
    st.markdown(
        '<div class="texto-apoio">Selecione os estilos de viagem mais relevantes. Se nada for marcado, a aplicação sugere todos brevemente.</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    aventureiro = col1.checkbox("Aventureiro", value=False)
    economico = col2.checkbox("Econômico", value=False)
    gastronomico = col3.checkbox("Gastronômico", value=False)
    cultural = col1.checkbox("Cultural", value=False)
    relaxamento = col2.checkbox("Relaxamento", value=False)
    vida_noturna = col3.checkbox("Vida noturna", value=False)
    ecoturismo_sustentavel = st.checkbox("Ecoturismo/Sustentável", value=False)
    renderizar_chips_interesses(
        {
            "Aventureiro": aventureiro,
            "Econômico": economico,
            "Gastronômico": gastronomico,
            "Cultural": cultural,
            "Relaxamento": relaxamento,
            "Vida noturna": vida_noturna,
            "Ecoturismo/Sustentável": ecoturismo_sustentavel,
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="bloco-secao">', unsafe_allow_html=True)
    st.markdown("### ✨ Nível de detalhamento")
    st.markdown(
        '<div class="texto-apoio">Escolha se o plano deve ser mais direto, equilibrado ou mais rico em contexto e sugestões.</div>',
        unsafe_allow_html=True,
    )
    nivel_detalhamento = st.select_slider(
        "Detalhamento do plano",
        options=_NIVEIS_DETALHAMENTO,
        value=nivel_detalhamento_padrao if nivel_detalhamento_padrao in _NIVEIS_DETALHAMENTO else "equilibrado",
        format_func=formatar_rotulo_nivel_detalhamento,
    )
    parametros_nivel = obter_parametros_detalhamento(nivel_detalhamento)
    st.caption(
        f"{formatar_rotulo_nivel_detalhamento(nivel_detalhamento)}: {obter_descricao_nivel_detalhamento(nivel_detalhamento)}. "
        f"Até {parametros_nivel['itens_grupo']} tópicos por grupo e até {parametros_nivel['fontes']} fontes recomendadas."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    buscar = st.form_submit_button("Buscar planejamento", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


if buscar:
    if data_inicio > data_fim:
        st.error("A data início não pode ser posterior à data fim. Corrija o período informado.")
    elif not destino.strip():
        st.error("O campo Destino é obrigatório.")
    else:
        try:
            solicitacao = SolicitacaoPlanoViagem(
                data_inicio=data_inicio,
                data_fim=data_fim,
                destino=destino,
                quantidade_adultos=quantidade_adultos,
                quantidade_criancas=quantidade_criancas,
                nivel_detalhamento=nivel_detalhamento,
                interesses=InteressesViagem(
                    aventureiro=aventureiro,
                    economico=economico,
                    gastronomico=gastronomico,
                    cultural=cultural,
                    relaxamento=relaxamento,
                    vida_noturna=vida_noturna,
                    ecoturismo_sustentavel=ecoturismo_sustentavel,
                ),
            )

            st.markdown(
                '<div class="bloco-carregando">🌍 Preparando um roteiro especial para você... buscando clima, cultura, experiências e dicas úteis do destino.</div>',
                unsafe_allow_html=True,
            )

            with st.spinner("Enviando os dados ao backend e montando o seu planejamento..."):
                plano = cliente_api.planejar_viagem(solicitacao)

            renderizar_resultado(plano)
        except ErroIntegracaoIA as erro:
            st.error(erro.mensagem_publica)
            if erro.retry_delay_segundos is not None:
                st.info(
                    f"Sugestão: aguarde cerca de {erro.retry_delay_segundos} segundo(s) antes de tentar novamente."
                )
        except ErroPlanejamentoViagem as erro:
            st.error(str(erro))
        except Exception:
            st.error("Ocorreu um erro inesperado ao gerar o planejamento. Tente novamente em alguns instantes.")
