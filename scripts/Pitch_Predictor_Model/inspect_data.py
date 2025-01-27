import pandas as pd

file_path = '/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast_Model_2024.csv'
data = pd.read_csv(file_path)

def inspect_data(df):
    print("\n--- Dataset Overview ---")
    print(f"Number of rows: {df.shape[0]}")
    print(f"Number of columns: {df.shape[1]}")

    print("\n--- Column Data Types ---")
    print(df.dtypes)

    print("\n--- Missing Values ---")
    missing_values = df.isnull().sum()
    print(missing_values[missing_values > 0])

    print("\n--- Summary Statistics ---")
    print(df.describe(include='all'))

    print("\n--- Sample Rows ---")
    print(df.head())

    print("\n--- Duplicate Rows ---")
    duplicates = df.duplicated().sum()
    print(f"Number of duplicate rows: {duplicates}")

    print("\n--- Unique Values Per Column ---")
    for column in df.columns:
        print(f"{column}: {df[column].nunique()} unique values")

inspect_data(data)