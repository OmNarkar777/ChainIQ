"""
Docker build step 1: generate synthetic dataset and train XGBoost model.
Called by Dockerfile — do not run manually (use ml_training/train.py instead).
"""
import sys
from pathlib import Path

sys.path.insert(0, ".")

data_path = Path("backend/data/sample_data.csv")
model_store = Path("model_store")

if not data_path.exists():
    print("[build] Generating synthetic dataset...")
    from backend.data.generator import main as generate_data
    generate_data()
    print("[build] Dataset ready.")
else:
    print(f"[build] Dataset already present ({data_path.stat().st_size // 1024}KB).")

existing = (
    [m for m in sorted(model_store.glob("xgb_v*.json")) if "_meta" not in m.name]
    if model_store.exists()
    else []
)
if not existing:
    print("[build] Training XGBoost model (first-time build, ~3s)...")
    from backend.ml.trainer import train
    train()
    print("[build] Model trained and saved.")
else:
    print(f"[build] Model already present: {existing[-1]}")
