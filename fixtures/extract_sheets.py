import pandas as pd

# Path to your downloaded Excel
excel_file = "/Users/yashaswipatki/Downloads/data.xlsx"

# Output directory
output_dir = "fixtures/"

# Sheets to extract
sheets = ["actuals", "budget", "fx", "cash"]

for sheet in sheets:
    df = pd.read_excel(excel_file, sheet_name=sheet)
    out_path = f"{output_dir}{sheet}.csv"
    df.to_csv(out_path, index=False)
    print(f"✅ Saved {sheet} → {out_path}")
