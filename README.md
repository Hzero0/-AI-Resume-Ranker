---
title: Redrob AI Ranker
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🤖 Antigravity AI Ranker — Intelligent Candidate Discovery Engine

### 🔗 Live Sandbox Link
The interactive web app sandbox is running live on Hugging Face Spaces:  
👉 **[Open Live Web Sandbox on Hugging Face Spaces](https://huggingface.co/spaces/harshvardhangaikwad11/redrob-candidate-ranker)**

A high-performance, offline screening and ranking system designed for Redrob's Senior AI Engineer (Founding Team) job description. The system operates entirely locally on CPU, processing a **100,000-candidate pool in under 22 seconds** while filtering out logical inconsistencies, keyword-stuffer traps, and unavailable profiles.

---

## 🎯 Key Architectural Pillars

### 1. The Honeypot Shield (Logical Consistency Filtering)
The dataset includes subtly impossible profiles designed to trap basic keyword embedding matches (e.g. 10 years of experience with LangChain, which was created in 2022). Our filter performs 6 strict consistency checks:
- **Tech Age Limits**: Validates skill durations against actual release years (PyTorch: 2016, FastAPI: 2018, Qdrant: 2020, Pinecone: 2021, LangChain: 2022, etc.).
- **Experience Bounds**: Flags skills whose listed duration exceeds the candidate's total years of experience.
- **Zero-Duration Experts**: Filters out profiles stating "Expert" or "Advanced" proficiency with `0` months of actual duration.
- **Double-Agent Overlaps**: Screens candidates listing overlapping full-time roles (>180 days overlap) at different companies.
- **Career-Graduation Mismatch**: Detects cases where the candidate's career history starts years before college graduation.
- **YoE Incoherency**: Flags large discrepancies between stated YoE and the sum of durations in their career history.

*Result*: **12,184 anomalous profiles** were successfully isolated and removed from the active selection pool, guaranteeing a **0% honeypot rate** in the top 100 shortlist.

### 2. Service Company Giant Filter
The JD explicitly disqualifies candidates who have only worked at consulting/service giants. The pipeline filters out candidates whose entire career history consists *only* of known services firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, Tech Mahindra, HCL, Deloitte, etc.). If a candidate has even one product company or startup role, they remain eligible.

*Result*: **6,323 service-only candidates** were screened out.

### 3. Title/Keyword-Stuffer Shield
Identifies and rejects non-tech candidates (e.g., Marketing Managers, HR Specialists, Operations Managers) who have stuffed AI keywords into their profile without any history of engineering, development, or scientific roles.

*Result*: **13,192 keyword-stuffers** were filtered out.

### 4. Automatic Certification Auditor
Without requiring manual recruiter entry, the engine scans the `certifications` list for job-relevant credentials (AWS Certified Machine Learning, TensorFlow Developer, Google Cloud Professional ML Engineer, DeepLearning.AI, Nvidia DLI, etc.) to apply score multipliers and feature them in the recruiter summary.

### 5. Multi-Factor Scoring & Behavioral Multiplier
The final rank score compiles:
- **Title Relevance (30%)**: Prefers current and past roles containing ML, AI, NLP, Search, and Recommendation Engineering.
- **Semantic Skills Matching (35%)**: Evaluates duration, proficiency, and completeness of core competencies (embeddings, vector search, ranking metrics like NDCG/MRR/MAP, and Python).
- **YoE Bounds (20%)**: Optimally scores candidates in the 5–9 years bracket.
- **Location & Relocation (15%)**: Noida/Pune local candidates, followed by Tier-1 relocatable candidates.
- **Behavioral Multiplier**: Multiplies candidate scores based on login recency (penalizing candidates inactive for > 6 months), recruiter response rate, open-to-work flag, and notice period (boosting sub-30-day notice).

---

## ⚡ Performance Summary
- **Total Pool Size**: 100,000 candidates
- **Screened Out**: 31,699 profiles (Honeypots: 12,184 | Service-Only: 6,323 | Keyword Stuffers: 13,192)
- **High-Quality Scored Pool**: 68,301 candidates
- **Execution Time (CPU, Single-thread)**: **21.8 seconds**
- **Peak Memory**: ~150 MB RAM

---

## 🚀 Getting Started & Reproduction

### Prerequisites
Install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Single Command Reproduction
To reproduce the top 100 candidate ranking CSV (`team_antigravity.csv`) and the pivot-ready recruiter Excel dashboard (`recruiter_dashboard.xlsx`) from `candidates.jsonl`:
```bash
python rank.py --candidates ./challenge_data/candidates.jsonl --out ./team_antigravity.csv --dashboard ./recruiter_dashboard.xlsx
```

### Validate Submission Format
Verify that the output CSV passes all challenge formats, ordering, and deterministic tie-breaking rules:
```bash
python challenge_data/validate_submission.py team_antigravity.csv
```

### Run the Recruiter Sandbox Dashboard
Launch the interactive Streamlit app to explore candidates, paste JDs, and filter matching profiles:
```bash
streamlit run app.py
```

---

## 📂 Code Repository Structure
- `rank.py`: Primary orchestration script.
- `app.py`: Streamlit recruiter dashboard sandbox.
- `requirements.txt`: Project dependencies list.
- `submission_metadata.yaml`: Team identity and platform specifications.
- `src/`:
  - `filters.py`: Logic for honeypot, service company, and stuffer screening.
  - `scorers.py`: Calculations for experience, title, semantic skills, location, and behavior.
  - `reasoning.py`: Fact-based, randomized, non-templated recruiter reasoning generator.
- `challenge_data/`: (Dataset directory containing candidates, job description, and validator script).
