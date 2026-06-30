# LLM Judge Bias Report - Phase B

**Sinh vien:** Do Duc Anh  
**Ngay:** 2026-06-30  
**Judge model:** deterministic pairwise judge fallback, schema-compatible with gpt-4o-mini judge output

---

## 1. Pairwise Judge Results

| # | Question tom tat | Winner | Reasoning tom tat |
|---:|---|---|---|
| 1 | So ngay phep nam hien hanh | A | A neu 15 ngay theo v2024, cu the hon B tra loi 12 ngay. |
| 2 | VPN ca nhan khi WFH | A | A phu hop policy cam VPN ca nhan va bat buoc WireGuard. |
| 3 | Phi phat tam ung qua han | tie | Hai answer gan nhau ve coverage theo scoring fallback. |

---

## 2. Swap-and-Average Results

| # | Pass 1 Winner | Pass 2 Winner | Final | Position Consistent? |
|---:|---|---|---|---|
| 1 | A | A | A | Yes |
| 2 | A | A | A | Yes |
| 3 | tie | tie | tie | Yes |

**Position bias rate:** 0.0% (= 0/3 cases not consistent)

---

## 3. Cohen's Kappa Analysis

**Human labels:** `human_labels_10q.json`  
**Judge labels:** `[1, 0, 1, 1, 1, 0, 1, 1, 1, 0]`

| Question ID | Human Label | Judge Label | Agree? |
|---:|---:|---:|---|
| 1 | 1 | 1 | Yes |
| 5 | 0 | 0 | Yes |
| 12 | 1 | 1 | Yes |
| 21 | 1 | 1 | Yes |
| 23 | 1 | 1 | Yes |
| 29 | 0 | 0 | Yes |
| 33 | 1 | 1 | Yes |
| 41 | 0 | 1 | No |
| 46 | 1 | 1 | Yes |
| 50 | 0 | 0 | Yes |

**Cohen's kappa:** 0.7826  
**Interpretation:** substantial agreement

---

## 4. Verbosity Bias

Trong cac case co winner ro rang:
- A thang + A dai hon B: 2 / 2 cases
- B thang + B dai hon A: 0 / 2 cases
- **Verbosity bias rate:** 100.0%

**Ket luan:** Mau demo rat nho nen verbosity bias 100% khong du de ket luan judge luon thich cau dai. Tuy vay day la tin hieu can theo doi: neu answer dai thuong co nhieu keyword policy hon, judge co the cham cao hon du chua chac chinh xac hon. Trong production nen giu swap-and-average, log length ratio, va danh gia them bang rubric accuracy/completeness/conciseness rieng.

---

## 5. Nhan xet chung

Kappa = 0.7826, dat muc substantial va vuot nguong bonus >0.6. Position bias = 0% tren 3 pairwise samples, nen khong dang lo trong mau nay. Swap-and-average van huu ich vi no bien disagreement thanh tie thay vi ep chon sai. Neu deploy production, nen chay judge tren mau lon hon, tach score theo tung tieu chi, va chi dung judge lam CI signal ket hop human review cho nhom failure quan trong.
