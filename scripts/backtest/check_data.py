"""
Check Data Range
"""
import pandas as pd

df = pd.read_csv('data/btcusdt_1m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("DATASET INFO:")
print(f"Start Date: {df['timestamp'].min()}")
print(f"End Date:   {df['timestamp'].max()}")
print(f"Total Days: {(df['timestamp'].max() - df['timestamp'].min()).days}")
