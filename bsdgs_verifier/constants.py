from __future__ import annotations

APP_NAME = "BSDGs — Verificador de Atualização"
APP_SLUG = "BSDGs_Verificador_Atualizacao"
APP_VERSION = "1.3.1"
TASK_NAME = "BSDGs - Verificador de Atualizacao"
CONFIG_VERSION = 3
DATABASE_SCHEMA_VERSION = 1

DEVELOPER_NAME = "Nathan Damas"
DEVELOPER_GITHUB_URL = "https://github.com/nathandamas"
LAGEAMB_SITE_URL = "https://lageamb.ufpr.br/"
LOCAL_OPERATION_NOTICE = (
    "Aplicação local: verifica somente pastas sincronizadas pelo OneDrive nesta máquina. "
    "Não acessa o SharePoint diretamente."
)

DAY_CODES = {
    "Segunda-feira": "MON",
    "Terça-feira": "TUE",
    "Quarta-feira": "WED",
    "Quinta-feira": "THU",
    "Sexta-feira": "FRI",
    "Sábado": "SAT",
    "Domingo": "SUN",
}
DAY_NAMES_BY_CODE = {value: key for key, value in DAY_CODES.items()}

# Windows file attributes used by OneDrive Files On-Demand.
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_PINNED = 0x00080000
FILE_ATTRIBUTE_UNPINNED = 0x00100000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000

CORE_GEOMETRY_TYPES = {
    "GEOMETRY",
    "POINT",
    "LINESTRING",
    "POLYGON",
    "MULTIPOINT",
    "MULTILINESTRING",
    "MULTIPOLYGON",
    "GEOMETRYCOLLECTION",
}

# Tipos estendidos usuais. São aceitos como declaração conhecida, mas o programa
# não tenta validar semanticamente todos os blobs geométricos sem GDAL/OGR.
EXTENDED_GEOMETRY_TYPES = {
    "CIRCULARSTRING",
    "COMPOUNDCURVE",
    "CURVEPOLYGON",
    "MULTICURVE",
    "MULTISURFACE",
    "CURVE",
    "SURFACE",
    "POLYHEDRALSURFACE",
    "TIN",
    "TRIANGLE",
}

KNOWN_GEOMETRY_TYPES = CORE_GEOMETRY_TYPES | EXTENDED_GEOMETRY_TYPES
