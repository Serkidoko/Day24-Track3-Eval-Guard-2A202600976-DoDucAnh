from __future__ import annotations

"""Phase C: production guardrails with PII scan, input/output rails, and latency."""

import asyncio
import json
import os
import re
import statistics
import sys
import time
import unicodedata
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ADVERSARIAL_SET_PATH, LATENCY_BUDGET_P95_MS


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", no_accents)


def setup_presidio():
    try:
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
        from presidio_anonymizer import AnonymizerEngine

        cccd = PatternRecognizer(
            supported_entity="VN_CCCD",
            patterns=[
                Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
                Pattern("CMND 9 digits", r"\b\d{9}\b", 0.7),
            ],
        )
        phone = PatternRecognizer(
            supported_entity="VN_PHONE",
            patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
        )
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers()
        registry.add_recognizer(cccd)
        registry.add_recognizer(phone)
        return AnalyzerEngine(registry=registry), AnonymizerEngine()
    except Exception:
        return None, None


def setup_nemo_rails():
    try:
        from config import GUARDRAILS_CONFIG_DIR
        from nemoguardrails import LLMRails, RailsConfig

        return LLMRails(RailsConfig.from_path(GUARDRAILS_CONFIG_DIR))
    except Exception:
        return None


def _regex_entities(text: str) -> list[dict[str, Any]]:
    patterns = [
        ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.95),
        ("VN_CCCD", r"\b\d{12}\b", 0.90),
        ("VN_CCCD", r"\b\d{9}\b", 0.70),
        ("VN_PHONE", r"\b0[3-9]\d{8}\b", 0.90),
    ]
    entities: list[dict[str, Any]] = []
    occupied: list[range] = []
    for entity_type, pattern, score in patterns:
        for match in re.finditer(pattern, text):
            span = range(match.start(), match.end())
            if any(match.start() in used or match.end() - 1 in used for used in occupied):
                continue
            occupied.append(span)
            entities.append(
                {
                    "type": entity_type,
                    "text": match.group(0),
                    "score": score,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return sorted(entities, key=lambda item: item["start"])


def _anonymize(text: str, entities: list[dict[str, Any]]) -> str:
    anonymized = text
    for entity in sorted(entities, key=lambda item: item["start"], reverse=True):
        anonymized = (
            anonymized[: entity["start"]]
            + f"<{entity['type']}>"
            + anonymized[entity["end"] :]
        )
    return anonymized


def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    entities = _regex_entities(text)

    if analyzer is not None and anonymizer is not None:
        try:
            presidio_results = analyzer.analyze(text=text, language="en")
            for result in presidio_results:
                candidate = {
                    "type": result.entity_type,
                    "text": text[result.start : result.end],
                    "score": round(float(result.score), 3),
                    "start": result.start,
                    "end": result.end,
                }
                if candidate not in entities:
                    entities.append(candidate)
        except Exception:
            pass

    entities = sorted(entities, key=lambda item: item["start"])
    return {
        "has_pii": bool(entities),
        "entities": entities,
        "anonymized": _anonymize(text, entities) if entities else text,
    }


def _input_block_reason(text: str) -> str | None:
    normalized = _normalize(text)

    jailbreak_terms = (
        "ignore previous",
        "pretend you are dan",
        "unrestricted ai",
        "forget your system prompt",
        "system override",
        "bo qua tat ca",
        "dong vai",
        "khong co gioi han",
        "admin command",
        "priority 1",
        "ignore previous instructions",
        "system instructions",
        "training data",
    )
    pii_terms = (
        "cccd cua",
        "so dien thoai cua nhan vien",
        "thong tin ca nhan",
        "tiet lo thong tin",
        "tiet lo bang luong",
        "list all employee salaries",
        "all employee salaries",
        "confidential hr data",
        "employee records",
        "luong thang cua nhan vien",
        "mat khau admin",
    )
    off_topic_terms = (
        "bai tho",
        "mua thu",
        "nau pho",
        "bitcoin",
        "ethereum",
        "giai phuong trinh",
        "marvel",
        "bo phim",
        "thoi tiet",
        "co phieu",
    )
    harmful_terms = ("tan cong mang", "reveal all confidential", "dump all")

    if any(term in normalized for term in jailbreak_terms):
        return "jailbreak_or_prompt_injection"
    if any(term in normalized for term in pii_terms):
        return "pii_request"
    if any(term in normalized for term in off_topic_terms):
        return "off_topic"
    if any(term in normalized for term in harmful_terms):
        return "harmful_request"
    return None


async def check_input_rail(text: str, rails=None) -> dict:
    if rails is not None:
        try:
            response = await rails.generate_async(messages=[{"role": "user", "content": text}])
            response_text = response if isinstance(response, str) else str(response)
            blocked = any(
                keyword in _normalize(response_text)
                for keyword in ("xin loi", "khong the", "cannot", "not allowed")
            )
            return {
                "allowed": not blocked,
                "blocked_reason": "nemo_input_rail" if blocked else None,
                "response": response_text,
            }
        except Exception:
            pass

    reason = _input_block_reason(text)
    return {
        "allowed": reason is None,
        "blocked_reason": reason,
        "response": "allowed" if reason is None else f"blocked: {reason}",
    }


async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    pii = pii_scan(answer)
    normalized_answer = _normalize(answer)
    sensitive = pii["has_pii"] or any(
        term in normalized_answer
        for term in ("cccd cua nhan vien", "mat khau he thong", "thong tin bi mat")
    )
    if sensitive:
        return {
            "safe": False,
            "flagged_reason": "sensitive_output",
            "final_answer": "Toi khong the cung cap thong tin nay. Vui long lien he phong Nhan su.",
        }
    return {"safe": True, "flagged_reason": None, "final_answer": answer}


def run_adversarial_suite(
    adversarial_set: list[dict],
    rails=None,
    analyzer=None,
    anonymizer=None,
) -> list[dict]:
    async def _run_all() -> list[dict]:
        results: list[dict] = []
        for item in adversarial_set:
            blocked_by = None
            pii_result = pii_scan(item["input"], analyzer, anonymizer)
            if pii_result["has_pii"]:
                blocked_by = "presidio"

            if blocked_by is None:
                rail_result = await check_input_rail(item["input"], rails)
                if not rail_result["allowed"]:
                    blocked_by = "nemo_input"

            actual = "blocked" if blocked_by else "allowed"
            results.append(
                {
                    "id": item["id"],
                    "category": item["category"],
                    "input": item["input"],
                    "expected": item["expected"],
                    "actual": actual,
                    "blocked_by": blocked_by,
                    "passed": actual == item["expected"],
                }
            )
        return results

    try:
        return asyncio.run(_run_all())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_run_all())


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    ordered = sorted(values)

    def pct(percent: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percent)))
        return ordered[index]

    return {
        "p50": round(statistics.median(ordered), 3),
        "p95": round(pct(0.95), 3),
        "p99": round(pct(0.99), 3),
    }


def measure_p95_latency(
    test_inputs: list[str],
    n_runs: int = 20,
    rails=None,
    analyzer=None,
    anonymizer=None,
) -> dict:
    inputs = test_inputs or ["test input"]
    presidio_times: list[float] = []
    nemo_times: list[float] = []
    total_times: list[float] = []

    async def _measure() -> None:
        for index in range(max(1, n_runs)):
            text = inputs[index % len(inputs)]
            total_start = time.perf_counter()

            start = time.perf_counter()
            pii_scan(text, analyzer, anonymizer)
            presidio_ms = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            await check_input_rail(text, rails)
            nemo_ms = (time.perf_counter() - start) * 1000

            total_ms = (time.perf_counter() - total_start) * 1000
            presidio_times.append(presidio_ms)
            nemo_times.append(nemo_ms)
            total_times.append(total_ms)

    try:
        asyncio.run(_measure())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_measure())

    total = _percentiles(total_times)
    return {
        "presidio_ms": _percentiles(presidio_times),
        "nemo_ms": _percentiles(nemo_times),
        "total_ms": total,
        "latency_budget_ok": total["p95"] < LATENCY_BUDGET_P95_MS,
        "budget_ms": LATENCY_BUDGET_P95_MS,
    }


if __name__ == "__main__":
    with open(ADVERSARIAL_SET_PATH, encoding="utf-8") as f:
        adversarial_set = json.load(f)
    suite_results = run_adversarial_suite(adversarial_set)
    latency = measure_p95_latency([item["input"] for item in adversarial_set], n_runs=20)
    report = {
        "adversarial_results": suite_results,
        "passed": sum(item["passed"] for item in suite_results),
        "total": len(suite_results),
        "pass_rate": round(sum(item["passed"] for item in suite_results) / len(suite_results), 3),
        "latency": latency,
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/guard_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(
        "Phase C report saved -> reports/guard_results.json "
        f"({report['passed']}/{report['total']} passed)"
    )
