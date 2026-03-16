"""
Complete Training Pipeline - 80%+ Accuracy Target

This script orchestrates the entire training process:
1. Data Collection (data_collector.py)
2. Advanced Backtesting (backtester_advanced.py)
3. Model Training (train_brain.py)
4. Model Evaluation (model_evaluator.py)

Usage:
python train_pipeline.py --target-accuracy 0.8 --stocks RELIANCE.NS,TCS.NS
"""

import argparse
import sys
import os
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_pipeline.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Complete Training Pipeline for Trading Bot')
    parser.add_argument(
        '--target-accuracy', 
        type=float, 
        default=0.8,
        help='Target accuracy threshold (default: 0.8)'
    )
    parser.add_argument(
        '--stocks',
        type=str,
        default='RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS',
        help='Comma-separated list of stock tickers'
    )
    parser.add_argument(
        '--years',
        type=int,
        default=2,
        help='Years of historical data to collect'
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=1000,
        help='Minimum samples required per stock'
    )
    parser.add_argument(
        '--skip-collection',
        action='store_true',
        help='Skip data collection (use existing training_data.csv)'
    )
    parser.add_argument(
        '--skip-backtesting',
        action='store_true',
        help='Skip backtesting phase'
    )
    return parser.parse_args()

def run_data_collection(args):
    """Run data collection phase"""
    if args.skip_collection:
        logger.info("⏭️ Skipping data collection (using existing data)")
        return True
        
    logger.info("[STATS] Phase 1: Data Collection")
    logger.info("=" * 40)
    
    try:
        from data_collector import DataCollector
        
        # Update configuration
        collector = DataCollector()
        collector.watchlist = args.stocks.split(',')
        collector.YEARS_OF_DATA = args.years
        collector.MIN_SAMPLES_PER_STOCK = args.min_samples
        
        # Run collection
        collector.run_collection()
        
        # Verify data quality
        import pandas as pd
        if os.path.exists('training_data.csv'):
            df = pd.read_csv('training_data.csv')
            logger.info(f"[OK] Data collection completed: {len(df)} samples")
            logger.info(f"[STATS] Win rate in collected data: {(df['outcome'] == 'WIN').mean():.2%}")
            return True
        else:
            logger.error("[X] Data collection failed - no training_data.csv created")
            return False
            
    except Exception as e:
        logger.error(f"[X] Data collection failed: {e}")
        return False

def run_backtesting(args):
    """Run advanced backtesting phase"""
    if args.skip_backtesting:
        logger.info("⏭️ Skipping backtesting phase")
        return True
        
    logger.info("🔍 Phase 2: Advanced Backtesting")
    logger.info("=" * 40)
    
    try:
        from backtester_advanced import AdvancedBacktester
        
        backtester = AdvancedBacktester()
        success = backtester.run_complete_backtest()
        
        if success:
            backtester.generate_report()
            logger.info("[OK] Backtesting completed successfully")
            return True
        else:
            logger.error("[X] Backtesting failed")
            return False
            
    except Exception as e:
        logger.error(f"[X] Backtesting failed: {e}")
        return False

def run_model_training(args):
    """Run model training phase"""
    logger.info("[AI] Phase 3: Model Training")
    logger.info("=" * 40)
    
    try:
        # Import the enhanced training module
        import train_brain
        train_brain.run_brain_training()
        
        # Check if models were created
        model_files = [
            'models/apex_model_rf.pkl',
            'models/apex_model_gb.pkl', 
            'models/apex_model_ensemble.pkl'
        ]
        
        created_models = [f for f in model_files if os.path.exists(f)]
        if created_models:
            logger.info(f"[OK] Model training completed: {len(created_models)} models created")
            return True
        else:
            logger.error("[X] Model training failed - no model files created")
            return False
            
    except Exception as e:
        logger.error(f"[X] Model training failed: {e}")
        return False

def run_model_evaluation(args):
    """Run model evaluation phase"""
    logger.info("[^] Phase 4: Model Evaluation")
    logger.info("=" * 40)
    
    try:
        from model_evaluator import ModelEvaluator
        
        evaluator = ModelEvaluator()
        success = evaluator.run_evaluation()
        
        if success and evaluator.results:
            # Check if target accuracy achieved
            best_model = max(evaluator.results.keys(), key=lambda k: evaluator.results[k]['auc'])
            best_auc = evaluator.results[best_model]['auc']
            target_achieved = best_auc >= args.target_accuracy
            
            logger.info(f"🎯 Best Model Performance: {best_model}")
            logger.info(f"🎯 AUC-ROC Score: {best_auc:.4f}")
            logger.info(f"🎯 Target Accuracy ({args.target_accuracy*100:.0f}%): {'[OK] ACHIEVED' if target_achieved else '[X] NOT ACHIEVED'}")
            
            return target_achieved
        else:
            logger.error("[X] Model evaluation failed")
            return False
            
    except Exception as e:
        logger.error(f"[X] Model evaluation failed: {e}")
        return False

def main():
    """Main training pipeline"""
    logger.info("STARTING COMPLETE TRAINING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Start Time: {datetime.now()}")
    logger.info("=" * 60)
    
    # Parse arguments
    args = parse_arguments()
    
    # Display configuration
    logger.info("CONFIGURATION:")
    logger.info(f"   Target Accuracy: {args.target_accuracy*100:.0f}%")
    logger.info(f"   Stocks: {args.stocks}")
    logger.info(f"   Years of Data: {args.years}")
    logger.info(f"   Min Samples per Stock: {args.min_samples}")
    logger.info(f"   Skip Collection: {args.skip_collection}")
    logger.info(f"   Skip Backtesting: {args.skip_backtesting}")
    logger.info("")
    
    # Phase 1: Data Collection
    if not run_data_collection(args):
        logger.error("Pipeline failed at Data Collection phase")
        return False
    
    # Phase 2: Backtesting
    if not run_backtesting(args):
        logger.error("Pipeline failed at Backtesting phase")
        return False
    
    # Phase 3: Model Training
    if not run_model_training(args):
        logger.error("Pipeline failed at Model Training phase")
        return False
    
    # Phase 4: Model Evaluation
    target_achieved = run_model_evaluation(args)
    
    # Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"End Time: {datetime.now()}")
    logger.info(f"Target Accuracy Achieved: {'YES' if target_achieved else 'NO'}")
    
    if target_achieved:
        logger.info("CONGRATULATIONS! Your trading bot is ready for deployment!")
        logger.info("Next steps:")
        logger.info("   1. Review the detailed reports in generated files")
        logger.info("   2. Test the bot in paper trading mode")
        logger.info("   3. Monitor performance and continue collecting data")
    else:
        logger.info("Target accuracy not achieved. Consider:")
        logger.info("   1. Collecting more training data")
        logger.info("   2. Adjusting feature engineering")
        logger.info("   3. Trying different model architectures")
        logger.info("   4. Improving data quality and labeling")
    
    return target_achieved

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
