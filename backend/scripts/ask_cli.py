from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

from backend.minha_proxima_viagem.modelos import InteressesViagem, SolicitacaoPlanoViagem
from backend.minha_proxima_viagem.servico_planejamento import instanciar_servico_planejamento


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera um mini planejamento de viagem no terminal.")
    parser.add_argument("--data-inicio", required=True, help="Data de início no formato AAAA-MM-DD.")
    parser.add_argument("--data-fim", required=True, help="Data fim no formato AAAA-MM-DD.")
    parser.add_argument("--destino", required=True, help="Destino da viagem.")
    parser.add_argument("--adultos", type=int, default=1, help="Quantidade de adultos.")
    parser.add_argument("--criancas", type=int, default=0, help="Quantidade de crianças.")
    parser.add_argument("--aventureiro", action="store_true")
    parser.add_argument("--economico", action="store_true")
    parser.add_argument("--gastronomico", action="store_true")
    parser.add_argument("--cultural", action="store_true")
    parser.add_argument("--relaxamento", action="store_true")
    parser.add_argument("--vida-noturna", dest="vida_noturna", action="store_true")
    parser.add_argument("--ecoturismo", dest="ecoturismo_sustentavel", action="store_true")
    parser.add_argument(
        "--nivel-detalhamento",
        choices=["enxuto", "equilibrado", "detalhado", "compacto", "padrao"],
        default="equilibrado",
        help="Controla quão resumido ou aprofundado será o planejamento. Também aceita os aliases legados compacto/padrao.",
    )
    return parser


def main() -> int:
    args = criar_parser().parse_args()

    solicitacao = SolicitacaoPlanoViagem(
        data_inicio=args.data_inicio,
        data_fim=args.data_fim,
        destino=args.destino,
        quantidade_adultos=args.adultos,
        quantidade_criancas=args.criancas,
        nivel_detalhamento=args.nivel_detalhamento,
        interesses=InteressesViagem(
            aventureiro=args.aventureiro,
            economico=args.economico,
            gastronomico=args.gastronomico,
            cultural=args.cultural,
            relaxamento=args.relaxamento,
            vida_noturna=args.vida_noturna,
            ecoturismo_sustentavel=args.ecoturismo_sustentavel,
        ),
    )

    servico = instanciar_servico_planejamento()
    plano = servico.gerar_plano(solicitacao)
    print(json.dumps(plano.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
