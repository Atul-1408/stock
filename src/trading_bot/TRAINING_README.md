# Bot AI Training System - 80%+ Accuracy Target

## 🎯 Objective
Train your trading bot's AI model to achieve 80%+ prediction accuracy using real historical market data for Indian stocks (NSE).

##🚀 Quick Start Commands

### 1. Install Required Dependencies
```bash
# Navigate to project root
cd c:\Users\Atul\project\stock

# Install/update dependencies
pip install -r requirements.txt
```

### 2. Run Complete Training Pipeline
```bash
# Run full pipeline with default settings (80% target accuracy)
python src/trading_bot/train_pipeline.py

# Run with custom parameters
python src/trading_bot/train_pipeline.py --target-accuracy 0.85 --stocks "RELIANCE.NS,TCS.NS,INFY.NS" --years 3
```

### 3. Run Individual Components
```bash
# Only collect data
python src/trading_bot/data_collector.py

# Only train models
python src/trading_bot/train_brain.py

# Only evaluate models
python src/trading_bot/model_evaluator.py

# Advanced backtesting
python src/trading_bot/backtester_advanced.py
```

## 📊 System Architecture

### Phase 1: Data Collection (`data_collector.py`)
- **Purpose**: Gather 2+ years of historical data for NSE stocks
- **Features Collected**:
  - Technical indicators (EMA, RSI, ADX, ATR, Supertrend, VWAP)
  - SMC patterns (Fair Value Gaps, Liquidity Sweeps)
  - Volume analysis and market regime detection
  - Sentiment scores (optional)
- **Labeling**: Each setup labeled as WIN/LOSS based on 2R target and 1R stop
- **Output**: `training_data.csv` with 1000+ samples per stock

### Phase 2: Advanced Backtesting (`backtester_advanced.py`)
- **Purpose**: Validate strategy performance before model training
- **Method**: Walk-forward validation (70% train, 15% validation, 15% test)
- **Metrics**: Win rate, profit factor, Sharpe ratio, max drawdown
- **Output**: Performance reports and trade logs

### Phase 3: Model Training (`train_brain.py`)
- **Purpose**: Train multiple ML models with hyperparameter tuning
- **Models**: 
  - Random Forest (with GridSearchCV optimization)
  - Gradient Boosting (with GridSearchCV optimization)  
  - Ensemble Voting Classifier
- **Validation**: TimeSeriesSplit cross-validation
- **Output**: Multiple model files in `models/` directory

### Phase 4: Model Evaluation (`model_evaluator.py`)
- **Purpose**: Validate models on unseen test data
- **Metrics**: Accuracy, AUC-ROC, precision, recall, F1-score
- **Analysis**: Confidence calibration, performance by market conditions
- **Output**: Detailed evaluation report and performance visualization

## 📈 Expected Performance Metrics

### Target Achievements:
- **Accuracy**: 80%+ on test set
- **AUC-ROC**: 0.80+ 
- **Precision**: 75%+
- **Recall**: 70%+
- **F1-Score**: 0.75+

### Data Requirements:
- **Minimum Samples**: 1000+ per stock
- **Time Period**: 2+ years of historical data
- **Stocks**: 5-10 major NSE stocks (RELIANCE, TCS, INFY, HDFCBANK, etc.)
- **Feature Quality**: Clean, engineered features with proper handling

##🛠️ Configuration Options

### Command Line Parameters:
```bash
python train_pipeline.py --help

# Key options:
--target-accuracy FLOAT    Target accuracy threshold (default: 0.8)
--stocks LIST              Comma-separated stock tickers (default: major NSE stocks)
--years INT                Years of historical data (default: 2)
--min-samples INT          Minimum samples per stock (default: 1000)
--skip-collection          Skip data collection (use existing data)
--skip-backtesting         Skip backtesting phase
```

### Key Files:
- `training_data.csv`: Main training dataset
- `models/`: Directory containing trained model files
- `training.log`: Training process logs
- `data_collection.log`: Data collection logs
- `model_evaluation.log`: Evaluation logs
- `model_evaluation_report.txt`: Final evaluation report
- `backtest_report.txt`: Backtesting results

## 📊 Monitoring and Validation

### Real-time Monitoring:
- **Training Progress**: Check `training.log` for model training status
- **Data Quality**: Review `data_collection.log` for data gathering issues
- **Performance Metrics**: Monitor logs for accuracy improvements

### Validation Reports:
1. **Backtesting Report**: `backtest_report.txt`
2. **Model Evaluation Report**: `model_evaluation_report.txt`
3. **Calibration Plots**: `calibration_*.png` (saved in current directory)

### Success Criteria:
✅ **Target Achieved**: Best model AUC-ROC ≥ 0.80
✅ **Data Quality**: Minimum 1000 samples per stock
✅ **Model Stability**: Consistent performance across validation folds
✅ **Confidence Calibration**: Well-calibrated probability estimates

##🔄 Improvement

### After Initial Training:
1. **Collect More Data**: Continue gathering live trading data
2. **Retrain Periodically**: Weekly/monthly model updates
3. **Feature Engineering**: Add new indicators and market features
4. **Model Optimization**: Experiment with different algorithms
5. **Performance Monitoring**: Track live trading results

### Troubleshooting:
- **Low Accuracy**: Increase training data, improve features, adjust parameters
- **Overfitting**: Add more regularization, use cross-validation
- **Data Issues**: Check data quality, handle missing values properly
- **Performance Degradation**: Retrain with recent data, check for market regime changes

## 📋 Prerequisites Checklist

Before running the training pipeline:

- [ ] Python 3.8+ installed
- [ ] Required packages installed (`pip install -r requirements.txt`)
- [ ] Sufficient disk space (1GB+ recommended)
- [ ] Internet connection (for data fetching)
- [ ] Write permissions in project directory
- [ ] At least 2 hours processing time for complete pipeline

##🏆 Success Indicators

When training is successful, you'll see:
- ✅ "🎯 Target Accuracy Achieved:✅ YES"
- ✅ Multiple high-performing model files in `models/` directory
- ✅ AUC-ROC scores above 0.80
-✅ Detailed performance reports generated
- ✅ Calibration plots showing well-calibrated models

##🆘 Support

For issues or questions:
1. Check the detailed logs in `training.log` and related log files
2. Verify data quality in `training_data.csv`
3. Review model performance reports
4. Ensure all dependencies are properly installed

---
**Note**: This system is designed for educational and research purposes. Always test thoroughly in paper trading before live deployment.