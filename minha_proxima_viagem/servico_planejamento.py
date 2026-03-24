from __future__ import annotations

import json
import unicodedata
from datetime import timedelta
from functools import lru_cache
from time import monotonic
from typing import Any

from minha_proxima_viagem.cliente_gemini import ClienteGemini
from minha_proxima_viagem.configuracao import ConfiguracaoAplicacao, obter_configuracao
from minha_proxima_viagem.logs import obter_logger
from minha_proxima_viagem.modelos import (
    GrupoConteudo,
    PlanoViagemGerado,
    SolicitacaoPlanoViagem,
    obter_parametros_detalhamento,
)
from minha_proxima_viagem.prompts import construir_prompt_usuario, obter_prompt_sistema


_MAPA_INTERESSES_FALLBACK = {
    "Aventureiro": "Busque experiências ao ar livre, com atenção ao preparo físico e às condições climáticas do período.",
    "Econômico": "Priorize atrações gratuitas, transporte público e restaurantes com bom custo-benefício.",
    "Gastronômico": "Combine mercados locais, pratos típicos, cafés e restaurantes em faixas variadas de preço.",
    "Cultural": "Inclua centros históricos, museus, feiras, visitas guiadas e contato com a identidade local.",
    "Relaxamento": "Reserve momentos de descanso, passeios leves e ambientes tranquilos durante a estadia.",
    "Vida noturna": "Pesquise regiões seguras, bares, eventos e alternativas compatíveis com o orçamento do grupo.",
    "Ecoturismo/Sustentável": "Considere parques, reservas, passeios responsáveis e práticas de turismo consciente.",
}

_MAPA_INTERESSES_NORMALIZADOS = {
    "aventureiro": "Aventureiro",
    "economico": "Econômico",
    "gastronomico": "Gastronômico",
    "gastronmico": "Gastronômico",
    "cultural": "Cultural",
    "relaxamento": "Relaxamento",
    "vida noturna": "Vida noturna",
    "ecoturismo/sustentavel": "Ecoturismo/Sustentável",
    "ecoturismo sustentavel": "Ecoturismo/Sustentável",
}

_MAPA_COMPLEMENTOS_GRUPOS = {
    "historia": [
        "Observe marcos históricos, arquitetura, praças, bairros antigos e símbolos que ajudam a entender a identidade local.",
        "Vale relacionar a história do destino com sua culinária, festas, sotaques e tradições que ainda permanecem no cotidiano.",
        "Centros culturais, museus, memoriais e visitas guiadas costumam aprofundar esse contexto para o viajante.",
        "Quando possível, combine o destino principal com bairros ou cidades próximas que complementem sua formação histórica.",
        "A história local costuma influenciar a forma de receber visitantes, os roteiros mais famosos e os hábitos da região.",
        "Procure referências oficiais de turismo cultural para confirmar atrações e horários antes de montar os passeios.",
        "Entender a origem econômica e social do destino ajuda a escolher experiências mais autênticas durante a viagem.",
    ],
    "periodo": [
        "Considere temperatura média, chance de chuva, sensação térmica e necessidade de roupas adequadas para o período.",
        "Verifique se a época costuma ter alta, média ou baixa temporada, pois isso altera preços, filas e necessidade de reservas.",
        "Feriados, festivais, feiras e eventos sazonais podem enriquecer a experiência ou exigir mais planejamento logístico.",
        "Avalie a duração do dia, horários de pôr do sol e ritmo do destino para distribuir melhor os passeios.",
        "No período escolhido, atrações ao ar livre podem exigir plano alternativo em caso de chuva, vento ou calor intenso.",
        "Para viagens familiares, confirme antecipadamente locais cobertos e pausas estratégicas compatíveis com o grupo.",
        "Em destinos muito procurados, vale reservar ingressos, restaurantes e deslocamentos com antecedência.",
    ],
    "seguranca": [
        "Prefira deslocamentos planejados entre regiões turísticas, especialmente à noite ou em horários de menor movimento.",
        "Mantenha documentos, celular, dinheiro e cartões organizados em locais seguros durante passeios longos.",
        "Acompanhe alertas de clima, mobilidade e orientações locais em canais oficiais antes de sair para atrações externas.",
        "Em saídas noturnas, confirme a melhor forma de retorno e evite improvisos em áreas pouco conhecidas.",
        "Se houver crianças, combine pontos de encontro, identificação e pausas regulares ao longo do dia.",
        "Antes de atividades pagas, confirme reputação do fornecedor, regras de cancelamento e necessidade de reserva.",
        "Tenha sempre uma alternativa de programação indoor para mudanças repentinas de clima ou lotação.",
    ],
}

_MAPA_COMPLEMENTOS_INTERESSES = {
    "Aventureiro": [
        "Busque trilhas, mirantes, passeios de bike, parques naturais ou atividades ao ar livre compatíveis com o preparo do grupo.",
        "Priorize experiências em horários com clima mais favorável e confirme nível de esforço físico antes de reservar.",
        "Inclua pausas para hidratação, protetor solar, calçados adequados e plano alternativo em caso de chuva.",
        "Se o destino permitir, avalie passeios guiados para ganhar segurança e contexto ambiental da região.",
        "Misture atividades intensas com momentos de descanso para evitar um roteiro cansativo demais.",
        "Dê preferência a operadores responsáveis e atrações com boa estrutura de apoio ao visitante.",
    ],
    "Econômico": [
        "Combine atrações gratuitas, caminhadas em bairros interessantes, parques urbanos e mirantes públicos.",
        "Use transporte público, deslocamentos a pé em regiões concentradas e horários fora do pico para economizar tempo e dinheiro.",
        "Procure menus executivos, mercados, feiras e cafés locais com bom custo-benefício ao longo do roteiro.",
        "Agrupe atrações próximas no mesmo dia para reduzir gastos com deslocamento.",
        "Verifique passes turísticos, combos de ingresso ou dias com entrada reduzida quando houver.",
        "Em destinos concorridos, reservar cedo pode evitar pagar mais caro por experiências semelhantes.",
    ],
    "Gastronômico": [
        "Inclua mercados, cafés, padarias, pratos típicos e restaurantes tradicionais para conhecer sabores locais em níveis diferentes de orçamento.",
        "Organize sugestões do mais econômico ao mais sofisticado, indicando o perfil de gasto de cada opção sem inventar preços exatos.",
        "Aproveite almoços executivos, feiras gastronômicas ou menus do dia para equilibrar custo e experiência.",
        "Reserve uma refeição mais especial para a noite ou para o dia de maior destaque do roteiro.",
        "Pesquise especialidades regionais e produtores locais para ir além dos lugares mais turísticos.",
        "Se o local for disputado, confirme reserva, fila e horário de funcionamento antes da visita.",
    ],
    "Cultural": [
        "Visite centro histórico, museus, igrejas, feiras, mercados e espaços que revelem a identidade local.",
        "Procure experiências que conectem patrimônio, arte, gastronomia e cotidiano da cidade.",
        "Eventos sazonais, apresentações, visitas guiadas e bairros tradicionais enriquecem a leitura cultural do destino.",
        "Reserve tempo para caminhar sem pressa e observar arquitetura, praças e costumes em diferentes períodos do dia.",
        "Sempre que possível, complemente a visita com materiais oficiais ou mediação cultural no local.",
        "Valorize também artesanato, música, manifestações populares e pequenos produtores da região.",
    ],
    "Relaxamento": [
        "Distribua o roteiro com parques, cafés tranquilos, orlas, spas, mirantes ou passeios leves em ritmo mais confortável.",
        "Intercale atrações intensas com janelas de descanso para evitar sensação de correria durante a viagem.",
        "Escolha horários de menor movimento para locais concorridos e experiências contemplativas.",
        "Considere finais de tarde agradáveis com pôr do sol, caminhada leve ou jantar sem pressa.",
        "Em viagens mais longas, mantenha ao menos um bloco mais flexível para descanso espontâneo.",
        "Combine conforto logístico com experiências autênticas, sem excesso de deslocamentos no mesmo dia.",
    ],
    "Vida noturna": [
        "Mapeie bairros ou regiões com movimento noturno, observando perfil do público e facilidade de retorno.",
        "Sugira opções do mais acessível ao mais sofisticado, como happy hour, bar com música, casa de shows ou coquetelaria.",
        "Prefira programações em áreas bem avaliadas e planeje o transporte de volta antes de sair.",
        "Equilibre noites mais intensas com manhãs seguintes de ritmo compatível para não desgastar o grupo.",
        "Considere alternativas culturais noturnas, como teatro, eventos, passeios iluminados ou concertos, quando fizer sentido.",
        "Verifique dress code, necessidade de reserva e horários de encerramento em canais oficiais ou redes do local.",
    ],
    "Ecoturismo/Sustentável": [
        "Prefira parques, reservas, trilhas sinalizadas e operadores comprometidos com turismo responsável.",
        "Respeite regras ambientais, limite de visitantes, descarte correto de resíduos e orientações dos guias.",
        "Priorize experiências que valorizem comunidades locais, educação ambiental e baixo impacto no destino.",
        "Leve água, proteção solar, roupas adequadas e planejamento de deslocamento para áreas naturais.",
        "Quando possível, combine natureza com produtores locais, gastronomia regional e práticas sustentáveis de consumo.",
        "Evite roteiros que concentrem deslocamentos excessivos sem necessidade, priorizando qualidade da experiência.",
    ],
}

_FRASES_GENERICAS_ROTEIRO = {
    "comece o dia com um cafe local e reconhecimento da regiao central do destino.",
    "reserve o periodo para a principal atracao sugerida, respeitando o perfil da viagem e o ritmo do grupo.",
    "finalize com uma refeicao tipica ou passeio leve em regiao movimentada e segura.",
}


class ServicoPlanejamentoViagem:
    def __init__(
        self,
        cliente_gemini: ClienteGemini | None = None,
        configuracao: ConfiguracaoAplicacao | None = None,
    ) -> None:
        self.configuracao = configuracao or obter_configuracao()
        self.cliente_gemini = cliente_gemini or ClienteGemini(configuracao=self.configuracao)
        if cliente_gemini is not None and hasattr(cliente_gemini, "configuracao"):
            self.configuracao = getattr(cliente_gemini, "configuracao")
        self.logger = obter_logger(__name__)
        self._cache_planos: dict[str, tuple[float, PlanoViagemGerado]] = {}

    def gerar_plano(self, solicitacao: SolicitacaoPlanoViagem) -> PlanoViagemGerado:
        self.logger.info(
            "Gerando plano de viagem para destino=%s periodo=%s",
            solicitacao.destino,
            solicitacao.periodo_formatado,
        )

        plano_em_cache = self._obter_do_cache(solicitacao)
        if plano_em_cache is not None:
            self.logger.info("Plano recuperado do cache para %s", solicitacao.destino)
            return plano_em_cache

        prompt_sistema = obter_prompt_sistema()
        prompt_usuario = construir_prompt_usuario(solicitacao)
        resposta = self.cliente_gemini.gerar_json(prompt_sistema, prompt_usuario)
        resposta_normalizada = self._normalizar_resposta(solicitacao, resposta)
        plano = PlanoViagemGerado.model_validate(resposta_normalizada)
        self._salvar_no_cache(solicitacao, plano)

        self.logger.info("Plano gerado com sucesso para %s", plano.destino)
        return plano

    def _obter_do_cache(self, solicitacao: SolicitacaoPlanoViagem) -> PlanoViagemGerado | None:
        if self.configuracao.cache_ttl_segundos <= 0:
            return None

        self._remover_expirados_do_cache()
        chave = self._gerar_chave_cache(solicitacao)
        entrada = self._cache_planos.get(chave)
        if entrada is None:
            return None

        _, plano = entrada
        plano_em_cache = plano.model_copy(deep=True)
        plano_em_cache.origem_cache = True
        return plano_em_cache

    def _salvar_no_cache(self, solicitacao: SolicitacaoPlanoViagem, plano: PlanoViagemGerado) -> None:
        if self.configuracao.cache_ttl_segundos <= 0 or self.configuracao.cache_max_entradas <= 0:
            return

        self._remover_expirados_do_cache()
        self._ajustar_limite_cache()
        chave = self._gerar_chave_cache(solicitacao)
        plano_para_cache = plano.model_copy(deep=True)
        plano_para_cache.origem_cache = False
        self._cache_planos[chave] = (monotonic(), plano_para_cache)

    def _remover_expirados_do_cache(self) -> None:
        ttl = self.configuracao.cache_ttl_segundos
        if ttl <= 0 or not self._cache_planos:
            return

        agora = monotonic()
        chaves_expiradas = [
            chave
            for chave, (instante, _) in self._cache_planos.items()
            if (agora - instante) > ttl
        ]
        for chave in chaves_expiradas:
            self._cache_planos.pop(chave, None)

    def _ajustar_limite_cache(self) -> None:
        max_entradas = self.configuracao.cache_max_entradas
        if max_entradas <= 0:
            self._cache_planos.clear()
            return

        while len(self._cache_planos) >= max_entradas:
            chave_mais_antiga = min(self._cache_planos, key=lambda chave: self._cache_planos[chave][0])
            self._cache_planos.pop(chave_mais_antiga, None)

    @staticmethod
    def _gerar_chave_cache(solicitacao: SolicitacaoPlanoViagem) -> str:
        return json.dumps(solicitacao.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)

    def _normalizar_resposta(
        self,
        solicitacao: SolicitacaoPlanoViagem,
        resposta: dict[str, Any],
    ) -> dict[str, Any]:
        metadados_resposta = resposta.get("__metadados_resposta") if isinstance(resposta, dict) else None
        roteiro = self._normalizar_roteiro(
            solicitacao,
            resposta.get("roteiro_dia_a_dia") or resposta.get("roteiro") or [],
        )

        interesses = self._normalizar_interesses(solicitacao, resposta.get("interesses") or [])
        if not interesses:
            interesses = self._gerar_interesses_fallback(solicitacao)

        resposta_normalizada = {
            "destino": resposta.get("destino") or solicitacao.destino,
            "periodo_viagem": resposta.get("periodo_viagem") or solicitacao.periodo_formatado,
            "total_dias": resposta.get("total_dias") or solicitacao.quantidade_dias,
            "perfil_viajantes": resposta.get("perfil_viajantes") or solicitacao.perfil_viajantes,
            "resumo_historia": self._normalizar_grupo(
                solicitacao,
                resposta.get("resumo_historia"),
                chave_grupo="historia",
                titulo_padrao="Resumo histórico do destino",
                resumo_padrao=f"Visão geral sobre a história e a identidade cultural de {solicitacao.destino}.",
            ),
            "contexto_periodo": self._normalizar_grupo(
                solicitacao,
                resposta.get("contexto_periodo"),
                chave_grupo="periodo",
                titulo_padrao="Clima, eventos e contexto do período",
                resumo_padrao=(
                    f"Resumo esperado para {solicitacao.destino} entre {solicitacao.periodo_formatado}, "
                    "incluindo clima, movimento turístico e eventos relevantes."
                ),
            ),
            "interesses": interesses,
            "dicas_seguranca": self._normalizar_grupo(
                solicitacao,
                resposta.get("dicas_seguranca"),
                chave_grupo="seguranca",
                titulo_padrao="Segurança no destino",
                resumo_padrao="Confirme condições locais, áreas recomendadas e cuidados gerais antes de cada passeio.",
            ),
            "roteiro_dia_a_dia": roteiro,
            "observacoes_gerais": self._complementar_observacoes_gerais(
                solicitacao,
                self._normalizar_lista_textos(resposta.get("observacoes_gerais")),
            ),
            "fontes_recomendadas": self._complementar_fontes_recomendadas(
                solicitacao,
                self._normalizar_lista_textos(resposta.get("fontes_recomendadas")),
            ),
            "modelo_utilizado": self._obter_metadado_resposta(metadados_resposta, "modelo_utilizado"),
            "familia_modelo": self._obter_metadado_resposta(metadados_resposta, "familia_modelo"),
            "nivel_detalhamento": solicitacao.nivel_detalhamento,
            "origem_cache": False,
            "aviso_importante": resposta.get("aviso_importante")
            or "Confirme preços, horários, clima e disponibilidade em canais oficiais antes da viagem.",
        }

        return resposta_normalizada

    @staticmethod
    def _obter_metadado_resposta(metadados: Any, chave: str) -> str | None:
        if isinstance(metadados, dict):
            valor = metadados.get(chave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
        return None

    def _normalizar_roteiro(
        self,
        solicitacao: SolicitacaoPlanoViagem,
        valor: Any,
    ) -> list[dict[str, Any]]:
        roteiro_minimo = self._gerar_roteiro_minimo(solicitacao)
        if not isinstance(valor, list) or not valor:
            return roteiro_minimo

        roteiro_normalizado: list[dict[str, Any]] = []
        assinaturas_utilizadas: set[str] = set()
        assinaturas_por_campo = {campo: set() for campo in ("tema_dia", "manha", "tarde", "noite")}
        for indice, item in enumerate(valor[: solicitacao.quantidade_dias]):
            padrao = roteiro_minimo[indice]
            if isinstance(item, dict):
                roteiro_dia = {
                    "dia": item.get("dia") or padrao["dia"],
                    "data": item.get("data") or padrao["data"],
                    "tema_dia": self._selecionar_texto_roteiro_variado(
                        self._normalizar_texto_curto(item.get("tema_dia")),
                        padrao["tema_dia"],
                        assinaturas_por_campo["tema_dia"],
                        considerar_generico=False,
                    ),
                    "manha": self._selecionar_texto_roteiro_variado(
                        self._normalizar_texto_roteiro(item.get("manha")),
                        padrao["manha"],
                        assinaturas_por_campo["manha"],
                    ),
                    "tarde": self._selecionar_texto_roteiro_variado(
                        self._normalizar_texto_roteiro(item.get("tarde")),
                        padrao["tarde"],
                        assinaturas_por_campo["tarde"],
                    ),
                    "noite": self._selecionar_texto_roteiro_variado(
                        self._normalizar_texto_roteiro(item.get("noite")),
                        padrao["noite"],
                        assinaturas_por_campo["noite"],
                    ),
                    "observacoes": self._normalizar_texto_roteiro(item.get("observacoes")) or padrao["observacoes"],
                }
                assinatura = self._gerar_assinatura_roteiro(roteiro_dia)
                if assinatura in assinaturas_utilizadas:
                    roteiro_dia = padrao
                    assinatura = self._gerar_assinatura_roteiro(roteiro_dia)
                self._registrar_assinaturas_campos_roteiro(roteiro_dia, assinaturas_por_campo)
                assinaturas_utilizadas.add(assinatura)
                roteiro_normalizado.append(roteiro_dia)
            else:
                roteiro_normalizado.append(padrao)
                self._registrar_assinaturas_campos_roteiro(padrao, assinaturas_por_campo)
                assinaturas_utilizadas.add(self._gerar_assinatura_roteiro(padrao))

        if len(roteiro_normalizado) < solicitacao.quantidade_dias:
            for padrao in roteiro_minimo[len(roteiro_normalizado) :]:
                roteiro_normalizado.append(padrao)
                self._registrar_assinaturas_campos_roteiro(padrao, assinaturas_por_campo)
                assinaturas_utilizadas.add(self._gerar_assinatura_roteiro(padrao))

        return roteiro_normalizado

    def _normalizar_interesses(self, solicitacao: SolicitacaoPlanoViagem, valor: Any) -> list[dict[str, Any]]:
        if not isinstance(valor, list):
            return []

        interesses_recebidos: dict[str, dict[str, Any]] = {}
        for item in valor:
            if not isinstance(item, dict):
                continue

            titulo_original = str(item.get("titulo") or "").strip()
            titulo_normalizado = self._normalizar_titulo_interesse(titulo_original)
            interesses_recebidos[titulo_normalizado] = {
                "titulo": titulo_normalizado,
                "resumo": self._normalizar_texto_roteiro(item.get("resumo")),
                "itens": self._normalizar_lista_textos(item.get("itens")),
            }

        interesses_esperados = solicitacao.interesses.selecionados or solicitacao.interesses.todos
        parametros = obter_parametros_detalhamento(solicitacao.nivel_detalhamento)
        minimo_itens = (
            parametros["itens_interesse_sugestao"]
            if not solicitacao.interesses.selecionados
            else parametros["itens_interesse_selecionado"]
        )

        interesses_normalizados: list[dict[str, Any]] = []
        for titulo in interesses_esperados:
            interesse = interesses_recebidos.get(titulo, {"titulo": titulo, "resumo": "", "itens": []})
            resumo = interesse["resumo"] or self._criar_resumo_interesse_fallback(titulo, solicitacao)
            itens = self._complementar_lista(
                interesse["itens"],
                self._gerar_itens_fallback_interesse(titulo, solicitacao),
                minimo_itens,
            )
            interesses_normalizados.append({"titulo": titulo, "resumo": resumo, "itens": itens})

        return interesses_normalizados

    @staticmethod
    def _normalizar_titulo_interesse(titulo: str) -> str:
        if not titulo:
            return "Interesse"

        titulo_base = unicodedata.normalize("NFKD", titulo.casefold())
        titulo_base = "".join(caractere for caractere in titulo_base if not unicodedata.combining(caractere))
        titulo_base = " ".join(titulo_base.split())

        return _MAPA_INTERESSES_NORMALIZADOS.get(titulo_base, titulo.strip())

    @staticmethod
    def _normalizar_lista_textos(valor: Any) -> list[str]:
        if isinstance(valor, list):
            itens_brutos = valor
        elif isinstance(valor, str) and valor.strip():
            itens_brutos = [valor]
        else:
            return []

        itens_normalizados: list[str] = []
        vistos: set[str] = set()
        for item in itens_brutos:
            texto = " ".join(str(item).strip().split())
            if not texto:
                continue
            assinatura = texto.casefold()
            if assinatura in vistos:
                continue
            vistos.add(assinatura)
            itens_normalizados.append(texto)

        return itens_normalizados

    @staticmethod
    def _normalizar_texto_curto(valor: Any) -> str:
        return " ".join(str(valor or "").strip().split())

    def _normalizar_texto_roteiro(self, valor: Any) -> str:
        texto = self._normalizar_texto_curto(valor)
        if not texto:
            return ""
        if self._gerar_assinatura_texto(texto) in _FRASES_GENERICAS_ROTEIRO:
            return ""
        return texto

    @staticmethod
    def _gerar_assinatura_texto(texto: str) -> str:
        texto_base = unicodedata.normalize("NFKD", texto.casefold())
        texto_base = "".join(caractere for caractere in texto_base if not unicodedata.combining(caractere))
        return " ".join(texto_base.split())

    def _gerar_assinatura_roteiro(self, roteiro_dia: dict[str, Any]) -> str:
        partes = [
            self._gerar_assinatura_texto(str(roteiro_dia.get("tema_dia") or "")),
            self._gerar_assinatura_texto(str(roteiro_dia.get("manha") or "")),
            self._gerar_assinatura_texto(str(roteiro_dia.get("tarde") or "")),
            self._gerar_assinatura_texto(str(roteiro_dia.get("noite") or "")),
        ]
        return " | ".join(partes)

    def _selecionar_texto_roteiro_variado(
        self,
        texto: str,
        texto_padrao: str,
        assinaturas_existentes: set[str],
        *,
        considerar_generico: bool = True,
    ) -> str:
        assinatura = self._gerar_assinatura_texto(texto)
        if not texto:
            return texto_padrao
        if considerar_generico and assinatura in _FRASES_GENERICAS_ROTEIRO:
            return texto_padrao
        if assinatura in assinaturas_existentes:
            return texto_padrao
        return texto

    def _registrar_assinaturas_campos_roteiro(
        self,
        roteiro_dia: dict[str, Any],
        assinaturas_por_campo: dict[str, set[str]],
    ) -> None:
        for campo in ("tema_dia", "manha", "tarde", "noite"):
            assinatura = self._gerar_assinatura_texto(str(roteiro_dia.get(campo) or ""))
            if assinatura:
                assinaturas_por_campo[campo].add(assinatura)

    def _normalizar_grupo(
        self,
        solicitacao: SolicitacaoPlanoViagem,
        valor: Any,
        *,
        chave_grupo: str,
        titulo_padrao: str,
        resumo_padrao: str,
    ) -> dict[str, Any]:
        if isinstance(valor, GrupoConteudo):
            valor = valor.model_dump()

        if isinstance(valor, dict):
            grupo = {
                "titulo": valor.get("titulo") or titulo_padrao,
                "resumo": self._normalizar_texto_roteiro(valor.get("resumo")) or resumo_padrao,
                "itens": self._normalizar_lista_textos(valor.get("itens")),
            }
        else:
            grupo = {
                "titulo": titulo_padrao,
                "resumo": resumo_padrao,
                "itens": [],
            }

        minimo_itens = obter_parametros_detalhamento(solicitacao.nivel_detalhamento)["itens_grupo"]
        grupo["itens"] = self._complementar_lista(
            grupo["itens"],
            self._gerar_itens_fallback_grupo(chave_grupo, solicitacao),
            minimo_itens,
        )
        return grupo

    def _gerar_interesses_fallback(self, solicitacao: SolicitacaoPlanoViagem) -> list[dict[str, Any]]:
        interesses = solicitacao.interesses.selecionados or solicitacao.interesses.todos
        parametros = obter_parametros_detalhamento(solicitacao.nivel_detalhamento)
        minimo_itens = (
            parametros["itens_interesse_sugestao"]
            if not solicitacao.interesses.selecionados
            else parametros["itens_interesse_selecionado"]
        )
        return [
            {
                "titulo": interesse,
                "resumo": self._criar_resumo_interesse_fallback(interesse, solicitacao),
                "itens": self._complementar_lista(
                    [],
                    self._gerar_itens_fallback_interesse(interesse, solicitacao),
                    minimo_itens,
                ),
            }
            for interesse in interesses
        ]

    def _gerar_roteiro_minimo(self, solicitacao: SolicitacaoPlanoViagem) -> list[dict[str, Any]]:
        temas = self._gerar_temas_roteiro(solicitacao)
        aberturas_manha = [
            "Comece a manhã com ritmo leve e foco em {tema_lower}, aproveitando o horário mais confortável para circular.",
            "Dedique a primeira parte do dia a {tema_lower}, priorizando um recorte do destino que combine boa energia e menor fila.",
            "Inicie o dia com café em uma área agradável e siga para {tema_lower}, observando a dinâmica local com mais tranquilidade.",
            "Reserve a manhã para um bloco central de {tema_lower}, com deslocamentos curtos e tempo para apreciar o entorno.",
            "Abra o dia por {tema_lower}, escolhendo um trecho do destino que faça sentido visitar cedo e sem correria.",
            "Use a manhã para entrar no clima de {tema_lower}, combinando orientação do espaço, fotos e pausas naturais ao longo do percurso.",
        ]
        complementos_manha = [
            "Se possível, concentre o início do dia em uma mesma região para ganhar tempo e entender melhor a dinâmica local.",
            "Prefira horários mais confortáveis para caminhar, observar o entorno e encaixar um primeiro ponto de apoio do grupo.",
            "Esse bloco funciona bem para ambientação, entradas antecipadas ou circulação mais tranquila antes do aumento do movimento.",
            "Mantenha uma margem flexível para adaptar o começo do dia ao clima, ao deslocamento e ao ritmo real da viagem.",
        ]
        aberturas_tarde = [
            "Use a tarde para aprofundar a experiência ligada a {tema_lower}, incluindo a principal atração ou região mais associada a esse recorte.",
            "No período da tarde, concentre a programação em {tema_lower}, combinando visita principal, pausa estratégica e algum tempo livre.",
            "A tarde pode ser dedicada ao ponto alto de {tema_lower}, com espaço para contemplação, registro de fotos e deslocamentos realistas.",
            "Aproveite a tarde para explorar {tema_lower} com mais calma, encaixando alimentação e descanso sem correria.",
            "Faça da tarde o bloco mais consistente de {tema_lower}, distribuindo bem deslocamento, refeição e experiência principal.",
            "Use esse período para o auge de {tema_lower}, sem exagerar na quantidade de paradas e mantendo logística realista.",
        ]
        complementos_tarde = [
            "Se houver mais de uma opção compatível, priorize a de melhor encaixe com o perfil do grupo e com o tempo disponível.",
            "Esse é um bom momento para incluir a atração mais representativa do dia, deixando pausas e alimentação em regiões convenientes.",
            "Evite sobrecarregar a metade do dia com trajetos longos demais; a ideia é sustentar a experiência com conforto.",
            "Quando fizer sentido, complemente a programação com mercado, café, vista panorâmica ou uma caminhada curta pela vizinhança.",
        ]
        aberturas_noite = [
            "Feche o dia com uma vivência alinhada a {tema_lower}, como jantar, passeio urbano, programação cultural ou descanso em região apropriada.",
            "À noite, escolha uma experiência coerente com {tema_lower}, mantendo conforto, segurança e bom ritmo para o grupo.",
            "Finalize o dia retomando o tema de {tema_lower} em um formato mais leve, acolhedor ou contemplativo.",
            "No encerramento da programação, conecte o dia a {tema_lower} com uma experiência agradável e logística simples para retornar.",
            "Use a noite para amarrar o dia com uma experiência de {tema_lower} que combine bem-estar, boa localização e encerramento sem pressa.",
            "Termine a programação com um recorte noturno coerente com {tema_lower}, preservando segurança e energia para o dia seguinte.",
        ]
        complementos_noite = [
            "Se o destino tiver cena gastronômica ou cultural forte, este pode ser o melhor espaço para valorizá-la sem correrias.",
            "Prefira um fechamento compatível com o deslocamento de volta e com o nível de energia restante do grupo.",
            "Esse período funciona bem para jantar especial, passeio urbano iluminado, evento leve ou simplesmente descanso qualificado.",
            "Em dias mais intensos, mantenha a noite mais enxuta para preservar o ritmo da viagem ao longo da estadia.",
        ]

        roteiro = []
        for indice in range(solicitacao.quantidade_dias):
            data_atual = solicitacao.data_inicio + timedelta(days=indice)
            tema_dia = temas[indice]
            tema_lower = tema_dia[:1].lower() + tema_dia[1:]
            roteiro.append(
                {
                    "dia": indice + 1,
                    "data": data_atual.strftime("%d/%m/%Y"),
                    "tema_dia": tema_dia,
                    "manha": self._compor_texto_periodo_roteiro(
                        periodo="manha",
                        indice=indice,
                        solicitacao=solicitacao,
                        tema_lower=tema_lower,
                        aberturas=aberturas_manha,
                        complementos=complementos_manha,
                    ),
                    "tarde": self._compor_texto_periodo_roteiro(
                        periodo="tarde",
                        indice=indice,
                        solicitacao=solicitacao,
                        tema_lower=tema_lower,
                        aberturas=aberturas_tarde,
                        complementos=complementos_tarde,
                    ),
                    "noite": self._compor_texto_periodo_roteiro(
                        periodo="noite",
                        indice=indice,
                        solicitacao=solicitacao,
                        tema_lower=tema_lower,
                        aberturas=aberturas_noite,
                        complementos=complementos_noite,
                    ),
                    "observacoes": self._gerar_observacao_roteiro(indice, solicitacao, tema_dia),
                }
            )
        return roteiro

    def _compor_texto_periodo_roteiro(
        self,
        *,
        periodo: str,
        indice: int,
        solicitacao: SolicitacaoPlanoViagem,
        tema_lower: str,
        aberturas: list[str],
        complementos: list[str],
    ) -> str:
        etapa = self._obter_etapa_viagem(indice, solicitacao.quantidade_dias)
        contextos_etapa = {
            "inicio": {
                "manha": "No começo da viagem, privilegie adaptação gradual e reconhecimento do entorno sem sobrecarregar o grupo.",
                "tarde": "Ainda na fase inicial da estadia, escolha um recorte forte do destino, mas sem depender de encaixes apressados.",
                "noite": "No início da viagem, vale fechar o dia com conforto para sustentar um bom ritmo nos próximos dias.",
            },
            "meio": {
                "manha": "No meio da viagem, aproveite para explorar melhor o que já faz mais sentido para o perfil escolhido.",
                "tarde": "Esse bloco costuma funcionar como o ponto alto do dia, então distribua energia e deslocamento com inteligência.",
                "noite": "Na parte central da viagem, a noite pode equilibrar experiência marcante com recuperação de energia.",
            },
            "encerramento": {
                "manha": "Perto do encerramento da viagem, mantenha prioridades claras e evite deixar tudo muito apertado.",
                "tarde": "Na reta final, prefira experiências que fechem bem a viagem sem gerar pressa excessiva.",
                "noite": "Ao encerrar a estadia, privilegie um fechamento agradável, fácil de executar e compatível com bagagem ou retorno.",
            },
        }

        complementos_perfil: list[str] = []
        interesses = solicitacao.interesses.selecionados
        if solicitacao.quantidade_criancas and periodo != "noite":
            complementos_perfil.append(
                "Se houver crianças, preserve pausas, alimentação simples de acessar e alternativas cobertas para mudanças de plano."
            )
        if "Econômico" in interesses:
            complementos_perfil.append(
                "Agrupar atividades próximas ajuda a manter o custo-benefício e reduzir perda de tempo com deslocamentos."
            )
        if "Gastronômico" in interesses and periodo in {"tarde", "noite"}:
            complementos_perfil.append(
                "Se combinar com o destino, inclua um mercado, café, prato típico ou refeição mais representativa nesse período."
            )
        if "Relaxamento" in interesses and periodo in {"manha", "noite"}:
            complementos_perfil.append(
                "Mantenha um ritmo confortável, com tempo real para apreciar o lugar e evitar sensação de correria."
            )
        if "Cultural" in interesses and periodo in {"manha", "tarde"}:
            complementos_perfil.append(
                "Aproveite para observar arquitetura, história local, bairros tradicionais e elementos que expliquem a identidade do destino."
            )
        if "Vida noturna" in interesses and periodo == "noite":
            complementos_perfil.append(
                "Se a viagem pedir saída noturna, prefira regiões bem avaliadas e já planeje a logística de retorno."
            )

        complemento_entorno = self._obter_complemento_entorno_para_tema(tema_lower, periodo)

        partes = [
            aberturas[indice % len(aberturas)].format(tema_lower=tema_lower),
            complementos[(indice + len(periodo)) % len(complementos)],
            contextos_etapa[etapa][periodo],
        ]
        if complemento_entorno:
            partes.append(complemento_entorno)
        if complementos_perfil:
            partes.append(complementos_perfil[indice % len(complementos_perfil)])
        return " ".join(parte for parte in partes if parte)

    @staticmethod
    def _obter_complemento_entorno_para_tema(tema_lower: str, periodo: str) -> str:
        if not any(chave in tema_lower for chave in ("região próxima", "bate-volta", "entorno", "fora do eixo", "regiões vizinhas", "cidade próxima")):
            return ""

        if periodo == "manha":
            return (
                "Se fizer sentido logisticamente, use este período para sair cedo rumo a uma cidade próxima, praia próxima ou outro recorte regional que complemente bem o destino-base."
            )
        if periodo == "tarde":
            return (
                "Ao explorar o entorno, prefira opções plausíveis para deslocamento curto ou bate-volta leve, sem transformar o dia em uma maratona excessiva."
            )
        return (
            "No retorno ao destino principal, mantenha margem para deslocamento tranquilo e confirme condições locais em fontes oficiais antes da saída."
        )

    @staticmethod
    def _obter_etapa_viagem(indice: int, total_dias: int) -> str:
        if total_dias <= 2:
            return "meio"
        if indice == 0:
            return "inicio"
        if indice >= total_dias - 2:
            return "encerramento"
        return "meio"

    @staticmethod
    def _complementar_lista(itens_atuais: list[str], complementos: list[str], minimo_itens: int) -> list[str]:
        itens = list(itens_atuais)
        vistos = {item.casefold() for item in itens}
        for complemento in complementos:
            if len(itens) >= minimo_itens:
                break
            assinatura = complemento.casefold()
            if assinatura in vistos:
                continue
            vistos.add(assinatura)
            itens.append(complemento)
        return itens

    def _gerar_itens_fallback_grupo(self, chave_grupo: str, solicitacao: SolicitacaoPlanoViagem) -> list[str]:
        destino = solicitacao.destino
        complementos = list(_MAPA_COMPLEMENTOS_GRUPOS.get(chave_grupo, []))
        if chave_grupo == "historia":
            complementos.insert(0, f"Considere como a formação de {destino} influenciou identidade cultural, arquitetura e experiências turísticas atuais.")
        elif chave_grupo == "periodo":
            complementos.insert(0, f"Analise como o período de {solicitacao.periodo_formatado} costuma afetar clima, agenda cultural e fluxo de visitantes em {destino}.")
            complementos.append(
                f"Quando fizer sentido, observe também como o período pode impactar praias, serras, bairros ou cidades próximas que costumam complementar quem se hospeda em {destino}."
            )
        elif chave_grupo == "seguranca":
            complementos.insert(0, f"Antes dos passeios em {destino}, revise áreas mais recomendadas, transporte adequado e canais oficiais úteis para apoio ao visitante.")
            complementos.append(
                "Se o roteiro incluir entorno regional, confirme tempo de deslocamento, condições de acesso e funcionamento dos atrativos antes de sair."
            )
        return complementos

    def _criar_resumo_interesse_fallback(self, titulo: str, solicitacao: SolicitacaoPlanoViagem) -> str:
        resumo_base = _MAPA_INTERESSES_FALLBACK[titulo]
        resumo_base = f"{resumo_base} Sempre que fizer sentido, combine experiências no destino-base com recortes próximos que ampliem a viagem sem perder coerência logística."
        if solicitacao.quantidade_criancas:
            return f"{resumo_base} Sempre que possível, adapte o ritmo e inclua alternativas adequadas para famílias com crianças."
        return resumo_base

    def _gerar_itens_fallback_interesse(self, titulo: str, solicitacao: SolicitacaoPlanoViagem) -> list[str]:
        itens = list(_MAPA_COMPLEMENTOS_INTERESSES[titulo])
        itens.append(
            f"Se enriquecer o plano para {solicitacao.destino}, vale considerar bairros, praias, cidades ou regiões próximas que façam sentido como extensão natural da experiência."
        )
        if solicitacao.quantidade_criancas:
            itens.append("Ao incluir esse interesse no roteiro, mantenha pausas, alimentação acessível e janelas realistas para crianças.")
        if titulo == "Econômico":
            itens.append("Prefira regiões com boa concentração de atrações para reduzir gastos com deslocamento ao longo do dia.")
        return itens

    def _gerar_temas_roteiro(self, solicitacao: SolicitacaoPlanoViagem) -> list[str]:
        temas_base = ["Ambientação e primeiras descobertas", "Centro histórico e identidade local"]
        interesses = solicitacao.interesses.selecionados

        if "Cultural" in interesses or not interesses:
            temas_base.append("Museus, patrimônio e cultura viva")
        if "Gastronômico" in interesses or not interesses:
            temas_base.append("Sabores locais, cafés e mercados")
        if "Aventureiro" in interesses or "Ecoturismo/Sustentável" in interesses or not interesses:
            temas_base.append("Natureza, mirantes e experiências ao ar livre")
        if "Relaxamento" in interesses or not interesses:
            temas_base.append("Ritmo leve, pausas e bem-estar")
        if solicitacao.quantidade_criancas:
            temas_base.append("Programa familiar e atrações infantis")
        if "Vida noturna" in interesses:
            temas_base.append("Noite local e experiências após o pôr do sol")
        if "Econômico" in interesses:
            temas_base.append("Custo-benefício e atrações acessíveis")

        temas_base.extend(
            [
                "Bairro charmoso, compras e cotidiano local",
                "Região próxima ou bate-volta leve",
                "Entorno do destino e recortes regionais",
                "Parques urbanos e contemplação",
                "Experiência principal do destino",
                "Encerramento com favoritos da viagem",
            ]
        )

        temas_complementares = [
            "Arquitetura, praças e cotidiano do destino",
            "Mercados, cafés e produtores locais",
            "Mirantes, orla ou paisagem marcante",
            "Bairro criativo e pequenas descobertas",
            "Ritmo leve com escolhas do grupo",
            "Cultura viva, feiras e experiências autênticas",
            "Passeio complementar fora do eixo principal",
            "Cidade próxima, distrito ou litoral de apoio",
            "Revisita aos destaques e despedida gradual",
        ]

        temas: list[str] = []
        for tema in temas_base:
            if tema not in temas:
                temas.append(tema)

        indice_tema_complementar = 0
        while len(temas) < solicitacao.quantidade_dias:
            tema_base = temas_complementares[indice_tema_complementar % len(temas_complementares)]
            tema = tema_base
            if tema in temas:
                tema = f"{tema_base} - roteiro complementar {indice_tema_complementar + 1}"
            temas.append(tema)
            indice_tema_complementar += 1

        return temas[: solicitacao.quantidade_dias]

    def _gerar_observacao_roteiro(self, indice: int, solicitacao: SolicitacaoPlanoViagem, tema_dia: str) -> str:
        etapa = self._obter_etapa_viagem(indice, solicitacao.quantidade_dias)
        observacoes = [
            "Confirme clima, deslocamentos e eventual necessidade de reserva antes de sair.",
            "Se o dia incluir área muito disputada, tente chegar cedo para aproveitar melhor e evitar filas longas.",
            "Mantenha uma pausa estratégica para alimentação e descanso, principalmente se o grupo tiver crianças ou idosos.",
            f"Ajuste o ritmo do dia ao foco em {tema_dia.lower()}, evitando deslocamentos longos demais no mesmo período.",
            "Mantenha alguma flexibilidade para adaptar a programação conforme cansaço, clima e achados espontâneos no destino.",
            "Se a atividade principal depender de ingresso, fila ou deslocamento maior, revise a logística na noite anterior.",
        ]
        if any(chave in tema_dia.casefold() for chave in ("região próxima", "bate-volta", "entorno", "fora do eixo", "cidade próxima")):
            observacoes.append(
                "Se o dia incluir entorno regional, confirme distância, acesso e janela de retorno para manter o destino principal como base confortável da viagem."
            )
        if etapa == "inicio":
            observacoes.insert(0, "No começo da viagem, use o dia para entender melhor o entorno e calibrar o ritmo real do grupo.")
        elif etapa == "encerramento":
            observacoes.insert(0, "Na reta final, preserve margem para bagagem, retorno, compras finais ou revisita aos lugares preferidos.")
        if solicitacao.quantidade_criancas:
            observacoes.append("Leve água, lanche, pontos de banheiro mapeados e alternativa coberta para imprevistos com crianças.")
        if "Econômico" in solicitacao.interesses.selecionados:
            observacoes.append("Agrupe atrações próximas e refeições com bom custo-benefício para manter o orçamento sob controle.")
        return observacoes[indice % len(observacoes)]

    def _complementar_observacoes_gerais(
        self,
        solicitacao: SolicitacaoPlanoViagem,
        observacoes_atuais: list[str],
    ) -> list[str]:
        maximo = obter_parametros_detalhamento(solicitacao.nivel_detalhamento)["observacoes"]
        complementos = [
            "Revise clima, feriados, eventos e reservas com poucos dias de antecedência para ajustar o roteiro final.",
            f"Se incluir cidades ou regiões próximas a {solicitacao.destino}, trate isso como extensão natural da viagem e confirme a logística final antes de sair.",
            "Confirme endereços, horários de funcionamento e regras de ingresso em canais oficiais antes de cada visita.",
            "Mantenha margem para mudanças espontâneas, principalmente em destinos com trânsito intenso ou clima instável.",
            "Separe documentos, meios de pagamento e contatos úteis para evitar contratempos durante deslocamentos.",
            "Se houver crianças, organize pausas e refeições em horários compatíveis com o ritmo do grupo.",
            "Use o planejamento como guia flexível e priorize as experiências que mais combinam com o perfil da viagem.",
        ]
        return self._complementar_lista(observacoes_atuais[:maximo], complementos, maximo)

    def _complementar_fontes_recomendadas(
        self,
        solicitacao: SolicitacaoPlanoViagem,
        fontes_atuais: list[str],
    ) -> list[str]:
        maximo = obter_parametros_detalhamento(solicitacao.nivel_detalhamento)["fontes"]
        complementos = [
            f"Portal oficial de turismo de {solicitacao.destino}",
            "Portais oficiais das cidades, regiões ou atrativos próximos citados no roteiro, quando houver",
            "Prefeitura local, secretaria de turismo ou órgão oficial equivalente",
            "Museus, parques, atrações e casas de evento em seus canais oficiais",
            "Serviços oficiais de meteorologia e mobilidade urbana do destino",
            "Guias de visitação e calendários culturais mantidos por instituições reconhecidas",
        ]
        return self._complementar_lista(fontes_atuais[:maximo], complementos, maximo)


@lru_cache(maxsize=1)
def instanciar_servico_planejamento() -> ServicoPlanejamentoViagem:
    return ServicoPlanejamentoViagem()

