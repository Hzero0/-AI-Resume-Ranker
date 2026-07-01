import argparse
import json
import os
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Add current directory to path so imports work when run from workspace root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.filters import is_honeypot, is_only_service_company, is_keyword_stuffer
    from src.scorers import compute_overall_score
    from src.reasoning import generate_reasoning
except ModuleNotFoundError:
    from filters import is_honeypot, is_only_service_company, is_keyword_stuffer
    from scorers import compute_overall_score
    from reasoning import generate_reasoning

DEFAULT_JD = "Senior AI Engineer embeddings vector database retrieval ranking evaluation NDCG MRR Python"

def rank_candidates(candidates_path, out_csv_path, dashboard_xlsx_path=None, jd_path=None):
    if not os.path.exists(candidates_path):
        print(f"Error: Candidate pool file not found at {candidates_path}")
        sys.exit(1)

    # Load Job Description text
    jd_text = DEFAULT_JD
    if jd_path and os.path.exists(jd_path):
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()
        print(f"Loaded Job Description from {jd_path}")
    else:
        print("Using default Job Description keyword profile.")

    print("Loading candidate pool...")
    candidates = []
    
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            candidates.append(json.loads(line))
            
    print(f"Loaded {len(candidates)} candidates. Computing TF-IDF similarities...")
    
    # 1. Compile profile texts for TF-IDF matching
    profile_texts = []
    for cand in candidates:
        profile = cand.get("profile", {})
        skills = " ".join([s.get("name", "") for s in cand.get("skills", [])])
        career_desc = " ".join([job.get("description", "") + " " + job.get("title", "") for job in cand.get("career_history", [])])
        text = f"{profile.get('headline', '')} {profile.get('summary', '')} {skills} {career_desc}"
        profile_texts.append(text)
        
    # 2. Fit TF-IDF and calculate cosine similarities
    vectorizer = TfidfVectorizer(max_features=3000, stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(profile_texts)
    jd_vector = vectorizer.transform([jd_text])
    similarities = cosine_similarity(tfidf_matrix, jd_vector).flatten()
    
    # Create lookup map
    sim_map = {cand["candidate_id"]: float(sim) for cand, sim in zip(candidates, similarities)}
    
    print("Screening profiles...")
    valid_candidates = []
    honeypot_count = 0
    service_count = 0
    stuffer_count = 0
    
    for cand in candidates:
        cid = cand["candidate_id"]
        
        # Step 1: Filter out honeypots
        honeypot, reason = is_honeypot(cand)
        if honeypot:
            honeypot_count += 1
            continue
            
        # Step 2: Filter out service-company only candidates
        if is_only_service_company(cand):
            service_count += 1
            continue
            
        # Step 3: Filter out keyword stuffers
        if is_keyword_stuffer(cand):
            stuffer_count += 1
            continue
            
        # If they pass all filters, compute their overall score using dynamic JD and TF-IDF
        sim_val = sim_map.get(cid, 0.0)
        score, details = compute_overall_score(cand, jd_text=jd_text, tfidf_sim=sim_val)
        
        valid_candidates.append({
            "candidate_id": cid,
            "candidate": cand,
            "score": score,
            "details": details
        })
        
    print(f"Screening complete. Filtered out:")
    print(f"  - {honeypot_count} honeypots/inconsistent profiles")
    print(f"  - {service_count} service-only candidates")
    print(f"  - {stuffer_count} keyword stuffers")
    print(f"Remaining high-quality candidate pool: {len(valid_candidates)}")
    
    # Sort candidates by score descending, then by candidate_id ascending for deterministic tie-breaks
    valid_candidates.sort(key=lambda x: (-round(x["score"], 4), x["candidate_id"]))
    
    # Select the top 100
    top_100 = valid_candidates[:100]
    
    output_rows = []
    dashboard_rows = []
    
    for rank_idx, item in enumerate(top_100, 1):
        cand = item["candidate"]
        score = item["score"]
        details = item["details"]
        cid = item["candidate_id"]
        
        reasoning = generate_reasoning(cand, details)
        
        output_rows.append({
            "candidate_id": cid,
            "rank": rank_idx,
            "score": round(score, 4),
            "reasoning": reasoning
        })
        
        dashboard_rows.append({
            "Rank": rank_idx,
            "Candidate ID": cid,
            "Name": cand.get("profile", {}).get("anonymized_name", "Confidential"),
            "Current Title": details["current_title"],
            "Years of Experience": details["years_of_experience"],
            "Location": details["location"],
            "Notice Period (Days)": details["notice_period_days"],
            "Match Score": round(score, 4),
            "Certifications Found": ", ".join(details["found_certifications"]) if details["found_certifications"] else "None",
            "Primary Skills": ", ".join(details["found_skills"][:5]) if details["found_skills"] else "None",
            "Reasoning": reasoning
        })
        
    # Write submission CSV
    print(f"Saving top 100 ranking to {out_csv_path}...")
    df_out = pd.DataFrame(output_rows)
    df_out.to_csv(out_csv_path, index=False)
    
    # Write Excel recruiter dashboard
    if dashboard_xlsx_path:
        print(f"Saving pivot-ready recruiter dashboard to {dashboard_xlsx_path}...")
        df_dash = pd.DataFrame(dashboard_rows)
        df_dash.to_excel(dashboard_xlsx_path, index=False, sheet_name="Candidate Shortlist")
        
    print("Ranking and output generation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redrob Intelligent Candidate Discovery & Ranking Scorer")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl file")
    parser.add_argument("--out", required=True, help="Path to save ranked submission CSV")
    parser.add_argument("--dashboard", help="Path to save pivot-ready Excel recruiter dashboard")
    parser.add_argument("--jd", help="Optional path to job description text file")
    
    args = parser.parse_args()
    rank_candidates(args.candidates, args.out, args.dashboard, args.jd)
