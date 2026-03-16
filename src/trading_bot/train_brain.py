"""
Enhanced AI Brain Training - Multiple Models with Hyperparameter Tuning

This enhanced training system:
- Loads high-quality training data from data_collector.py
- Implements multiple ML models with ensemble voting
- Performs hyperparameter tuning using GridSearchCV
- Uses time series cross-validation
- Provides detailed feature importance analysis
- Saves multiple model variants for comparison
"""

# Fix for sklearn hanging on import (Windows-specific issue)
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TRAINING_DATA_FILE = "training_data.csv"  # New high-quality data
OLD_MEMORY_FILE = "trade_memory.csv"      # Legacy data
MODEL_DIR = "models"

# Model filenames
MODELS = {
    'rf': 'apex_model_rf.pkl',
    'gb': 'apex_model_gb.pkl',
    'ensemble': 'apex_model_ensemble.pkl'
}

# Feature configuration
FEATURES = [
    'rsi', 'adx', 'atr', 'ema_9', 'ema_21', 'ema_50', 'ema_200',
    'supertrend', 'vwap', 'fvg_bullish', 'fvg_bearish', 
    'liquidity_sweep', 'volume_spike', 'market_regime', 'volatility_regime'
]

def load_training_data():
    """Load and prepare training data"""
    # Try new training data first
    if os.path.exists(TRAINING_DATA_FILE):
        logger.info(f"Loading high-quality training data from {TRAINING_DATA_FILE}")
        df = pd.read_csv(TRAINING_DATA_FILE)
        # Convert outcome to binary (WIN=1, LOSS=0)
        df['target'] = (df['outcome'] == 'WIN').astype(int)
        return df
    
    # Fallback to old memory data
    elif os.path.exists(OLD_MEMORY_FILE):
        logger.warning(f"Using legacy data from {OLD_MEMORY_FILE}")
        df = pd.read_csv(OLD_MEMORY_FILE)
        df.columns = df.columns.str.lower()
        return df
    
    else:
        logger.error("No training data found!")
        return None

def prepare_features(df):
    """Prepare and engineer features"""
    if df is None or df.empty:
        return None, None
        
    # Select available features
    available_features = [f for f in FEATURES if f in df.columns]
    logger.info(f"Available features: {available_features}")
    
    # Handle missing values
    X = df[available_features].fillna(0)
    
    # Feature engineering
    if 'rsi' in X.columns:
        # RSI-based features
        X['rsi_overbought'] = (X['rsi'] > 70).astype(int)
        X['rsi_oversold'] = (X['rsi'] < 30).astype(int)
        X['rsi_neutral'] = ((X['rsi'] >= 30) & (X['rsi'] <= 70)).astype(int)
    
    if 'adx' in X.columns:
        # Trend strength features
        X['trend_strong'] = (X['adx'] > 25).astype(int)
        X['trend_weak'] = (X['adx'] <= 25).astype(int)
    
    if 'atr' in X.columns and 'close' in df.columns:
        # Volatility features
        X['volatility_high'] = (X['atr'] / df['close'] > 0.02).astype(int)  # 2% threshold
    
    # Target variable
    if 'target' in df.columns:
        y = df['target']
    elif 'result' in df.columns:
        y = df['result']
    else:
        logger.error("No target variable found!")
        return None, None
    
    logger.info(f"Feature matrix shape: {X.shape}")
    logger.info(f"Target distribution: {y.value_counts().to_dict()}")
    
    return X, y

def train_random_forest(X, y):
    """Train optimized Random Forest model"""
    logger.info("Training Random Forest model...")
    
    # Hyperparameter grid
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }
    
    # Time series cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    # Grid search
    rf = RandomForestClassifier(random_state=42)
    grid_search = GridSearchCV(
        rf, param_grid, 
        cv=tscv, 
        scoring='roc_auc',
        n_jobs=-1,
        verbose=1
    )
    
    grid_search.fit(X, y)
    
    logger.info(f"Best RF parameters: {grid_search.best_params_}")
    logger.info(f"Best RF score: {grid_search.best_score_:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': grid_search.best_estimator_.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("Top 10 important features:")
    logger.info(feature_importance.head(10))
    
    return grid_search.best_estimator_

def train_gradient_boosting(X, y):
    """Train optimized Gradient Boosting model"""
    logger.info("Training Gradient Boosting model...")
    
    # Hyperparameter grid
    param_grid = {
        'n_estimators': [50, 100, 200],
        'learning_rate': [0.01, 0.1, 0.2],
        'max_depth': [3, 5, 7],
        'subsample': [0.8, 1.0]
    }
    
    # Time series cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    # Grid search
    gb = GradientBoostingClassifier(random_state=42)
    grid_search = GridSearchCV(
        gb, param_grid,
        cv=tscv,
        scoring='roc_auc',
        n_jobs=-1,
        verbose=1
    )
    
    grid_search.fit(X, y)
    
    logger.info(f"Best GB parameters: {grid_search.best_params_}")
    logger.info(f"Best GB score: {grid_search.best_score_:.4f}")
    
    return grid_search.best_estimator_

def train_ensemble(X, y, models):
    """Train ensemble voting classifier"""
    logger.info("Training Ensemble model...")
    
    # Create ensemble
    ensemble = VotingClassifier(
        estimators=[(name, model) for name, model in models.items()],
        voting='soft'  # Use probability averaging
    )
    
    # Time series cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    scores = cross_val_score(ensemble, X, y, cv=tscv, scoring='roc_auc')
    
    logger.info(f"Ensemble CV scores: {scores}")
    logger.info(f"Ensemble mean score: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
    
    # Train on full dataset
    ensemble.fit(X, y)
    
    return ensemble

def evaluate_model(model, X, y, model_name):
    """Comprehensive model evaluation"""
    logger.info(f"\n=== Evaluating {model_name} ===")
    
    # Predictions
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    
    # Metrics
    accuracy = (y_pred == y).mean()
    auc_score = roc_auc_score(y, y_prob)
    
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"AUC-ROC: {auc_score:.4f}")
    
    # Classification report
    logger.info("\nClassification Report:")
    logger.info(classification_report(y, y_pred, target_names=['LOSS', 'WIN']))
    
    # Confusion matrix
    cm = confusion_matrix(y, y_pred)
    logger.info(f"\nConfusion Matrix:")
    logger.info(f"True Negatives: {cm[0,0]}, False Positives: {cm[0,1]}")
    logger.info(f"False Negatives: {cm[1,0]}, True Positives: {cm[1,1]}")
    
    return {
        'accuracy': accuracy,
        'auc': auc_score,
        'predictions': y_pred,
        'probabilities': y_prob
    }

def save_model(model, filename):
    """Save model with metadata"""
    model_path = os.path.join(MODEL_DIR, filename)
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Add metadata
    model.metadata = {
        'trained_at': datetime.now().isoformat(),
        'features': FEATURES
    }
    
    joblib.dump(model, model_path)
    logger.info(f"Model saved to {model_path}")

def run_brain_training():
    """Main training pipeline"""
    logger.info("[START] Starting Enhanced AI Brain Training")
    logger.info("=" * 50)
    
    # Load data
    df = load_training_data()
    if df is None:
        return
    
    # Prepare features
    X, y = prepare_features(df)
    if X is None or y is None:
        return
    
    # Check data quality
    if len(X) < 100:
        logger.error(f"Insufficient training data: {len(X)} samples")
        return
    
    logger.info(f"Training on {len(X)} samples")
    
    # Train individual models
    models = {}
    results = {}
    
    # Random Forest
    try:
        rf_model = train_random_forest(X, y)
        models['rf'] = rf_model
        results['rf'] = evaluate_model(rf_model, X, y, "Random Forest")
        save_model(rf_model, MODELS['rf'])
    except Exception as e:
        logger.error(f"RF training failed: {e}")
    
    # Gradient Boosting
    try:
        gb_model = train_gradient_boosting(X, y)
        models['gb'] = gb_model
        results['gb'] = evaluate_model(gb_model, X, y, "Gradient Boosting")
        save_model(gb_model, MODELS['gb'])
    except Exception as e:
        logger.error(f"GB training failed: {e}")
    
    # Ensemble
    if len(models) >= 2:
        try:
            ensemble_model = train_ensemble(X, y, models)
            models['ensemble'] = ensemble_model
            results['ensemble'] = evaluate_model(ensemble_model, X, y, "Ensemble")
            save_model(ensemble_model, MODELS['ensemble'])
        except Exception as e:
            logger.error(f"Ensemble training failed: {e}")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 50)
    
    for model_name, result in results.items():
        logger.info(f"{model_name.upper()}:")
        logger.info(f"  Accuracy: {result['accuracy']:.4f}")
        logger.info(f"  AUC-ROC:  {result['auc']:.4f}")
    
    # Select best model
    if results:
        best_model = max(results.keys(), key=lambda k: results[k]['auc'])
        logger.info(f"\n🏆 Best Model: {best_model.upper()} (AUC: {results[best_model]['auc']:.4f})")
        logger.info("[AI] AI Brain Training Complete!")

if __name__ == "__main__":
    run_brain_training()
