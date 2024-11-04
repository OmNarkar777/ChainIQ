"""
Standalone training script. Run from project root:
  python ml_training/train.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data.generator import main as generate_data
from backend.ml.trainer import train


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ChainIQ XGBoost Training")
    parser.add_argument("--generate", action="store_true", help="Regenerate synthetic data")
    parser.add_argument("--data-path", default="backend/data/sample_data.csv")
    parser.add_argument("--model-store", default="model_store")
    parser.add_argument("--horizon", type=int, default=7)
    args = parser.parse_args()

    csv_path = Path(args.data_path)
    if args.generate or not csv_path.exists():
        print("[setup] Generating synthetic dataset...")
        generate_data()

    model, meta = train(
        data_path=args.data_path,
        model_store_dir=args.model_store,
        target_horizon=args.horizon,
    )
    print(f"\n[ready] Run inference with:")
    print(f"  from backend.ml.predictor import DemandPredictor")
    print(f"  p = DemandPredictor(); p.load_model()")
    print(f"  print(p.predict_sku('SKU_0001'))")
