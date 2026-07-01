import re
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Reference date for activity calculation
REF_DATE = datetime(2026, 7, 1)

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def extract_yoe_requirements(jd_text):
    """
    Dynamically extracts experience requirements (e.g. '5-9 years' or '3+ years') from JD text.
    Returns (min_yoe, max_yoe)
    """
    jd_lower = jd_text.lower()
    # Pattern for ranges: '5-9 years', '5 to 9 yrs', '5 - 9 yoe'
    range_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years|yrs|yoe|year)', jd_lower)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
        
    # Pattern for minimums: '5+ years', 'at least 5 yrs', '5 years'
    min_match = re.search(r'(\d+)\s*\+\s*(?:years|yrs|yoe|year)', jd_lower)
    if min_match:
        return float(min_match.group(1)), 15.0
        
    single_match = re.search(r'(?:experience|yoe|yrs|years)\s*(?:of|required|preferred)?\s*(\d+)', jd_lower)
    if single_match:
        val = float(single_match.group(1))
        return max(0.0, val - 2.0), val + 2.0
        
    return 5.0, 9.0  # Fallback to default Senior AI Engineer range

def extract_cities(jd_text):
    """
    Extracts city names mentioned in the Job Description.
    """
    jd_lower = jd_text.lower()
    cities = []
    known_cities = ["noida", "pune", "bangalore", "bengaluru", "hyderabad", "chennai", "mumbai", "delhi", "gurgaon", "kolkata"]
    for city in known_cities:
        if city in jd_lower:
            cities.append(city)
    return cities

def score_behavioral(signals):
    """
    Evaluates behavioral and platform activity signals.
    """
    # 1. Recruiter Response Rate (linear scaling)
    response_rate = signals.get("recruiter_response_rate", 0.0)
    response_score = 0.2 + 0.8 * response_rate # 0.2 to 1.0
    
    # 2. Last active date check (Down-weight heavily if idle > 6 months)
    last_active_str = signals.get("last_active_date")
    last_active = parse_date(last_active_str)
    
    active_mult = 1.0
    if last_active:
        days_idle = (REF_DATE - last_active).days
        if days_idle <= 30:
            active_mult = 1.0
        elif days_idle <= 90:
            active_mult = 0.8
        elif days_idle <= 180:
            active_mult = 0.5
        else:
            active_mult = 0.1 # Heavy penalty (inactive > 6 months)
            
    # 3. Open to work flag
    open_to_work = signals.get("open_to_work_flag", False)
    otw_boost = 1.1 if open_to_work else 0.9
    
    # 4. Stated notice period (Sub-30-day notice is preferred)
    notice_days = signals.get("notice_period_days", 90)
    notice_mult = 1.0
    if notice_days <= 15:
        notice_mult = 1.2
    elif notice_days <= 30:
        notice_mult = 1.1
    elif notice_days <= 60:
        notice_mult = 0.8
    else:
        notice_mult = 0.5 # Long notice period has high friction
        
    # 5. Profile completeness
    completeness = signals.get("profile_completeness_score", 100) / 100.0
    
    # 6. GitHub activity score
    github_score = signals.get("github_activity_score", -1)
    github_boost = 1.0
    if github_score > 70:
        github_boost = 1.1
    elif github_score == -1:
        github_boost = 0.95
        
    behavior_score = response_score * active_mult * otw_boost * notice_mult * github_boost * (0.8 + 0.2 * completeness)
    return behavior_score

def compute_overall_score(cand, jd_text=None, tfidf_sim=0.0):
    """
    Computes candidate overall score using a combination of dynamic matching and behavioral signals.
    """
    if jd_text is None:
        # Default JD description text fallback
        jd_text = "Senior AI Engineer embeddings vector database retrieval ranking evaluation NDCG MRR Python"
        
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    certifications = cand.get("certifications", [])
    
    # 1. Experience Score (dynamic range)
    yoe = profile.get("years_of_experience", 0)
    min_req, max_req = extract_yoe_requirements(jd_text)
    if min_req <= yoe <= max_req:
        exp_score = 1.0
    elif (min_req - 1.0) <= yoe < min_req or max_req < yoe <= (max_req + 1.0):
        exp_score = 0.8
    elif (min_req - 2.0) <= yoe < (min_req - 1.0) or (max_req + 1.0) < yoe <= (max_req + 3.0):
        exp_score = 0.5
    else:
        exp_score = 0.2
        
    # 2. Location matching (dynamic cities)
    loc = profile.get("location", "").lower()
    willing_relocate = signals.get("willing_to_relocate", False)
    target_cities = extract_cities(jd_text)
    
    loc_score = 0.5 # Default middle score
    if target_cities:
        if any(city in loc for city in target_cities):
            loc_score = 1.0
        elif willing_relocate:
            loc_score = 0.8
        else:
            loc_score = 0.2
            
    # 3. Dynamic Skills Match
    # Score candidate skills if they are mentioned anywhere in the JD
    skills_score = 0.0
    found_skills = []
    jd_lower = jd_text.lower()
    
    for s in skills:
        name = s.get("name", "").lower()
        prof = s.get("proficiency", "beginner").lower()
        dur = s.get("duration_months", 0)
        
        # If the skill name matches a word or phrase in the JD
        if name in jd_lower or any(word in jd_lower for word in name.split() if len(word) > 3):
            prof_mult = 1.5 if prof == "expert" else (1.2 if prof == "advanced" else (1.0 if prof == "intermediate" else 0.6))
            dur_years = min(dur / 12.0, 5.0)
            dur_mult = 0.5 + 0.1 * dur_years
            
            skills_score += 1.0 * prof_mult * dur_mult
            found_skills.append(s.get("name"))
            
    # 4. Certification Scorer
    # Automatically scan for certifications containing keywords from the JD (or common cloud certs)
    cert_boost = 0.0
    found_certs = []
    for cert in certifications:
        cname = cert.get("name", "").lower()
        cissuer = cert.get("issuer", "").lower()
        
        # Check if the certification contains words present in the JD (e.g. AWS, Tensorflow, Kubernetes, etc.)
        for word in jd_lower.split():
            if len(word) > 3 and (word in cname or word in cissuer):
                cert_boost += 0.5
                found_certs.append(cert.get("name"))
                break
                
    # 5. Title Relevance
    # Check if the current title or past titles match key words in the JD
    title = profile.get("current_title", "").lower()
    headline = profile.get("headline", "").lower()
    
    # Find matching noun phrases or key job title tokens in the JD
    jd_tokens = [w for w in re.findall(r'\b\w+\b', jd_lower) if len(w) > 3]
    title_words = [w for w in title.split() if len(w) > 3]
    
    title_score = 0.2 # default base
    if any(w in jd_lower for w in title_words):
        title_score = 0.8
        if "senior" in title or "lead" in title or "principal" in title:
            title_score = 1.0
            
    # Combine everything
    # We weigh:
    # 30% TF-IDF Cosine Similarity (handles semantic expansion & broad profile fit)
    # 25% Title relevance
    # 20% Dynamic Skills Match
    # 15% Experience match
    # 10% Location match
    base_match = (0.30 * tfidf_sim +
                  0.25 * title_score +
                  0.20 * min(skills_score / 5.0, 1.0) +
                  0.15 * exp_score +
                  0.10 * loc_score)
                  
    # Scale base score with behavioral multiplier (availability)
    behavior_mult = score_behavioral(signals)
    final_score = (base_match * behavior_mult) + (cert_boost * 0.05)
    final_score = max(0.0, min(1.0, final_score))
    
    details = {
        "experience_score": exp_score,
        "title_score": title_score,
        "skills_score": skills_score,
        "behavior_multiplier": behavior_mult,
        "location_score": loc_score,
        "certifications_boost": cert_boost,
        "found_skills": found_skills,
        "found_certifications": found_certs,
        "years_of_experience": yoe,
        "location": profile.get("location", ""),
        "current_title": profile.get("current_title", ""),
        "notice_period_days": signals.get("notice_period_days", 90)
    }
    
    return final_score, details
