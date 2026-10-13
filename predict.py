import argparse

import joblib


MODEL_PATH = "model.pkl"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict banana freshness/spoilage from supported sensor readings."
    )
    parser.add_argument("--mq135", type=float, required=True, help="MQ135 sensor value")
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Accepted for ESP32 input shape, but ignored unless the model was trained with it.",
    )
    parser.add_argument(
        "--humidity",
        type=float,
        default=None,
        help="Accepted for ESP32 input shape, but ignored unless the model was trained with it.",
    )
    args = parser.parse_args()

    artifact = joblib.load(MODEL_PATH)
    features = artifact["features"]
    values_by_feature = {
        "MQ135": args.mq135,
        "Temperature": args.temperature,
        "Humidity": args.humidity,
    }

    missing = [
        feature for feature in features if values_by_feature.get(feature) is None
    ]
    if missing:
        raise SystemExit(f"Missing required model inputs: {missing}")

    ignored = [
        name
        for name in ["Temperature", "Humidity"]
        if values_by_feature[name] is not None and name not in features
    ]
    if ignored:
        print(
            "Note: ignoring "
            + ", ".join(ignored)
            + " because model.pkl was not trained with those columns."
        )

    X = [[values_by_feature[feature] for feature in features]]
    predicted_class = artifact["model"].predict(X)[0]
    output = artifact["output_labels"][predicted_class]
    print(output)


if __name__ == "__main__":
    main()
