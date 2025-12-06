"""Dynamic discovery and dispatch logic for plugins."""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List

from .base import BasePlugin


class PluginManager:
    def __init__(self, package: str = "smart_customer_service.plugins", **deps):
        self.package = package
        self.deps = deps
        self._plugins: Dict[str, BasePlugin] = {}
        self._capability_index: Dict[str, str] = {}
        self.reload()

    @property
    def plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def reload(self) -> None:
        self._plugins.clear()
        self._capability_index.clear()
        module = importlib.import_module(self.package)
        package_path = Path(module.__file__).parent
        for finder, name, ispkg in pkgutil.iter_modules([str(package_path)]):
            if ispkg:
                continue
            full_name = f"{self.package}.{name}"
            loaded = importlib.import_module(full_name)
            if hasattr(loaded, "build_plugin"):
                plugin: BasePlugin = loaded.build_plugin(**self.deps)
                self._plugins[plugin.metadata.name] = plugin
                for capability in plugin.metadata.capabilities:
                    self._capability_index[capability] = plugin.metadata.name

    def dispatch(self, capability: str, payload: dict):
        plugin_name = self._capability_index.get(capability)
        if not plugin_name:
            raise ValueError(f"未找到能力 {capability} 对应的插件")
        plugin = self._plugins[plugin_name]
        return plugin.handle(payload)
