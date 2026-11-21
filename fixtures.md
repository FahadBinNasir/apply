# Test fixtures (from real posts). Treat as the acceptance tests for the filter.
Test clock: NOW = 2026-11-21 (the app must support a NOW_OVERRIDE env var for tests).
Profile: profile.seed.yaml. Tier names: STRONG, STRETCH, SKIPPED(reason), MANUAL(reason), WALKIN, OPPORTUNITY, NOISE.

## Full-text cases (store each as a test input verbatim)

### F1 - Paysys Labs DevOps  => STRONG
Source: alumni group
```
We're Hiring – *DevOps Engineer!*
Paysys Labs is looking for an enthusiastic and detail-oriented DevOps Engineer to join our growing team!
📍 Location: *Karachi (On-site)*
💼 Experience: *0–1 Years | Fresh Graduates Encouraged to Apply*
Key Skills & Requirements:
CI/CD pipelines and automation
Linux administration and troubleshooting
On-premises deployments and release management
SQL and relational databases
Git and version control
Scripting and process automation
API testing and test automation
Basic understanding of AI-assisted development and automation tools
🎓 Qualification: Bachelor's degree in Computer Science, Software Engineering, IT, or a related field.
📩 Apply Now!
Send your updated CV to hiring@paysyslabs.com with the subject line "DevOps Engineer – Application".
```
Expect: apply_email=hiring@paysyslabs.com, exact_subject="DevOps Engineer – Application" (keep the en dash exactly), tier STRONG.

### F2 - Decibel MTO .NET => STRONG
```
Hiring: *MTO - Dot Net Developer* at Decibel HRMS
📍 Location: *Shahra-e-Faisal, Karachi*
·Develop and maintain scalable web-based applications using C#, *ASP .NET with webforms* .
·Build and integrate REST APIs across systems.
·Create and manage SQL database objects: procedures, functions, and views.
·Bachelor's degree in computer science or relevant field
·0-1 years of experience of backend development using .NET with webforms
📩 Interested candidates can apply at careers@decibel360.com by mentioning the position title "MTO - Dot Net Developer" in the subject line.
```
Expect: exact_subject="MTO - Dot Net Developer", STRONG (note: webforms is a gap, mention honestly, never claim webforms experience).

### F3 - EBG Storage & Compute intern => STRETCH (IT infrastructure, not core dev)
```
*Internship Opportunity | Storage & Compute | Karachi,* Pakistan
An EBG Partner in Karachi is looking for enthusiastic and motivated Interns in the Storage and Compute domains!
Domains: Enterprise Storage, Compute Technologies, Data Center Infrastructure
Who can apply? Fresh graduates.
Interested candidates can share their updated CV through LinkedIn Inbox or directly via email: muhammad.bilal.ahmed30@gmail.com
```
Expect: STRETCH with note, apply_email present.

### F4 - Pentaloop iOS (Lahore) => SKIPPED(location)
```
HIRING | *Associate Software Engineer (ASE)* PAID INTERNSHIP with an opportunity for a FULL-TIME JOB!
Position: ASE - iOS Developer | Experience: Freshers Welcome | Location: Johar Town, Lahore
Share your CV at hr@pentaloop.com
```
Must appear in the collapsed Skipped list with reason "Lahore onsite".

### F5 - Techtimize MERN + AI intern (Lahore onsite) => SKIPPED(location)
### F6 - Superior University (about 30 roles in one post) => split into one item per role; none STRONG; "Lecturer for CS & IT (MS in SE, CS, IT & DA)" => SKIPPED(requires MS); the rest SKIPPED(field)
### F7 - Wenawa Business Development Trainee (Hybrid Karachi) => SKIPPED(field: sales/BD)
### F8 - Inovativex BD Intern (Remote, business graduates only) => SKIPPED(field)
### F9 - Roomi Associates (ACCA/CA/ICMA) => SKIPPED(field)
### F10 - Code Avenue Senior Project Manager (2-4 yrs) => SKIPPED(field+experience)
### F11 - Alkhidmat HR & Admin (deadline 20 Nov 2026) => SKIPPED(field) and also expired
### F12 - Nimir Chemicals MTO Lahore (deadline 16 Nov 2026) => SKIPPED(location, expired)

## Image / poster cases (use the screenshot-style posters if provided; otherwise mock with generated images)
- MCB Funds "We're Hiring - Software Engineer" poster, Karachi head office, 1-2 years experience, apply via careers site or email in the poster => STRETCH (experience ceiling is soft), email must be shown highlighted for human verification because it came from OCR.
- DigiPersona "INTERNS (Account Management, Creative & Digital Media)" poster, email info@digipersona.com.pk => SKIPPED(field)
- PMTF engineering CoE poster, hr@pmtfl.com, deadline 20 Nov 2026 => SKIPPED(expired) even though fresh engineers are eligible. (If NOW were before the deadline it would be STRETCH.)

## Special handling cases
- Global Step (walk-in Thursday 12 Nov 2026, marketing/graphic roles) => SKIPPED(field); but the walk-in parser must still extract date/time/address (tests the WALKIN type) and an .ics must be generated if a walk-in is relevant.
- Pintern headline posts like "Techdots — Pakistan" + link only => pipeline must FETCH the link, read the page, and then classify. If the page can't be read => MANUAL(unreadable).
- "Pentaloop"/"Decibel" appear both in alumni group and Pintern => DEDUPE into one job (company + normalized title).
- lnkd.in / linkedin.com link-only posts => MANUAL(link only, login wall).
- "Send CV on WhatsApp 0313-xxxxxxx" posts => apply_method=whatsapp, dashboard shows a wa.me button with prefilled text and a CV download button (WhatsApp cannot pre-attach files).
- "Female only" posts => if profile gender unknown: flag "gender requirement" and tier STRETCH-with-warning only if field matches; if gender=male => SKIPPED(gender).
- Night shift (7 PM - 4 AM) => SKIPPED(night shift) when accepts_night_shift=false.

## NOISE (must not create job cards, but log as noise)
- Bahria 22nd Convocation announcement
- Legacy Medal alumni fundraising post
- Master's research survey (Google Form)
- Matrimonial platform ad
- "Need CVs for PBO and trade officer position, BBA/MBA, Meezan bank" (not tech; would be SKIPPED(field) if treated as a job - either is acceptable but never STRONG)
- "Is there any alumnus working at JBS Global?" / "Any alumni in Dawlance, Nestle?" / someone else's job-hunting post

## OPPORTUNITY (Pintern Scholarship channel)
- CERN Summer Student Programme 2027, QNX Global Hackathon, NASA Open Science Essentials, Dubai Free AI Course => OPPORTUNITY tab (links only, tech-relevant)
- Fellowships in policy/health/marketing/journalism => hidden NOISE/OPPORTUNITY-low
