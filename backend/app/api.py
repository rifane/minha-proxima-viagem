import sys
import json
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

from backend.minha_proxima_viagem.configuracao import obter_configuracao
from backend.minha_proxima_viagem.excecoes import ErroIntegracaoIA, ErroPlanejamentoViagem
from backend.minha_proxima_viagem.logs import configurar_logs, obter_logger
from backend.minha_proxima_viagem.modelos import PlanoViagemGerado, SolicitacaoPlanoViagem
from backend.minha_proxima_viagem.servico_planejamento import instanciar_servico_planejamento


configurar_logs()
configuracao = obter_configuracao()
logger = obter_logger(__name__)
servico_planejamento = instanciar_servico_planejamento()

app = FastAPI(
    title=configuracao.nome_aplicacao,
    version="1.0.0",
    description="API para geração de mini planejamentos de viagem com apoio do Gemini.",
)
app.state.servico_planejamento = servico_planejamento


def obter_servico_planejamento_atual() -> object:
    return app.state.servico_planejamento


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao_request(_: Request, erro: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detalhe": jsonable_encoder(erro.errors())})


@app.exception_handler(ValidationError)
async def tratar_erro_validacao_modelo(_: Request, erro: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detalhe": jsonable_encoder(erro.errors())})


@app.exception_handler(ErroIntegracaoIA)
async def tratar_erro_integracao(_: Request, erro: ErroIntegracaoIA) -> JSONResponse:
    logger.error("Falha de integração com IA | codigo=%s | detalhe=%s", erro.codigo_erro, erro.mensagem_tecnica)
    return JSONResponse(status_code=erro.status_code, content=erro.para_resposta())


@app.exception_handler(ErroPlanejamentoViagem)
async def tratar_erro_aplicacao(_: Request, erro: ErroPlanejamentoViagem) -> JSONResponse:
    logger.exception("Erro de aplicação: %s", erro)
    return JSONResponse(status_code=400, content={"detalhe": str(erro)})


@app.exception_handler(Exception)
async def tratar_erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
    logger.exception("Erro inesperado na API: %s", erro)
    return JSONResponse(status_code=500, content={"detalhe": "Ocorreu um erro interno ao gerar o planejamento."})


@app.get("/")
def raiz() -> dict[str, str]:
    return {
        "aplicacao": configuracao.nome_aplicacao,
        "mensagem": "Use o endpoint POST /planejar-viagem para gerar seu plano.",
    }


@app.get("/teste")
def teste() -> dict[str, object]:
    return {
        "ok": True,
        "mensagem": "API operacional para receber solicitações de planejamento.",
        "rota_principal": "/planejar-viagem",
        "streaming_disponivel": True,
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "aplicacao": configuracao.nome_aplicacao,
        "ambiente": configuracao.ambiente,
        "gemini_configurado": configuracao.gemini_configurado,
        "rota_teste": "/teste",
        "rota_planejamento": "/planejar-viagem",
        "rota_streaming": "/planejar-viagem/stream",
    }


@app.post("/planejar-viagem", response_model=PlanoViagemGerado)
def planejar_viagem(payload: SolicitacaoPlanoViagem) -> PlanoViagemGerado:
    logger.info("Nova solicitação recebida para destino=%s", payload.destino)
    return obter_servico_planejamento_atual().gerar_plano(payload)


def _gerar_eventos_planejamento(payload: SolicitacaoPlanoViagem) -> Iterator[str]:
    yield json.dumps(
        {
            "tipo": "status",
            "mensagem": "Solicitação recebida. Iniciando geração do planejamento.",
            "destino": payload.destino,
        },
        ensure_ascii=False,
    ) + "\n"

    try:
        plano = obter_servico_planejamento_atual().gerar_plano(payload)
        yield json.dumps(
            {
                "tipo": "resultado",
                "plano": jsonable_encoder(plano),
            },
            ensure_ascii=False,
        ) + "\n"
        yield json.dumps({"tipo": "fim", "mensagem": "Planejamento concluído."}, ensure_ascii=False) + "\n"
    except ErroIntegracaoIA as erro:
        yield json.dumps(
            {
                "tipo": "erro",
                "erro": erro.para_resposta(),
            },
            ensure_ascii=False,
        ) + "\n"
    except Exception as erro:
        logger.exception("Erro inesperado no streaming da API: %s", erro)
        yield json.dumps(
            {
                "tipo": "erro",
                "erro": {"detalhe": "Ocorreu um erro interno ao gerar o planejamento."},
            },
            ensure_ascii=False,
        ) + "\n"


@app.post("/planejar-viagem/stream")
def planejar_viagem_stream(payload: SolicitacaoPlanoViagem) -> StreamingResponse:
    logger.info("Nova solicitação em streaming recebida para destino=%s", payload.destino)
    return StreamingResponse(_gerar_eventos_planejamento(payload), media_type="application/x-ndjson")
