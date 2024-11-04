"""
Model versioning: save, load, list XGBoost models.
"""

import json
from pathlib import Path
from typing import Optional
import xgboost as xgb


MODEL_STORE = Path("model_store")


def get_latest_version() -> Optional[str]:
    models = sorted(MODEL_STORE.glob("xgb_v*.json"))
    # Filter out meta files
    models = [m for m in models if "_meta" not in m.name]
    if not models:
        return None
    latest = models[-1]
    return latest.stem.replace("xgb_v", "")


def load_model(version: Optional[str] = None) -> xgb.XGBRegressor:
    if version is None:
        version = get_latest_version()
    if version is None:
        raise FileNotFoundError(
            "No trained model found. Run: python ml_training/train.py"
        )
    path = MODEL_STORE / f"xgb_v{version}.json"
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    model = xgb.XGBRegressor()
    model.load_model(str(path))
    return model


def load_meta(version: Optional[str] = None) -> dict:
    if version is None:
        version = get_latest_version()
    meta_path = MODEL_STORE / f"xgb_v{version}_meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text())


def list_models() -> list:
    return [
        {
            "version": p.stem.replace("xgb_v", ""),
            "path": str(p),
            "meta": load_meta(p.stem.replace("xgb_v", "")),
        }
        for p in sorted(MODEL_STORE.glob("xgb_v*.json"))
        if "_meta" not in p.name
    ]
