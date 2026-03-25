# Minha Próxima Viagem

Aplicação MVP para gerar um mini planejamento de viagem com apoio de IA.

O usuário informa datas, destino, quantidade de pessoas e interesses opcionais. A aplicação consulta o Gemini com um prompt dinâmico e devolve um planejamento organizado por categorias, incluindo:

- resumo histórico do destino;
- contexto do período da viagem;
- sugestões alinhadas aos interesses escolhidos;
- dicas de segurança;
- roteiro dia a dia;
- observações finais e fontes recomendadas para validação.

O destino informado é tratado como base principal do plano, mas a aplicação também pode considerar bairros, praias, cidades e regiões próximas quando isso fizer sentido para enriquecer a experiência do turista.

## Objetivo do projeto

Resolver o problema de quem perde muito tempo pesquisando informações espalhadas sobre um destino antes de viajar.

Este MVP concentra a experiência em uma interface simples e em uma API reutilizável.

## Tecnologias utilizadas

- Python 3.10 ou superior
- Streamlit
- FastAPI
- Uvicorn
- Pydantic
- google-generativeai
- json-repair
- python-dotenv
- Google Gemini

## Versões de bibliotecas e ferramentas utilizadas

As versões abaixo refletem o estado atual do projeto e do arquivo `requirements.txt`.

| Item | Versão |
|---|---|
| Python (requisito mínimo) | 3.10+ |
| Python validado nos testes locais | 3.12 |
| Windows PowerShell | 5.1 |
| Streamlit | 1.43.2 |
| FastAPI | 0.115.11 |
| Uvicorn | 0.34.0 |
| Pydantic | 2.10.6 |
| google-generativeai | 0.8.5 |
| json-repair | 0.58.6 |
| python-dotenv | 1.0.1 |
| Modelo Gemini padrão no projeto | `models/gemini-2.5-flash-lite` |

## Arquitetura atual

```text
minha-proxima-viagem/
├── app/
│   ├── api.py                         # API FastAPI
│   └── streamlit_app.py               # Frontend Streamlit
├── minha_proxima_viagem/
│   ├── __init__.py
│   ├── cliente_gemini.py              # Integração com Gemini
│   ├── configuracao.py                # Configuração centralizada via .env
│   ├── excecoes.py                    # Exceções da aplicação
│   ├── logs.py                        # Logging centralizado
│   ├── modelos.py                     # Modelos Pydantic e regras de validação
│   ├── prompts.py                     # Prompt dinâmico conforme interesses
│   └── servico_planejamento.py        # Orquestração da geração do plano
├── scripts/
│   ├── ask_cli.py                     # Geração via terminal
│   ├── list_models.py                 # Lista modelos disponíveis no Gemini
│   └── quick_eval.py                  # Smoke test local sem chamada externa real
├── .env.example
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.10 ou superior
- chave de API do Gemini

## Configuração do ambiente

### 1. Criar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 3. Criar o arquivo `.env`

Copie o `.env.example` para `.env` e preencha sua chave:

```env
APP_NOME=Minha Próxima Viagem
APP_AMBIENTE=desenvolvimento
APP_API_BACKEND_URL=http://127.0.0.1:8000
APP_API_TIMEOUT_SEGUNDOS=120
PLANEJAMENTO_NIVEL_DETALHAMENTO_PADRAO=equilibrado
GEMINI_API_KEY=cole_sua_chave_aqui
GEMINI_MODEL=models/gemini-2.5-flash-lite
GEMINI_MODELOS_FALLBACK=models/gemma-3-4b-it,models/gemini-2.5-flash,models/gemini-3-flash-preview
GEMINI_TEMPERATURE=0.3
GEMINI_MAX_TOKENS=2600
GEMINI_TIMEOUT_SEGUNDOS=90
CACHE_TTL_SEGUNDOS=600
CACHE_MAX_ENTRADAS=128
LOG_LEVEL=INFO
```

### Controle de detalhamento do planejamento

O projeto agora suporta três níveis canônicos de detalhamento:

- `enxuto`: resposta mais direta, com menos itens por seção e roteiro mais compacto;
- `equilibrado`: padrão recomendado, equilibrando clareza, contexto e objetividade;
- `detalhado`: resposta mais rica, com mais variedade, contexto e expansão do roteiro.

Valor padrão atual:

```env
PLANEJAMENTO_NIVEL_DETALHAMENTO_PADRAO=equilibrado
```

Compatibilidade retroativa mantida:

- `compacto` é aceito como alias de `enxuto`;
- `padrao` ou `padrão` são aceitos como alias de `equilibrado`.

Para respostas mais ricas, o `.env.example` e a documentação passam a sugerir:

- `GEMINI_TEMPERATURE=0.3`
- `GEMINI_MAX_TOKENS=2600`

Se quiser um comportamento mais conservador, você ainda pode reduzir esses valores.

## Como executar

### Script único para Git Bash

Se você quiser subir backend e frontend de uma vez só no Windows usando Git Bash, execute na raiz do projeto:

```bash
bash iniciar_app.sh
```

O script:

- cria a `.venv` automaticamente caso ela ainda não exista;
- ativa o ambiente virtual;
- instala `requirements.txt` se estiver faltando alguma dependência principal;
- garante `APP_API_BACKEND_URL=http://127.0.0.1:8000` para alinhar frontend e backend durante a execução;
- inicia o backend FastAPI e espera o endpoint `/health` responder;
- inicia o frontend Streamlit em seguida;
- encerra o backend automaticamente quando você pressionar `Ctrl+C`.

Portas padrão do script:

- backend: `127.0.0.1:8000`
- frontend: `127.0.0.1:8501`

Se quiser customizar, você pode exportar variáveis antes de executar:

```bash
APP_BACKEND_PORT=8001 APP_FRONTEND_PORT=8502 bash iniciar_app.sh
```

### Frontend Streamlit

O frontend consome a API FastAPI via HTTP. Por isso, inicie primeiro o backend e depois o Streamlit.

1. Inicie a API:

```powershell
uvicorn app.api:app --reload
```

2. Em outro terminal, inicie o frontend:

```powershell
streamlit run app/streamlit_app.py
```

### API FastAPI

```powershell
uvicorn app.api:app --reload
```

Documentação interativa da API:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/teste`
- `POST /planejar-viagem`
- `POST /planejar-viagem/stream` (streaming em `application/x-ndjson`)

### Uso via terminal

```powershell
python scripts/ask_cli.py --data-inicio 2026-07-10 --data-fim 2026-07-14 --destino "Lisboa, Portugal" --adultos 2 --gastronomico --cultural --nivel-detalhamento detalhado
```

### Diagnóstico real dos modelos Gemini

```powershell
python scripts/testar_modelos_gemini.py
```

Esse script faz chamadas reais mínimas com baixo consumo de tokens para ajudar a identificar quais modelos estão utilizáveis para a sua chave/projeto no momento.

## Regras de negócio implementadas

- `Data início`, `Data fim` e `Destino` obrigatórios.
- frontend e backend validam os campos obrigatórios antes de gerar o planejamento.
- validação para impedir `data_inicio > data_fim`.
- campos opcionais para quantidade de adultos, quantidade de crianças e interesses.
- prompt dinâmico: apenas os interesses selecionados são enviados como prioridade.
- quando nenhum interesse é selecionado, o prompt pede sugestões breves para todos.
- controle de detalhamento ponta a ponta via frontend, API, domínio e prompt.
- níveis suportados no domínio: `enxuto`, `equilibrado` e `detalhado`.
- o destino informado permanece como base do plano, mas o roteiro pode incluir entorno próximo, bairros, praias e cidades vizinhas quando isso for plausível e útil.
- se houver crianças, o prompt força recomendações compatíveis com esse perfil.
- se `Econômico` for marcado, a IA deve priorizar custo-benefício.
- se `Gastronômico` ou `Vida noturna` forem marcados, o prompt pede sugestões do mais barato ao mais caro.
- fallback do roteiro reforçado para variar melhor viagens longas ou respostas incompletas da IA.
- o resultado é apresentado por categorias e com roteiro dia a dia.

## Estrutura da resposta gerada

A aplicação pede ao Gemini um JSON estruturado, que depois é validado por Pydantic. Isso reduz respostas inconsistentes e facilita o reuso em frontend e API.

Principais blocos retornados:

- `resumo_historia`
- `contexto_periodo`
- `interesses`
- `dicas_seguranca`
- `roteiro_dia_a_dia`
- `observacoes_gerais`
- `fontes_recomendadas`

## Exemplo de payload da API

```json
{
  "data_inicio": "2026-07-10",
  "data_fim": "2026-07-14",
  "destino": "Lisboa, Portugal",
  "quantidade_adultos": 2,
  "quantidade_criancas": 1,
  "nivel_detalhamento": "equilibrado",
  "interesses": {
    "economico": true,
    "gastronomico": true,
    "cultural": true,
    "aventureiro": false,
    "relaxamento": false,
    "vida_noturna": false,
    "ecoturismo_sustentavel": false
  }
}
```

## Endpoint principal

### `POST /planejar-viagem`

Gera o planejamento estruturado da viagem.

### `POST /planejar-viagem/stream`

Retorna eventos em streaming (`application/x-ndjson`) com mensagens de status e o resultado final do planejamento.

### `GET /teste`

Rota simples para validar se a API está operacional.

### `GET /health`

Retorna o estado da aplicação e informa se a chave Gemini está configurada.

## Logs e tratamento de erros

- logs centralizados via `logging`;
- exceções de integração separadas das exceções de domínio;
- handlers globais no FastAPI para erros de validação, integração e falhas inesperadas;
- mensagens amigáveis na interface Streamlit.
- tratamento específico para erro `429` de quota/rate limit do Gemini, com orientação para nova tentativa quando o provedor informar `retry_delay`.
- fallback automático entre modelos Gemini candidatos quando o modelo principal estiver sem quota ou indisponível para a conta atual.
- cache em memória com TTL no serviço central para reaproveitar respostas de solicitações idênticas no mesmo processo.
- frontend consumindo o backend FastAPI via HTTP, com verificação de saúde da API no carregamento da interface.

## Validação local rápida

Foi incluído um smoke test que não depende de chamada real à API do Gemini.

Execute:

```powershell
python scripts/quick_eval.py
```

Esse script valida:

- obrigatoriedade e consistência dos campos principais;
- regras do modelo de entrada;
- normalização de níveis de detalhamento e aliases legados;
- montagem dinâmica do prompt;
- exclusão de interesses não selecionados do prompt;
- fallback para todos os interesses quando nenhum for marcado;
- fallback variado do roteiro para viagens mais longas;
- orquestração do serviço principal;
- validação da resposta estruturada.

Também foram adicionados testes automatizados com `pytest` para:

- rota `GET /teste`;
- `POST /planejar-viagem` com sucesso e validação de payload;
- `POST /planejar-viagem/stream` com retorno em streaming;
- cliente HTTP do frontend consumindo o backend.

Execute, se desejar:

```powershell
pytest
```

## Observações importantes

- o modelo de IA pode variar conforme a sua conta no Google AI Studio;
- a aplicação pede resposta estruturada em JSON, mas ainda assim reforça validação e fallback no backend;
- horários, clima, preços e disponibilidade devem sempre ser confirmados em fontes oficiais antes da viagem.

## Melhorias futuras sugeridas

- integração com APIs de clima e eventos em tempo real;
- cache de planejamentos por destino e período;
- exportação para PDF;
- histórico de viagens planejadas;
- autenticação de usuários.
