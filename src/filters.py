import re
from datetime import datetime

# Technology creation years (current year assumed to be 2026)
TECH_CREATION = {
    "LangChain": 2022,
    "FastAPI": 2018,
    "Transformers": 2019,
    "PyTorch": 2016,
    "Tailwind": 2017,
    "Qdrant": 2020,
    "Pinecone": 2021,
    "Weaviate": 2020,
    "GPT-4": 2023,
    "ChatGPT": 2022
}

# Major service/consulting companies in IT
SERVICE_COMPANIES = [
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "tech mahindra", "l&t", "lnt", "mindtree", "deloitte",
    "pwc", "ey", "kpmg"
]

# Non-tech/unrelated roles that represent keyword stuffers if they contain AI keywords
NON_TECH_ROLES = [
    "marketing manager", "marketing associate", "hr specialist", "hr manager",
    "recruiter", "talent acquisition", "sales manager", "sales representative",
    "accountant", "financial analyst", "operations manager", "project manager",
    "office administrator"
]

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def is_honeypot(cand):
    """
    Checks if a candidate profile is a honeypot (has logical inconsistencies).
    Returns (bool, reason_string)
    """
    profile = cand.get("profile", {})
    yoe = profile.get("years_of_experience", 0)
    career = cand.get("career_history", [])
    skills = cand.get("skills", [])
    education = cand.get("education", [])
    
    # 1. Skill duration exceeds technology age
    for s in skills:
        name = s.get("name", "")
        dur_months = s.get("duration_months", 0)
        dur_years = dur_months / 12.0
        for tech, birth_year in TECH_CREATION.items():
            if tech.lower() in name.lower():
                age = 2026 - birth_year
                # Allow a small buffer of 1.0 years for rounding/part-time overlaps
                if dur_years > age + 1.0:
                    return True, f"Skill '{name}' duration ({dur_years:.1f} yrs) exceeds technology age ({age} yrs, born {birth_year})"

    # 2. Skill duration exceeds candidate's total years of experience
    for s in skills:
        name = s.get("name", "")
        dur_months = s.get("duration_months", 0)
        dur_years = dur_months / 12.0
        if dur_years > yoe + 1.0:
            return True, f"Skill '{name}' duration ({dur_years:.1f} yrs) exceeds total YoE ({yoe:.1f} yrs)"

    # 3. Expert/Advanced proficiency with 0 months duration
    for s in skills:
        name = s.get("name", "")
        dur_months = s.get("duration_months", 0)
        prof = s.get("proficiency", "").lower()
        if dur_months == 0 and prof in ["advanced", "expert"]:
            return True, f"Skill '{name}' is '{prof}' but has 0 months duration"

    # 4. Overlapping full-time jobs at different companies (> 180 days overlap)
    jobs = []
    for job in career:
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date"))
        if not end:
            end = datetime(2026, 7, 1) # Assumed current date
        if start and end:
            jobs.append((start, end, job.get("company", ""), job.get("title", "")))
    
    jobs.sort(key=lambda x: x[0])
    for i in range(len(jobs)):
        for j in range(i + 1, len(jobs)):
            s1, e1, c1, t1 = jobs[i]
            s2, e2, c2, t2 = jobs[j]
            if c1.lower() != c2.lower():
                overlap_start = max(s1, s2)
                overlap_end = min(e1, e2)
                if overlap_start < overlap_end:
                    overlap_days = (overlap_end - overlap_start).days
                    if overlap_days > 180: # More than 6 months overlap
                        return True, f"Overlapping jobs at '{c1}' ({t1}) and '{c2}' ({t2}) for {overlap_days} days"

    # 5. First job started way before graduation year (e.g. started job > 4 years before graduating B.E./B.Tech)
    grad_years = [edu.get("end_year") for edu in education if edu.get("end_year") and "b" in edu.get("degree", "").lower()]
    if grad_years and jobs:
        min_grad_year = min(grad_years)
        first_job_start = jobs[0][0].year
        if min_grad_year - first_job_start > 4:
            return True, f"First job started in {first_job_start} but graduated in {min_grad_year}"

    # 6. Stated YoE vs. sum of job durations
    sum_job_years = sum(job.get("duration_months", 0) for job in career) / 12.0
    if abs(yoe - sum_job_years) > 5.0 and sum_job_years > 0:
        return True, f"Stated YoE is {yoe:.1f} but sum of job durations is {sum_job_years:.1f} years"

    return False, ""

def is_only_service_company(cand):
    """
    Checks if a candidate has only worked at service/consulting companies.
    """
    career = cand.get("career_history", [])
    if not career:
        return False
        
    for job in career:
        company = job.get("company", "").lower()
        # If we find at least one company that is NOT a service company, return False
        is_service = False
        for s in SERVICE_COMPANIES:
            if s in company:
                is_service = True
                break
        if not is_service:
            return False # Found a non-service company (startup, product company, etc.)
            
    return True

def is_keyword_stuffer(cand):
    """
    Checks if the candidate is in a non-tech role (like Marketing Manager or Accountant)
    but listed AI skills to stuff keywords.
    """
    profile = cand.get("profile", {})
    title = profile.get("current_title", "").lower()
    headline = profile.get("headline", "").lower()
    summary = profile.get("summary", "").lower()
    
    # Check if current title is non-tech
    for role in NON_TECH_ROLES:
        if role in title:
            # If the current title is non-tech, check if they have any ML/AI title in history
            has_tech_history = False
            for job in cand.get("career_history", []):
                job_title = job.get("title", "").lower()
                if any(x in job_title for x in ["engineer", "developer", "scientist", "analyst", "programmer"]):
                    if not any(role in job_title for role in NON_TECH_ROLES):
                        has_tech_history = True
                        break
            if not has_tech_history:
                return True
                
    return False
