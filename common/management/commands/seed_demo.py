import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seeds the database with a realistic demo dataset for the Adepa org."

    def handle(self, *args, **options):
        from accounts.models import User
        from ai.models import AIScreeningResult, AttritionFlag
        from attendance.models import AttendanceRecord, LeaveBalance, LeaveRequest, LeaveType
        from employees.models import Employment
        from interviews.models import InterviewParticipant, InterviewSession
        from orgs.models import Announcement, Department, Organisation, PolicyDocument
        from payroll.models import PayrollRun, Payslip, SalaryStructure
        from payroll.services import calculate_payslip
        from people.models import Person
        from performance.models import FeedbackNote, PerformanceReview, ReviewCycle
        from recruitment.models import Application, JobPosting

        org, _ = Organisation.objects.get_or_create(slug="adepa", defaults={"name": "Adepa"})

        if Person.objects.filter(organisation=org).count() > 5:
            self.stdout.write(self.style.WARNING("Looks already seeded (>5 people exist) — skipping."))
            return

        today = timezone.localdate()

        # ---- Departments -----------------------------------------------------
        dept_names = ["Engineering", "Design", "Sales", "Marketing", "People Ops", "Finance"]
        depts = {}
        for name in dept_names:
            d, _ = Department.objects.get_or_create(organisation=org, name=name)
            depts[name] = d

        # ---- Leave types --------------------------------------------------
        leave_types = {}
        for name, days, paid in [
            ("Annual", 21, True),
            ("Sick", 10, True),
            ("Maternity", 90, True),
            ("Unpaid", 30, False),
        ]:
            lt, _ = LeaveType.objects.get_or_create(
                organisation=org, name=name, defaults={"days_per_year": days, "paid": paid}
            )
            leave_types[name] = lt

        # ---- Employees ------------------------------------------------------
        admin_user = User.objects.get(username="admin")
        admin_person = Person.objects.get(user=admin_user)
        admin_person.phone = "+233 24 000 0001"
        admin_person.save(update_fields=["phone"])

        EMPLOYEES = [
            # (first, last, role, dept, title, manager_key)
            ("Efua", "Mensah", "hr", "People Ops", "HR Business Partner", None),
            ("Kojo", "Owusu", "hr", "People Ops", "Talent Acquisition Lead", None),
            ("Kwabena", "Asante", "manager", "Engineering", "Engineering Manager", None),
            ("Adjoa", "Darko", "manager", "Sales", "Sales Manager", None),
            ("Yaw", "Boateng", "manager", "Design", "Design Lead", None),
            ("Abena", "Osei", "employee", "Engineering", "Backend Engineer", "Kwabena"),
            ("Kofi", "Appiah", "employee", "Engineering", "Frontend Engineer", "Kwabena"),
            ("Akosua", "Frimpong", "employee", "Engineering", "QA Engineer", "Kwabena"),
            ("Kwame", "Nkrumah", "employee", "Sales", "Account Executive", "Adjoa"),
            ("Efe", "Adjei", "employee", "Sales", "Sales Development Rep", "Adjoa"),
            ("Nana", "Yaa", "employee", "Design", "Product Designer", "Yaw"),
            ("Kwesi", "Amponsah", "employee", "Marketing", "Marketing Specialist", "Yaw"),
            ("Abigail", "Tetteh", "employee", "Finance", "Financial Analyst", None),
        ]

        people = {"Ama": admin_person}
        employments = {"Ama": admin_person.employment if hasattr(admin_person, "employment") else None}

        if not employments["Ama"]:
            employments["Ama"] = Employment.objects.create(
                person=admin_person,
                organisation=org,
                department=depts["People Ops"],
                job_title="Head of People",
                employee_no="ADP-2026-0001",
                start_date=date(2024, 1, 15),
                status=Employment.Status.ACTIVE,
            )
            admin_person.lifecycle_stage = Person.LifecycleStage.EMPLOYEE
            admin_person.save(update_fields=["lifecycle_stage"])

        for i, (first, last, role, dept_name, title, mgr_key) in enumerate(EMPLOYEES, start=2):
            email = f"{first.lower()}.{last.lower()}@adepa.test"
            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "role": role, "organisation": org, "first_name": first, "last_name": last},
            )
            if created:
                user.set_password("Test1234!")
                user.save()

            person, _ = Person.objects.get_or_create(
                organisation=org,
                email=email,
                defaults={
                    "user": user, "first_name": first, "last_name": last,
                    "phone": f"+233 24 000 {1000+i}", "lifecycle_stage": Person.LifecycleStage.EMPLOYEE,
                },
            )
            people[first] = person

            emp, _ = Employment.objects.get_or_create(
                person=person,
                defaults={
                    "organisation": org, "department": depts[dept_name], "job_title": title,
                    "employee_no": f"ADP-2026-{i:04d}",
                    "start_date": today - timedelta(days=random.randint(60, 900)),
                    "status": Employment.Status.ACTIVE,
                },
            )
            employments[first] = emp

        # second pass: wire up managers now that all Employments exist
        for first, _, _, _, _, mgr_key in EMPLOYEES:
            if mgr_key:
                emp = employments[first]
                emp.manager = people[mgr_key]
                emp.save(update_fields=["manager"])

        all_employee_firsts = ["Ama"] + [e[0] for e in EMPLOYEES]

        # ---- Salary structures ---------------------------------------------
        for first in all_employee_firsts:
            person = people[first]
            base = Decimal(random.choice([3200, 4500, 5800, 7200, 9000, 12000, 15000]))
            SalaryStructure.objects.get_or_create(
                person=person,
                effective_from=date(2026, 1, 1),
                defaults={
                    "base_salary": base,
                    "allowances": [{"name": "Transport", "amount": 300}],
                    "deductions": [{"name": "SSNIT", "percent": 5.5}],
                },
            )

        # ---- Leave balances + a handful of requests --------------------------
        approver = employments["Kwabena"]
        for first in all_employee_firsts:
            person = people[first]
            for name, lt in leave_types.items():
                LeaveBalance.objects.get_or_create(
                    person=person, leave_type=lt, year=2026,
                    defaults={"entitled": lt.days_per_year, "taken": random.choice([0, 1, 2, 3, 5])},
                )

        leave_samples = [
            ("Abena", "Annual", 3, LeaveRequest.Status.PENDING),
            ("Kofi", "Sick", 1, LeaveRequest.Status.APPROVED),
            ("Nana", "Annual", 5, LeaveRequest.Status.PENDING),
            ("Kwame", "Unpaid", 2, LeaveRequest.Status.REJECTED),
            ("Akosua", "Annual", 2, LeaveRequest.Status.APPROVED),
        ]
        for first, type_name, days, status in leave_samples:
            person = people[first]
            start = today + timedelta(days=random.randint(-20, 20))
            LeaveRequest.objects.get_or_create(
                person=person, leave_type=leave_types[type_name], start_date=start,
                defaults={
                    "end_date": start + timedelta(days=days - 1), "days": days,
                    "reason": "Personal time off", "status": status,
                    "approver": person.employment.manager if status != LeaveRequest.Status.PENDING else None,
                    "decided_at": timezone.now() if status != LeaveRequest.Status.PENDING else None,
                },
            )

        # ---- Attendance: last 20 weekdays for everyone -----------------------
        day = today
        added = 0
        while added < 20:
            day -= timedelta(days=1)
            if day.weekday() >= 5:
                continue
            for first in all_employee_firsts:
                person = people[first]
                roll = random.random()
                if roll < 0.05:
                    AttendanceRecord.objects.get_or_create(person=person, date=day, defaults={"status": "absent"})
                    continue
                status = "late" if roll < 0.2 else "present"
                clock_in_hour = 9 if status == "present" else 10
                clock_in = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time())) + timedelta(hours=clock_in_hour, minutes=random.randint(0, 30))
                clock_out = clock_in + timedelta(hours=8, minutes=random.randint(-15, 45))
                AttendanceRecord.objects.get_or_create(
                    person=person, date=day,
                    defaults={"clock_in": clock_in, "clock_out": clock_out, "status": status},
                )
            added += 1

        # ---- Job postings -----------------------------------------------------
        JOBS = [
            ("Backend Engineer", "Engineering", "Accra, Ghana", "full_time", JobPosting.Status.OPEN,
             ["3+ years Django/Python", "REST API design", "PostgreSQL"]),
            ("Product Designer", "Design", "Remote", "full_time", JobPosting.Status.OPEN,
             ["Portfolio required", "Figma", "3+ years product design"]),
            ("Sales Executive", "Sales", "Accra, Ghana", "full_time", JobPosting.Status.OPEN,
             ["B2B sales experience", "CRM tools"]),
            ("Financial Analyst", "Finance", "Accra, Ghana", "full_time", JobPosting.Status.DRAFT,
             ["Excel modeling", "Accounting degree"]),
            ("Marketing Intern", "Marketing", "Accra, Ghana", "intern", JobPosting.Status.OPEN,
             ["Currently enrolled in a marketing or business program"]),
        ]
        jobs = {}
        for title, dept_name, location, etype, status, reqs in JOBS:
            slug = title.lower().replace(" ", "-")
            job, _ = JobPosting.objects.get_or_create(
                slug=slug,
                defaults={
                    "organisation": org, "department": depts[dept_name], "title": title,
                    "description": f"We're looking for a {title} to join the {dept_name} team at Adepa.",
                    "requirements": reqs, "location": location, "employment_type": etype,
                    "salary_min": Decimal(random.choice([3000, 5000, 8000])),
                    "salary_max": Decimal(random.choice([6000, 9000, 14000])),
                    "status": status, "created_by": admin_user,
                },
            )
            jobs[title] = job

        # ---- Applications across the pipeline ---------------------------------
        CANDIDATES = [
            ("Linda", "Owusu", "Backend Engineer", "hired"),
            ("Michael", "Boateng", "Backend Engineer", "interview"),
            ("Grace", "Ansah", "Backend Engineer", "screening"),
            ("Samuel", "Kufuor", "Backend Engineer", "rejected"),
            ("Priscilla", "Amoah", "Product Designer", "shortlisted"),
            ("Emmanuel", "Sarpong", "Product Designer", "offer"),
            ("Comfort", "Addo", "Sales Executive", "received"),
            ("Isaac", "Danso", "Sales Executive", "interview"),
            ("Rebecca", "Agyei", "Marketing Intern", "screening"),
            ("Daniel", "Osei", "Marketing Intern", "withdrawn"),
        ]
        applications = []
        for i, (first, last, job_title, stage) in enumerate(CANDIDATES):
            email = f"{first.lower()}.{last.lower()}@example.com"
            person, _ = Person.objects.get_or_create(
                organisation=org, email=email,
                defaults={
                    "first_name": first, "last_name": last, "phone": f"+233 20 111 {2000+i}",
                    "lifecycle_stage": Person.LifecycleStage.EMPLOYEE if stage == "hired" else Person.LifecycleStage.CANDIDATE,
                },
            )
            job = jobs[job_title]
            app, created = Application.objects.get_or_create(
                job=job, person=person,
                defaults={
                    "cover_letter": f"I'm excited to apply for the {job_title} role.",
                    "cv_file": f"cvs/2026/01/{first.lower()}-{last.lower()}-cv.pdf",
                    "source": "careers_portal", "stage": stage,
                    "stage_history": [{"stage": "received", "at": timezone.now().isoformat(), "by": None}],
                },
            )
            applications.append((app, stage))

            if stage in ("screening", "shortlisted", "interview", "offer", "hired"):
                AIScreeningResult.objects.get_or_create(
                    application=app,
                    defaults={
                        "score": Decimal(random.randint(62, 96)),
                        "summary": f"Strong candidate for {job_title} with relevant experience.",
                        "extracted": {"skills": ["communication", "teamwork"], "years_experience": random.randint(1, 6)},
                        "requirement_matches": [{"requirement": r, "met": True, "evidence": "Mentioned in CV"} for r in job.requirements[:2]],
                        "model_used": "gemini-flash-latest", "prompt_version": "v1",
                    },
                )

        # Convert the "hired" candidate into an employee for real
        hired_app = next(app for app, stage in applications if stage == "hired")
        if not hasattr(hired_app.person, "employment"):
            Employment.objects.create(
                person=hired_app.person, organisation=org, department=depts["Engineering"],
                job_title="Backend Engineer", manager=people["Kwabena"],
                employee_no="ADP-2026-0099", start_date=today - timedelta(days=10),
                status=Employment.Status.ACTIVE, hired_from_application=hired_app,
            )
            hired_app.person.lifecycle_stage = Person.LifecycleStage.EMPLOYEE
            hired_app.person.save(update_fields=["lifecycle_stage"])

        # ---- Interviews for candidates in the interview stage -----------------
        for app, stage in applications:
            if stage not in ("interview", "offer"):
                continue
            scheduled = timezone.now() + timedelta(days=random.choice([-3, 2, 5]))
            session, created = InterviewSession.objects.get_or_create(
                application=app,
                defaults={
                    "organisation": org, "kind": InterviewSession.Kind.INTERVIEW,
                    "title": f"Interview — {app.person.first_name} {app.person.last_name}",
                    "scheduled_at": scheduled, "duration_minutes": 45,
                    "channel_name": str(uuid.uuid4()),
                    "status": InterviewSession.Status.COMPLETED if scheduled < timezone.now() else InterviewSession.Status.SCHEDULED,
                },
            )
            if created:
                InterviewParticipant.objects.create(
                    session=session, person=app.person, role=InterviewParticipant.Role.CANDIDATE, agora_uid=1,
                )
                InterviewParticipant.objects.create(
                    session=session, person=people["Kwabena"], role=InterviewParticipant.Role.INTERVIEWER, agora_uid=2,
                )

        # ---- Payroll: one paid run for last month, one draft for this month ---
        last_month = today.replace(day=1) - timedelta(days=1)
        run, created = PayrollRun.objects.get_or_create(
            organisation=org, period_year=last_month.year, period_month=last_month.month,
            defaults={"status": PayrollRun.Status.PAID, "approved_by": admin_user},
        )
        if created:
            for first in all_employee_firsts:
                person = people[first]
                structure = SalaryStructure.objects.filter(person=person).order_by("-effective_from").first()
                result = calculate_payslip(structure, last_month.year, last_month.month)
                Payslip.objects.create(run=run, person=person, **result)

        PayrollRun.objects.get_or_create(
            organisation=org, period_year=today.year, period_month=today.month,
            defaults={"status": PayrollRun.Status.DRAFT},
        )

        # ---- Performance ------------------------------------------------------
        cycle, _ = ReviewCycle.objects.get_or_create(
            organisation=org, name="2026 Mid-Year",
            defaults={"starts_on": date(2026, 6, 1), "ends_on": date(2026, 8, 31), "is_active": True},
        )
        for first in [f for f in all_employee_firsts if f != "Ama"]:
            person = people[first]
            reviewer = person.employment.manager or admin_person
            FeedbackNote.objects.get_or_create(
                person=person, author=reviewer, cycle=cycle,
                body=f"{first} has been consistently delivering on sprint commitments and collaborating well with the team.",
            )
            PerformanceReview.objects.get_or_create(
                cycle=cycle, person=person, reviewer=reviewer,
                defaults={
                    "ratings": {"technical": random.randint(3, 5), "communication": random.randint(3, 5)},
                    "summary": f"{first} had a solid quarter with clear growth in ownership and collaboration.",
                    "status": random.choice([PerformanceReview.Status.DRAFT, PerformanceReview.Status.SUBMITTED]),
                },
            )

        # ---- Announcements ------------------------------------------------------
        for title, body in [
            ("Welcome to the new Adepa HR platform", "You can now manage your leave, payslips, and profile all in one place."),
            ("Office closed for Founders' Day", "The Accra office will be closed on August 4th. Remote work is fine as usual."),
            ("Q3 all-hands next Friday", "Join us at 3pm for the quarterly all-hands — link in your calendar invite."),
            ("New health insurance provider", "We've switched providers effective next month — details in the compliance section."),
        ]:
            Announcement.objects.get_or_create(organisation=org, title=title, defaults={"body": body, "created_by": admin_user})

        # ---- Compliance documents ------------------------------------------------
        for title, category in [
            ("Employee Handbook 2026", "handbook"),
            ("Code of Conduct", "compliance"),
            ("Health Insurance Benefits Guide", "benefits"),
        ]:
            PolicyDocument.objects.get_or_create(
                organisation=org, title=title,
                defaults={"category": category, "file": f"policies/2026/{title.lower().replace(' ', '-')}.pdf", "uploaded_by": admin_user},
            )

        # ---- Attrition flags ------------------------------------------------------
        AttritionFlag.objects.get_or_create(
            person=people["Efe"], risk_level="medium",
            defaults={
                "signals": ["lateness up 35% over 60 days", "leave requests trending up"],
                "narrative": "Efe has shown increased lateness and leave requests over the last two months.",
                "period_start": today - timedelta(days=60), "period_end": today,
            },
        )
        AttritionFlag.objects.get_or_create(
            person=people["Kwesi"], risk_level="low",
            defaults={
                "signals": ["one late clock-in this month"],
                "narrative": "No significant risk signals — flagged for routine monitoring only.",
                "period_start": today - timedelta(days=30), "period_end": today,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Person.objects.filter(organisation=org).count()} people, "
            f"{JobPosting.objects.count()} jobs, {Application.objects.count()} applications, "
            f"{AttendanceRecord.objects.count()} attendance records, {Payslip.objects.count()} payslips."
        ))
