# Failure Cluster Analysis - Phase A

**Sinh vien:** Do Duc Anh  
**Ngay:** 2026-06-30

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---:|---:|---:|
| faithfulness | 1.0000 | 1.0000 | 1.0000 |
| answer_relevancy | 0.8030 | 0.6289 | 0.5883 |
| context_precision | 0.4299 | 0.3992 | 0.3714 |
| context_recall | 0.9284 | 0.7086 | 0.5983 |
| **avg_score** | **0.7903** | **0.6842** | **0.6395** |

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question | avg_score | worst_metric |
|---:|---|---|---:|---|
| 1 | adversarial | Bao lau phai doi mat khau mot lan? | 0.5493 | context_precision |
| 2 | multi_hop | Luong thu viec cua nhan vien Junior muc cao nhat la bao nhieu? | 0.5659 | context_precision |
| 3 | adversarial | Manager co the dung VPN ca nhan khi WFH khong? | 0.5692 | context_precision |
| 4 | adversarial | Nhan vien duoc nghi bao nhieu ngay phep nam? | 0.5756 | context_precision |
| 5 | adversarial | Theo chinh sach nghi phep cu v2023, hien tai ban nao co hieu luc? | 0.5791 | context_precision |
| 6 | multi_hop | So sanh yeu cau mat khau giua policy v1.0 va v2.0 | 0.5884 | context_precision |
| 7 | multi_hop | Manager tham nien 12 nam: phu cap va so ngay phep nam | 0.5957 | context_precision |
| 8 | adversarial | Tham nien bao nhieu nam thi duoc cong them ngay phep? | 0.6026 | context_precision |
| 9 | multi_hop | Laptop 30 trieu cho nhan vien moi can phe duyet va CNTT gi? | 0.6075 | context_precision |
| 10 | multi_hop | Tam ung 4 trieu va 7 trieu: quy trinh phe duyet khac nhau the nao? | 0.6124 | context_precision |

---

## 3. Failure Cluster Matrix

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---:|---:|---:|---:|
| faithfulness | 0 | 0 | 0 | 0 |
| answer_relevancy | 0 | 0 | 0 | 0 |
| context_precision | 20 | 20 | 10 | 50 |
| context_recall | 0 | 0 | 0 | 0 |

---

## 4. Dominant Failure Analysis

**Dominant distribution:** factual  
**Dominant metric:** context_precision

**Ly do phan tich:**

Context precision la diem yeu ro nhat: tat ca 50 cau deu co worst_metric la `context_precision`. Dieu nay cho thay retriever lay duoc ngu canh lien quan de giu faithfulness/context_recall kha tot, nhung top contexts van lan nhieu chunk gan dung hoac trung chu de. Distribution factual va multi_hop cung co 20 failure vi co nhieu cau hon adversarial; tuy nhien avg_score thap nhat lai la adversarial (0.6395), dung voi ky vong version-conflict/negation trap kho hon factual. Can uu tien metadata filter theo phien ban policy va reranking manh hon cho cac cau lien quan v2023/v2024, v1/v2.

---

## 5. Suggested Fixes

| Metric yeu | Root cause | Suggested fix |
|---|---|---|
| faithfulness | LLM hallucinating | Giu prompt bat buoc tra loi theo context, kem citation chunk/source. |
| context_recall | Missing relevant chunks | Tang top_k ung vien, them lexical/BM25 fallback va query expansion cho tieng Viet. |
| context_precision | Too many irrelevant chunks | Them reranker, filter metadata theo ngay hieu luc/phien ban, uu tien policy hien hanh. |
| answer_relevancy | Answer does not match question | Prompt tra loi truc tiep cau hoi, cat bot noi dung policy khong duoc hoi. |

---

## 6. Nhan xet ve Adversarial Distribution

Adversarial avg_score = 0.6395, thap hon multi_hop = 0.6842 va factual = 0.7903, nen bonus Phase A duoc thoa. Trong bottom 10 co 5 cau adversarial: #44, #50, #41, #49, #42. Cac cau nay deu lien quan version conflict (mat khau v1/v2, nghi phep 2023/2024) hoac policy contradiction (VPN ca nhan), nen retriever de lay ca chunk cu va chunk moi lam giam precision. Huong cai thien uu tien la gan metadata `effective_date`, `status`, `version` vao chunk va filter/rerank ban policy hien hanh.
