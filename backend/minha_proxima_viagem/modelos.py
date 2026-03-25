from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


_MAPA_INTERESSES = {
    "aventureiro": "Aventureiro",
    "economico": "Econômico",
    "gastronomico": "Gastronômico",
    "cultural": "Cultural",
    "relaxamento": "Relaxamento",
    "vida_noturna": "Vida noturna",
    "ecoturismo_sustentavel": "Ecoturismo/Sustentável",
}

_MAPA_NIVEIS_DETALHAMENTO = {
    "enxuto": {
        "rotulo": "Enxuto",
        "descricao": "retorno mais enxuto, direto ao ponto e com menos itens por seção",
        "itens_grupo": 3,
        "itens_interesse_selecionado": 3,
        "itens_interesse_sugestao": 2,
        "fontes": 3,
        "observacoes": 4,
    },
    "equilibrado": {
        "rotulo": "Equilibrado",
        "descricao": "equilíbrio entre objetividade e explicações mais úteis",
        "itens_grupo": 5,
        "itens_interesse_selecionado": 5,
        "itens_interesse_sugestao": 3,
        "fontes": 4,
        "observacoes": 5,
    },
    "detalhado": {
        "rotulo": "Detalhado",
        "descricao": "resposta mais completa, com mais contexto, sugestões e roteiro expandido",
        "itens_grupo": 7,
        "itens_interesse_selecionado": 6,
        "itens_interesse_sugestao": 4,
        "fontes": 5,
        "observacoes": 6,
    },
}

_MAPA_ALIASES_NIVEL_DETALHAMENTO = {
    "enxuto": "enxuto",
    "compacto": "enxuto",
    "equilibrado": "equilibrado",
    "padrao": "equilibrado",
    "padrão": "equilibrado",
    "detalhado": "detalhado",
}


def normalizar_nivel_detalhamento(valor: str | None) -> str:
    nivel = (valor or "equilibrado").strip().casefold()
    return _MAPA_ALIASES_NIVEL_DETALHAMENTO.get(nivel, "equilibrado")


def obter_parametros_detalhamento(nivel: str) -> dict[str, Any]:
    return dict(_MAPA_NIVEIS_DETALHAMENTO[normalizar_nivel_detalhamento(nivel)])


class InteressesViagem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    aventureiro: bool = False
    economico: bool = False
    gastronomico: bool = False
    cultural: bool = False
    relaxamento: bool = False
    vida_noturna: bool = False
    ecoturismo_sustentavel: bool = False

    @property
    def selecionados(self) -> list[str]:
        return [
            titulo
            for chave, titulo in _MAPA_INTERESSES.items()
            if getattr(self, chave)
        ]

    @property
    def todos(self) -> list[str]:
        return list(_MAPA_INTERESSES.values())


class SolicitacaoPlanoViagem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    data_inicio: date
    data_fim: date
    destino: str = Field(min_length=2, max_length=120)
    quantidade_adultos: int = Field(default=1, ge=0)
    quantidade_criancas: int = Field(default=0, ge=0)
    interesses: InteressesViagem = Field(default_factory=InteressesViagem)
    nivel_detalhamento: str = Field(
        default="equilibrado",
        validation_alias=AliasChoices("nivel_detalhamento", "nivel_detalhe"),
    )

    @field_validator("destino")
    @classmethod
    def validar_destino(cls, valor: str) -> str:
        destino = " ".join(valor.split())
        if len(destino) < 2:
            raise ValueError("Informe um destino válido com pelo menos 2 caracteres.")
        return destino

    @field_validator("nivel_detalhamento")
    @classmethod
    def validar_nivel_detalhamento(cls, valor: str) -> str:
        return normalizar_nivel_detalhamento(valor)

    @model_validator(mode="after")
    def validar_periodo_e_quantidades(self) -> "SolicitacaoPlanoViagem":
        if self.data_inicio > self.data_fim:
            raise ValueError("A data de início não pode ser posterior à data fim.")

        if (self.quantidade_adultos + self.quantidade_criancas) <= 0:
            raise ValueError("Informe ao menos 1 viajante entre adultos e crianças.")

        return self

    @property
    def quantidade_dias(self) -> int:
        return (self.data_fim - self.data_inicio).days + 1

    @property
    def periodo_formatado(self) -> str:
        return f"{self.data_inicio.strftime('%d/%m/%Y')} a {self.data_fim.strftime('%d/%m/%Y')}"

    @property
    def perfil_viajantes(self) -> str:
        partes = [f"{self.quantidade_adultos} adulto(s)"]
        if self.quantidade_criancas:
            partes.append(f"{self.quantidade_criancas} criança(s)")
        return ", ".join(partes)

    @property
    def parametros_detalhamento(self) -> dict[str, Any]:
        return obter_parametros_detalhamento(self.nivel_detalhamento)


class GrupoConteudo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    titulo: str
    resumo: str
    itens: list[str] = Field(default_factory=list)


class RoteiroDiario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dia: int = Field(ge=1)
    data: str
    tema_dia: str = ""
    manha: str
    tarde: str
    noite: str
    observacoes: str = ""


class PlanoViagemGerado(BaseModel):
    model_config = ConfigDict(extra="ignore")

    destino: str
    periodo_viagem: str
    total_dias: int = Field(ge=1)
    perfil_viajantes: str
    resumo_historia: GrupoConteudo
    contexto_periodo: GrupoConteudo
    interesses: list[GrupoConteudo] = Field(default_factory=list)
    dicas_seguranca: GrupoConteudo
    roteiro_dia_a_dia: list[RoteiroDiario] = Field(default_factory=list)
    observacoes_gerais: list[str] = Field(default_factory=list)
    fontes_recomendadas: list[str] = Field(default_factory=list)
    modelo_utilizado: str | None = None
    familia_modelo: str | None = None
    nivel_detalhamento: str = "equilibrado"
    origem_cache: bool = False
    aviso_importante: str = (
        "Confirme preços, horários de funcionamento, clima e disponibilidade em canais oficiais antes de viajar."
    )

