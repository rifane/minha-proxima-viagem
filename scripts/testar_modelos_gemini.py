from __future__ import annotations

import os
import sys
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from minha_proxima_viagem.configuracao import obter_configuracao


MODELOS_PADRAO = [
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.5-flash",
    "models/gemini-3.1-flash-lite-preview",
    "models/gemini-3-flash-preview",
    "models/gemini-flash-lite-latest",
    "models/gemma-3-4b-it",
]


def main() -> int:
    load_dotenv(root_dir / ".env")
    configuracao = obter_configuracao()

    if not configuracao.gemini_configurado:
        print("GEMINI_API_KEY ausente, inválida ou em formato placeholder no arquivo .env.")
        return 1

    genai.configure(api_key=configuracao.gemini_api_key)

    print("\n=== TESTE REAL DE MODELOS GEMINI ===\n")
    for nome in MODELOS_PADRAO:
        print("=" * 90)
        print(f"Testando: {nome}")
        try:
            model = genai.GenerativeModel(
                model_name=nome,
                system_instruction="Responda em português do Brasil e seja extremamente breve.",
            )
            resposta = model.generate_content(
                "Responda apenas com a palavra OK.",
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=10,
                ),
                request_options={"timeout": int(os.getenv("GEMINI_TIMEOUT_SEGUNDOS", "45"))},
            )
            texto = (getattr(resposta, "text", "") or "").strip()
            print(f"SUCESSO: {texto!r}")
        except Exception as erro:
            print(f"ERRO: {type(erro).__name__}: {erro}")

    print("\nFim dos testes.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

