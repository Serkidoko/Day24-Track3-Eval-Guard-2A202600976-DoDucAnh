from __future__ import annotations

"""Phase A: deterministic RAGAS-style production evaluation."""

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANSWERS_PATH, TEST_SET_PATH

Distribution = str

METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
DISTRIBUTIONS = ("factual", "multi_hop", "adversarial")

DIAGNOSTIC_TREE = {
    "faithfulness": ("LLM hallucinating", "Tighten system prompt and require citations from retrieved context"),
    "context_recall": ("Missing relevant chunks", "Improve chunking, add lexical fallback, and retrieve more diverse chunks"),
    "context_precision": ("Too many irrelevant chunks", "Add reranking and metadata filters for policy version/date"),
    "answer_relevancy": ("Answer does not match question", "Make the prompt answer only the requested policy point"),
}


@dataclass
class RagasResult:
    question_id: int
    distribution: Distribution
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    @property
    def avg_score(self) -> float:
        return (
            self.faithfulness
            + self.answer_relevancy
            + self.context_precision
            + self.context_recall
        ) / 4

    @property
    def worst_metric(self) -> str:
        scores = {metric: getattr(self, metric) for metric in METRICS}
        return min(scores, key=scores.get)


def load_test_set_50q(path: str = TEST_SET_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_answers(path: str = ANSWERS_PATH) -> list[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"answers_50q.json not found at {path}. Run python setup_answers.py first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]:
    groups = {distribution: [] for distribution in DISTRIBUTIONS}
    for item in test_set:
        distribution = item.get("distribution")
        if distribution in groups:
            groups[distribution].append(item)
    return groups


def _metric_value(row: Any, name: str, default: float = 0.0) -> float:
    if isinstance(row, dict):
        value = row.get(name, default)
    else:
        value = getattr(row, name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def run_ragas_50q(answers: list[dict]) -> list[RagasResult]:
    from src.m4_eval import evaluate_ragas

    questions = [item.get("question", "") for item in answers]
    answer_texts = [item.get("answer", "") for item in answers]
    contexts = [item.get("contexts", []) for item in answers]
    ground_truths = [item.get("ground_truth", "") for item in answers]

    raw = evaluate_ragas(questions, answer_texts, contexts, ground_truths)
    per_question = raw.get("per_question", []) if isinstance(raw, dict) else []

    results: list[RagasResult] = []
    for index, answer in enumerate(answers):
        metric_row = per_question[index] if index < len(per_question) else {}
        results.append(
            RagasResult(
                question_id=int(answer.get("id", index + 1)),
                distribution=answer.get("distribution", "factual"),
                question=answer.get("question", ""),
                answer=answer.get("answer", ""),
                contexts=list(answer.get("contexts", [])),
                ground_truth=answer.get("ground_truth", ""),
                faithfulness=_metric_value(metric_row, "faithfulness"),
                answer_relevancy=_metric_value(metric_row, "answer_relevancy"),
                context_precision=_metric_value(metric_row, "context_precision"),
                context_recall=_metric_value(metric_row, "context_recall"),
            )
        )
    return results


def bottom_10(results: list[RagasResult]) -> list[dict]:
    output: list[dict] = []
    for rank, result in enumerate(sorted(results, key=lambda item: item.avg_score)[:10], start=1):
        diagnosis, suggested_fix = DIAGNOSTIC_TREE[result.worst_metric]
        output.append(
            {
                "rank": rank,
                "question_id": result.question_id,
                "distribution": result.distribution,
                "question": result.question,
                "avg_score": round(result.avg_score, 4),
                "worst_metric": result.worst_metric,
                "diagnosis": diagnosis,
                "suggested_fix": suggested_fix,
            }
        )
    return output


def cluster_analysis(results: list[RagasResult]) -> dict:
    matrix = {metric: {distribution: 0 for distribution in DISTRIBUTIONS} for metric in METRICS}
    for result in results:
        if result.distribution in DISTRIBUTIONS:
            matrix[result.worst_metric][result.distribution] += 1

    if not results:
        return {
            "matrix": matrix,
            "dominant_failure_distribution": None,
            "dominant_failure_metric": None,
            "insight": "No RAGAS results were available for cluster analysis.",
        }

    dominant_distribution = max(
        DISTRIBUTIONS,
        key=lambda distribution: sum(matrix[metric][distribution] for metric in METRICS),
    )
    dominant_metric = max(METRICS, key=lambda metric: sum(matrix[metric].values()))
    diagnosis, suggested_fix = DIAGNOSTIC_TREE[dominant_metric]
    insight = (
        f"The dominant cluster is {dominant_distribution}/{dominant_metric}: {diagnosis}. "
        f"Recommended fix: {suggested_fix}."
    )

    return {
        "matrix": matrix,
        "dominant_failure_distribution": dominant_distribution,
        "dominant_failure_metric": dominant_metric,
        "insight": insight,
    }


def _per_distribution(results: list[RagasResult]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for distribution in DISTRIBUTIONS:
        subset = [result for result in results if result.distribution == distribution]
        if not subset:
            summary[distribution] = {"count": 0}
            continue
        summary[distribution] = {"count": len(subset)}
        for metric in METRICS:
            summary[distribution][metric] = round(
                sum(getattr(item, metric) for item in subset) / len(subset), 4
            )
        summary[distribution]["avg_score"] = round(
            sum(item.avg_score for item in subset) / len(subset), 4
        )
    return summary


def save_phase_a_report(
    results: list[RagasResult],
    clusters: dict,
    path: str = "reports/ragas_50q.json",
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    report = {
        "total_questions": len(results),
        "per_distribution": _per_distribution(results),
        "failure_clusters": clusters,
        "bottom_10": bottom_10(results),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Phase A report saved -> {path}")


if __name__ == "__main__":
    test_set = load_test_set_50q()
    groups = group_by_distribution(test_set)
    print(f"Loaded {len(test_set)} questions")
    for distribution, questions in groups.items():
        print(f"  {distribution}: {len(questions)}")

    results = run_ragas_50q(load_answers())
    clusters = cluster_analysis(results)
    save_phase_a_report(results, clusters)

    print("Bottom 10:")
    for item in bottom_10(results):
        print(
            f"  #{item['rank']} [{item['distribution']}] "
            f"avg={item['avg_score']:.3f} worst={item['worst_metric']}"
        )
    print(
        "Dominant failure: "
        f"{clusters.get('dominant_failure_distribution')} / "
        f"{clusters.get('dominant_failure_metric')}"
    )
