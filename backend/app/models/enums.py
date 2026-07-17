"""Enumerações do domínio, fiéis ao vocabulário do SINPE original."""
import enum


class UserRole(str, enum.Enum):
    """Papéis do SINPE: definem o que cada usuário pode fazer."""

    ADMIN = "administrador"        # único com acesso ao Protocolo Mestre
    VIEWER = "visualizador"
    COLLECTOR = "coletor"
    RESEARCHER = "pesquisador"


class ProtocolKind(str, enum.Enum):
    MASTER = "mestre"             # árvore com todos os parâmetros possíveis
    SPECIFIC = "especifico"       # subconjunto focado em uma patologia


class ItemType(str, enum.Enum):
    """Tipos de dado que um item da árvore suporta (como no SINPE)."""

    LOGICAL = "logical"          # marcado / não marcado
    NUMERIC = "numeric"
    TEXT = "text"
    DATETIME = "datetime"
    IMAGE = "image"
    SOUND = "sound"
    VIDEO = "video"


class SelectionType(str, enum.Enum):
    SINGLE = "single"            # única seleção entre filhos
    MULTIPLE = "multiple"        # múltipla seleção


class CollectionStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"        # "Finalizar coleta"


class CollectionSource(str, enum.Enum):
    MANUAL = "manual"
    AI = "ai"                    # pré-preenchido por IA de voz
