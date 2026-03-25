from __future__ import annotations

import json
import re
from typing import Any

import google.generativeai as genai

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover - fallback para ambientes sem a dependência opcional
    repair_json = None


def _reparar_json_se_disponivel(texto: str) -> str | None:
    if repair_json is None:
        return None

    try:
        return repair_json(texto)
    except Exception:
        return None


def _sanitizar_texto_json(texto: str) -> str:
    texto_limpo = texto.strip()
    texto_limpo = texto_limpo.replace("\ufeff", "")
    return texto_limpo

from backend.minha_proxima_viagem.configuracao import ConfiguracaoAplicacao, obter_configuracao
from backend.minha_proxima_viagem.excecoes import ErroIntegracaoIA
from backend.minha_proxima_viagem.logs import obter_logger


class ClienteGemini:
    def __init__(self, configuracao: ConfiguracaoAplicacao | None = None) -> None:
        self.configuracao = configuracao or obter_configuracao()
        self.logger = obter_logger(__name__)

    def gerar_json(self, prompt_sistema: str, prompt_usuario: str) -> dict[str, Any]:
        if not self.configuracao.gemini_configurado:
            raise ErroIntegracaoIA(
                "A integração com o Gemini não está configurada corretamente. Informe uma chave válida em GEMINI_API_KEY no arquivo .env.",
                status_code=503,
                codigo_erro="gemini_nao_configurado",
            )

        genai.configure(api_key=self.configuracao.gemini_api_key)
        ultima_excecao: ErroIntegracaoIA | None = None

        for modelo_nome in self.configuracao.gemini_modelos_candidatos:
            modelo = self._criar_modelo(modelo_nome, prompt_sistema)
            conteudo = self._montar_conteudo_solicitacao(modelo_nome, prompt_sistema, prompt_usuario)
            generation_config = self._montar_generation_config(modelo_nome)

            self.logger.info("Solicitando plano ao Gemini com modelo %s", modelo_nome)

            try:
                resposta = modelo.generate_content(
                    conteudo,
                    generation_config=generation_config,
                    request_options={"timeout": self.configuracao.gemini_timeout_segundos},
                )
                texto = (getattr(resposta, "text", "") or "").strip()
                if not texto:
                    texto = self._extrair_texto_da_resposta(resposta)

                if not texto:
                    raise ErroIntegracaoIA(
                        "O Gemini retornou uma resposta vazia. Tente novamente em alguns instantes.",
                        mensagem_tecnica=f"Resposta vazia recebida do Gemini no modelo {modelo_nome}.",
                        status_code=502,
                        codigo_erro="gemini_resposta_vazia",
                    )

                dados = self._converter_json(texto)
                if isinstance(dados, dict):
                    dados.setdefault(
                        "__metadados_resposta",
                        {
                            "modelo_utilizado": modelo_nome,
                            "familia_modelo": self._obter_familia_modelo(modelo_nome),
                        },
                    )
                return dados
            except ErroIntegracaoIA as erro:
                ultima_excecao = erro
                if erro.codigo_erro in {
                    "gemini_quota_excedida",
                    "gemini_modelo_indisponivel",
                    "gemini_json_invalido",
                    "gemini_json_nao_encontrado",
                    "gemini_resposta_vazia",
                }:
                    self.logger.warning(
                        "Tentando próximo modelo Gemini após falha controlada | modelo=%s | codigo=%s",
                        modelo_nome,
                        erro.codigo_erro,
                    )
                    continue
                raise
            except Exception as erro:
                ultima_excecao = self._classificar_erro_integracao(erro, modelo_nome)
                if ultima_excecao.codigo_erro in {
                    "gemini_quota_excedida",
                    "gemini_modelo_indisponivel",
                    "gemini_json_invalido",
                    "gemini_json_nao_encontrado",
                    "gemini_resposta_vazia",
                }:
                    self.logger.warning(
                        "Tentando próximo modelo Gemini após exceção do provedor | modelo=%s | codigo=%s",
                        modelo_nome,
                        ultima_excecao.codigo_erro,
                    )
                    continue
                raise ultima_excecao from erro

        if ultima_excecao is not None:
            raise ultima_excecao

        raise ErroIntegracaoIA(
            "Não foi possível consultar o Gemini agora. Tente novamente em alguns instantes.",
            mensagem_tecnica="Nenhum modelo candidato do Gemini pôde ser utilizado.",
            status_code=502,
            codigo_erro="gemini_sem_modelo_disponivel",
        )

    @staticmethod
    def _eh_modelo_gemma(modelo_nome: str) -> bool:
        return "/gemma-" in modelo_nome.casefold()

    @classmethod
    def _obter_familia_modelo(cls, modelo_nome: str) -> str:
        return "Gemma" if cls._eh_modelo_gemma(modelo_nome) else "Gemini"

    def _criar_modelo(self, modelo_nome: str, prompt_sistema: str) -> genai.GenerativeModel:
        if self._eh_modelo_gemma(modelo_nome):
            return genai.GenerativeModel(model_name=modelo_nome)

        return genai.GenerativeModel(
            model_name=modelo_nome,
            system_instruction=prompt_sistema,
        )

    def _montar_conteudo_solicitacao(self, modelo_nome: str, prompt_sistema: str, prompt_usuario: str) -> str:
        if self._eh_modelo_gemma(modelo_nome):
            return f"{prompt_sistema}\n\n{prompt_usuario}"
        return prompt_usuario

    def _montar_generation_config(self, modelo_nome: str) -> genai.types.GenerationConfig:
        parametros: dict[str, Any] = {
            "temperature": self.configuracao.gemini_temperatura,
            "max_output_tokens": self.configuracao.gemini_max_tokens,
        }
        if not self._eh_modelo_gemma(modelo_nome):
            parametros["response_mime_type"] = "application/json"
        return genai.types.GenerationConfig(**parametros)

    def _extrair_texto_da_resposta(self, resposta: Any) -> str:
        partes: list[str] = []
        for candidato in getattr(resposta, "candidates", []) or []:
            conteudo = getattr(candidato, "content", None)
            for parte in getattr(conteudo, "parts", []) or []:
                texto = getattr(parte, "text", "")
                if texto:
                    partes.append(texto)
        return "\n".join(partes).strip()

    def _converter_json(self, texto: str) -> dict[str, Any]:
        texto_sanitizado = _sanitizar_texto_json(texto)
        try:
            dados = json.loads(texto_sanitizado)
            if isinstance(dados, dict):
                return dados
        except json.JSONDecodeError:
            pass

        bloco_json = self._extrair_bloco_json(texto_sanitizado)
        if bloco_json is None:
            raise ErroIntegracaoIA(
                "A resposta da IA veio em um formato inesperado. Tente novamente em alguns instantes.",
                mensagem_tecnica="Não foi possível interpretar a resposta da IA como JSON válido.",
                status_code=502,
                codigo_erro="gemini_json_nao_encontrado",
            )

        candidatos_reparo = self._gerar_candidatos_json(bloco_json)
        for candidato in candidatos_reparo:
            try:
                dados = json.loads(candidato)
                if isinstance(dados, dict):
                    return dados
            except json.JSONDecodeError:
                continue

        try:
            dados = json.loads(bloco_json)
            if isinstance(dados, dict):
                return dados
        except json.JSONDecodeError as erro:
            bloco_reparado = _reparar_json_se_disponivel(bloco_json)
            if bloco_reparado is not None:
                try:
                    dados = json.loads(bloco_reparado)
                    if isinstance(dados, dict):
                        return dados
                except Exception:
                    pass

            raise ErroIntegracaoIA(
                "A resposta da IA veio com dados inconsistentes. Tente novamente em alguns instantes.",
                mensagem_tecnica=(
                    f"A IA retornou um JSON inválido. tamanho={len(bloco_json)} | "
                    f"truncado={self._parece_json_truncado(bloco_json)} | trecho={bloco_json[:300]}"
                ),
                status_code=502,
                codigo_erro="gemini_json_invalido",
            ) from erro

        raise ErroIntegracaoIA(
            "A resposta da IA veio em um formato inesperado. Tente novamente em alguns instantes.",
            mensagem_tecnica=f"A IA retornou JSON não estruturado como objeto. Trecho recebido: {bloco_json[:300]}",
            status_code=502,
            codigo_erro="gemini_json_invalido",
        )

    def _gerar_candidatos_json(self, bloco_json: str) -> list[str]:
        candidatos: list[str] = []
        bloco_sanitizado = _sanitizar_texto_json(bloco_json)
        candidatos.append(bloco_sanitizado)

        if self._parece_json_truncado(bloco_sanitizado):
            candidato_balanceado = self._balancear_json_truncado(bloco_sanitizado)
            if candidato_balanceado and candidato_balanceado not in candidatos:
                candidatos.append(candidato_balanceado)

        bloco_sem_virgula_final = self._remover_virgulas_finais(bloco_sanitizado)
        if bloco_sem_virgula_final not in candidatos:
            candidatos.append(bloco_sem_virgula_final)

        if self._parece_json_truncado(bloco_sem_virgula_final):
            candidato_balanceado = self._balancear_json_truncado(bloco_sem_virgula_final)
            if candidato_balanceado and candidato_balanceado not in candidatos:
                candidatos.append(candidato_balanceado)

        return candidatos

    @staticmethod
    def _remover_virgulas_finais(texto: str) -> str:
        return re.sub(r",\s*([}\]])", r"\1", texto)

    @staticmethod
    def _parece_json_truncado(texto: str) -> bool:
        if not texto:
            return False
        return texto.count("{") > texto.count("}") or texto.count("[") > texto.count("]")

    def _balancear_json_truncado(self, texto: str) -> str | None:
        if not self._parece_json_truncado(texto):
            return None

        texto_balanceado = texto.rstrip()
        texto_balanceado = re.sub(r',\s*$', '', texto_balanceado)

        while texto_balanceado and texto_balanceado[-1] in {',', ':', '"', '\\'}:
            texto_balanceado = texto_balanceado[:-1].rstrip()

        diferenca_colchetes = texto_balanceado.count("[") - texto_balanceado.count("]")
        if diferenca_colchetes > 0:
            texto_balanceado += "]" * diferenca_colchetes

        diferenca_chaves = texto_balanceado.count("{") - texto_balanceado.count("}")
        if diferenca_chaves > 0:
            texto_balanceado += "}" * diferenca_chaves

        return self._remover_virgulas_finais(texto_balanceado)

    def _classificar_erro_integracao(self, erro: Exception, modelo_nome: str | None = None) -> ErroIntegracaoIA:
        mensagem_tecnica = str(erro).strip() or repr(erro)
        mensagem_normalizada = mensagem_tecnica.lower()
        retry_delay_segundos = self._extrair_retry_delay_segundos(erro, mensagem_tecnica)
        modelo_referencia = modelo_nome or self.configuracao.gemini_modelo

        if self._eh_erro_autenticacao(mensagem_normalizada):
            return ErroIntegracaoIA(
                "A chave da API do Gemini parece inválida ou sem permissão. Revise GEMINI_API_KEY e tente novamente.",
                mensagem_tecnica=mensagem_tecnica,
                status_code=401,
                codigo_erro="gemini_api_key_invalida",
            )

        if self._eh_erro_modelo_indisponivel(mensagem_normalizada):
            self.logger.warning(
                "Modelo Gemini indisponível para a conta atual | modelo=%s | detalhe=%s",
                modelo_referencia,
                mensagem_tecnica,
            )
            return ErroIntegracaoIA(
                "O modelo Gemini selecionado não está disponível para esta conta no momento. Tentando outro modelo compatível.",
                mensagem_tecnica=mensagem_tecnica,
                status_code=503,
                codigo_erro="gemini_modelo_indisponivel",
            )

        if self._eh_erro_quota_ou_rate_limit(erro, mensagem_normalizada):
            mensagem_publica = (
                "O limite de uso da API do Gemini foi atingido no momento. "
                "Aguarde um pouco e tente novamente."
            )
            if retry_delay_segundos is not None:
                mensagem_publica = (
                    f"O limite de uso da API do Gemini foi atingido no momento. "
                    f"Aguarde cerca de {retry_delay_segundos} segundo(s) e tente novamente."
                )

            self.logger.warning(
                "Gemini retornou quota/rate limit | modelo=%s | retry_delay_segundos=%s | detalhe=%s",
                modelo_referencia,
                retry_delay_segundos,
                mensagem_tecnica,
            )

            return ErroIntegracaoIA(
                mensagem_publica,
                mensagem_tecnica=mensagem_tecnica,
                status_code=429,
                codigo_erro="gemini_quota_excedida",
                retry_delay_segundos=retry_delay_segundos,
            )

        self.logger.error(
            "Falha genérica ao consultar Gemini | modelo=%s | detalhe=%s",
            modelo_referencia,
            mensagem_tecnica,
        )

        return ErroIntegracaoIA(
            "Não foi possível consultar o Gemini agora. Tente novamente em alguns instantes.",
            mensagem_tecnica=mensagem_tecnica,
            status_code=502,
            codigo_erro="gemini_falha_consulta",
        )

    @staticmethod
    def _eh_erro_quota_ou_rate_limit(erro: Exception, mensagem_normalizada: str) -> bool:
        codigo = getattr(erro, "code", None)
        status = getattr(erro, "status_code", None)

        indicadores = [
            "429",
            "quota exceeded",
            "rate limit",
            "resource_exhausted",
            "too many requests",
            "retry_delay",
            "generate_content_free_tier",
        ]

        return codigo == 429 or status == 429 or any(indicador in mensagem_normalizada for indicador in indicadores)

    @staticmethod
    def _eh_erro_modelo_indisponivel(mensagem_normalizada: str) -> bool:
        indicadores = [
            "not found for api version",
            "is not found",
            "does not exist",
            "unsupported model",
            "permission denied",
            "not available",
            "has no supported generation methods",
        ]
        return any(indicador in mensagem_normalizada for indicador in indicadores)

    @staticmethod
    def _eh_erro_autenticacao(mensagem_normalizada: str) -> bool:
        indicadores = [
            "api key not valid",
            "invalid api key",
            "permission denied: api key",
            "request had invalid authentication credentials",
            "unauthenticated",
        ]
        return any(indicador in mensagem_normalizada for indicador in indicadores)

    @staticmethod
    def _extrair_retry_delay_segundos(erro: Exception, mensagem_tecnica: str) -> int | None:
        possiveis_textos = [mensagem_tecnica]

        detalhes = getattr(erro, "details", None)
        if detalhes:
            possiveis_textos.append(str(detalhes))

        for texto in possiveis_textos:
            padroes = [
                r"retry in\s+(\d+(?:\.\d+)?)s",
                r"retry_delay\s*\{\s*seconds:\s*(\d+)",
                r"retry delay[^\d]*(\d+(?:\.\d+)?)",
                r"aguarde[^\d]*(\d+(?:\.\d+)?)\s*seg",
            ]
            for padrao in padroes:
                encontrado = re.search(padrao, texto, flags=re.IGNORECASE)
                if encontrado:
                    return max(1, int(float(encontrado.group(1))))

        return None

    @staticmethod
    def _extrair_bloco_json(texto: str) -> str | None:
        padrao_markdown = re.search(r"```json\s*(\{.*})\s*```", texto, flags=re.DOTALL | re.IGNORECASE)
        if padrao_markdown:
            return padrao_markdown.group(1)

        padrao_markdown_generico = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", texto, flags=re.DOTALL | re.IGNORECASE)
        if padrao_markdown_generico:
            return padrao_markdown_generico.group(1)

        inicio = texto.find("{")
        fim = texto.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            return texto[inicio : fim + 1]

        if inicio != -1:
            return texto[inicio:]

        inicio_lista = texto.find("[")
        fim_lista = texto.rfind("]")
        if inicio_lista != -1 and fim_lista != -1 and fim_lista > inicio_lista:
            return texto[inicio_lista : fim_lista + 1]

        return None

