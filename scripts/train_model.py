
"""
ML Training Pipeline
- Trains XGBoost Classifier to predict next 15m candle direction
- Saves model to models/btc_predictor_v2.pkl
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

DATA_FILE = "data/btcusdt_1m.csv"
MODEL_PATH = "models/btc_predictor_v2.pkl"

def compute_features(df):
    # Same feature engineering as V2 bot
    # Resample to 15m
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    # Target: Next candle close > Current candle close (1=Up, 0=Down)
    df_15m['target'] = (df_15m['close'].shift(-1) > df_15m['close']).astype(int)
    
    # Features
    # 1. RSI
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    
    # 2. EMAs
    df_15m['ema_20'] = df_15m['close'].ewm(span=20, adjust=False).mean()
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    df_15m['dist_ema_20'] = (df_15m['close'] / df_15m['ema_20']) - 1
    df_15m['dist_ema_50'] = (df_15m['close'] / df_15m['ema_50']) - 1
    
    # 3. Returns
    df_15m['ret_1'] = df_15m['close'].pct_change()
    df_15m['ret_4'] = df_15m['close'].pct_change(4)
    
    # 4. Volatility
    df_15m['volatility'] = df_15m['ret_1'].rolling(20).std()
    
    # Drop NaNs
    df_model = df_15m.dropna()
    return df_model

def train_model():
    print("Loading data...")
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return
        
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df_model = compute_features(df)
    
    print(f"Dataset Shape: {df_model.shape}")
    
    features = ['rsi', 'dist_ema_20', 'dist_ema_50', 'ret_1', 'ret_4', 'volatility']
    X = df_model[features]
    y = df_model['target']
    
    # Split
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    print(f"Training XGBoost on {len(X_train)} samples...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds)
    roc = roc_auc_score(y_test, probs)
    
    print("\n--------------------------------------------------")
    print("MODEL PERFORMANCE")
    print("--------------------------------------------------")
    print(f"Accuracy: {acc:.4f}")
    print(f"ROC AUC:  {roc:.4f}")
    print("--------------------------------------------------")
    
    # Save
    os.makedirs("models", exist_ok=True)
    artifact = {
        'model': model,
        'features': features,
        'version': 'v2_xgboost'
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artifact, f)
        
    print(f"Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_model()
