from __future__ import annotations

from contextlib import nullcontext
from typing import Any

import httpx

from backend.minha_proxima_viagem.configuracao import ConfiguracaoAplicacao, obter_configuracao
from backend.minha_proxima_viagem.excecoes import ErroIntegracaoIA, ErroPlanejamentoViagem
from backend.minha_proxima_viagem.modelos import PlanoViagemGerado, SolicitacaoPlanoViagem


class ClienteAPIPlanejamento:
    def __init__(
        self,
        configuracao: ConfiguracaoAplicacao | None = None,
        cliente_http: httpx.Client | None = None,
    ) -> None:
        self.configuracao = configuracao or obter_configuracao()
        self._cliente_http = cliente_http

    @property
    def base_url(self) -> str:
        return self.configuracao.api_backend_url.rstrip("/")

    def obter_health(self) -> dict[str, Any]:
        resposta = self._executar_requisicao("GET", "/health")
        return self._converter_json(resposta)

    def verificar_backend(self) -> tuple[bool, str, dict[str, Any] | None]:
        try:
            dados = self.obter_health()
        except ErroPlanejamentoViagem as erro:
            return False, str(erro), None

        return True, "Backend disponível.", dados

    def planejar_viagem(self, solicitacao: SolicitacaoPlanoViagem) -> PlanoViagemGerado:
        resposta = self._executar_requisicao(
            "POST",
            "/planejar-viagem",
            json=solicitacao.model_dump(mode="json"),
        )
        return PlanoViagemGerado.model_validate(self._converter_json(resposta))

    def _executar_requisicao(self, metodo: str, rota: str, **kwargs: Any) -> httpx.Response:
        gerenciador_cliente = nullcontext(self._cliente_http) if self._cliente_http else httpx.Client(
            base_url=self.base_url,
            timeout=self.configuracao.api_timeout_segundos,
        )

        try:
            with gerenciador_cliente as cliente:
                resposta = cliente.request(metodo, rota, **kwargs)
                resposta.raise_for_status()
                return resposta
        except httpx.ConnectError as erro:
            raise ErroPlanejamentoViagem(
                "Não foi possível alcançar o backend da aplicação. Inicie a API FastAPI e tente novamente."
            ) from erro
        except httpx.TimeoutException as erro:
            raise ErroPlanejamentoViagem(
                "O backend demorou mais do que o esperado para responder. Tente novamente em alguns instantes."
            ) from erro
        except httpx.HTTPStatusError as erro:
            raise self._mapear_erro_http(erro.response) from erro
        except httpx.HTTPError as erro:
            raise ErroPlanejamentoViagem(
                "Falha inesperada ao se comunicar com o backend da aplicação. Tente novamente."
            ) from erro

    @staticmethod
    def _converter_json(resposta: httpx.Response) -> dict[str, Any]:
        dados = resposta.json()
        if not isinstance(dados, dict):
            raise ErroPlanejamentoViagem("O backend retornou uma resposta em formato inesperado.")
        return dados

    def _mapear_erro_http(self, resposta: httpx.Response) -> ErroPlanejamentoViagem:
        try:
            dados = resposta.json()
        except Exception:
            dados = {}

        if not isinstance(dados, dict):
            dados = {}

        detalhe = self._extrair_mensagem_erro(dados) or "O backend retornou um erro ao processar a solicitação."
        codigo_erro = str(dados.get("codigo_erro") or "")
        retry_delay = dados.get("retry_delay_segundos")
        retry_delay_normalizado = int(retry_delay) if isinstance(retry_delay, int) else None

        if resposta.status_code in {429, 502, 503} or codigo_erro.startswith("gemini_"):
            return ErroIntegracaoIA(
                detalhe,
                mensagem_tecnica=f"HTTP {resposta.status_code}: {dados}",
                status_code=resposta.status_code,
                codigo_erro=codigo_erro or "backend_integracao_ia",
                retry_delay_segundos=retry_delay_normalizado,
            )

        return ErroPlanejamentoViagem(detalhe)

    @staticmethod
    def _extrair_mensagem_erro(dados: dict[str, Any]) -> str:
        detalhe = dados.get("detalhe")
        if isinstance(detalhe, str) and detalhe.strip():
            return detalhe.strip()
        if isinstance(detalhe, list) and detalhe:
            primeiro = detalhe[0]
            if isinstance(primeiro, dict):
                mensagem = primeiro.get("msg") or primeiro.get("message")
                if isinstance(mensagem, str) and mensagem.strip():
                    return mensagem.strip()
        return ""


def instanciar_cliente_api_planejamento() -> ClienteAPIPlanejamento:
    return ClienteAPIPlanejamento()

