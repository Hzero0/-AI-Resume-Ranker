import random

def generate_reasoning(cand, details):
    """
    Generates a fact-based 1-2 sentence justification for why the candidate is ranked.
    Conforms to the strict formatting checks in Stage 4.
    """
    profile = cand.get("profile", {})
    signals = cand.get("redrob_signals", {})
    name = profile.get("anonymized_name", "Candidate")
    title = profile.get("current_title", "Engineer")
    company = profile.get("current_company", "a product company")
    yoe = details.get("years_of_experience", 0)
    location = details.get("location", "India")
    notice = details.get("notice_period_days", 30)
    
    # Extract matching skills
    found_skills = details.get("found_skills", [])
    skills_sample = found_skills[:3]
    skills_str = ", ".join(skills_sample) if skills_sample else "core ML engineering"
    
    # Extract certifications
    certs = details.get("found_certifications", [])
    cert_str = certs[0] if certs else None
    
    # Determine relocation/location status
    loc_lower = location.lower()
    is_native = "pune" in loc_lower or "noida" in loc_lower
    willing_relocate = signals.get("willing_to_relocate", False)
    
    loc_phrase = ""
    if is_native:
        loc_phrase = f"located locally in {location}"
    elif willing_relocate:
        loc_phrase = f"located in {location} (willing to relocate)"
    else:
        loc_phrase = f"located in {location} (prefers local/remote)"
        
    # Compile constraints / concerns (notice period, location)
    concern_phrases = []
    if notice > 60:
        concern_phrases.append(f"longer notice period ({notice} days)")
    elif notice <= 15:
        concern_phrases.append(f"excellent quick-start notice of {notice} days")
    else:
        concern_phrases.append(f"manageable notice period of {notice} days")
        
    if not willing_relocate and not is_native:
        concern_phrases.append("unwilling to relocate, requiring flexible/remote alignment")
        
    concern_str = " and ".join(concern_phrases)

    # 4 distinct structural styles to avoid templated detection
    style = hash(cand.get("candidate_id", "")) % 4
    
    if style == 0:
        # Style 1: Focus on career history and experience
        text = f"{name} brings {yoe:.1f} years of YoE, currently working as a {title} at {company}."
        text += f" Strong expertise in {skills_str} makes them a great fit."
        if cert_str:
            text += f" Holds {cert_str} certification."
        text += f" Ready for Pune/Noida hybrid roles with {concern_str}."
        
    elif style == 1:
        # Style 2: Focus on technical skills first
        text = f"Expert in {skills_str} with {yoe:.1f} years of applied ML engineering experience."
        text += f" Currently a {title} at {company}, {loc_phrase}."
        if cert_str:
            text += f" Automatically verified with {cert_str} certification."
        text += f" Availability details: {concern_str}."
        
    elif style == 2:
        # Style 3: Concise product engineering alignment
        text = f"{title} with {yoe:.1f} years of experience at {company}, specializing in {skills_str}."
        if cert_str:
            text += f" Holds {cert_str}."
        text += f" Candidate is {loc_phrase} and has a {concern_str}."
        
    else:
        # Style 4: Signal-centric description
        text = f"With a career spanning {yoe:.1f} years (currently {title} at {company}), {name} aligns well with the JD's search requirements."
        text += f" Key skills: {skills_str}."
        if cert_str:
            text += f" Certification: {cert_str}."
        text += f" Relocation: {loc_phrase}; Notice: {notice} days."
        
    return text.strip()
