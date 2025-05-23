# -*- coding: utf-8 -*-
"""correlation_analysis_for_important_features.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1PIKWd3ofLl2pPY-_THQ-DC39Ue1nvnRt
"""

import pandas as pd

# Load the data
df_financial = pd.read_csv("filtered_security_data.csv")

# Step 1: Drop columns with all null values
df_financial = df_financial.dropna(axis=1, how='all')

# Step 2: Preserve 'symbol' before removing non-numeric columns
symbol_col = df_financial["symbol"]

# Step 3: Drop irrelevant non-numeric columns
columns_to_drop = [
    "zip", "sector", "longBusinessSummary", "city", "phone", "state", "country", "company",
    "website", "maxAge", "address1", "industry", "currency", "exchange", "shortName", "longName",
    "exchangeTimezoneName", "exchangeTimezoneShortName", "isEsgPopulated", "quoteType",
    "messageBoardId", "uuid", "market", "logo_url", "address2", "fax"
]

df_financial.drop(columns=[col for col in columns_to_drop if col in df_financial.columns], inplace=True)

# Step 4: Keep only numeric columns
df_financial = df_financial.select_dtypes(include=['number'])

# Step 5: Add 'symbol' back at the beginning
df_financial.insert(0, "symbol", symbol_col)

# Done
print("Final shape after cleanup:", df_financial.shape)
df_financial.head()

# Load ESG data
df_esg = pd.read_csv("esg_scores_2021.csv")

# Merge on 'symbol'
df_merged = pd.merge(df_financial, df_esg[["symbol", "totalEsg", "highestControversy"]], on="symbol", how="inner")

# print(df_merged.head(10))

# Compute correlation
correlation_matrix = df_merged.corr(numeric_only=True)

# Extract correlation with totalEsg and highestControversy
correlation_with_esg = correlation_matrix[["totalEsg", "highestControversy"]].sort_values(by="totalEsg", ascending=False)

# Display top correlations
print("Top correlations with totalEsg and highestControversy:")
print(correlation_with_esg.head(25))