import json

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from fruit_freshness_common import (
    CLASS_LABELS,
    FINAL_RANDOM_FOREST_CONFIG,
    MODEL_FEATURES,
    feature_importance_text,
    leave_one_file_out,
    load_all_data,
    print_dataset_summary,
    standard_validation,
)


MODEL_PATH = "model.pkl"
SUMMARY_PATH = "model_summary.json"


def tree_summary(model: RandomForestClassifier) -> list[dict[str, int]]:
    return [
        {
            "tree_index": index,
            "node_count": int(tree.tree_.node_count),
            "max_depth": int(tree.tree_.max_depth),
        }
        for index, tree in enumerate(model.estimators_)
    ]


def tree_structure(model: RandomForestClassifier) -> list[dict[str, object]]:
    structures = []
    classes = list(model.classes_)
    late_index = classes.index("LATE")

    for tree_index, estimator in enumerate(model.estimators_):
        tree = estimator.tree_
        nodes = []
        for node_id in range(tree.node_count):
            counts = tree.value[node_id][0]
            total = float(np.sum(counts))
            late_probability = 0.0 if total == 0 else float(counts[late_index] / total)
            nodes.append(
                {
                    "node": int(node_id),
                    "feature": (
                        None
                        if int(tree.feature[node_id]) < 0
                        else MODEL_FEATURES[int(tree.feature[node_id])]
                    ),
                    "threshold": (
                        None
                        if int(tree.feature[node_id]) < 0
                        else float(tree.threshold[node_id])
                    ),
                    "left": int(tree.children_left[node_id]),
                    "right": int(tree.children_right[node_id]),
                    "late_probability": late_probability,
                }
            )
        structures.append({"tree_index": tree_index, "nodes": nodes})
    return structures


def main() -> None:
    print_dataset_summary(MODEL_FEATURES)

    rf = RandomForestClassifier(**FINAL_RANDOM_FOREST_CONFIG)

    print("\n" + "=" * 72)
    print("FINAL RANDOM FOREST VALIDATION")
    print("=" * 72)

    standard = standard_validation(rf, MODEL_FEATURES)
    lofo_results, lofo_average = leave_one_file_out(rf, MODEL_FEATURES)

    print("\nStandard train/test validation")
    print(f"Accuracy:  {standard['accuracy'] * 100:.2f}%")
    print(f"Precision: {standard['precision']:.4f}")
    print(f"Recall:    {standard['recall']:.4f}")
    print(f"F1:        {standard['f1']:.4f}")
    print("Confusion matrix [EARLY, LATE]:")
    print(standard["confusion_matrix"])

    print("\nLeave-one-file-out validation")
    for result in lofo_results:
        print(
            f"{result['file']} ({result['label']}): "
            f"{result['accuracy'] * 100:.2f}%"
        )
        print("Confusion matrix [EARLY, LATE]:")
        print(result["confusion_matrix"])
    print(f"Random Forest leave-one-file-out average: {lofo_average * 100:.2f}%")
    print("Reference: previous best cross-file average was 83.55% from Gaussian NB.")

    data = load_all_data(MODEL_FEATURES)
    final_model = RandomForestClassifier(**FINAL_RANDOM_FOREST_CONFIG)
    final_model.fit(data[MODEL_FEATURES].to_numpy(), data["Class"].to_numpy())

    summary = {
        "model_name": "Random Forest",
        "features": MODEL_FEATURES,
        "classes": CLASS_LABELS,
        "random_forest_config": {
            key: value
            for key, value in FINAL_RANDOM_FOREST_CONFIG.items()
            if key != "n_jobs"
        },
        "n_trees": int(len(final_model.estimators_)),
        "tree_summary": tree_summary(final_model),
        "tree_structure": tree_structure(final_model),
        "feature_importance": {
            feature: float(value)
            for feature, value in zip(MODEL_FEATURES, final_model.feature_importances_)
        },
        "standard_validation": {
            "accuracy": float(standard["accuracy"]),
            "precision": float(standard["precision"]),
            "recall": float(standard["recall"]),
            "f1": float(standard["f1"]),
            "confusion_matrix": standard["confusion_matrix"].tolist(),
        },
        "leave_one_file_out": {
            "random_forest_average_accuracy": float(lofo_average),
            "reference_best_average_accuracy": 0.8355,
            "reference_best_model": "Gaussian NB",
            "results": [
                {
                    "file": result["file"],
                    "label": result["label"],
                    "accuracy": float(result["accuracy"]),
                    "precision": float(result["precision"]),
                    "recall": float(result["recall"]),
                    "f1": float(result["f1"]),
                    "confusion_matrix": result["confusion_matrix"].tolist(),
                }
                for result in lofo_results
            ],
        },
        "dataset_limitation": (
            "The training dataset has MQ gas sensor columns only. DHT22 "
            "temperature and humidity are read on ESP32 for display/logging but "
            "are not ML inputs."
        ),
    }

    artifact = {
        "model": final_model,
        "model_name": "Random Forest",
        "features": MODEL_FEATURES,
        "class_labels": CLASS_LABELS,
        "output_labels": {"EARLY": "EARLY", "LATE": "LATE"},
        "summary": summary,
    }

    joblib.dump(artifact, MODEL_PATH)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 72)
    print("FINAL RANDOM FOREST MODEL")
    print("=" * 72)
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved summary: {SUMMARY_PATH}")
    print(f"Trees: {summary['n_trees']}")
    for item in summary["tree_summary"]:
        print(
            f"Tree {item['tree_index']}: "
            f"nodes={item['node_count']}, max_depth={item['max_depth']}"
        )
    print("Feature importance / coefficient:")
    print(feature_importance_text(final_model, MODEL_FEATURES))


if __name__ == "__main__":
    main()
