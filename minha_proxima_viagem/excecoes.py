from __future__ import annotations


class ErroPlanejamentoViagem(Exception):
    """Exceção base da aplicação de planejamento de viagens."""


class ErroValidacaoViagem(ErroPlanejamentoViagem):
    """Erro para inconsistências de entrada do usuário."""


class ErroIntegracaoIA(ErroPlanejamentoViagem):
    """Erro para falhas de comunicação ou resposta da IA."""

    def __init__(
        self,
        mensagem_publica: str,
        *,
        mensagem_tecnica: str | None = None,
        status_code: int = 502,
        codigo_erro: str = "falha_integracao_ia",
        retry_delay_segundos: int | None = None,
    ) -> None:
        super().__init__(mensagem_publica)
        self.mensagem_publica = mensagem_publica
        self.mensagem_tecnica = mensagem_tecnica or mensagem_publica
        self.status_code = status_code
        self.codigo_erro = codigo_erro
        self.retry_delay_segundos = retry_delay_segundos

    def para_resposta(self) -> dict[str, object]:
        resposta: dict[str, object] = {
            "detalhe": self.mensagem_publica,
            "codigo_erro": self.codigo_erro,
        }
        if self.retry_delay_segundos is not None:
            resposta["retry_delay_segundos"] = self.retry_delay_segundos
        return resposta

