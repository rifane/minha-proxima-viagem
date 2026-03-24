from __future__ import annotations

import sys
from pathlib import Path

import google.generativeai as genai

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from minha_proxima_viagem.configuracao import obter_configuracao


def main() -> int:
    configuracao = obter_configuracao()
    if not configuracao.gemini_configurado:
        print("GEMINI_API_KEY não configurada no arquivo .env.")
        return 1

    genai.configure(api_key=configuracao.gemini_api_key)

    print("\n=== MODELOS GEMINI DISPONÍVEIS ===\n")

    total = 0
    try:
        for modelo in genai.list_models():
            total += 1
            nome = getattr(modelo, "name", None)
            metodos = getattr(modelo, "supported_generation_methods", None)
            print(f"- {nome} | methods={metodos}")
    except Exception as erro:
        print(f"Erro ao listar modelos: {erro!r}")
        return 1

    print(f"\nTOTAL: {total}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
