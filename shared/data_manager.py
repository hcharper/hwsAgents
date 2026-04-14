"""Loads, saves, and validates YAML data files. Triggers prompt rebuild on change."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from loguru import logger


class DataManager:
    """Manages pricing and objection YAML data files."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.pricing_path = self.data_dir / "pricing.yaml"
        self.objections_path = self.data_dir / "objections.yaml"
        self._pricing_data: dict | None = None
        self._objections_data: dict | None = None
        self._on_change_callbacks: list = []

    def on_change(self, callback) -> None:
        """Register a callback to be called when data changes."""
        self._on_change_callbacks.append(callback)

    def load(self) -> None:
        """Load both YAML files from disk."""
        self._pricing_data = self._load_yaml(self.pricing_path)
        self._objections_data = self._load_yaml(self.objections_path)
        logger.info("Loaded pricing data: {} products", len(self._pricing_data.get("products", [])))
        logger.info("Loaded objections: {} universal, {} per-product",
                     len(self._objections_data.get("universal", [])),
                     len(self._objections_data.get("per_product", {})))

    def _load_yaml(self, path: Path) -> dict:
        """Load a single YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict from {path}, got {type(data)}")
        return data

    @property
    def pricing(self) -> dict:
        if self._pricing_data is None:
            self.load()
        return self._pricing_data

    @property
    def objections(self) -> dict:
        if self._objections_data is None:
            self.load()
        return self._objections_data

    def save_pricing(self, data: dict) -> None:
        """Save pricing data to YAML, creating a backup first."""
        self._backup(self.pricing_path)
        self._save_yaml(self.pricing_path, data)
        self._pricing_data = data
        logger.info("Saved updated pricing data")
        self._notify_change()

    def save_objections(self, data: dict) -> None:
        """Save objections data to YAML, creating a backup first."""
        self._backup(self.objections_path)
        self._save_yaml(self.objections_path, data)
        self._objections_data = data
        logger.info("Saved updated objections data")
        self._notify_change()

    def _save_yaml(self, path: Path, data: dict) -> None:
        """Write data to a YAML file."""
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def _backup(self, path: Path) -> None:
        """Create a timestamped backup of a file before overwriting."""
        if path.exists():
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup = path.with_suffix(f".{ts}.bak")
            shutil.copy2(path, backup)
            logger.info("Backed up {} → {}", path.name, backup.name)

    def _notify_change(self) -> None:
        """Call all registered change callbacks."""
        for cb in self._on_change_callbacks:
            cb()

    def reload(self) -> None:
        """Reload data from disk and notify listeners."""
        self.load()
        self._notify_change()
