"""
Configuration loading and validation for Cerberus.

Supports YAML or JSON at ~/.cerberus/config.yaml (default).
Environment variables take precedence over file values for secrets.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


DEFAULT_CONFIG_DIR = Path.home() / ".cerberus"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_BASE_URL = "https://gen.pollinations.ai/v1"
DEFAULT_MODEL = "kimi"
DEFAULT_TIMEOUT = 120.0
DEFAULT_BASH_TIMEOUT = 45
DEFAULT_MAX_TOOL_ROUNDS = 48
DEFAULT_WORKSPACE = Path.cwd()


@dataclass
class ProviderConfig:
    """OpenAI-compatible chat-completions provider settings."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL
    models: list[str] = field(default_factory=lambda: ["kimi", "deepseek", "hermes", "openai"])
    provider_models: dict[str, dict[str, Any]] = field(default_factory=dict)
    timeout: float = DEFAULT_TIMEOUT
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    stream_final: bool = True


@dataclass
class ToolConfig:
    """Local tool execution constraints and safety boundaries."""

    bash_timeout: int = DEFAULT_BASH_TIMEOUT
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS
    enforce_workspace_boundary: bool = True
    enforce_cerberusignore: bool = True
    redact_secrets_in_output: bool = True
    extra_destructive_patterns: list[str] = field(default_factory=list)
    approve_external: bool = True
    approve_builds: bool = True
    permissions: dict[str, str] = field(default_factory=dict)


@dataclass
class UIConfig:
    """Terminal presentation preferences."""

    show_tool_args: bool = True
    syntax_theme: str = "monokai"
    spinner_style: str = "dots"
    theme: str = "verdant"


@dataclass
class AgentPolicyConfig:
    """Per-persona policy settings, tool allowances, and default execution mode."""

    default_mode: str = "build"
    max_rounds: int = 32
    allowed_tools: list[str] = field(default_factory=list)


DEFAULT_AGENT_POLICIES: dict[str, dict[str, Any]] = {
    "sentinel": {
        "default_mode": "build",
        "max_rounds": 48,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log",
        ],
    },
    "vault": {
        "default_mode": "plan",
        "max_rounds": 32,
        "allowed_tools": [
            "read_file", "search_workspace", "list_symbols",
            "git_status", "git_diff", "git_log", "create_pull_request",
        ],
    },
    "gatekeeper": {
        "default_mode": "plan",
        "max_rounds": 32,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "git_status", "git_diff", "git_log",
        ],
    },
    "librarian": {
        "default_mode": "build",
        "max_rounds": 36,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "execute_bash_command", "browse_web_content", "git_status", "git_diff", "git_log",
        ],
    },
    "conduit": {
        "default_mode": "build",
        "max_rounds": 36,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log",
        ],
    },
    "watchtower": {
        "default_mode": "build",
        "max_rounds": 36,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log",
        ],
    },
    "shield": {
        "default_mode": "build",
        "max_rounds": 36,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "git_status", "git_diff", "git_log",
        ],
    },
    "auditor": {
        "default_mode": "build",
        "max_rounds": 32,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "git_status", "git_diff", "git_log",
        ],
    },
    "architect": {
        "default_mode": "build",
        "max_rounds": 36,
        "allowed_tools": [
            "read_file", "edit_file", "multiedit_file", "search_workspace",
            "list_symbols", "git_status", "git_diff", "git_log",
        ],
    },
}


@dataclass
class AppConfig:
    """Root Cerberus agent configuration."""

    provider: ProviderConfig = field(default_factory=ProviderConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    workspace: Path = field(default_factory=lambda: DEFAULT_WORKSPACE)
    system_prompt_extra: str = ""
    agent_mode: str = "plan"  # "build" or "plan" — plan is the safe default
    auto_save: bool = True
    agents: dict[str, AgentPolicyConfig] = field(default_factory=dict)

    def resolve_api_key(self) -> str:
        from servers.auth.store import resolve_api_key as _resolve

        found = _resolve(config_file_key=self.provider.api_key)
        return found.key if found else ""

    def policy_for(self, agent_name: str) -> AgentPolicyConfig:
        key = (agent_name or "").lower()
        if key in self.agents:
            return self.agents[key]
        default = DEFAULT_AGENT_POLICIES.get(key, {})
        return AgentPolicyConfig(
            default_mode=default.get("default_mode", "build"),
            max_rounds=default.get("max_rounds", DEFAULT_MAX_TOOL_ROUNDS),
            allowed_tools=list(default.get("allowed_tools", [])),
        )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _load_raw(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required for .yaml configs. Install PyYAML or use config.json."
            )
        data = yaml.safe_load(text) or {}
    elif suffix == ".json":
        data = json.loads(text) if text.strip() else {}
    else:
        if yaml is not None:
            try:
                data = yaml.safe_load(text) or {}
            except Exception:
                data = json.loads(text) if text.strip() else {}
        else:
            data = json.loads(text) if text.strip() else {}

    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping, got {type(data).__name__}")
    return data


def _normalize_models(raw: Any) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Accept models as [id…], [{id, base_url?, api_key_env?, temperature?}], or {id: {...}}."""
    ids: list[str] = []
    meta: dict[str, dict[str, Any]] = {}

    def _meta_for(mid: str, raw_meta: Any) -> None:
        if isinstance(raw_meta, dict):
            kept = {k: raw_meta[k] for k in ("base_url", "api_key_env", "temperature") if k in raw_meta}
            if kept:
                meta[mid] = kept

    if isinstance(raw, dict):
        for mid, raw_meta in raw.items():
            ids.append(str(mid))
            _meta_for(str(mid), raw_meta)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
                _meta_for(str(item["id"]), item)
            elif isinstance(item, str) and item.strip():
                ids.append(item.strip())
    if not ids:
        ids = ["kimi", "deepseek", "hermes", "openai"]
    return ids, meta


def _from_dict(data: dict[str, Any]) -> AppConfig:
    prov = data.get("provider") or {}
    tools = data.get("tools") or {}
    ui = data.get("ui") or {}
    agents_raw = data.get("agents") or {}
    model_ids, model_meta = _normalize_models(prov.get("models"))
    raw_permissions: dict[str, Any] = {}
    for section in (tools.get("permissions"), data.get("permissions")):
        if isinstance(section, dict):
            raw_permissions.update(section)
    permissions = {
        str(k): str(v).lower()
        for k, v in raw_permissions.items()
        if str(v).lower() in {"allow", "ask", "deny"}
    }

    provider = ProviderConfig(
        base_url=str(prov.get("base_url", DEFAULT_BASE_URL)).rstrip("/"),
        api_key=str(prov.get("api_key", "") or ""),
        model=str(prov.get("model", DEFAULT_MODEL)),
        models=model_ids,
        provider_models=model_meta,
        timeout=float(prov.get("timeout", DEFAULT_TIMEOUT)),
        temperature=float(prov.get("temperature", 0.2)),
        max_tokens=prov.get("max_tokens"),
        stream_final=bool(prov.get("stream_final", True)),
    )

    tool_cfg = ToolConfig(
        bash_timeout=int(tools.get("bash_timeout", DEFAULT_BASH_TIMEOUT)),
        max_tool_rounds=int(tools.get("max_tool_rounds", DEFAULT_MAX_TOOL_ROUNDS)),
        enforce_workspace_boundary=bool(tools.get("enforce_workspace_boundary", True)),
        enforce_cerberusignore=bool(tools.get("enforce_cerberusignore", True)),
        redact_secrets_in_output=bool(tools.get("redact_secrets_in_output", True)),
        extra_destructive_patterns=list(tools.get("extra_destructive_patterns") or []),
        approve_external=bool(tools.get("approve_external", True)),
        approve_builds=bool(tools.get("approve_builds", True)),
        permissions=permissions,
    )

    ui_cfg = UIConfig(
        show_tool_args=bool(ui.get("show_tool_args", True)),
        syntax_theme=str(ui.get("syntax_theme", "monokai")),
        spinner_style=str(ui.get("spinner_style", "dots")),
        theme=str(ui.get("theme", "verdant")),
    )

    workspace_raw = data.get("workspace") or str(DEFAULT_WORKSPACE)
    workspace = Path(workspace_raw).expanduser().resolve()

    mode = str(data.get("agent_mode") or "plan").strip().lower()
    if mode not in {"build", "plan"}:
        mode = "plan"

    auto_save = bool(data.get("auto_save", True))

    agents: dict[str, AgentPolicyConfig] = {}
    for name, a_info in agents_raw.items():
        if isinstance(a_info, dict):
            agents[str(name).lower()] = AgentPolicyConfig(
                default_mode=str(a_info.get("default_mode", "build")),
                max_rounds=int(a_info.get("max_rounds", DEFAULT_MAX_TOOL_ROUNDS)),
                allowed_tools=list(a_info.get("allowed_tools") or []),
            )

    return AppConfig(
        provider=provider,
        tools=tool_cfg,
        ui=ui_cfg,
        workspace=workspace,
        system_prompt_extra=str(data.get("system_prompt_extra") or ""),
        agent_mode=mode,
        auto_save=auto_save,
        agents=agents,
    )


PROJECT_CONFIG_NAME = "cerberus.yaml"
PROJECT_CONFIG_DIRNAME = ".cerberus"
PROJECT_MEMORY_NAME = "CERBERUS.md"


def project_config_path(directory: Optional[Path] = None) -> Path:
    """Project config location: <dir>/.cerberus/cerberus.yaml (or .json)."""
    base = Path(directory).expanduser() if directory else Path.cwd()
    yaml_path = base / PROJECT_CONFIG_DIRNAME / PROJECT_CONFIG_NAME
    json_path = yaml_path.with_suffix(".json")
    if not yaml_path.exists() and json_path.exists():
        return json_path
    return yaml_path


def load_config(
    config_path: Optional[Path] = None,
    *,
    workspace_override: Optional[Path] = None,
    model_override: Optional[str] = None,
    base_url_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
    mode_override: Optional[str] = None,
    project_dir: Optional[Path] = None,
) -> AppConfig:
    """
    Load AppConfig with full cascade:
      1. Hardcoded defaults
      2. Global file (config_path or ~/.cerberus/config.yaml / json)
      3. Project file (./.cerberus/cerberus.yaml — deep-merged over global)
      4. ./CERBERUS.md project memory (appended to system instructions)
      5. Environment variable overrides (CERBERUS_API_KEY, POLLINATIONS_API_KEY, OPENAI_API_KEY)
      6. Explicit runtime CLI argument overrides
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    raw = _load_raw(path) if path.exists() else {}
    project_path = project_config_path(project_dir)
    project_raw = _load_raw(project_path) if project_path.exists() else {}
    if project_raw:
        raw = _deep_merge(dict(raw), project_raw)
    cfg = _from_dict(raw)

    # CLI workspace wins for project-memory discovery; else CWD project dir.
    if workspace_override:
        cfg.workspace = Path(workspace_override).expanduser().resolve()
    memory_dir = cfg.workspace if workspace_override else (Path(project_dir) if project_dir else Path.cwd())
    memory_file = memory_dir / PROJECT_MEMORY_NAME
    if memory_file.is_file():
        try:
            extra = memory_file.read_text(encoding="utf-8").strip()
        except OSError:
            extra = ""
        if extra:
            joined = (cfg.system_prompt_extra + "\n\n" + extra).strip()
            cfg.system_prompt_extra = joined

    # Env overlays
    env_base = os.environ.get("CERBERUS_BASE_URL") or os.environ.get("OPENCODE_HARNESS_BASE_URL")
    if env_base:
        cfg.provider.base_url = env_base.rstrip("/")
    env_model = os.environ.get("CERBERUS_MODEL") or os.environ.get("OPENCODE_HARNESS_MODEL")
    if env_model:
        cfg.provider.model = env_model

    # CLI overrides
    if model_override:
        cfg.provider.model = model_override
    if base_url_override:
        cfg.provider.base_url = base_url_override.rstrip("/")
    if api_key_override:
        cfg.provider.api_key = api_key_override
    if mode_override and mode_override.lower() in {"build", "plan"}:
        cfg.agent_mode = mode_override.lower()

    return cfg


PERMISSION_TARGETS = ("external", "builds")


def effective_tier(tools: ToolConfig, kind: str) -> str:
    """Persisted allow|ask|deny for a gate kind (no session state).

    Kinds: "external", "builds", or "external:<tool>".
    Precedence: per-tool map > category map > legacy booleans.
    """
    override = tools.permissions.get(kind, "")
    if override in {"allow", "ask", "deny"}:
        return override
    category = "external" if kind.startswith("external") else "builds"
    cat = tools.permissions.get(category, "")
    if cat in {"allow", "ask", "deny"}:
        return cat
    if category == "external":
        return "allow" if not tools.approve_external else "ask"
    return "allow" if not tools.approve_builds else "ask"


def set_permission_tier(tools: ToolConfig, target: str, tier: str) -> None:
    """Set a tier in memory, keeping legacy booleans in sync."""
    tools.permissions[target] = tier
    if target == "external":
        tools.approve_external = tier != "allow"
    elif target == "builds":
        tools.approve_builds = tier != "allow"


SECRET_KEY_PARTS = ("api_key", "apikey", "token", "secret", "password")


def _coerce_value(text: str) -> Any:
    low = text.strip().lower()
    if low in {"true", "yes", "on"}:
        return True
    if low in {"false", "no", "off"}:
        return False
    if low in {"null", "none", "~", ""}:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def _write_raw(path: Path, raw: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    elif yaml is not None:
        path.write_text(yaml.safe_dump(raw, default_flow_style=False), encoding="utf-8")
    else:
        raise RuntimeError("PyYAML is required to write .yaml configs (or use a .json path).")
    return path


def config_set(config_path: Optional[Path], dotted: str, value: str) -> Path:
    """Set a dotted key (e.g. provider.model) in a config file. Secrets refused."""
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        raise ValueError("Empty key.")
    if any(secret in p.lower() for p in parts for secret in SECRET_KEY_PARTS):
        raise ValueError(f"Refusing to persist a secret via config ({dotted}).")
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.exists():
        raw = _load_raw(path)
        if not isinstance(raw, dict):
            raw = {}
    node = raw
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = _coerce_value(value)
    return _write_raw(path, raw)


def config_unset(config_path: Optional[Path], dotted: str) -> Path:
    """Remove a dotted key from a config file (no-op when absent)."""
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        raise ValueError("Empty key.")
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.exists():
        raw = _load_raw(path)
        if not isinstance(raw, dict):
            raw = {}
    node = raw
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            return path
        node = child
    node.pop(parts[-1], None)
    return _write_raw(path, raw)


def config_get(cfg: AppConfig, dotted: str) -> Any:
    """Read a dotted key from an AppConfig (dataclasses, dicts, Paths)."""
    node: Any = cfg
    for part in dotted.split("."):
        if isinstance(node, dict):
            node = node.get(part)
        else:
            node = getattr(node, part, None)
        if node is None:
            raise KeyError(dotted)
    if isinstance(node, Path):
        return str(node)
    return node


def scaffold_project(directory: Optional[Path] = None) -> tuple[Path, Path, bool, bool]:
    """Write ./.cerberus/cerberus.yaml + ./CERBERUS.md (never overwrite).

    Returns (config_path, memory_path, config_created, memory_created).
    """
    from servers.commands import init_project_file  # lazy: keep config stdlib-light

    base = Path(directory).expanduser().resolve() if directory else Path.cwd()
    cfg_path = base / PROJECT_CONFIG_DIRNAME / PROJECT_CONFIG_NAME
    mem_path = base / PROJECT_MEMORY_NAME
    cfg_created = False
    if not cfg_path.exists() and not cfg_path.with_suffix(".json").exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(
            '# Cerberus project config — merged over ~/.cerberus/config.yaml\n'
            'agent_mode: "plan"\n'
            'provider:\n'
            '  model: "kimi"\n'
            'tools:\n'
            '  approve_external: true\n'
            '  approve_builds: true\n',
            encoding="utf-8",
        )
        cfg_created = True
    mem_msg = init_project_file(base)
    return cfg_path, mem_path, cfg_created, "Wrote project memory" in mem_msg


def save_model(model: str, config_path: Optional[Path] = None) -> Path:
    """Persist provider.model to the config file (YAML or JSON aware)."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.exists():
        try:
            raw = _load_raw(path)
        except Exception:
            raw = {}
    provider = raw.get("provider")
    if not isinstance(provider, dict):
        provider = {}
        raw["provider"] = provider
    provider["model"] = model
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    elif yaml is not None:
        path.write_text(yaml.safe_dump(raw, default_flow_style=False), encoding="utf-8")
    else:
        # No PyYAML: surgical text edit of the `model:` line under
        # `provider:` — never clobber the rest of the YAML file.
        _set_yaml_model_text(path, model)
    return path


def _set_yaml_model_text(path: Path, model: str) -> None:
    """Replace the provider.model line in a YAML file without a YAML parser."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out: list[str] = []
    in_provider = False
    done = False
    for ln in lines:
        stripped = ln.strip()
        if ln and not ln[0] in " \t" and stripped and not stripped.startswith("#"):
            in_provider = stripped == "provider:"
        if in_provider and not done and re.match(r"\s*model\s*:", ln):
            indent = ln[: len(ln) - len(ln.lstrip())]
            out.append(f'{indent}model: "{model}"')
            done = True
        else:
            out.append(ln)
    if not done:
        if not any(l.strip() == "provider:" for l in out):
            out.append("provider:")
        out.append(f'  model: "{model}"')
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def ensure_default_config() -> Path:
    """Create a commented default config.yaml at ~/.cerberus/config.yaml if absent."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    body = f"""# Cerberus Agent Configuration
# Saved at {DEFAULT_CONFIG_PATH}

provider:
  base_url: "https://gen.pollinations.ai/v1"
  model: "kimi"
  models:
    - "kimi"
    - "deepseek"
    - "hermes"
    - "openai"
  timeout: 120.0
  temperature: 0.2

tools:
  bash_timeout: 45
  max_tool_rounds: 48
  enforce_workspace_boundary: true
  enforce_cerberusignore: true
  redact_secrets_in_output: true
  approve_external: true   # ask before web fetches / searches / PR creation
  approve_builds: true     # ask before build & test commands (pytest, npm, make…)

ui:
  theme: "verdant"
  show_tool_args: true

agent_mode: "plan"
auto_save: true
"""
    DEFAULT_CONFIG_PATH.write_text(body, encoding="utf-8")
    return DEFAULT_CONFIG_PATH
