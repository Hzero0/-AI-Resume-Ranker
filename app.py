import streamlit as st
import pandas as pd
import json
import os
import sys

# Ensure import path includes src folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.filters import is_honeypot, is_only_service_company, is_keyword_stuffer
    from src.scorers import compute_overall_score
    from src.reasoning import generate_reasoning
except ModuleNotFoundError:
    from filters import is_honeypot, is_only_service_company, is_keyword_stuffer
    from scorers import compute_overall_score
    from reasoning import generate_reasoning

st.set_page_config(
    page_title="Redrob AI Ranker — Premium Candidate Discovery",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Style Customization
st.markdown("""
<style>
    .reportview-container {
        background: #0f172a;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #38bdf8 !important;
    }
    .stButton>button {
        background-color: #0284c7;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #38bdf8;
        color: #0f172a;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Redrob AI Ranker — Intelligent Candidate Discovery")
st.markdown("""
Upload a candidate pool file and rank candidates **the way a great recruiter would**—matching concepts, auditing certifications, and evaluating behavioral availability.
""")

# Default Job Description to pre-populate
DEFAULT_JD = """Job Description: Senior AI Engineer — Founding Team
Company: Redrob AI (Series A AI-native talent intelligence platform)
Experience Required: 5–9 years
Required skills:
- Embeddings-based retrieval systems (sentence-transformers, OpenAI, BGE, E5)
- Vector databases or hybrid search (Pinecone, Weaviate, Qdrant, Milvus, FAISS)
- Strong Python coding depth
- Evaluation frameworks (NDCG, MRR, MAP)
Nice to have: LLM fine-tuning, learning-to-rank, distributed inference.
Disqualifiers: Research-only background, service-only careers (TCS, Infosys, Wipro, etc.), non-coding managers, keyword-stuffers (e.g. marketing roles with AI keywords)."""

# Setup Layout
col_jd, col_files = st.columns([1, 1])

with col_jd:
    st.subheader("📝 Job Description (JD)")
    jd_text = st.text_area("Paste or edit the target Job Description:", value=DEFAULT_JD, height=220)
    
    st.sidebar.header("⚙️ Pipeline Filters")
    min_yoe = st.sidebar.slider("Min Years of Experience", 0.0, 15.0, 5.0)
    max_notice = st.sidebar.slider("Max Notice Period (Days)", 0, 180, 60)
    enable_honeypots_filter = st.sidebar.checkbox("Filter Honeypots (Logical Checks)", value=True)
    enable_service_filter = st.sidebar.checkbox("Filter Service Company Only Profiles", value=True)
    enable_stuffer_filter = st.sidebar.checkbox("Filter Keyword Stuffers", value=True)

with col_files:
    st.subheader("📂 Upload Candidate Data")
    uploaded_files = st.file_uploader("Upload candidates.jsonl or PDF resumes (Multiple Files OK):", type=["jsonl", "json", "pdf"], accept_multiple_files=True)
    
    # We bundle a few sample profiles so the site is instantly testable on HuggingFace Spaces without upload
    use_sample = st.checkbox("Or use pre-loaded sample candidates (50)", value=True)

candidates = []

if uploaded_files:
    try:
        for ufile in uploaded_files:
            if ufile.name.endswith(".pdf"):
                from pypdf import PdfReader
                reader = PdfReader(ufile)
                text = ""
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
                
                # Parse candidate details from PDF text
                name = ufile.name.replace(".pdf", "").replace("_", " ").title()
                
                # Extract Experience
                import re
                yoe_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:years|yrs|yoe|year)', text.lower())
                yoe = float(yoe_match.group(1)) if yoe_match else 5.0
                
                # Extract Location
                loc = "India"
                for city in ["pune", "noida", "bangalore", "bengaluru", "hyderabad", "chennai", "mumbai", "delhi", "gurgaon", "kolkata"]:
                    if city in text.lower():
                        loc = city.title()
                        break
                
                # Extract Skills
                found_skills = []
                known_skills = ["python", "pytorch", "tensorflow", "langchain", "pinecone", "qdrant", "weaviate", "sql", "git", "ndcg", "mrr", "map", "machine learning", "deep learning", "nlp", "fastapi"]
                for s in known_skills:
                    if s in text.lower():
                        found_skills.append({
                            "name": s.title() if s != "nlp" and s != "sql" else s.upper(),
                            "proficiency": "advanced",
                            "endorsements": 15,
                            "duration_months": 36
                        })
                
                # Extract Certifications
                found_certs = []
                known_certs = ["aws", "tensorflow", "google cloud", "gcp", "azure", "nvidia", "deeplearning.ai"]
                for c in known_certs:
                    if c in text.lower():
                        found_certs.append({
                            "name": f"Certified {c.title()} specialist",
                            "issuer": c.title(),
                            "year": 2024
                        })
                
                # Mock platform activity signals
                signals = {
                    "profile_completeness_score": 90,
                    "signup_date": "2024-01-01",
                    "last_active_date": "2026-06-30",
                    "open_to_work_flag": True,
                    "profile_views_received_30d": 15,
                    "applications_submitted_30d": 3,
                    "recruiter_response_rate": 0.90,
                    "avg_response_time_hours": 1.5,
                    "skill_assessment_scores": {},
                    "connection_count": 120,
                    "endorsements_received": 15,
                    "notice_period_days": 15,
                    "expected_salary_range_inr_lpa": {"min": 18, "max": 28},
                    "preferred_work_mode": "hybrid",
                    "willing_to_relocate": True,
                    "github_activity_score": 75,
                    "search_appearance_30d": 25,
                    "saved_by_recruiters_30d": 6,
                    "interview_completion_rate": 1.0,
                    "offer_acceptance_rate": 0.8,
                    "verified_email": True,
                    "verified_phone": True,
                    "linkedin_connected": True
                }
                
                candidates.append({
                    "candidate_id": f"CAND_PDF_{len(candidates)+1:03d}",
                    "profile": {
                        "anonymized_name": name,
                        "headline": f"Parsed from resume PDF {ufile.name}",
                        "summary": text[:400] + "...",
                        "location": loc,
                        "country": "India",
                        "years_of_experience": yoe,
                        "current_title": "AI/ML Engineer" if "ai" in text.lower() or "ml" in text.lower() else "Software Engineer",
                        "current_company": "Product Company",
                        "current_company_size": "201-500",
                        "current_industry": "Internet"
                    },
                    "career_history": [
                        {
                            "company": "Tech Company",
                            "title": "Engineer",
                            "start_date": "2022-01-01",
                            "end_date": None,
                            "duration_months": 36,
                            "is_current": True,
                            "industry": "Internet",
                            "company_size": "201-500",
                            "description": text[:600]
                        }
                    ],
                    "education": [],
                    "skills": found_skills,
                    "certifications": found_certs,
                    "redrob_signals": signals
                })
            else:
                # Process JSON / JSONL
                content = ufile.getvalue().decode("utf-8")
                lines = content.strip().split("\n")
                if len(lines) == 1 and (lines[0].startswith("[") or lines[0].strip().endswith("]")):
                    candidates.extend(json.loads(content))
                else:
                    for line in lines:
                        if line.strip():
                            candidates.append(json.loads(line))
        st.success(f"Successfully loaded {len(candidates)} candidates from upload.")
    except Exception as e:
        st.error(f"Error parsing uploaded files: {e}")
elif use_sample:
    sample_path = "challenge_data/sample_candidates.json"
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)
        st.info(f"Loaded {len(candidates)} standard sample candidates.")
    else:
        # Emergency backup sample to make HF Spaces work 100% standalone
        candidates = [
            {
                "candidate_id": "CAND_0010892",
                "profile": {
                    "anonymized_name": "Aditya Hegde",
                    "headline": "AI Engineer | Vector Search & RAG | Python, Qdrant, Pinecone",
                    "summary": "AI Engineer with 5.5 years of experience building and deploying embeddings-based retrieval systems. I design and scale hybrid search systems (dense + sparse retrieval), set up vector databases (Qdrant, Pinecone), and build eval frameworks using NDCG and MRR. Strong Python background and focused on practical system engineering rather than research.",
                    "location": "Noida",
                    "country": "India",
                    "years_of_experience": 5.5,
                    "current_title": "AI Engineer",
                    "current_company": "InMobi",
                    "current_company_size": "1001-5000",
                    "current_industry": "AdTech"
                },
                "career_history": [
                    {"company": "InMobi", "title": "AI Engineer", "start_date": "2024-03-08", "end_date": None, "duration_months": 27, "is_current": True, "industry": "AdTech", "company_size": "1001-5000", "description": "Owned context retrieval pipeline. Replaced BM25 with hybrid dense retrieval."}
                ],
                "education": [
                    {"institution": "B. M. S. College of Engineering", "degree": "B.Tech", "field_of_study": "Computer Science", "start_year": 2016, "end_year": 2020, "grade": "8.8 CGPA", "tier": "tier_2"}
                ],
                "skills": [
                    {"name": "Embeddings-based retrieval", "proficiency": "expert", "endorsements": 83, "duration_months": 45},
                    {"name": "Qdrant", "proficiency": "expert", "endorsements": 60, "duration_months": 30},
                    {"name": "Pinecone", "proficiency": "expert", "endorsements": 60, "duration_months": 36},
                    {"name": "Python", "proficiency": "expert", "endorsements": 91, "duration_months": 66},
                    {"name": "NDCG", "proficiency": "expert", "endorsements": 54, "duration_months": 36},
                    {"name": "MRR", "proficiency": "expert", "duration_months": 36}
                ],
                "certifications": [{"name": "AWS Certified Cloud Practitioner", "issuer": "AWS", "year": 2023}],
                "redrob_signals": {
                    "profile_completeness_score": 93, "signup_date": "2024-03-08", "last_active_date": "2026-06-30", "open_to_work_flag": True, "profile_views_received_30d": 12, "applications_submitted_30d": 4, "recruiter_response_rate": 0.88, "avg_response_time_hours": 1.5, "skill_assessment_scores": {"Python": 95, "Embeddings-based retrieval": 92}, "connection_count": 142, "endorsements_received": 143, "notice_period_days": 15, "expected_salary_range_inr_lpa": {"min": 24.0, "max": 32.0}, "preferred_work_mode": "hybrid", "willing_to_relocate": True, "github_activity_score": 78, "search_appearance_30d": 54, "saved_by_recruiters_30d": 8, "interview_completion_rate": 1.0, "offer_acceptance_rate": 0.8, "verified_email": True, "verified_phone": True, "linkedin_connected": True
                }
            }
        ]
        st.warning("Sample files not found locally. Loaded pre-bundled Aditya Hegde profile.")

if candidates and st.button("🚀 Analyze & Rank Candidates"):
    # 1. Compile profile texts for TF-IDF matching
    profile_texts = []
    for cand in candidates:
        profile = cand.get("profile", {})
        skills = " ".join([s.get("name", "") for s in cand.get("skills", [])])
        career_desc = " ".join([job.get("description", "") + " " + job.get("title", "") for job in cand.get("career_history", [])])
        text = f"{profile.get('headline', '')} {profile.get('summary', '')} {skills} {career_desc}"
        profile_texts.append(text)
        
    # 2. Fit TF-IDF and calculate similarities
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    vectorizer = TfidfVectorizer(max_features=3000, stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(profile_texts)
    jd_vector = vectorizer.transform([jd_text])
    similarities = cosine_similarity(tfidf_matrix, jd_vector).flatten()
    sim_map = {cand["candidate_id"]: float(sim) for cand, sim in zip(candidates, similarities)}

    valid_candidates = []
    honeypot_count = 0
    service_count = 0
    stuffer_count = 0
    
    for cand in candidates:
        cid = cand["candidate_id"]
        # Apply Filters
        if enable_honeypots_filter:
            honeypot, _ = is_honeypot(cand)
            if honeypot:
                honeypot_count += 1
                continue
                
        if enable_service_filter:
            if is_only_service_company(cand):
                service_count += 1
                continue
                
        if enable_stuffer_filter:
            if is_keyword_stuffer(cand):
                stuffer_count += 1
                continue
                
        # Calculate Scores using dynamic JD and TF-IDF similarity
        sim_val = sim_map.get(cid, 0.0)
        score, details = compute_overall_score(cand, jd_text=jd_text, tfidf_sim=sim_val)
        
        # Apply manual bounds from slider
        if details["years_of_experience"] < min_yoe:
            continue
        if details["notice_period_days"] > max_notice:
            continue
            
        valid_candidates.append({
            "candidate_id": cand["candidate_id"],
            "candidate": cand,
            "score": score,
            "details": details
        })
        
    # Sort candidates
    valid_candidates.sort(key=lambda x: (-round(x["score"], 4), x["candidate_id"]))
    
    # Display Stats & Charts
    st.subheader("📊 Screening Analytics")
    stat1, stat2, stat3, stat4 = st.columns(4)
    stat1.metric("Total Input Profiles", len(candidates))
    stat2.metric("Honeypots Flagged", honeypot_count)
    stat3.metric("Service-Only Flagged", service_count)
    stat4.metric("Scored shortlist", len(valid_candidates))
    
    # Show graphic bar chart of filter stats
    filter_data = pd.DataFrame({
        "Exclusion Reason": ["Honeypots", "Service Companies", "Keyword Stuffers", "Scored Shortlist"],
        "Count": [honeypot_count, service_count, stuffer_count, len(valid_candidates)]
    })
    st.bar_chart(filter_data.set_index("Exclusion Reason"))
    
    if not valid_candidates:
        st.warning("No candidates met the filtered criteria.")
    else:
        # Create dataframe for output
        data = []
        for rank_idx, item in enumerate(valid_candidates, 1):
            cand = item["candidate"]
            details = item["details"]
            score = item["score"]
            
            reasoning = generate_reasoning(cand, details)
            
            data.append({
                "Rank": rank_idx,
                "ID": item["candidate_id"],
                "Name": cand.get("profile", {}).get("anonymized_name", "Confidential"),
                "Match Score": f"{score:.2%}",
                "Years of Exp": details["years_of_experience"],
                "Location": details["location"],
                "Notice Period (Days)": details["notice_period_days"],
                "Certifications": ", ".join(details["found_certifications"]) if details["found_certifications"] else "None",
                "Skills Found": ", ".join(details["found_skills"][:4]),
                "Reasoning": reasoning
            })
            
        df = pd.DataFrame(data)
        st.session_state["df_results"] = df
        st.session_state["current_candidates"] = {c["candidate_id"]: c for c in candidates}

if "df_results" in st.session_state:
    df = st.session_state["df_results"]
    
    st.subheader("🔎 Ranked Candidate Shortlist")
    
    # Recruiter filtering controls (Pivot-Table feel)
    col_filt1, col_filt2 = st.columns(2)
    with col_filt1:
        loc_filter = st.multiselect("Filter by Location Hub:", options=df["Location"].unique())
    with col_filt2:
        cert_filter = st.multiselect("Filter by Certifications:", options=[c for c in df["Certifications"].unique() if c != "None"])
        
    df_filtered = df
    if loc_filter:
        df_filtered = df_filtered[df_filtered["Location"].isin(loc_filter)]
    if cert_filter:
        df_filtered = df_filtered[df_filtered["Certifications"].isin(cert_filter)]
        
    st.dataframe(df_filtered, use_container_width=True)
    
    # Download Button
    csv_data = df_filtered[["ID", "Rank", "Match Score", "Reasoning"]].to_csv(index=False)
    st.download_button(
        label="📥 Download Shortlist CSV (submission.csv format)",
        data=csv_data,
        file_name="team_antigravity.csv",
        mime="text/csv"
    )
    
    # Interactive inspect window
    st.subheader("🔍 Profile Inspector & Fact Checker")
    selected_name = st.selectbox("Select candidate to review full JSON profile:", options=df_filtered["Name"].unique())
    
    if selected_name:
        row_details = df_filtered[df_filtered["Name"] == selected_name].iloc[0]
        cand_id = row_details["ID"]
        
        st.info(f"**AI Reason for Rank:** {row_details['Reasoning']}")
        
        if "current_candidates" in st.session_state:
            full_cand = st.session_state["current_candidates"].get(cand_id)
            if full_cand:
                st.json(full_cand)
