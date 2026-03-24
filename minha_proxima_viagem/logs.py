from __future__ import annotations

import logging

from minha_proxima_viagem.configuracao import obter_configuracao


_FORMATO_LOG = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configurar_logs() -> None:
    configuracao = obter_configuracao()
    nivel = getattr(logging, configuracao.nivel_log, logging.INFO)

    if logging.getLogger().handlers:
        logging.getLogger().setLevel(nivel)
        return

    logging.basicConfig(level=nivel, format=_FORMATO_LOG)


def obter_logger(nome: str) -> logging.Logger:
    configurar_logs()
    return logging.getLogger(nome)

