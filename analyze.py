import pandas as pd
from pathlib import Path

DATA_DIR = Path(
    r"Food-Freshness-E-Nose-Dataset\AllSamples-Report"
)

FILES = [
    ("Banana D1.csv", "EARLY"),
    ("Banana D2.csv", "EARLY"),
    ("Banana D3.csv", "EARLY"),
    ("Banana D4.csv", "LATE"),
    ("Banana D5.csv", "LATE"),
]

all_data = []

for filename, stage in FILES:

    path = DATA_DIR / filename

    df = pd.read_csv(path)

    df["Stage"] = stage

    all_data.append(df[["MQ135", "Stage"]])


data = pd.concat(all_data, ignore_index=True)


print("\n========================================")
print("MQ135 STATISTICS BY BINARY CLASS")
print("========================================\n")

stats = data.groupby("Stage")["MQ135"].agg(
    [
        "count",
        "mean",
        "median",
        "std",
        "min",
        "max",
        lambda x: x.quantile(0.25),
        lambda x: x.quantile(0.75),
    ]
)

stats.columns = [
    "Count",
    "Mean",
    "Median",
    "Std",
    "Min",
    "Max",
    "Q1",
    "Q3",
]

print(stats.round(2).to_string())


print("\n========================================")
print("RANGE OVERLAP")
print("========================================\n")

for stage in ["EARLY", "LATE"]:

    values = data[data["Stage"] == stage]["MQ135"]

    print(
        f"{stage}: "
        f"{values.min():.0f} - "
        f"{values.max():.0f}"
    )
