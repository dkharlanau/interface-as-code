from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import yaml

from .scaffold import profile_spec


class StandardImportError(ValueError):
    pass


def _load(path: str | Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StandardImportError(str(exc)) from exc
    if not isinstance(data, dict):
        raise StandardImportError("Contract document must be an object.")
    return data


def _relative_ref(contract_path: Path, output_dir: Path) -> str:
    try:
        return str(contract_path.resolve().relative_to(output_dir.resolve()))
    except ValueError:
        import os
        return os.path.relpath(contract_path.resolve(), output_dir.resolve())


def import_openapi(path: str | Path, *, interface_id: str, source: str, target: str, output_dir: str | Path) -> tuple[dict[str, Any], list[str]]:
    contract_path = Path(path)
    doc = _load(contract_path)
    version = str(doc.get("openapi", ""))
    if not version.startswith("3."):
        raise StandardImportError(f"Unsupported OpenAPI version: {version or 'missing'}")
    info = doc.get("info", {}) if isinstance(doc.get("info"), dict) else {}
    name = str(info.get("title") or f"OpenAPI interface {interface_id}")
    spec = profile_spec("rest-api", interface_id, name, source, target)
    spec["contract"]["version"] = str(info.get("version") or version)
    spec["contract"]["ref"] = {"kind": "openapi", "uri": _relative_ref(contract_path, Path(output_dir))}
    warnings: list[str] = []
    operations: list[tuple[str, str, dict[str, Any]]] = []
    for route, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete", "options", "head"):
            op = item.get(method)
            if isinstance(op, dict):
                operations.append((method.upper(), str(route), op))
    if operations:
        method, route, op = operations[0]
        spec["trigger"] = {"operation": f"{method} {route}"}
        request_body = op.get("requestBody", {}) if isinstance(op.get("requestBody"), dict) else {}
        content = request_body.get("content", {}) if isinstance(request_body.get("content"), dict) else {}
        if content:
            spec["contract"]["content_type"] = next(iter(content))
        if len(operations) > 1:
            warnings.append(f"OpenAPI contains {len(operations)} operations; imported the first. Split logical interfaces deliberately.")
    else:
        warnings.append("OpenAPI contains no supported path operation; trigger remains a TODO.")
    return spec, warnings


def import_asyncapi(path: str | Path, *, interface_id: str, source: str, target: str, output_dir: str | Path) -> tuple[dict[str, Any], list[str]]:
    contract_path = Path(path)
    doc = _load(contract_path)
    version = str(doc.get("asyncapi", ""))
    if not version.startswith(("2.", "3.")):
        raise StandardImportError(f"Unsupported AsyncAPI version: {version or 'missing'}")
    info = doc.get("info", {}) if isinstance(doc.get("info"), dict) else {}
    name = str(info.get("title") or f"AsyncAPI interface {interface_id}")
    spec = profile_spec("event", interface_id, name, source, target)
    spec["contract"]["version"] = str(info.get("version") or version)
    spec["contract"]["ref"] = {"kind": "asyncapi", "uri": _relative_ref(contract_path, Path(output_dir))}
    warnings: list[str] = []
    servers = doc.get("servers") or {}
    protocols = [str(v.get("protocol", "")) for v in servers.values() if isinstance(v, dict) and v.get("protocol")]
    if protocols:
        p = protocols[0].lower()
        if "kafka" in p:
            spec["contract"]["format"] = "Kafka"
        elif "jms" in p:
            spec["contract"]["format"] = "JMS"
    channels = doc.get("channels") or {}
    if channels:
        channel_name = next(iter(channels))
        spec["trigger"] = {"event": str(channel_name)}
        if len(channels) > 1:
            warnings.append(f"AsyncAPI contains {len(channels)} channels; imported the first as the logical interface trigger.")
    else:
        warnings.append("AsyncAPI contains no channels; trigger remains a TODO.")
    return spec, warnings


def imported_metadata(spec: dict[str, Any]) -> dict[str, Any]:
    return deepcopy({"name": spec.get("interface", {}).get("name"), "trigger": spec.get("trigger"), "contract": spec.get("contract")})
