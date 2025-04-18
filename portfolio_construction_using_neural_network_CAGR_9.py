# -*- coding: utf-8 -*-
"""Portfolio_construction_using_Neural_Network.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1QdZvUQoKoqWNf_YOG1hoAxsRdll7PMag
"""

import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import cvxpy as cp
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# Load ESG, financial, and stock price datasets
esg_data = pd.read_csv("esg_scores_2021.csv")
financial_data = pd.read_csv("filtered_security_data.csv")
price_data = pd.read_csv("snp500_stocks_closing_price_daily_data.csv")

# Remove columns that contain only NaN values
esg_data.dropna(axis=1, how='all', inplace=True)
financial_data.dropna(axis=1, how='all', inplace=True)
price_data.dropna(axis=1, how='all', inplace=True)

# Merge ESG & Financial Data
data = esg_data.merge(financial_data, on="symbol", how="inner")

print("Data Loaded & Merged and its shape is: ", data.shape)
print(data.head())

# Select stocks with ESG scores above the median & low controversy
esg_threshold = data['totalEsg'].median()
selected_stocks = data[(data['totalEsg'] >= esg_threshold) & (data['highestControversy'] <= 2)]

# Create Initial Portfolio with Equal Weights
initial_portfolio = selected_stocks[['symbol', 'totalEsg', 'sector']]
print(initial_portfolio.shape)
initial_weights = np.full(len(initial_portfolio), 1 / len(initial_portfolio))

portfolio = pd.DataFrame({
    'symbol': initial_portfolio['symbol'],
    'weight': initial_weights
})

print("\u2705 Initial Portfolio Created: ", portfolio.shape)
print(portfolio.head())

# Convert wide-format stock prices to long format
price_data_melted = price_data.melt(id_vars=["symbol"], var_name="date", value_name="closing_price")
price_data_melted["date"] = pd.to_datetime(price_data_melted["date"], errors='coerce')
price_data_melted = price_data_melted.sort_values(["symbol", "date"])

# Compute daily returns
price_data_melted["daily_return"] = price_data_melted.groupby("symbol")["closing_price"].pct_change()
print(price_data_melted.isnull().sum())
price_data_melted.dropna(inplace=True)
print(price_data_melted.isnull().sum())

def train_neural_network_for_returns(data, price_data_melted):
    print(list(price_data_melted.columns))

    X = data.select_dtypes(include=[np.number]).copy()
    X = X.drop(columns=['totalEsg'], errors='ignore')

    df_merged = price_data_melted.merge(data, on="symbol", how="inner")
    columns_to_keep = ["symbol", "date"] + df_merged.select_dtypes(include=['float64', 'int64']).columns.tolist()
    df_merged = df_merged[columns_to_keep]

    print(" Merged Data Shape:", df_merged.shape)

    numeric_cols = df_merged.select_dtypes(include=[np.number]).columns
    df_merged[numeric_cols] = df_merged[numeric_cols].fillna(df_merged[numeric_cols].median())

    X = df_merged.drop(columns=["symbol", "date", "closing_price", "daily_return"], errors='ignore')
    y = df_merged["daily_return"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    model = tf.keras.Sequential([
        layers.Dense(64, activation='relu', input_shape=(X_train.shape[1],)),
        layers.Dense(32, activation='relu'),
        layers.Dense(1, activation='linear')
    ])

    model.compile(optimizer='adam', loss='mse', metrics=['mae'])

    history = model.fit(X_train, y_train, epochs=10, batch_size=16, validation_data=(X_test, y_test))

    return model, scaler, X_scaled, history, df_merged

# Train Neural Network to predict future returns
nn_model, scaler, X_scaled, history, df_merged = train_neural_network_for_returns(data, price_data_melted)
print("\u2705 Neural Network Trained to Predict Future Stock Returns")

def optimize_portfolio(nn_model, df_merged, scaler):
    print("\n🚀 Optimizing Portfolio Allocation...")

    # Prepare feature matrix for prediction
    X_new = df_merged.drop(columns=["symbol", "date", "closing_price", "daily_return"], errors='ignore')
    X_new_scaled = scaler.transform(X_new)

    # Predict returns
    predicted_returns = nn_model.predict(X_new_scaled).flatten()
    df_merged['predicted_return'] = predicted_returns

    # Get average predicted return for each stock
    stock_return = df_merged.groupby("symbol")["predicted_return"].mean()

    # Compute covariance matrix of historical daily returns
    return_pivot = df_merged.pivot(index="date", columns="symbol", values="daily_return")
    return_pivot = return_pivot.dropna(axis=1, how='any')  # Drop stocks with missing return history
    cov_matrix = return_pivot.cov()

    common_symbols = list(set(stock_return.index).intersection(set(cov_matrix.columns)))
    stock_return = stock_return[common_symbols]
    cov_matrix = cov_matrix.loc[common_symbols, common_symbols]

    # Define variables for optimization
    n = len(stock_return)
    w = cp.Variable(n)
    ret = stock_return.values
    risk = cp.quad_form(w, cov_matrix.values)

    # Objective: Maximize Sharpe Ratio = Return / Risk
    objective = cp.Maximize(ret @ w - 0.5 * risk)  # trade-off between return and risk
    constraints = [cp.sum(w) == 1, w >= 0]  # long-only portfolio

    problem = cp.Problem(objective, constraints)
    problem.solve()

    # Extract results
    optimal_weights = w.value
    optimal_portfolio = pd.DataFrame({
        "symbol": stock_return.index,
        "weight": optimal_weights
    }).sort_values(by="weight", ascending=False)

    print("✅ Portfolio Optimization Complete. Top Allocations:")
    print(optimal_portfolio.head(10))

    return optimal_portfolio

optimized_portfolio = optimize_portfolio(nn_model, df_merged, scaler)

import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.bar(optimized_portfolio['symbol'], optimized_portfolio['weight'])
plt.xticks(rotation=90)
plt.title("Optimized Portfolio Weights")
plt.ylabel("Weight")
plt.grid(True)
plt.tight_layout()
plt.show()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1️⃣ Load S&P 500 Index Data
sp500_index_data = pd.read_csv("snp500_INDEX_daily_closing_prices.csv")
sp500_index_data["date"] = pd.to_datetime(sp500_index_data["Date"])
sp500_index_data = sp500_index_data.sort_values("date")
sp500_index_data["daily_return"] = sp500_index_data["Close Price"].pct_change()
sp500_index_data = sp500_index_data.dropna(subset=["daily_return"])

# 2️⃣ Prepare Portfolio Daily Returns
# Filter melted price data to symbols in optimized portfolio
selected_symbols = optimized_portfolio["symbol"].tolist()
weights_dict = optimized_portfolio.set_index("symbol")["weight"].to_dict()

# Filter melted stock prices (assuming you already have this)
filtered_price_data = price_data_melted[price_data_melted["symbol"].isin(selected_symbols)]

# Pivot to wide format: date x symbol
pivot_prices = filtered_price_data.pivot(index="date", columns="symbol", values="closing_price")
pivot_prices = pivot_prices.dropna()  # remove rows with missing data

# Calculate daily returns
daily_returns = pivot_prices.pct_change().dropna()

# Align weights with columns
aligned_weights = np.array([weights_dict[symbol] for symbol in daily_returns.columns])

# Calculate portfolio daily returns
portfolio_daily_returns = daily_returns.dot(aligned_weights)

# 3️⃣ Calculate Cumulative Returns
portfolio_cumulative_returns = (1 + portfolio_daily_returns).cumprod()
sp500_cumulative_returns = (1 + sp500_index_data.set_index("date")["daily_return"]).cumprod()

# Align both series to common dates
common_dates = portfolio_cumulative_returns.index.intersection(sp500_cumulative_returns.index)
portfolio_cumulative_returns = portfolio_cumulative_returns.loc[common_dates]
sp500_cumulative_returns = sp500_cumulative_returns.loc[common_dates]

# 4️⃣ Calculate CAGR Function
def calculate_cagr(cumulative_returns):
    total_days = (cumulative_returns.index[-1] - cumulative_returns.index[0]).days
    num_years = total_days / 365.25
    final_return = cumulative_returns.iloc[-1]
    return (final_return ** (1 / num_years) - 1) * 100

portfolio_cagr = calculate_cagr(portfolio_cumulative_returns)
sp500_cagr = calculate_cagr(sp500_cumulative_returns)

# 5️⃣ Plotting Performance
plt.figure(figsize=(12, 6))
plt.plot(portfolio_cumulative_returns, label=f"📈 Optimized Portfolio (CAGR: {portfolio_cagr:.2f}%)", linewidth=2)
plt.plot(sp500_cumulative_returns, label=f"🏛️ S&P 500 Index (CAGR: {sp500_cagr:.2f}%)", linestyle='--', linewidth=2)
plt.title("📊 Backtest: Optimized Portfolio vs. S&P 500 Index")
plt.xlabel("Date")
plt.ylabel("Cumulative Return")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()