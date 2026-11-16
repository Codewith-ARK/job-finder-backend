"""Idempotent development and demo seed data."""

from datetime import timedelta

from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .models import (
    Activity,
    Agency,
    Application,
    AuditEvent,
    CandidateAssignment,
    CandidateEducation,
    CandidateExperience,
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    Document,
    Integration,
    Job,
    Membership,
    OnboardingStep,
    ReferralLink,
    Team,
    User,
)
from .models.common import new_id, utcnow
from .services import storage
from .services.credentials import hash_password, hash_secret

DEMO_PASSWORD = "Demo1234!"
DEMO_REFERRAL_TOKENS = {
    "active": "northstar-referral-demo",
    "used": "harbor-referral-used",
    "expired": "northstar-referral-expired",
}
ONBOARDING_KEYS = ("personal", "professional", "academic", "documents")
MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def _steps(profile: CandidateProfile, statuses: tuple[str, str, str, str]) -> None:
    for position, (key, status) in enumerate(zip(ONBOARDING_KEYS, statuses, strict=True)):
        profile.steps.append(
            OnboardingStep(
                candidate_id=profile.user_id,
                key=key,
                position=position,
                status=status,
                completed_at=utcnow() if status == "complete" else None,
            )
        )


def _seed_document(profile: CandidateProfile) -> None:
    """Attach a real tiny PDF so the documents step is genuinely complete."""
    blob_pathname = storage.upload(
        f"documents/{profile.user_id}/seed-cv.pdf", MINIMAL_PDF, "application/pdf"
    )
    profile.documents.append(
        Document(
            id=new_id(),
            candidate_id=profile.user_id,
            filename="cv.pdf",
            content_type="application/pdf",
            size=len(MINIMAL_PDF),
            blob_pathname=blob_pathname,
        )
    )


def seed() -> bool:
    """Create the demo dataset when the database is empty. Returns True if seeded."""

    if get_settings().app_environment == "production":
        raise RuntimeError("Demo seeding is disabled in production.")
    with SessionLocal() as db:
        if db.scalar(select(Agency.id).limit(1)):
            return False

        password = hash_password(DEMO_PASSWORD)
        northstar = Agency(name="Northstar Careers", slug="northstar", region="Northeast")
        harbor = Agency(name="Harbor Talent", slug="harbor", region="West")
        meridian = Agency(name="Meridian Group", slug="meridian", region="South", status="pending")
        summit = Agency(name="Summit Talent", slug="summit", region="Midwest", status="suspended")
        db.add_all([northstar, harbor, meridian, summit])
        db.flush()

        success_team = Team(agency_id=northstar.id, name="Candidate success")
        ops_team = Team(agency_id=northstar.id, name="Data and operations")
        harbor_team = Team(agency_id=harbor.id, name="Talent delivery")
        db.add_all([success_team, ops_team, harbor_team])
        db.flush()

        def person(
            email: str,
            name: str,
            role: str,
            *,
            demo: bool = False,
        ) -> User:
            user = User(
                email=email,
                name=name,
                role=role,
                password_hash=password,
                is_demo=demo,
            )
            db.add(user)
            db.flush()
            return user

        def join(user: User, agency: Agency, title: str, team: Team | None = None) -> Membership:
            membership = Membership(
                user_id=user.id,
                agency_id=agency.id,
                title=title,
                team_id=team.id if team else None,
            )
            db.add(membership)
            db.flush()
            return membership

        def candidate(
            email: str,
            name: str,
            agency: Agency | None,
            *,
            headline: str,
            location: str,
            phone: str = "",
            summary: str = "",
            current_title: str = "",
            experience_level: str = "",
            skills: list[str],
            stage: str,
            statuses: tuple[str, str, str, str],
            experience: list[dict] | None = None,
            education: list[dict] | None = None,
            prefs: dict | None = None,
            demo: bool = False,
        ) -> CandidateProfile:
            user = person(email, name, "candidate", demo=demo)
            if agency is not None:
                join(user, agency, "Candidate")
            profile = CandidateProfile(
                user_id=user.id,
                agency_id=agency.id if agency else None,
                headline=headline,
                location=location,
                phone=phone,
                summary=summary,
                current_title=current_title,
                experience_level=experience_level,
                stage=stage,
            )
            db.add(profile)
            _steps(profile, statuses)
            preference = prefs or {}
            db.add(
                CandidatePreference(
                    user_id=user.id,
                    work_type=preference.get("work_type", "Hybrid"),
                    preferred_location=preference.get("preferred_location", "Remote"),
                    salary_expectation=preference.get("salary_expectation", ""),
                    availability=preference.get("availability", "2 weeks"),
                    willing_to_relocate=preference.get("willing_to_relocate", False),
                )
            )
            for skill in skills:
                db.add(CandidateSkill(candidate_id=user.id, name=skill))
            for item in experience or []:
                db.add(CandidateExperience(candidate_id=user.id, **item))
            for item in education or []:
                db.add(CandidateEducation(candidate_id=user.id, **item))
            if statuses[-1] == "complete":
                _seed_document(profile)
            db.flush()
            return profile

        # Demo perspectives
        aya = candidate(
            "aya@demo.example.com",
            "Aya Khan",
            None,  # independent candidate: no agency membership
            headline="Aspiring product designer",
            location="Lahore, Pakistan",
            phone="+92 300 1234567",
            summary="Designer moving from research into product design.",
            current_title="Junior product designer",
            experience_level="Junior",
            skills=["Research", "Figma", "Communication"],
            stage="onboarding",
            statuses=("next", "upcoming", "upcoming", "upcoming"),
            demo=True,
        )
        sam = person("sam@demo.example.com", "Sam Ali", "employee", demo=True)
        join(sam, northstar, "Talent advisor", success_team)
        noor = person("noor@demo.example.com", "Noor Ahmed", "supervisor", demo=True)
        join(noor, northstar, "Supervisor", success_team)
        join(noor, harbor, "Supervisor", harbor_team)
        jules = person("jules@demo.example.com", "Jules Lee", "platform_admin", demo=True)

        # Agency staff
        olivia = person("olivia@northstar.example.com", "Olivia Carter", "employee")
        join(olivia, northstar, "Candidate partner", success_team)
        marcus = person("marcus@northstar.example.com", "Marcus Lee", "employee")
        join(marcus, northstar, "Data specialist", ops_team)
        priya = person("priya@northstar.example.com", "Priya Shah", "employee")
        join(priya, northstar, "Candidate partner", success_team)
        daniel = person("daniel@northstar.example.com", "Daniel Kim", "employee")
        join(daniel, northstar, "Candidate partner", success_team)
        elena = person("elena@harbor.example.com", "Elena Ruiz", "supervisor")
        join(elena, harbor, "Supervisor", harbor_team)

        # Candidate directory
        candidate(
            "ava@northstar.example.com",
            "Ava Johnson",
            northstar,
            headline="Customer support specialist",
            location="Austin, Texas",
            phone="+1 512 555 0100",
            current_title="Support specialist",
            experience_level="Mid",
            skills=["Communication", "CRM", "Customer success"],
            stage="onboarding",
            statuses=("next", "upcoming", "upcoming", "upcoming"),
            experience=[
                {
                    "company": "Lone Star Retail",
                    "title": "Customer support specialist",
                    "location": "Austin, Texas",
                    "start_date": "2021-03",
                    "current": True,
                    "description": "Support a regional retail customer base.",
                }
            ],
        )
        liam = candidate(
            "liam@northstar.example.com",
            "Liam Patel",
            northstar,
            headline="Data analyst",
            location="Remote",
            phone="+1 206 555 0111",
            current_title="Data analyst",
            experience_level="Mid",
            skills=["SQL", "Python", "Reporting"],
            stage="review",
            statuses=("complete", "complete", "complete", "next"),
            experience=[
                {
                    "company": "Northwind Logistics",
                    "title": "Data analyst",
                    "location": "Remote",
                    "start_date": "2020-06",
                    "current": True,
                    "description": "Own weekly operational reporting.",
                }
            ],
            education=[
                {
                    "institution": "State University",
                    "degree": "BSc",
                    "field_of_study": "Statistics",
                    "start_year": 2015,
                    "end_year": 2019,
                    "grade": "3.7 GPA",
                }
            ],
        )
        noah = candidate(
            "noah@northstar.example.com",
            "Noah Kim",
            northstar,
            headline="Product specialist",
            location="Seattle, Washington",
            phone="+1 206 555 0122",
            current_title="Product specialist",
            experience_level="Senior",
            skills=["Product", "Research", "Enablement"],
            stage="interview",
            statuses=("complete", "complete", "complete", "complete"),
            experience=[
                {
                    "company": "Cascade Software",
                    "title": "Product specialist",
                    "location": "Seattle, Washington",
                    "start_date": "2018-01",
                    "current": True,
                    "description": "Guide product discovery and launch readiness.",
                }
            ],
            education=[
                {
                    "institution": "Pacific College",
                    "degree": "BA",
                    "field_of_study": "Communication",
                    "start_year": 2011,
                    "end_year": 2015,
                    "grade": "Honours",
                }
            ],
        )
        emma = candidate(
            "emma@northstar.example.com",
            "Emma Davis",
            northstar,
            headline="Operations associate",
            location="Chicago, Illinois",
            phone="+1 312 555 0133",
            current_title="Operations associate",
            experience_level="Junior",
            skills=["Operations", "Coordination", "Process"],
            stage="ready",
            statuses=("complete", "complete", "complete", "complete"),
            education=[
                {
                    "institution": "Midwest University",
                    "degree": "BBA",
                    "field_of_study": "Operations",
                    "start_year": 2018,
                    "end_year": 2022,
                    "grade": "3.5 GPA",
                }
            ],
        )
        mia = candidate(
            "mia@harbor.example.com",
            "Mia Chen",
            harbor,
            headline="UX writer",
            location="Portland, Oregon",
            phone="+1 503 555 0144",
            current_title="UX writer",
            experience_level="Mid",
            skills=["Writing", "Content design"],
            stage="onboarding",
            statuses=("complete", "next", "upcoming", "upcoming"),
        )

        db.add_all(
            [
                CandidateAssignment(
                    agency_id=northstar.id, candidate_id=liam.user_id, member_id=marcus.id
                ),
                CandidateAssignment(
                    agency_id=northstar.id, candidate_id=noah.user_id, member_id=olivia.id
                ),
            ]
        )

        # Referral fixtures: one usable link plus used and expired examples.
        now = utcnow()
        active_token = DEMO_REFERRAL_TOKENS["active"]
        db.add_all(
            [
                ReferralLink(
                    agency_id=northstar.id,
                    created_by=sam.id,
                    token_hash=hash_secret(active_token),
                    token_hint=active_token[:8],
                    label="Product design referrals",
                    expires_at=now + timedelta(days=get_settings().referral_expiry_days),
                ),
                ReferralLink(
                    agency_id=harbor.id,
                    created_by=elena.id,
                    token_hash=hash_secret(DEMO_REFERRAL_TOKENS["used"]),
                    token_hint=DEMO_REFERRAL_TOKENS["used"][:8],
                    label="Harbor writing referrals",
                    expires_at=now + timedelta(days=7),
                    used_at=now - timedelta(days=2),
                    used_by=mia.user_id,
                ),
                ReferralLink(
                    agency_id=northstar.id,
                    created_by=sam.id,
                    token_hash=hash_secret(DEMO_REFERRAL_TOKENS["expired"]),
                    token_hint=DEMO_REFERRAL_TOKENS["expired"][:8],
                    label="Autumn campaign",
                    expires_at=now - timedelta(days=2),
                ),
            ]
        )

        jobs = [
            Job(
                agency_id=northstar.id,
                title="Product Designer",
                company="Brightpath",
                location="San Francisco, CA",
                work_type="Hybrid",
                salary="$120k – $160k",
                tags=["Product", "Figma", "Research"],
                description="Shape end-to-end product experiences with a small, research-led team.",
                created_by=noor.id,
                created_at=now - timedelta(days=2),
            ),
            Job(
                agency_id=northstar.id,
                title="Senior UX Researcher",
                company="Northpeak",
                location="Remote",
                work_type="Remote",
                salary="$105k – $140k",
                tags=["Research", "UX", "Strategy"],
                description="Lead discovery for a B2B platform and turn insight into direction",
                created_by=noor.id,
                created_at=now - timedelta(days=4),
            ),
            Job(
                agency_id=northstar.id,
                title="Frontend Engineer",
                company="Vertex",
                location="New York, NY",
                work_type="Hybrid",
                salary="$100k – $135k",
                tags=["React", "TypeScript", "Web"],
                description="Build accessible, fast interfaces used by thousands daily.",
                created_by=noor.id,
                created_at=now - timedelta(days=5),
            ),
            Job(
                agency_id=northstar.id,
                title="Product Manager",
                company="Lumen",
                location="Remote",
                work_type="Remote",
                salary="$110k – $150k",
                tags=["Product", "Roadmaps", "SaaS"],
                description="Own a product area from problem framing through delivery.",
                created_by=noor.id,
                created_at=now - timedelta(days=7),
            ),
            Job(
                agency_id=harbor.id,
                title="Content Designer",
                company="Harbor Studio",
                location="Portland, OR",
                work_type="Hybrid",
                salary="$90k – $115k",
                tags=["Content", "UX", "Writing"],
                description="Design clear product language for complex financial workflows.",
                created_by=elena.id,
                created_at=now - timedelta(days=3),
            ),
        ]
        db.add_all(jobs)
        db.flush()
        product_designer, researcher, frontend, manager, content = jobs

        db.add_all(
            [
                Application(
                    agency_id=northstar.id,
                    job_id=product_designer.id,
                    candidate_id=aya.user_id,
                    status="review",
                    next_step="Usually responds in 1–2 weeks",
                    created_at=now - timedelta(days=3),
                    updated_at=now - timedelta(days=2),
                ),
                Application(
                    agency_id=northstar.id,
                    job_id=researcher.id,
                    candidate_id=aya.user_id,
                    status="interview",
                    next_step="Interview scheduled",
                    created_at=now - timedelta(days=8),
                    updated_at=now - timedelta(days=1),
                ),
                Application(
                    agency_id=northstar.id,
                    job_id=frontend.id,
                    candidate_id=liam.user_id,
                    status="submitted",
                    next_step="The team will review your application",
                    created_at=now - timedelta(days=4),
                    updated_at=now - timedelta(days=3),
                ),
                Application(
                    agency_id=northstar.id,
                    job_id=manager.id,
                    candidate_id=noah.user_id,
                    status="offer",
                    next_step="Review your offer",
                    created_at=now - timedelta(days=10),
                    updated_at=now - timedelta(hours=5),
                ),
                Application(
                    agency_id=northstar.id,
                    job_id=product_designer.id,
                    candidate_id=emma.user_id,
                    status="review",
                    next_step="Usually responds in 1–2 weeks",
                    created_at=now - timedelta(days=1),
                    updated_at=now - timedelta(hours=3),
                ),
                Application(
                    agency_id=harbor.id,
                    job_id=content.id,
                    candidate_id=mia.user_id,
                    status="submitted",
                    next_step="The team will review your application",
                    created_at=now - timedelta(days=2),
                    updated_at=now - timedelta(days=2),
                ),
            ]
        )

        db.add_all(
            [
                Activity(
                    agency_id=northstar.id,
                    actor_id=noor.id,
                    title="Aya Khan applied to Product Designer",
                    detail="Independent candidate application",
                    tone="success",
                    created_at=now - timedelta(minutes=12),
                ),
                Activity(
                    agency_id=northstar.id,
                    actor_id=marcus.id,
                    title="Liam's application moved to review",
                    detail="Updated by Marcus Lee",
                    tone="info",
                    created_at=now - timedelta(hours=1),
                ),
                Activity(
                    agency_id=northstar.id,
                    actor_id=noor.id,
                    title="Assignment needs attention",
                    detail="Emma Davis is waiting for a team member",
                    tone="warning",
                    created_at=now - timedelta(hours=2),
                ),
                Activity(
                    agency_id=harbor.id,
                    actor_id=elena.id,
                    title="Mia Chen joined Harbor Talent",
                    detail="Onboarding started after referral",
                    tone="info",
                    created_at=now - timedelta(hours=4),
                ),
            ]
        )

        db.add_all(
            [
                Integration(
                    name="Civic Data Exchange",
                    type="Data provider",
                    status="connected",
                    last_sync="2 hours ago",
                ),
                Integration(
                    name="Document Storage",
                    type="File storage",
                    status="connected",
                    last_sync="4 hours ago",
                ),
                Integration(
                    name="Email Service",
                    type="Communication",
                    status="syncing",
                    last_sync="In progress",
                ),
                Integration(
                    name="Payment Processor",
                    type="Payments",
                    status="error",
                    last_sync="3 hours ago",
                ),
            ]
        )

        db.add_all(
            [
                AuditEvent(
                    actor_id=jules.id,
                    event="User login",
                    detail="Platform administrator signed in",
                    created_at=now - timedelta(minutes=2),
                ),
                AuditEvent(
                    actor_id=jules.id,
                    agency_id=meridian.id,
                    event="Agency updated",
                    detail="Updated agency settings for Meridian Group",
                    created_at=now - timedelta(minutes=15),
                ),
                AuditEvent(
                    event="Integration sync",
                    detail="Civic Data Exchange sync completed",
                    created_at=now - timedelta(hours=1),
                ),
                AuditEvent(
                    event="Integration error",
                    detail="Payment Processor returned an error",
                    created_at=now - timedelta(hours=3),
                ),
            ]
        )

        db.commit()
        print(f"Seeded demo data. Demo password: {DEMO_PASSWORD}")
        print(f"Active Northstar referral path: /join/{DEMO_REFERRAL_TOKENS['active']}")
        return True


def main() -> None:
    if not seed():
        print("Database already contains data; seed skipped.")


if __name__ == "__main__":
    main()
