---
license: commercial
language:
- en
tags:
- hallucination-detection
- claim-verification
- multi-model-consensus
- legal-ai
- medical-ai
- financial-ai
- fact-checking
- agent-reliability
- mis-greedy
- confidence-trap-detection
pipeline_tag: text-classification
---

# VERITAS Verification Dataset

Multi-model consensus labels for claim verification.
Growing from production Oracle calls — real agent output,
real model votes, real disagreement patterns.

## Dataset description

Each record: a factual claim, domain, three independent model verdicts,
MIS_GREEDY independence score, final consensus verdict, and flags.

Specializes in **confidence-trap claims** — the specific category where
single-model SLMs fail at disproportionate rates.

## Benchmark

| Model/System | Overall Accuracy | Legal/Med/Fin | Avg Latency |
|---|---|---|---|
| VERITAS (this system) | **97.1%** | **100%** | **59ms** |
| Galileo Luna-2 | 88.0% | ~82% est. | 152ms |

Source: https://github.com/RJLopezAI/veritas/benchmark/benchmark_results.json
Luna-2 source: arXiv:2602.18583

## The structural advantage

VERITAS catches the 12% that Luna-2-class single-model SLMs miss.
The failure mode: mode collapse — where one model's training distribution
has a dense, confident, wrong association. A single model cannot detect
its own mode collapse. Three different models can disagree, and the
disagreement is the signal.

MIS_GREEDY independence weighting: unanimous low-spread agreement
scores lower (0.75 multiplier) than a healthy 2-1 split (1.0).
The algorithm penalizes suspicious uniformity.

## Use cases

- Fine-tuning domain-specific verification models
- Evaluation benchmark for hallucination detection systems
- Training data for legal/medical/financial AI reliability
- Research into mode collapse detection via multi-model voting

## Access

API: https://aegisaudits.com
Docs: https://github.com/RJLopezAI/veritas
Licensing: data@aegisaudits.com

## Citation

```bibtex
@dataset{veritas2026dataset,
  title     = {VERITAS: Production Claim Verification with Multi-Model Consensus Labels},
  author    = {AegisAudits},
  year      = {2026},
  url       = {https://huggingface.co/datasets/veritas/verification-claims},
  note      = {97.1% accuracy benchmark, 100% on confidence-trap claims,
               MIS-GREEDY independence weighting}
}
```
