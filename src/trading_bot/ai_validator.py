# Fix for sklearn hanging on import (Windows-specific issue)
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
from trading_bot import config

class AIValidator:
    def __init__(self):
        self.model = None
        self.feature_cols = ['rsi', 'adx', 'trend']
        self.load_model()
        
    def load_model(self):
        try:
            if os.path.exists(config.MODEL_PATH):
                self.model = joblib.load(config.MODEL_PATH)
                print(f"[OK] AI Model Loaded: {config.MODEL_PATH}")
            else:
                print("[!] No AI Model found. Training initial model...")
                self.train_dummy_model()
        except Exception as e:
            print(f"[X] Error loading model: {e}")
            self.train_dummy_model()

    def train_dummy_model(self):
        """Trains a basic model on synthetic data to ensure system functionality."""
        print("[AI] Training Initial AI Model...")
        # Create Dummy Data (RSI, ADX, Trend)
        X = np.random.rand(100, 3)
        X[:, 0] *= 100 # RSI 0-100
        X[:, 1] *= 50  # ADX 0-50
        X[:, 2] = np.random.randint(0, 2, 100) # Trend 0 or 1
        
        # Logic: If RSI < 30 and Trend is Bullish (1) -> Buy (1)
        y = ((X[:, 0] < 30) & (X[:, 2] == 1)).astype(int) 
        
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        clf.fit(X, y)
        
        self.model = clf
        joblib.dump(clf, config.MODEL_PATH)
        print("[OK] Initial Model Saved.")

    def prepare_features(self, row):
        """Extracts features from the DataFrame row."""
        # Note: In decision_engine, we've already calculated these.
        # But prepare_features usually takes the raw row.
        # We need to calculate Trend here as well to be safe.
        
        features = []
        
        # 1. RSI
        features.append(row.get(f'RSI_{config.RSI_PERIOD}', 50))
        
        # 2. ADX
        features.append(row.get(f'ADX_{config.ADX_PERIOD}', 25))
        
        # 3. Trend (Close > EMA200)
        close = row['Close']
        ema = row.get(f'EMA_{config.EMA_PERIOD}', close)
        trend = 1 if close > ema else 0
        features.append(trend)
        
        return np.array(features).reshape(1, -1)

    def get_confidence(self, row):
        """
        Returns probability of 'Class 1' (Buy Success).
        """
        if self.model is None:
            return 0.5 # Neutral
            
        X = self.prepare_features(row)
        
        try:
            prob = self.model.predict_proba(X)[0][1] # Probability of Class 1
            return prob
        except Exception as e:
            print(f"Prediction Error: {e}")
            return 0.0

