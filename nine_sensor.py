from fruit_freshness_common import ALL_SENSOR_COLUMNS, feature_importance_text
from train_binary import main


print(
    "Note: this project is now fixed to binary EARLY/LATE labels. "
    "The ESP32-compatible model uses MQ135 only because the hardware has one MQ gas sensor. "
    "Dataset columns available for future multi-sensor experiments: "
    + ", ".join(ALL_SENSOR_COLUMNS)
)

if __name__ == "__main__":
    main()
