"""Seeds 5 additional test employees with data across every feature area, for
manual QA. Distinct from seed_demo.py (which seeds the base org) — this is
safe to re-run and always upserts on the same 5 fixed emails, so it won't
duplicate on repeat runs.

Note: EmployeeDocument.file / DocumentRequest.file / Person.avatar are all
Cloudinary-backed fields. Real binary uploads to this org's Cloudinary
account are currently blocked (API key lacks "create" permission — a
dashboard-side fix, not a code one), so this command records real DB rows
for every document/avatar but leaves the file a placeholder path, same as
the existing careers-portal CV/policy-document seed data already does.
Once Cloudinary is fixed, re-run with --with-files to actually upload real
bytes for a subset (one avatar + one document) as a smoke test.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seeds 5 test employees with comprehensive data (leave, attendance, payslips, onboarding, assets, documents, tickets, reviews)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-files",
            action="store_true",
            help="Attempt one real Cloudinary upload (avatar + document) as a smoke test instead of a placeholder path.",
        )

    def handle(self, *args, **options):
        from accounts.models import User
        from assets.models import Asset, AssetAssignment, AssetCategory
        from attendance.models import AttendanceRecord, LeaveBalance, LeaveRequest, LeaveType
        from documents.models import DocumentRequest
        from employees.models import Employment, EmployeeDocument
        from helpdesk.models import Ticket, TicketType
        from onboarding.models import OnboardingStage, OnboardingTaskTemplate, PersonOnboarding, PersonOnboardingTask
        from orgs.models import Department, Organisation
        from payroll.models import Payslip, SalaryStructure
        from payroll.services import calculate_payslip
        from people.models import Person
        from performance.models import PerformanceReview, ReviewCycle

        org = Organisation.objects.get(slug="adepa")
        today = timezone.localdate()
        depts = {d.name: d for d in Department.objects.filter(organisation=org)}
        leave_types = {lt.name: lt for lt in LeaveType.objects.filter(organisation=org)}
        manager = Person.objects.filter(email="kwabena.asante@adepa.test").first()

        onboarding_stage = OnboardingStage.objects.filter(organisation=org).order_by("sequence").first()
        if not onboarding_stage:
            onboarding_stage = OnboardingStage.objects.create(organisation=org, title="Paperwork", sequence=1)
            OnboardingTaskTemplate.objects.create(stage=onboarding_stage, title="Sign offer letter")
            OnboardingTaskTemplate.objects.create(stage=onboarding_stage, title="Upload ID")
            OnboardingTaskTemplate.objects.create(stage=onboarding_stage, title="Add bank details")

        asset_category, _ = AssetCategory.objects.get_or_create(organisation=org, name="Laptop")
        ticket_type, _ = TicketType.objects.get_or_create(organisation=org, title="IT support")
        cycle = ReviewCycle.objects.filter(organisation=org).order_by("-starts_on").first()

        TEST_EMPLOYEES = [
            # (first, last, dept, title, credentials note)
            ("Zainab", "Iddrisu", "Engineering", "Mobile Engineer"),
            ("Kwadwo", "Mensah", "Design", "UX Researcher"),
            ("Fatima", "Alhassan", "Sales", "Regional Sales Manager"),
            ("Yaw", "Owusu-Ansah", "Marketing", "Content Strategist"),
            ("Esi", "Bonsu", "Finance", "Payroll Specialist"),
        ]

        credentials = []
        created_people = []

        for i, (first, last, dept_name, title) in enumerate(TEST_EMPLOYEES, start=1):
            email = f"{first.lower()}.{last.lower()}@adepa.test"
            password = "Test1234!"
            user, user_created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "role": "employee", "organisation": org, "first_name": first, "last_name": last},
            )
            if user_created:
                user.set_password(password)
                user.save()

            person, _ = Person.objects.get_or_create(
                organisation=org, email=email,
                defaults={
                    "user": user, "first_name": first, "last_name": last,
                    "phone": f"+233 26 555 {2000 + i}",
                    "lifecycle_stage": Person.LifecycleStage.EMPLOYEE,
                },
            )
            created_people.append(person)
            credentials.append((f"{first} {last}", email, password, title))

            employee_no = f"ADP-2026-{9000 + i}"
            Employment.objects.get_or_create(
                person=person,
                defaults={
                    "organisation": org, "department": depts.get(dept_name), "job_title": title,
                    "manager": manager, "employee_no": employee_no,
                    "start_date": today - timedelta(days=random.randint(5, 400)),
                    "status": Employment.Status.ACTIVE,
                },
            )

            # ---- Salary + payslips -----------------------------------------
            base = Decimal(random.choice([5200, 6800, 8500, 11000]))
            structure, _ = SalaryStructure.objects.get_or_create(
                person=person, effective_from=date(2026, 1, 1),
                defaults={
                    "base_salary": base,
                    "allowances": [{"name": "Transport", "amount": 300}],
                    "deductions": [{"name": "SSNIT", "percent": 5.5}],
                },
            )
            last_month = today.replace(day=1) - timedelta(days=1)
            if not Payslip.objects.filter(person=person, run__period_year=last_month.year, run__period_month=last_month.month).exists():
                from payroll.models import PayrollRun
                run, _ = PayrollRun.objects.get_or_create(
                    organisation=org, period_year=last_month.year, period_month=last_month.month,
                    defaults={"status": PayrollRun.Status.PAID},
                )
                result = calculate_payslip(structure, last_month.year, last_month.month)
                Payslip.objects.create(run=run, person=person, **result)

            # ---- Leave balances + a request ---------------------------------
            for name, lt in leave_types.items():
                LeaveBalance.objects.get_or_create(
                    person=person, leave_type=lt, year=2026,
                    defaults={"entitled": lt.days_per_year, "taken": random.choice([0, 1, 2, 4])},
                )
            if "Annual" in leave_types:
                start = today + timedelta(days=random.randint(3, 25))
                LeaveRequest.objects.get_or_create(
                    person=person, leave_type=leave_types["Annual"], start_date=start,
                    defaults={"end_date": start + timedelta(days=2), "days": 3, "reason": "Family trip", "status": "pending"},
                )

            # ---- Attendance: last 10 weekdays -------------------------------
            day = today
            added = 0
            while added < 10:
                day -= timedelta(days=1)
                if day.weekday() >= 5:
                    continue
                if not AttendanceRecord.objects.filter(person=person, date=day).exists():
                    clock_in = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time())) + timedelta(hours=9, minutes=random.randint(0, 20))
                    AttendanceRecord.objects.create(
                        person=person, date=day, clock_in=clock_in,
                        clock_out=clock_in + timedelta(hours=8), status="present",
                    )
                added += 1

            # ---- Onboarding (in progress, partially done) --------------------
            po, po_created = PersonOnboarding.objects.get_or_create(
                person=person, defaults={"current_stage": onboarding_stage},
            )
            if po_created:
                for j, tmpl in enumerate(onboarding_stage.task_templates.all()):
                    PersonOnboardingTask.objects.create(
                        person_onboarding=po, task_template=tmpl,
                        status=PersonOnboardingTask.Status.DONE if j == 0 else PersonOnboardingTask.Status.PENDING,
                        completed_at=timezone.now() if j == 0 else None,
                    )

            # ---- Asset assignment ---------------------------------------------
            asset, _ = Asset.objects.get_or_create(
                organisation=org, tracking_id=f"AD-TEST-{9000 + i}",
                defaults={"category": asset_category, "name": "MacBook Air 13\"", "status": Asset.Status.ASSIGNED, "purchase_cost": Decimal("14000")},
            )
            AssetAssignment.objects.get_or_create(
                asset=asset, person=person, defaults={"status": AssetAssignment.Status.ASSIGNED},
            )

            # ---- Documents (real Cloudinary upload if --with-files and i==1) -
            avatar_uploaded = False
            doc_uploaded = False
            if options["with_files"] and i == 1:
                try:
                    import base64
                    from django.core.files.base import ContentFile
                    png = base64.b64decode(
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                    )
                    person.avatar = ContentFile(png, name=f"{first.lower()}-{last.lower()}-avatar.png")
                    person.save(update_fields=["avatar"])
                    avatar_uploaded = True
                    doc = EmployeeDocument(person=person, kind="id_card")
                    doc.file.save(f"{first.lower()}-{last.lower()}-id.pdf", ContentFile(_MINI_PDF, name="id.pdf"), save=True)
                    doc_uploaded = True
                except Exception as e:  # noqa: BLE001 — deliberately broad: this is a best-effort smoke test
                    self.stdout.write(self.style.WARNING(f"  Real upload failed for {first}: {e}"))

            if not avatar_uploaded:
                pass  # leave Person.avatar empty — no real file, no fake path (CloudinaryField can't take a bare string safely)
            if not doc_uploaded:
                EmployeeDocument.objects.get_or_create(
                    person=person, kind="id_card",
                    defaults={"file": f"employee-docs/2026/{first.lower()}-{last.lower()}-id.pdf"},
                )
            EmployeeDocument.objects.get_or_create(
                person=person, kind="contract",
                defaults={"file": f"employee-docs/2026/{first.lower()}-{last.lower()}-contract.pdf"},
            )

            # ---- Document request pending signature ---------------------------
            DocumentRequest.objects.get_or_create(
                organisation=org, person=person, title="Remote work policy acknowledgement",
                defaults={"file": f"document-requests/2026/{first.lower()}-{last.lower()}-remote-policy.pdf", "status": "pending"},
            )

            # ---- Performance review -------------------------------------------
            if cycle:
                PerformanceReview.objects.get_or_create(
                    cycle=cycle, person=person, reviewer=manager or person,
                    defaults={
                        "ratings": {"technical": random.randint(3, 5), "communication": random.randint(3, 5)},
                        "summary": f"{first} is ramping up well in the {dept_name} team.",
                        "status": "draft",
                    },
                )

            # ---- Helpdesk ticket ------------------------------------------------
            Ticket.objects.get_or_create(
                organisation=org, raised_by=person, title="Laptop running slow",
                defaults={"ticket_type": ticket_type, "description": "My laptop has been very slow since the last update.", "priority": "medium", "status": "new"},
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_people)} test employees."))

        # ---- Write credentials to markdown -----------------------------------
        lines = [
            "# Test employee logins",
            "",
            f"Generated {timezone.localdate().isoformat()}. All passwords are `Test1234!`.",
            "",
            "| Name | Email (username) | Password | Title |",
            "| --- | --- | --- | --- |",
        ]
        for name, email, password, title in credentials:
            lines.append(f"| {name} | {email} | {password} | {title} |")
        lines.append("")
        lines.append(
            "Each has: employment record, salary structure + last month's payslip, leave balances "
            "+ one pending leave request, 10 days of attendance, onboarding checklist in progress, "
            "an assigned laptop, an ID + contract document, a pending document request to sign, a "
            "draft performance review, and a helpdesk ticket."
        )
        out_path = "/tmp/adepa-test-employees.md"
        with open(out_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        self.stdout.write(self.style.SUCCESS(f"Wrote credentials to {out_path}"))


_MINI_PDF = (
    b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj\n"
    b"trailer<</Root 1 0 R>>"
)
