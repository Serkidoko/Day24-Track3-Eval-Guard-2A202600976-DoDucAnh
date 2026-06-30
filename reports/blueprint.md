# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh vien:** Do Duc Anh  
**Ngay:** 2026-06-30

---

## Guard Stack Pipeline

| Layer | Tool | Latency P95 | Failure Action |
|---|---|---:|---|
| PII Detection | Presidio-compatible regex recognizers | 0.024ms | Reject + log |
| Topic/Jailbreak | NeMo Input Rail compatible async checker | 0.065ms | 503 + reason |
| RAG Pipeline | Day 18 local fallback pipeline | ~2.0ms | Fallback answer from top context |
| Output Check | NeMo Output Rail compatible checker | ~0.065ms | Block + log |

---

## Latency Budget

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---:|---:|---:|---:|
| Presidio PII | 0.018 | 0.024 | 0.063 | <10ms |
| NeMo Input Rail | 0.036 | 0.065 | 0.095 | <300ms |
| RAG Pipeline | ~2.000 | ~2.000 | ~2.000 | <2000ms |
| NeMo Output Rail | ~0.036 | ~0.065 | ~0.095 | <300ms |
| **Total Guard** | 0.055 | **0.117** | 0.130 | **<500ms** |

**Budget OK?** Yes  
**Comment:** Guard latency is far below budget because the submitted stack uses deterministic local rails for testability. In production, the NeMo/LLM rail would dominate latency and should be monitored separately from the RAG call.

---

## CI/CD Gates

- [x] RAGAS faithfulness >= 0.75: factual=1.0000, multi_hop=1.0000, adversarial=1.0000.
- [x] RAGAS avg_score >= 0.65 overall: weighted avg_score = 0.7177.
- [x] Adversarial suite pass rate >= 90%: 20/20 passed.
- [x] P95 total guard latency < 500ms: 0.117ms.
- [x] Cohen's kappa > 0.6 for judge sanity: 0.7826.

---

## Monitoring Dashboard

| Metric | Current Lab Result | Alert Threshold | Action |
|---|---:|---:|---|
| RAGAS faithfulness daily sample | 1.0000 | <0.70 | Page owner and inspect hallucination cases |
| RAGAS context_precision | 0.4019 overall | <0.55 | Tune reranker and policy metadata filters |
| Adversarial pass rate | 20/20 | <18/20 | Review new attack patterns and update rails |
| Guard P95 latency | 0.117ms | >600ms | Profile rail layer and cache deterministic checks |
| PII detected count | measured per request | spike >10/hour | Security alert and audit logs |

---

## Ket qua thuc te tu Lab

| | Ket qua |
|---|---:|
| RAGAS avg_score (50q) | 0.7177 |
| Worst metric | context_precision |
| Dominant failure distribution | factual |
| Lowest avg_score distribution | adversarial |
| Cohen's kappa | 0.7826 |
| Adversarial pass rate | 20 / 20 |
| Guard P95 latency | 0.117 ms |

---

## Nhan xet & Cai tien

Stack hien tai pass toan bo guard tests va co latency rat thap vi dung local deterministic fallback. RAGAS cho thay context_precision la diem yeu lon nhat: retriever lay duoc thong tin de giu faithfulness cao, nhung top contexts con nhieu chunk gan dung lam giam precision. Neu deploy production, nen them metadata version/effective_date/status cho tung policy, rerank theo policy hien hanh, va chay canary eval hang ngay tren factual/multi-hop/adversarial. LLM judge dat kappa 0.7826, du tot lam signal CI, nhung van can human review cho cac failure lien quan compliance/security.
