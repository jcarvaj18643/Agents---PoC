from enum import Enum


class Language(str, Enum):
    """Programming languages the agent can operate on."""

    PYTHON = "python"
    CSHARP = "csharp"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    HTML = "html"
    SCSS = "scss"
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    TOML = "toml"
    CONFIG = "config"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    SQL = "sql"
    UNKNOWN = "unknown"
