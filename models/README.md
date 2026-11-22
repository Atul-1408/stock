# Machine Learning Model Assets & Security Notice

## Model Assets
This directory stores serialized scikit-learn/joblib machine learning models used by the trading bot's AI validation engine:
- `apex_model_ensemble.pkl`: Voting/Ensemble classifier combining Gradient Boosting and Random Forest predictions.
- `apex_model_gb.pkl`: Gradient Boosting classifier.
- `apex_model_rf.pkl`: Random Forest classifier.

These files, along with `training_data.csv` and `data/trade_memory.csv`, are managed via **Git LFS** (see `.gitattributes`).

## Security & Deserialization Notice
> [!CAUTION]
> Python `pickle` and `joblib.load` can execute arbitrary code during unpickling.
>
> - **Only load `.pkl` models produced by your own trusted training pipeline** (`src/trading_bot/train_models.py`).
> - **Never deserialize** `.pkl` model files received from external, untrusted, or unverified sources.
> - If an untrusted model file is introduced, reject it and retrain using the internal synthetic/historical training pipeline.
