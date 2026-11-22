import sys,os; sys.path.insert(0,'.')
os.environ["NOW_OVERRIDE"]="2026-11-21T00:00:00"
from app.main import load_profile
from app.pipeline.rules.engine import ProductionRulesEngine
from contracts.models import ExtractedRole, WorkMode, ApplyMethod
P=load_profile(); E=ProductionRulesEngine()
def r(**k):
    base=dict(title="Software Engineer",company="Acme",field="software engineering",city="Karachi",location_text="Karachi",work_mode=WorkMode.ONSITE,apply_method=ApplyMethod.EMAIL,apply_email="hr@acme.pk",experience_min_years=0.0,skills=["Python"])
    base.update(k); return ExtractedRole(**base)
cases={
 "Senior Software Engineer, 0 yrs listed": r(title="Senior Software Engineer"),
 "Lahore onsite (city=Lahore)": r(city="Lahore",location_text="Lahore, Johar Town"),
 "Lahore job whose text says 'Karachi office' too": r(city="Lahore",location_text="Lahore (head office Karachi)"),
 "Unknown location, no city": r(city="",location_text="",work_mode=WorkMode.UNKNOWN),
 "Marketing field w/ python skill": r(title="Digital Marketing Intern",field="marketing"),
 "Sales Executive": r(title="Sales Executive",field="sales"),
 "3 yrs experience": r(experience_min_years=3.0),
 "Unpaid/volunteer (post_type unknown)": r(title="Software Developer volunteer",notes="unpaid volunteer position"),
 "Field missing -> default": r(field=""),
 "Business Development Trainee remote": r(title="Business Development Trainee",field="business development",work_mode=WorkMode.REMOTE,city="",location_text="Remote Pakistan"),
 "Expired deadline 20 Nov 2026": r(deadline="20 Nov 2026"),
 "Deadline today-ish 22 Nov": r(deadline="22 Nov 2026"),
}
for k,role in cases.items():
    t,reasons,score,m,g=E.evaluate(role,P)
    print(f"{k:55s} -> {t.value:9s} {score:5.0f}  {reasons[:1]}")
print("\nProfile loaded: gender=",P.personal.gender,"night=",P.personal.accepts_night_shift,"exp thresholds=",P.matching.experience)
print("\n--- generic-token false positives ---")
for k,role in {
 "Civil Engineer Karachi fresh":r(title="Civil Engineer",field="civil engineering",skills=[]),
 "Accounts Officer (field=finance) Karachi":r(title="Accounts Officer",field="finance",skills=["Excel"]),
 "Customer Support Rep Karachi":r(title="Customer Support Executive",field="customer support",skills=["email"]),
 "Graphic Designer Karachi":r(title="Graphic Designer",field="design",skills=["Figma"]),
}.items():
    t,reasons,score,m,g=E.evaluate(role,P); print(f"{k:45s} -> {t.value:8s} {score:4.0f} {reasons[:1]}")
