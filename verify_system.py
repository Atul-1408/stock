"""
System Verification Script - Quick Test

This script verifies that all components of the training system
are properly installed and can run basic functionality tests.
"""

import sys
import os

def test_python_environment():
    """Test Python environment and basic imports"""
    print("🔍 Testing Python Environment...")
    print(f"Python Version: {sys.version}")
    
    required_packages = [
        'pandas', 'numpy', 'sklearn', 'yfinance', 
        'matplotlib', 'seaborn', 'joblib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("✅ All required packages installed!")
        return True

def test_file_structure():
    """Test if all required files exist"""
    print("\n🔍 Testing File Structure...")
    
    required_files = [
        'src/trading_bot/data_collector.py',
        'src/trading_bot/backtester_advanced.py', 
        'src/trading_bot/train_brain.py',
        'src/trading_bot/model_evaluator.py',
        'src/trading_bot/train_pipeline.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing files: {len(missing_files)}")
        return False
    else:
        print("✅ All required files present!")
        return True

def test_basic_functionality():
    """Test basic functionality of key components"""
    print("\n🔍 Testing Basic Functionality...")
    
    try:
        # Test data collector import
        from src.trading_bot.data_collector import DataCollector
        print("  ✅ DataCollector import successful")
        
        # Test backtester import  
        from src.trading_bot.backtester_advanced import AdvancedBacktester
        print("  ✅ AdvancedBacktester import successful")
        
        # Test train brain import
        import src.trading_bot.train_brain
        print("  ✅ TrainBrain import successful")
        
        # Test model evaluator import
        from src.trading_bot.model_evaluator import ModelEvaluator
        print("  ✅ ModelEvaluator import successful")
        
        # Test train pipeline import
        import src.trading_bot.train_pipeline
        print("  ✅ TrainPipeline import successful")
        
        print("✅ All components imported successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def main():
    """Main verification function"""
    print("=" * 50)
    print("🚀 TRADING BOT TRAINING SYSTEM - VERIFICATION")
    print("=" * 50)
    
    # Run all tests
    tests = [
        test_python_environment,
        test_file_structure, 
        test_basic_functionality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    # Final summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    if all(results):
        print("🎉 ALL TESTS PASSED!")
        print("✅ System is ready for training!")
        print("\n🚀 NEXT STEPS:")
        print("1. Run complete training: python src/trading_bot/train_pipeline.py")
        print("2. Or run individual components as needed")
        print("3. Check TRAINING_README.md for detailed instructions")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Please check the errors above and install missing dependencies")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)