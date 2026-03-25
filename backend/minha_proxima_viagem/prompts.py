from __future__ import annotations

from datetime import timedelta

from backend.minha_proxima_viagem.modelos import SolicitacaoPlanoViagem, obter_parametros_detalhamento


_PROMPT_SISTEMA = """
Você é um consultor especializado em planejamento de viagens.
Responda sempre em português do Brasil, com linguagem clara, útil e objetiva.
Priorize informações historicamente conhecidas, fontes oficiais e referências confiáveis do destino.
Trate o destino informado como base principal da viagem, mas considere também cidades próximas, bairros próximos, litoral próximo, serra próxima ou outras regiões próximas quando isso for plausível e útil para o turista.
Quando houver incerteza, deixe isso explícito e recomende validação final em canais oficiais.
Retorne somente um JSON válido, sem markdown, sem comentários e sem texto fora do JSON.
""".strip()


_INSTRUCOES_INTERESSES = {
    "Aventureiro": "inclua experiências ao ar livre, trilhas leves ou moderadas, mirantes, esportes e passeios ativos compatíveis com o destino",
    "Econômico": "priorize custo-benefício, atrações gratuitas ou baratas e deslocamentos eficientes",
    "Gastronômico": "destaque pratos típicos, mercados, cafés, restaurantes e faixas de preço do mais barato ao mais caro",
    "Cultural": "valorize museus, centros históricos, feiras, manifestações locais e tradições do destino",
    "Relaxamento": "inclua momentos tranquilos, parques, spas, praias calmas ou cafés aconchegantes",
    "Vida noturna": "traga bares, eventos, shows, ruas movimentadas e indique opções do mais barato ao mais caro",
    "Ecoturismo/Sustentável": "inclua atrações de natureza, turismo responsável, práticas sustentáveis e respeito à cultura local",
}


def obter_prompt_sistema() -> str:
    return _PROMPT_SISTEMA


def _montar_bloco_interesses(solicitacao: SolicitacaoPlanoViagem) -> str:
    interesses = solicitacao.interesses.selecionados

    if interesses:
        linhas = ["Interesses selecionados com alta prioridade:"]
        for interesse in interesses:
            linhas.append(f"- {interesse}: {_INSTRUCOES_INTERESSES[interesse]}")
        return "\n".join(linhas)

    linhas = [
        "Nenhum interesse foi selecionado.",
        "Gere pequenas sugestões para todos os interesses abaixo, com tom de recomendação inicial:",
    ]
    for interesse in solicitacao.interesses.todos:
        linhas.append(f"- {interesse}: {_INSTRUCOES_INTERESSES[interesse]}")
    return "\n".join(linhas)


def _montar_datas(solicitacao: SolicitacaoPlanoViagem) -> str:
    datas = []
    for indice in range(solicitacao.quantidade_dias):
        data_atual = solicitacao.data_inicio + timedelta(days=indice)
        datas.append(f"Dia {indice + 1}: {data_atual.strftime('%d/%m/%Y')}")
    return "\n".join(datas)


def _montar_bloco_detalhamento(solicitacao: SolicitacaoPlanoViagem) -> str:
    parametros = obter_parametros_detalhamento(solicitacao.nivel_detalhamento)
    nenhum_interesse_selecionado = not solicitacao.interesses.selecionados
    itens_interesse = (
        parametros["itens_interesse_sugestao"]
        if nenhum_interesse_selecionado
        else parametros["itens_interesse_selecionado"]
    )
    tom_interesses = (
        "Como nenhum interesse foi selecionado, mantenha todos os interesses no planejamento, mas ainda assim entregue conteúdo útil, sem respostas telegráficas."
        if nenhum_interesse_selecionado
        else "Para cada interesse selecionado, aprofunde as sugestões com exemplos práticos, contexto e variedade de opções."
    )

    regras_periodos = {
        "enxuto": "cada período do roteiro deve ter 1 frase bem específica ou, no máximo, 2 frases curtas, sem ficar telegráfico",
        "equilibrado": "cada período do roteiro deve ter pelo menos 2 frases curtas ou 1 frase mais desenvolvida, com contexto suficiente para diferenciar o dia",
        "detalhado": "cada período do roteiro deve ter 2 ou 3 frases curtas, trazendo foco do momento, tipo de experiência e orientação prática",
    }

    reforcos_por_nivel = {
        "enxuto": "Priorize síntese, mas preserve orientação prática e referências concretas de experiência.",
        "equilibrado": "Equilibre contexto e objetividade, entregando um guia útil sem alongar desnecessariamente cada seção.",
        "detalhado": "Aprofunde o conteúdo com mais contexto, variedade de exemplos e melhor distribuição do ritmo da viagem.",
    }

    return f"""
Nível de detalhamento solicitado: {solicitacao.nivel_detalhamento.upper()}.
- Histórico, contexto do período e segurança: produza resumos completos, sem superficialidade, com pelo menos {parametros['itens_grupo']} itens por grupo quando houver conteúdo plausível.
- Interesses: use pelo menos {itens_interesse} itens em cada grupo de interesse retornado.
- Observações gerais: inclua até {parametros['observacoes']} itens realmente úteis.
- Fontes recomendadas: inclua até {parametros['fontes']} referências confiáveis ou tipos de fonte oficial relevantes.
- Roteiro dia a dia: {regras_periodos[solicitacao.nivel_detalhamento]}.
- Evite respostas minimalistas com 2 ou 3 itens quando o destino e o período permitirem mais profundidade.
- {reforcos_por_nivel[solicitacao.nivel_detalhamento]}
- {tom_interesses}
""".strip()


def _montar_regras_variacao_roteiro(solicitacao: SolicitacaoPlanoViagem) -> str:
    if solicitacao.quantidade_dias <= 3:
        return (
            "No roteiro, cada dia deve ter identidade própria, evitando repetir a mesma estrutura entre manhã, tarde e noite. Mesmo em viagens curtas, faça os dias parecerem complementares, e não cópias com pequenas trocas de palavras. Se alguma cidade, praia, bairro ou região próxima agregar muito valor e couber bem na logística, ela pode aparecer como complemento do destino-base."
        )

    if solicitacao.quantidade_dias <= 7:
        return f"""
No roteiro de {solicitacao.quantidade_dias} dias, distribua a viagem com variedade real entre os dias.
- Cada dia deve ter um `tema_dia` distinto e coerente com o destino.
- Alterne focos como centro histórico, bairro gastronômico, mercados, parques, museus, mirantes, experiências culturais, compras locais, descanso, atrações familiares ou região próxima, conforme fizer sentido.
- Considere, quando fizer sentido logístico, incluir cidade próxima, distrito vizinho, praia próxima, serra próxima ou outro recorte regional relevante como parte do roteiro.
- Crie sensação de progressão: começo de ambientação, meio com pontos altos e fim com fechamento mais leve ou revisita aos favoritos.
- Não reutilize o mesmo texto entre dias diferentes, nem a mesma sequência de manhã, tarde e noite.
- Não devolva dias genéricos copiando frases como "reconhecimento da região central", "principal atração sugerida" ou "refeição típica" em sequência.
- Quando faltar dado específico em tempo real, continue variando o roteiro com base em perfis de viagem plausíveis para o destino, sem inventar fatos muito precisos.
""".strip()

    return f"""
No roteiro de {solicitacao.quantidade_dias} dias, distribua a viagem com variedade real entre os dias.
- Cada dia deve ter um `tema_dia` distinto e coerente com o destino.
- Alterne focos como centro histórico, bairro gastronômico, mercados, parques, museus, mirantes, experiências culturais, compras locais, descanso, atrações familiares, região próxima e dias de ritmo mais leve, conforme fizer sentido.
- Em viagens mais longas, considere distribuir pelo menos um ou mais dias com recortes de entorno, como cidades próximas ou regiões vizinhas plausíveis para bate-volta ou deslocamento curto.
- Distribua melhor viagens longas: não concentre cultura ou gastronomia apenas no início e não repita a mesma estrutura na segunda metade do roteiro.
- Faça o roteiro respirar: intercale dias intensos com blocos mais leves, especialmente em viagens com crianças ou com muitos deslocamentos.
- Não reutilize o mesmo texto entre dias diferentes.
- Não devolva dias genéricos copiando frases como "reconhecimento da região central", "principal atração sugerida" ou "refeição típica" em sequência.
- Quando faltar dado específico em tempo real, continue variando o roteiro com base em perfis de viagem plausíveis para o destino, sem inventar fatos muito precisos.
- Em destinos litorâneos, distribua orla, praias, gastronomia, mercados, bairros, mirantes e pausas ao longo da estadia; em destinos urbanos, varie entre história, cultura viva, bairros, gastronomia, parques e compras locais.
- Se citar entorno regional, faça isso como complemento natural do destino principal e com linguagem prudente, como "se fizer sentido logisticamente" ou "vale considerar", evitando afirmar detalhes excessivamente específicos sem alta confiança.
""".strip()


def construir_prompt_usuario(solicitacao: SolicitacaoPlanoViagem) -> str:
    contexto_criancas = (
        "Há crianças na viagem. Inclua atividades seguras, pausas, alimentação adequada e opções infantis."
        if solicitacao.quantidade_criancas
        else "Não há crianças informadas."
    )
    schema_json = """
{
  "destino": "string",
  "periodo_viagem": "dd/mm/yyyy a dd/mm/yyyy",
  "total_dias": 0,
  "perfil_viajantes": "string",
  "resumo_historia": {
    "titulo": "Resumo histórico do destino",
    "resumo": "string",
    "itens": ["string"]
  },
  "contexto_periodo": {
    "titulo": "Clima, eventos e contexto do período",
    "resumo": "string",
    "itens": ["string"]
  },
  "interesses": [
    {
      "titulo": "string",
      "resumo": "string",
      "itens": ["string"]
    }
  ],
  "dicas_seguranca": {
    "titulo": "Segurança no destino",
    "resumo": "string",
    "itens": ["string"]
  },
  "roteiro_dia_a_dia": [
    {
      "dia": 1,
      "data": "dd/mm/yyyy",
      "tema_dia": "string",
      "manha": "string",
      "tarde": "string",
      "noite": "string",
      "observacoes": "string"
    }
  ],
  "observacoes_gerais": ["string"],
  "fontes_recomendadas": ["string"],
  "aviso_importante": "string"
}
""".strip()

    return f"""
Monte um mini planejamento completo da viagem respeitando integralmente os requisitos abaixo.

Dados da solicitação:
- Destino: {solicitacao.destino}
- Período: {solicitacao.periodo_formatado}
- Total de dias: {solicitacao.quantidade_dias}
- Perfil de viajantes: {solicitacao.perfil_viajantes}
- Quantidade de adultos: {solicitacao.quantidade_adultos}
- Quantidade de crianças: {solicitacao.quantidade_criancas}
- {contexto_criancas}
- Nível de detalhamento do plano: {solicitacao.nivel_detalhamento}

{_montar_bloco_interesses(solicitacao)}

{_montar_bloco_detalhamento(solicitacao)}

Regras de negócio obrigatórias:
1. Faça um resumo da história do destino.
2. Explique o que costuma acontecer no destino no período informado, cobrindo clima, temperatura média, eventos e movimento turístico quando fizer sentido.
3. Monte uma seção de interesses com sugestões alinhadas ao perfil informado.
4. Se nenhum interesse for selecionado, gere sugestões curtas para todos os interesses.
5. Monte um roteiro dia a dia cobrindo manhã, tarde e noite, do acordar ao encerramento do dia.
6. O destino informado deve ser a base do plano, mas você pode incluir cidades, praias, bairros e regiões próximas quando isso enriquecer a experiência do turista.
7. Ao incluir entorno próximo, privilegie opções plausíveis para deslocamento curto, bate-volta ou extensão natural da estadia, sem tirar o foco do destino principal.
8. Se houver crianças, inclua atividades infantis e ritmo adequado.
9. Se o perfil gastronômico estiver selecionado, cite sugestões do mais barato ao mais caro.
10. Se vida noturna estiver selecionado, cite sugestões do mais barato ao mais caro.
11. Valorize a cultura local.
12. Se o perfil econômico estiver selecionado, privilegie custo-benefício na programação.
13. Evite afirmar preços exatos, horários exatos ou disponibilidade em tempo real sem ressalvas.
14. Ao final, recomende fontes oficiais ou confiáveis para validação final.
15. Entregue conteúdo útil e mais desenvolvido, evitando listas mínimas demais quando houver espaço para orientar melhor o viajante.
16. No roteiro, dê uma sensação de progressão da viagem, com dias diferentes entre si.

Regras obrigatórias de riqueza da resposta:
- `resumo_historia.resumo`, `contexto_periodo.resumo` e `dicas_seguranca.resumo` devem ir além de frases genéricas e trazer contexto prático para quem está planejando a viagem.
- `resumo_historia.itens`, `contexto_periodo.itens` e `dicas_seguranca.itens` devem listar pontos complementares entre si, não apenas sinônimos.
- Em `interesses`, os itens devem citar tipos de lugares, experiências, regiões ou estratégias compatíveis com o perfil informado.
- Se `Gastronômico` estiver selecionado, inclua variedade entre mercado, café, prato típico, restaurante ou experiência local, deixando claro o que tende a ser mais econômico ou mais caro.
- Se `Vida noturna` estiver selecionado, inclua regiões ou perfis de saída noturna e organize do mais acessível ao mais sofisticado quando fizer sentido.
- Se houver crianças, mencione pausas, logística e alternativas infantis no roteiro e nas recomendações relacionadas.
- Quando o entorno próximo for útil, distribua isso de maneira natural em `interesses`, `roteiro_dia_a_dia` e `observacoes_gerais`, sem transformar todo o plano em uma viagem para outra cidade.

Regras obrigatórias de formatação e consistência:
- O JSON deve ser completo, claro e útil, sem ficar excessivamente resumido.
- Não repita explicações muito parecidas entre categorias.
- Cada grupo deve trazer conteúdo complementar, e não reciclar a mesma frase em versões ligeiramente diferentes.
- Não trate o destino informado de forma isolada quando o contexto turístico normalmente envolver cidades ou regiões próximas, mas preserve o destino principal como referência central do plano.
- Em `roteiro_dia_a_dia`, use todas as datas fornecidas e devolva exatamente {solicitacao.quantidade_dias} dias.
- Em cada dia do roteiro, preencha `tema_dia`, `manha`, `tarde`, `noite` e `observacoes`.
- O campo `observacoes` deve registrar atenção prática do dia, como reservas, ritmo do grupo, clima, deslocamento ou melhor janela para a atividade.

{_montar_regras_variacao_roteiro(solicitacao)}

Datas que precisam aparecer no roteiro:
{_montar_datas(solicitacao)}

Formato de saída obrigatório:
- Retorne somente JSON válido.
- Não use markdown.
- Use exatamente a estrutura abaixo como referência, preenchendo com conteúdo real:
{schema_json}
""".strip()

