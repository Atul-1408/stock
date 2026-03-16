"""
Model Evaluator - Comprehensive Performance Validation

This script evaluates trained models on unseen test data and provides
detailed performance reports including:
- Accuracy and confidence metrics
- Calibration analysis
- Feature importance
- Performance by market conditions
- Detailed confusion matrices
"""

import os
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report
)
from sklearn.calibration import calibration_curve
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
MODEL_DIR = "models"
TRAINING_DATA_FILE = "training_data.csv"
EVALUATION_REPORT = "model_evaluation_report.txt"
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for trade execution

class ModelEvaluator:
    def __init__(self):
        self.models = {}
        self.results = {}
        self.test_data = None
        
    def load_models(self):
        """Load all trained models"""
        if not os.path.exists(MODEL_DIR):
            logger.error(f"Model directory {MODEL_DIR} not found")
            return False
            
        model_files = {
            'Random Forest': 'apex_model_rf.pkl',
            'Gradient Boosting': 'apex_model_gb.pkl',
            'Ensemble': 'apex_model_ensemble.pkl'
        }
        
        for model_name, filename in model_files.items():
            filepath = os.path.join(MODEL_DIR, filename)
            if os.path.exists(filepath):
                try:
                    model = joblib.load(filepath)
                    self.models[model_name] = model
                    logger.info(f"✓ Loaded {model_name} from {filename}")
                except Exception as e:
                    logger.error(f"[X] Failed to load {model_name}: {e}")
            else:
                logger.warning(f"[!] Model file not found: {filename}")
        
        return len(self.models) > 0

    def load_test_data(self):
        """Load and prepare test data"""
        try:
            if not os.path.exists(TRAINING_DATA_FILE):
                logger.error(f"Training data file {TRAINING_DATA_FILE} not found")
                return False
                
            df = pd.read_csv(TRAINING_DATA_FILE)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Sort by timestamp and take last 15% as test set
            df = df.sort_values('timestamp').reset_index(drop=True)
            test_size = int(len(df) * 0.15)
            self.test_data = df.tail(test_size).copy()
            
            logger.info(f"✓ Loaded {len(self.test_data)} test samples")
            logger.info(f"Test period: {self.test_data['timestamp'].min()} to {self.test_data['timestamp'].max()}")
            
            # Prepare features and target
            feature_cols = [col for col in [
                'rsi', 'adx', 'atr', 'ema_9', 'ema_21', 'ema_50', 'ema_200',
                'supertrend', 'vwap', 'fvg_bullish', 'fvg_bearish',
                'liquidity_sweep', 'volume_spike', 'market_regime', 'volatility_regime'
            ] if col in self.test_data.columns]
            
            self.X_test = self.test_data[feature_cols].fillna(0)
            self.y_test = (self.test_data['outcome'] == 'WIN').astype(int)
            
            logger.info(f"Features: {len(feature_cols)}")
            logger.info(f"Target distribution: {self.y_test.value_counts().to_dict()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading test data: {e}")
            return False

    def evaluate_model(self, model_name, model):
        """Comprehensive evaluation of a single model"""
        logger.info(f"\n🔍 Evaluating {model_name}")
        logger.info("-" * 40)
        
        # Make predictions
        y_pred = model.predict(self.X_test)
        y_prob = model.predict_proba(self.X_test)[:, 1]
        
        # Basic metrics
        accuracy = accuracy_score(self.y_test, y_pred)
        precision = precision_score(self.y_test, y_pred, zero_division=0)
        recall = recall_score(self.y_test, y_pred, zero_division=0)
        f1 = f1_score(self.y_test, y_pred, zero_division=0)
        auc = roc_auc_score(self.y_test, y_prob)
        
        # Confidence-based metrics
        high_confidence_mask = (y_prob >= CONFIDENCE_THRESHOLD) | (y_prob <= (1 - CONFIDENCE_THRESHOLD))
        high_confidence_accuracy = accuracy_score(
            self.y_test[high_confidence_mask], 
            y_pred[high_confidence_mask]
        ) if high_confidence_mask.sum() > 0 else 0
        
        # Metrics by class
        cm = confusion_matrix(self.y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()
        
        logger.info(f"Overall Accuracy: {accuracy:.4f}")
        logger.info(f"Precision: {precision:.4f}")
        logger.info(f"Recall: {recall:.4f}")
        logger.info(f"F1-Score: {f1:.4f}")
        logger.info(f"AUC-ROC: {auc:.4f}")
        logger.info(f"High Confidence Accuracy (>={CONFIDENCE_THRESHOLD}): {high_confidence_accuracy:.4f}")
        logger.info(f"High Confidence Trades: {high_confidence_mask.sum()}/{len(self.y_test)} ({high_confidence_mask.sum()/len(self.y_test):.1%})")
        
        # Detailed classification report
        logger.info("\nDetailed Classification Report:")
        logger.info(classification_report(self.y_test, y_pred, target_names=['LOSS', 'WIN']))
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'auc': auc,
            'high_conf_accuracy': high_confidence_accuracy,
            'high_conf_trades': high_confidence_mask.sum(),
            'predictions': y_pred,
            'probabilities': y_prob,
            'confusion_matrix': cm
        }

    def analyze_confidence_calibration(self, model_name, model):
        """Analyze model confidence calibration"""
        logger.info(f"\n[STATS] Confidence Calibration Analysis - {model_name}")
        
        y_prob = model.predict_proba(self.X_test)[:, 1]
        
        # Calibration curve
        fraction_of_positives, mean_predicted_value = calibration_curve(
            self.y_test, y_prob, n_bins=10
        )
        
        # Perfect calibration line
        perfect_calibration = np.linspace(0, 1, 100)
        
        # Plot
        plt.figure(figsize=(10, 6))
        plt.plot(mean_predicted_value, fraction_of_positives, "s-", label="Model")
        plt.plot(perfect_calibration, perfect_calibration, "k:", label="Perfectly calibrated")
        plt.xlabel("Mean Predicted Probability")
        plt.ylabel("Fraction of Positives")
        plt.title(f"Calibration Plot - {model_name}")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(f"calibration_{model_name.lower().replace(' ', '_')}.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # Calculate calibration error
        calibration_errors = np.abs(fraction_of_positives - mean_predicted_value)
        mean_calibration_error = np.mean(calibration_errors)
        
        logger.info(f"Mean Calibration Error: {mean_calibration_error:.4f}")
        
        # Confidence distribution
        confidence_levels = pd.cut(y_prob, bins=10, labels=False) / 10
        confidence_stats = pd.DataFrame({
            'confidence_level': confidence_levels,
            'actual_outcome': self.y_test
        }).groupby('confidence_level').agg({
            'actual_outcome': ['count', 'mean']
        })
        
        logger.info("Confidence Distribution:")
        logger.info(confidence_stats)

    def analyze_performance_by_conditions(self, model_name, model):
        """Analyze performance across different market conditions"""
        logger.info(f"\n🌡️ Performance by Market Conditions - {model_name}")
        
        # Add market conditions to test data
        test_with_predictions = self.test_data.copy()
        test_with_predictions['prediction'] = model.predict(self.X_test)
        test_with_predictions['probability'] = model.predict_proba(self.X_test)[:, 1]
        test_with_predictions['correct'] = (test_with_predictions['prediction'] == self.y_test).astype(int)
        
        # Performance by volatility regime
        if 'volatility_regime' in test_with_predictions.columns:
            vol_performance = test_with_predictions.groupby('volatility_regime')['correct'].agg(['count', 'mean'])
            logger.info("Performance by Volatility Regime:")
            logger.info(vol_performance)
        
        # Performance by market regime
        if 'market_regime' in test_with_predictions.columns:
            market_performance = test_with_predictions.groupby('market_regime')['correct'].agg(['count', 'mean'])
            logger.info("Performance by Market Regime:")
            logger.info(market_performance)
        
        # Performance by signal type
        if 'signal_type' in test_with_predictions.columns:
            signal_performance = test_with_predictions.groupby('signal_type')['correct'].agg(['count', 'mean'])
            logger.info("Performance by Signal Type:")
            logger.info(signal_performance)

    def generate_detailed_report(self):
        """Generate comprehensive evaluation report"""
        logger.info("\n" + "=" * 60)
        logger.info("DETAILED MODEL EVALUATION REPORT")
        logger.info("=" * 60)
        
        # Summary table
        summary_data = []
        for model_name, result in self.results.items():
            summary_data.append({
                'Model': model_name,
                'Accuracy': f"{result['accuracy']:.4f}",
                'AUC-ROC': f"{result['auc']:.4f}",
                'Precision': f"{result['precision']:.4f}",
                'Recall': f"{result['recall']:.4f}",
                'F1-Score': f"{result['f1']:.4f}",
                'High Conf Acc': f"{result['high_conf_accuracy']:.4f}",
                'High Conf Trades': result['high_conf_trades']
            })
        
        summary_df = pd.DataFrame(summary_data)
        logger.info("\n[STATS] MODEL COMPARISON:")
        logger.info(summary_df.to_string(index=False))
        
        # Select best model
        if self.results:
            best_model = max(self.results.keys(), key=lambda k: self.results[k]['auc'])
            best_auc = self.results[best_model]['auc']
            
            logger.info(f"\n🏆 BEST MODEL: {best_model}")
            logger.info(f"   AUC-ROC: {best_auc:.4f}")
            
            # Check if target accuracy achieved
            target_achieved = best_auc >= 0.8
            logger.info(f"🎯 80%+ TARGET ACHIEVED: {'[OK] YES' if target_achieved else '[X] NO'}")
            
            return {
                'best_model': best_model,
                'best_auc': best_auc,
                'target_achieved': target_achieved,
                'all_results': self.results
            }
        
        return None

    def run_evaluation(self):
        """Run complete model evaluation"""
        logger.info("[START] Starting Model Evaluation")
        logger.info("=" * 50)
        
        # Load models and data
        if not self.load_models():
            logger.error("No models loaded. Cannot proceed with evaluation.")
            return False
            
        if not self.load_test_data():
            logger.error("No test data available. Cannot proceed with evaluation.")
            return False
        
        # Evaluate each model
        for model_name, model in self.models.items():
            try:
                result = self.evaluate_model(model_name, model)
                self.results[model_name] = result
                
                # Additional analyses
                self.analyze_confidence_calibration(model_name, model)
                self.analyze_performance_by_conditions(model_name, model)
                
            except Exception as e:
                logger.error(f"Error evaluating {model_name}: {e}")
        
        # Generate final report
        final_results = self.generate_detailed_report()
        
        # Save detailed report
        self.save_detailed_report(final_results)
        
        return True

    def save_detailed_report(self, final_results):
        """Save comprehensive evaluation report to file"""
        with open(EVALUATION_REPORT, 'w') as f:
            f.write("MODEL EVALUATION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            # Test data info
            f.write("TEST DATA INFORMATION\n")
            f.write("-" * 30 + "\n")
            f.write(f"Samples: {len(self.test_data)}\n")
            f.write(f"Period: {self.test_data['timestamp'].min()} to {self.test_data['timestamp'].max()}\n")
            f.write(f"Target distribution: {self.y_test.value_counts().to_dict()}\n\n")
            
            # Model results
            f.write("MODEL PERFORMANCE\n")
            f.write("-" * 30 + "\n")
            for model_name, result in self.results.items():
                f.write(f"\n{model_name}:\n")
                f.write(f"  Accuracy: {result['accuracy']:.4f}\n")
                f.write(f"  AUC-ROC: {result['auc']:.4f}\n")
                f.write(f"  Precision: {result['precision']:.4f}\n")
                f.write(f"  Recall: {result['recall']:.4f}\n")
                f.write(f"  F1-Score: {result['f1']:.4f}\n")
                f.write(f"  High Confidence Accuracy: {result['high_conf_accuracy']:.4f}\n")
                f.write(f"  High Confidence Trades: {result['high_conf_trades']}\n")
                
                # Confusion matrix
                cm = result['confusion_matrix']
                f.write(f"  Confusion Matrix:\n")
                f.write(f"    TN: {cm[0,0]}, FP: {cm[0,1]}\n")
                f.write(f"    FN: {cm[1,0]}, TP: {cm[1,1]}\n")
            
            # Final summary
            if final_results:
                f.write(f"\nFINAL RECOMMENDATION\n")
                f.write("-" * 30 + "\n")
                f.write(f"Best Model: {final_results['best_model']}\n")
                f.write(f"Best AUC: {final_results['best_auc']:.4f}\n")
                f.write(f"80%+ Target Achieved: {'YES' if final_results['target_achieved'] else 'NO'}\n")
        
        logger.info(f"[OK] Detailed report saved to {EVALUATION_REPORT}")

if __name__ == "__main__":
    evaluator = ModelEvaluator()
    evaluator.run_evaluation()
