from fruit_freshness_common import (
    MODEL_FEATURES,
    feature_importance_text,
    get_model_candidates,
    leave_one_file_out,
    load_all_data,
    print_dataset_summary,
)


def main() -> None:
    print_dataset_summary(MODEL_FEATURES)

    for name, model in get_model_candidates().items():
        results, average_accuracy = leave_one_file_out(model, MODEL_FEATURES)

        print("\n" + "=" * 72)
        print(f"{name} LEAVE-ONE-FILE-OUT")
        print("=" * 72)

        for result in results:
            print(f"\nTest file: {result['file']} ({result['label']})")
            print(f"Accuracy:  {result['accuracy'] * 100:.2f}%")
            print(f"Precision: {result['precision']:.4f}")
            print(f"Recall:    {result['recall']:.4f}")
            print(f"F1:        {result['f1']:.4f}")
            print("Confusion matrix [EARLY, LATE]:")
            print(result["confusion_matrix"])
            print("Classification report:")
            print(result["classification_report"])

        data = load_all_data(MODEL_FEATURES)
        fitted = model.fit(data[MODEL_FEATURES].to_numpy(), data["Class"].to_numpy())
        print("\nFeature importance / coefficient on all data:")
        print(feature_importance_text(fitted, MODEL_FEATURES))
        print(f"\nAverage leave-one-file-out accuracy: {average_accuracy * 100:.2f}%")


if __name__ == "__main__":
    main()
