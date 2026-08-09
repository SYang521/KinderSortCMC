# benchmark_evaluator.py
#
# Evaluate KinderSort output against a CSV ground-truth file.
#
# This tool:
# 1. Reads expected identities from ground_truth.csv.
# 2. Scans KinderSort output folders.
# 3. Determines the identities predicted for every image.
# 4. Calculates exact-match accuracy.
# 5. Exports detailed results to a CSV file.
#
# This tool does not modify or upload test photographs.

import argparse
import csv
from collections import defaultdict
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


def normalize_name(value: str) -> str:
    # Remove surrounding spaces and convert text to lowercase.
    return value.strip().lower()


def original_filename(output_filename: str) -> str:
    # KinderSort may rename an output file like this:
    # Event_Name__original_photo.jpg
    #
    # Return only the original filename after the double underscore.

    if "__" in output_filename:
        return output_filename.split("__", 1)[1]

    return output_filename


def parse_people(value: str) -> set[str]:
    # Convert semicolon-separated identities into a normalized set.
    #
    # Example:
    # Person_A;Person_C
    # Result:
    # {"person_a", "person_c"}

    if not value.strip():
        return set()

    return {
        normalize_name(person)
        for person in value.split(";")
        if person.strip()
    }


def display_people(people: set[str]) -> str:
    # Convert an identity set into readable semicolon-separated text.

    if not people:
        return "_unmatched"

    return ";".join(sorted(people))


def load_ground_truth(csv_path: Path) -> list[dict[str, object]]:
    # Load and validate benchmark ground-truth records.

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Ground-truth file was not found: {csv_path}"
        )

    required_columns = {
        "filename",
        "expected_people",
        "category",
    }

    records: list[dict[str, object]] = []
    seen_filenames: set[str] = set()

    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError(
                "The ground-truth CSV file has no header row."
            )

        # Normalize fieldnames to strip accidental whitespace
        reader.fieldnames = [col.strip() for col in reader.fieldnames if col]
        actual_columns = set(reader.fieldnames)

        missing_columns = required_columns - actual_columns

        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))

            raise ValueError(
                f"Ground-truth CSV is missing columns: {missing_text}"
            )

        for row_number, row in enumerate(reader, start=2):
            filename = (row.get("filename") or "").strip()
            expected_text = (row.get("expected_people") or "").strip()
            category = (row.get("category") or "").strip()

            if not filename:
                raise ValueError(
                    f"Filename is empty on CSV row {row_number}."
                )

            normalized_filename = normalize_name(filename)

            if normalized_filename in seen_filenames:
                raise ValueError(
                    f"Duplicate filename on CSV row {row_number}: "
                    f"{filename}"
                )

            seen_filenames.add(normalized_filename)

            records.append(
                {
                    "filename": filename,
                    "normalized_filename": normalized_filename,
                    "expected": parse_people(expected_text),
                    "category": category or "not_specified",
                }
            )

    if not records:
        raise ValueError(
            "The ground-truth CSV contains no test records."
        )

    return records


def scan_predictions(
    output_folder: Path,
) -> dict[str, set[str]]:
    # Scan KinderSort output folders and collect predicted identities.
    #
    # Normal person folders represent predicted identities.
    # Files in the _unmatched folder produce an empty identity set.

    if not output_folder.is_dir():
        raise NotADirectoryError(
            f"KinderSort output folder was not found: {output_folder}"
        )

    predictions: dict[str, set[str]] = defaultdict(set)

    for person_folder in output_folder.iterdir():
        if not person_folder.is_dir():
            continue

        person_name = normalize_name(person_folder.name)

        for image_path in person_folder.rglob("*"):
            if not image_path.is_file():
                continue

            if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            source_name = original_filename(image_path.name)
            normalized_filename = normalize_name(source_name)

            if person_name == "_unmatched":
                predictions.setdefault(normalized_filename, set())
            else:
                predictions[normalized_filename].add(person_name)

    return dict(predictions)


def evaluate(
    ground_truth: list[dict[str, object]],
    predictions: dict[str, set[str]],
) -> list[dict[str, str]]:
    # Compare expected identities with predicted identities.

    results: list[dict[str, str]] = []

    for record in ground_truth:
        filename = str(record["filename"])
        normalized_filename = str(
            record["normalized_filename"]
        )
        expected = set(record["expected"])
        category = str(record["category"])

        actual = predictions.get(normalized_filename, set())
        is_correct = expected == actual

        if is_correct:
            notes = ""
        elif not actual:
            notes = "Face not matched"
        elif expected.isdisjoint(actual):
            notes = "Wrong identity"
        else:
            notes = "Partial or additional identity match"

        results.append(
            {
                "filename": filename,
                "expected": display_people(expected),
                "actual": display_people(actual),
                "category": category,
                "result": (
                    "Correct" if is_correct else "Incorrect"
                ),
                "notes": notes,
            }
        )

    return results


def write_results(
    results: list[dict[str, str]],
    output_csv: Path,
) -> None:
    # Write detailed benchmark results to a CSV file.

    output_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "filename",
        "expected",
        "actual",
        "category",
        "result",
        "notes",
    ]

    with output_csv.open(
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)


def calculate_summary(
    results: list[dict[str, str]],
) -> dict[str, str]:
    # Calculate benchmark summary metrics.

    total = len(results)

    correct = sum(
        row["result"] == "Correct"
        for row in results
    )

    incorrect = total - correct

    unmatched = sum(
        row["actual"] == "_unmatched"
        for row in results
    )

    wrong_identity = sum(
        row["notes"] == "Wrong identity"
        for row in results
    )

    partial_match = sum(
        row["notes"] == "Partial or additional identity match"
        for row in results
    )

    accuracy = correct / total if total else 0.0

    return {
        "total_images": str(total),
        "correct_classifications": str(correct),
        "incorrect_classifications": str(incorrect),
        "unmatched_images": str(unmatched),
        "wrong_identity_classifications": str(wrong_identity),
        "partial_or_additional_matches": str(partial_match),
        "exact_match_accuracy": f"{accuracy:.2%}",
    }


def write_summary(
    summary: dict[str, str],
    summary_csv: Path,
) -> None:
    # Export benchmark summary metrics to a CSV file.

    summary_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with summary_csv.open(
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "metric",
                "value",
            ]
        )

        for metric, value in summary.items():
            writer.writerow(
                [
                    metric,
                    value,
                ]
            )


def print_summary(
    results: list[dict[str, str]],
) -> None:
    # Calculate and display benchmark metrics.

    total = len(results)

    correct = sum(
        row["result"] == "Correct"
        for row in results
    )

    incorrect = total - correct

    unmatched = sum(
        row["actual"] == "_unmatched"
        for row in results
    )

    wrong_identity = sum(
        row["notes"] == "Wrong identity"
        for row in results
    )

    partial_match = sum(
        row["notes"] == "Partial or additional identity match"
        for row in results
    )

    accuracy = correct / total if total else 0.0

    print()
    print("=" * 56)
    print("KinderSort Benchmark Evaluation")
    print("=" * 56)
    print(f"Total images                    : {total}")
    print(f"Correct classifications         : {correct}")
    print(f"Incorrect classifications       : {incorrect}")
    print(f"Unmatched images                : {unmatched}")
    print(f"Wrong-identity classifications  : {wrong_identity}")
    print(f"Partial/additional matches       : {partial_match}")
    print(f"Exact-match accuracy            : {accuracy:.2%}")
    print("=" * 56)


def build_parser() -> argparse.ArgumentParser:
    # Create the command-line arguments.

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate KinderSort output against "
            "a ground-truth CSV file."
        )
    )

    parser.add_argument(
        "--ground-truth",
        required=True,
        type=Path,
        help="Path to the ground_truth.csv file",
    )

    parser.add_argument(
        "--output-folder",
        required=True,
        type=Path,
        help="Path to the KinderSort Output folder",
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=Path("benchmark_evaluation.csv"),
        help=(
            "Path for the generated result CSV. "
            "Default: benchmark_evaluation.csv"
        ),
    )

    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("benchmark_summary.csv"),
        help=(
            "Path for the generated summary CSV. "
            "Default: benchmark_summary.csv"
        ),
    )

    return parser


def main() -> None:
    # Run the complete benchmark evaluation.

    parser = build_parser()
    args = parser.parse_args()

    try:
        ground_truth = load_ground_truth(
            args.ground_truth
        )

        predictions = scan_predictions(
            args.output_folder
        )

        results = evaluate(
            ground_truth,
            predictions,
        )

        write_results(
            results,
            args.results,
        )

        summary = calculate_summary(results)

        write_summary(
            summary,
            args.summary,
        )

        print_summary(results)

        print()
        print(
            "Detailed results saved to: "
            f"{args.results.resolve()}"
        )

        print(
            "Summary results saved to: "
            f"{args.summary.resolve()}"
        )

    except (
        FileNotFoundError,
        NotADirectoryError,
        ValueError,
    ) as error:
        print()
        print(f"Evaluation failed: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()