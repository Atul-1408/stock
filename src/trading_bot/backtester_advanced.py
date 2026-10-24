"""
Advanced Backtester for Trading Strategy Validation

Implements walk-forward backtesting with proper risk management
and performance metrics calculation.

Features:
- Walk-forward validation (70% train, 15% validation, 15% test)
- Risk-adjusted performance metrics
- Detailed trade logging
- Drawdown analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import logging
from typing import Dict, List, Tuple
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedBacktester:
    def __init__(self, data_file: str = 'training_data.csv'):
        self.data_file = data_file
        self.data = None
        self.results = {}
        self.trade_log = []
        
    def load_data(self):
        """Load training data"""
        try:
            self.data = pd.read_csv(self.data_file)
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
            self.data = self.data.sort_values('timestamp').reset_index(drop=True)
            logger.info(f"✓ Loaded {len(self.data)} samples from {self.data_file}")
            return True
        except Exception as e:
            logger.error(f"[X] Error loading data: {e}")
            return False

    def split_data(self, train_pct: float = 0.7, val_pct: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data using time series approach"""
        if self.data is None:
            raise ValueError("Data not loaded")
            
        n = len(self.data)
        train_end = int(n * train_pct)
        val_end = int(n * (train_pct + val_pct))
        
        train_data = self.data.iloc[:train_end].copy()
        val_data = self.data.iloc[train_end:val_end].copy()
        test_data = self.data.iloc[val_end:].copy()
        
        logger.info(f"[STATS] Data Split:")
        logger.info(f"   Train: {len(train_data)} samples ({train_pct*100:.0f}%)")
        logger.info(f"   Validation: {len(val_data)} samples ({val_pct*100:.0f}%)")
        logger.info(f"   Test: {len(test_data)} samples ({(1-train_pct-val_pct)*100:.0f}%)")
        
        return train_data, val_data, test_data

    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {}
            
        # Extract P&L values
        pnl_values = [trade['pnl'] for trade in trades]
        returns = [trade['return_pct'] for trade in trades]
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = sum(1 for t in trades if t['pnl'] < 0)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if losing_trades > 0 else 0
        
        # Profit factor
        total_wins = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Risk metrics
        total_pnl = sum(pnl_values)
        max_pnl = max(pnl_values) if pnl_values else 0
        min_pnl = min(pnl_values) if pnl_values else 0
        
        # Drawdown calculation
        cumulative_pnl = np.cumsum(pnl_values)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = min(drawdown) if len(drawdown) > 0 else 0
        
        # Return-based metrics
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if len(returns) > 1 else 0
        sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Trade duration analysis
        durations = [t['holding_period'] for t in trades if t['holding_period'] > 0]
        avg_duration = np.mean(durations) if durations else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'max_pnl': max_pnl,
            'min_pnl': min_pnl,
            'max_drawdown': max_drawdown,
            'avg_return': avg_return,
            'std_return': std_return,
            'sharpe_ratio': sharpe_ratio,
            'avg_duration': avg_duration
        }

    def simulate_trading(self, data: pd.DataFrame, initial_capital: float = 100000) -> Tuple[List[Dict], Dict]:
        """Simulate trading on given data"""
        if data.empty:
            return [], {}
            
        trades = []
        capital = initial_capital
        position = 0
        entry_price = 0
        entry_signal = None
        
        for idx, row in data.iterrows():
            signal = row['signal_type']
            close_price = row['close']
            timestamp = row['timestamp']
            
            # Position management
            if position == 0 and signal in ['BUY', 'SELL']:
                # Enter position
                position = 1 if signal == 'BUY' else -1
                entry_price = close_price
                entry_signal = signal
                capital -= 10  # Transaction cost
                
            elif position != 0:
                # Check exit conditions
                atr = row['atr'] if not pd.isna(row['atr']) else close_price * 0.01
                target_price = entry_price + (2 * atr * position)
                stop_price = entry_price - (1 * atr * position)
                
                exit_trade = False
                exit_price = close_price
                exit_reason = 'TIME_EXPIRY'
                
                # Target hit
                if (position == 1 and close_price >= target_price) or \
                   (position == -1 and close_price <= target_price):
                    exit_price = target_price
                    exit_reason = 'TARGET_HIT'
                    exit_trade = True
                    
                # Stop loss hit
                elif (position == 1 and close_price <= stop_price) or \
                     (position == -1 and close_price >= stop_price):
                    exit_price = stop_price
                    exit_reason = 'STOP_HIT'
                    exit_trade = True
                
                # Time-based exit (if no target/stop hit)
                elif idx == len(data) - 1:
                    exit_trade = True
                    
                if exit_trade:
                    # Calculate P&L
                    if position == 1:  # Long position
                        pnl = (exit_price - entry_price) * 100  # Assuming 100 shares
                    else:  # Short position
                        pnl = (entry_price - exit_price) * 100
                    
                    pnl -= 20  # Round-trip transaction costs
                    return_pct = pnl / (entry_price * 100)  # As percentage of capital at risk
                    
                    trade = {
                        'entry_time': timestamp,
                        'exit_time': timestamp,
                        'signal': entry_signal,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'return_pct': return_pct,
                        'holding_period': 1,
                        'exit_reason': exit_reason
                    }
                    trades.append(trade)
                    
                    # Update capital
                    capital += pnl
                    position = 0
                    entry_price = 0
                    entry_signal = None
        
        # Calculate metrics
        metrics = self.calculate_performance_metrics(trades)
        metrics['final_capital'] = capital
        metrics['total_return'] = (capital - initial_capital) / initial_capital
        
        return trades, metrics

    def walk_forward_validation(self, n_splits: int = 5):
        """Perform walk-forward validation"""
        if self.data is None:
            raise ValueError("Data not loaded")
            
        tscv = TimeSeriesSplit(n_splits=n_splits)
        all_metrics = []
        
        logger.info(f"🔄 Performing {n_splits}-fold walk-forward validation")
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(self.data)):
            train_data = self.data.iloc[train_idx]
            test_data = self.data.iloc[test_idx]
            
            logger.info(f"Fold {fold + 1}/{n_splits}")
            logger.info(f"  Train: {len(train_data)} samples")
            logger.info(f"  Test: {len(test_data)} samples")
            
            # Simulate trading on test set
            trades, metrics = self.simulate_trading(test_data)
            
            if metrics:
                metrics['fold'] = fold + 1
                all_metrics.append(metrics)
                logger.info(f"  Win Rate: {metrics['win_rate']:.2%}")
                logger.info(f"  Profit Factor: {metrics['profit_factor']:.2f}")
                logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        
        # Aggregate results
        if all_metrics:
            df_metrics = pd.DataFrame(all_metrics)
            avg_metrics = df_metrics.mean(numeric_only=True)
            
            logger.info("\n[^] Walk-Forward Validation Results:")
            logger.info(f"Average Win Rate: {avg_metrics['win_rate']:.2%}")
            logger.info(f"Average Profit Factor: {avg_metrics['profit_factor']:.2f}")
            logger.info(f"Average Sharpe Ratio: {avg_metrics['sharpe_ratio']:.2f}")
            logger.info(f"Average Max Drawdown: {avg_metrics['max_drawdown']:.2f}")
            
            self.results['walk_forward'] = {
                'individual_folds': all_metrics,
                'average_metrics': avg_metrics.to_dict()
            }

    def run_complete_backtest(self):
        """Run complete backtesting workflow"""
        logger.info("[START] Starting Advanced Backtesting")
        
        # Load data
        if not self.load_data():
            return False
            
        # Split data
        train_data, val_data, test_data = self.split_data()
        
        # Test on validation set
        logger.info("\n🔍 Validation Set Performance:")
        val_trades, val_metrics = self.simulate_trading(val_data)
        
        if val_metrics:
            logger.info(f"Win Rate: {val_metrics['win_rate']:.2%}")
            logger.info(f"Profit Factor: {val_metrics['profit_factor']:.2f}")
            logger.info(f"Sharpe Ratio: {val_metrics['sharpe_ratio']:.2f}")
            logger.info(f"Max Drawdown: {val_metrics['max_drawdown']:.2f}")
            logger.info(f"Total Return: {val_metrics['total_return']:.2%}")
        
        # Test on test set
        logger.info("\n🧪 Test Set Performance:")
        test_trades, test_metrics = self.simulate_trading(test_data)
        
        if test_metrics:
            logger.info(f"Win Rate: {test_metrics['win_rate']:.2%}")
            logger.info(f"Profit Factor: {test_metrics['profit_factor']:.2f}")
            logger.info(f"Sharpe Ratio: {test_metrics['sharpe_ratio']:.2f}")
            logger.info(f"Max Drawdown: {test_metrics['max_drawdown']:.2f}")
            logger.info(f"Total Return: {test_metrics['total_return']:.2%}")
        
        # Walk-forward validation
        logger.info("\n🔄 Walk-Forward Validation:")
        self.walk_forward_validation()
        
        # Save results
        self.results['validation'] = val_metrics
        self.results['test'] = test_metrics
        self.results['trade_log'] = {
            'validation': val_trades,
            'test': test_trades
        }
        
        return True

    def generate_report(self, output_file: str = 'backtest_report.txt'):
        """Generate detailed performance report"""
        if not self.results:
            logger.error("No results to report")
            return
            
        with open(output_file, 'w') as f:
            f.write("ADVANCED BACKTESTING REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            # Validation results
            if 'validation' in self.results and self.results['validation']:
                f.write("VALIDATION SET RESULTS\n")
                f.write("-" * 30 + "\n")
                for key, value in self.results['validation'].items():
                    if isinstance(value, float):
                        f.write(f"{key}: {value:.4f}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                f.write("\n")
            
            # Test results
            if 'test' in self.results and self.results['test']:
                f.write("TEST SET RESULTS\n")
                f.write("-" * 30 + "\n")
                for key, value in self.results['test'].items():
                    if isinstance(value, float):
                        f.write(f"{key}: {value:.4f}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                f.write("\n")
            
            # Walk-forward results
            if 'walk_forward' in self.results:
                f.write("WALK-FORWARD VALIDATION\n")
                f.write("-" * 30 + "\n")
                avg_metrics = self.results['walk_forward']['average_metrics']
                for key, value in avg_metrics.items():
                    if isinstance(value, float):
                        f.write(f"Average {key}: {value:.4f}\n")
                    else:
                        f.write(f"Average {key}: {value}\n")
        
        logger.info(f"[OK] Report saved to {output_file}")

if __name__ == "__main__":
    backtester = AdvancedBacktester()
    if backtester.run_complete_backtest():
        backtester.generate_report()
