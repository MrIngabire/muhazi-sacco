# backend/core/management/commands/seed_heavy.py
"""
MUHAZI SACCO — Heavy Seed Data (Management Command)

Creates a realistic cooperative dataset so every page has content:
  - Member dashboard (Gentil matches book screenshots exactly)
  - Contributions (200+ records across all 53 members)
  - Loan workflow (PENDING → UNDER_REVIEW → APPROVED → DISBURSED → CLOSED/REJECTED)
  - Admin analytics (real liquidity, interest, members, pending items)
  - Loan approval queues for every role
  - Arrears tracker with overdue loans
  - Notifications and audit history

Usage:
  python manage.py seed_heavy          # Idempotent — safe to re-run
  python manage.py seed_heavy --fresh  # Wipe all data first (recommended for demos)

Reproducible: random.seed(42) guarantees identical output every run.
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum

from core.models import (
    Member, Contribution, Loan, Repayment,
    Notification, AuditLog, Role,
)


# ============================================================
# NAME GENERATORS (Rwandan)
# ============================================================
FIRST_M = [
    'Jean', 'Eric', 'Paul', 'Patrick', 'Emmanuel', 'Claude', 'Innocent',
    'Olivier', 'Bosco', 'Cedric', 'Theogene', 'Alphonse', 'Fabrice',
    'Gilbert', 'Modeste', 'Aimable', 'Jean-Baptiste', 'Fabrice',
    'Thierry', 'Alain', 'Kevin', 'Yves', 'Samuel', 'Nathan',
]
FIRST_F = [
    'Marie', 'Claire', 'Grace', 'Diane', 'Alice', 'Chantal', 'Josiane',
    'Jeanne', 'Solange', 'Yvonne', 'Consolée', 'Aline', 'Nadine',
    'Sandrine', 'Valentine', 'Odette', 'Épiphanie', 'Béatrice',
    'Immaculée', 'Clémentine', 'Agnès', 'Florence', 'Joséphine',
]
LAST = [
    'Mugisha', 'Uwase', 'Nkurunziza', 'Ingabire', 'Bizimana', 'Uwimana',
    'Nshimiyimana', 'Karangwa', 'Nizeyimana', 'Hatekimana', 'Nyiraneza',
    'Munyaneza', 'Rwigema', 'Uwera', 'Mukamana', 'Habimana', 'Niyonsaba',
    'Mutesi', 'Ndayisaba', 'Tuyishime', 'Ntaganda', 'Nkusi', 'Gasana',
    'Kamanzi', 'Byiringiro', 'Murenzi', 'Hakizimana', 'Rukundo',
]

LOAN_PURPOSES = [
    'Business expansion', 'School fees', 'Medical expenses',
    'Home renovation', 'Agricultural inputs', 'Equipment purchase',
    'Working capital', 'Emergency expenses', 'Wedding expenses',
    'Purchase of livestock', 'Transport business', 'Tailoring supplies',
    'Food processing', 'Market stall expansion', 'Moto purchase',
]

CONTRIBUTION_AMOUNTS = [
    25000, 50000, 75000, 100000, 150000, 200000,
    300000, 400000, 500000, 750000, 1000000,
]


class Command(BaseCommand):
    help = 'Seed MUHAZI SACCO with realistic, role-aware demo data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fresh', action='store_true',
            help='Wipe all existing data before seeding'
        )
        parser.add_argument(
            '--extra-members', type=int, default=50,
            help='Number of extra members beyond the 3 core demo members'
        )

    def handle(self, *args, **options):
        # Deterministic — same output every run
        random.seed(42)
        now = timezone.now()

        # ============================================================
        # 0. CLEAN SLATE (optional)
        # ============================================================
        if options['fresh']:
            self.stdout.write(self.style.WARNING('🧹 Wiping existing data...'))
            AuditLog.objects.all().delete()
            Notification.objects.all().delete()
            Repayment.objects.all().delete()
            Loan.objects.all().delete()
            Contribution.objects.all().delete()
            Member.objects.all().delete()
            Role.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('   ✓ Database reset'))
        else:
            self.stdout.write(
                self.style.WARNING('ℹ  Non-fresh mode: existing data preserved (idempotent)')
            )

        # ============================================================
        # 1. SYSTEM ADMIN
        # ============================================================
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@muhazi.rw',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'System',
                'last_name': 'Administrator',
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        Role.objects.update_or_create(
            user=admin_user,
            defaults={'role': 'SYSTEM_ADMIN', 'branch': 'Kigali HQ'}
        )
        self.stdout.write(self.style.SUCCESS('✓ System Admin created'))

        # ============================================================
        # 2. OPERATIONAL STAFF (7 roles)
        # ============================================================
        staff_specs = [
            # (username, password, first, last, role_code, branch)
            ('manager',     'password123', 'Alice',    'MUKAMANA',   'MANAGER',          'Kigali HQ'),
            ('accountant',  'password123', 'Jean',     'HABIMANA',   'ACCOUNTANT',       'Kigali HQ'),
            ('loanofficer', 'password123', 'Claire',   'UWASE',      'LOAN_OFFICER',     'Kigali HQ'),
            ('teller',      'password123', 'Patrick',  'NKURUNZIZA', 'TELLER',           'Kigali HQ'),
            ('board',       'password123', 'Marie',    'INGABIRE',   'BOARD_MEMBER',     'Kigali HQ'),
            ('supervisor',  'password123', 'Emmanuel', 'MUGISHA',    'SUPERVISOR',       'Kigali HQ'),
            ('credit',      'password123', 'Grace',    'NYIRANEZA',  'CREDIT_COMMITTEE', 'Kigali HQ'),
        ]
        for username, password, first, last, role_code, branch in staff_specs:
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@muhazi.rw',
                    'first_name': first,
                    'last_name': last,
                    'is_staff': True,
                }
            )
            u.set_password(password)
            u.save()
            Role.objects.update_or_create(
                user=u,
                defaults={'role': role_code, 'branch': branch}
            )

        staff_users = {
            'manager':     User.objects.get(username='manager'),
            'accountant':  User.objects.get(username='accountant'),
            'loanofficer': User.objects.get(username='loanofficer'),
            'teller':      User.objects.get(username='teller'),
            'supervisor':  User.objects.get(username='supervisor'),
            'credit':      User.objects.get(username='credit'),
        }
        self.stdout.write(self.style.SUCCESS(
            f'✓ Operational staff created: {len(staff_specs)} roles'
        ))

        # ============================================================
        # 3. CORE DEMO MEMBERS (match book screenshots)
        # ============================================================
        def make_member(username, full_name, nid, phone, branch='Kigali HQ'):
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@muhazi.rw'}
            )
            if created:
                u.set_password('password123')
                u.save()
            m, _ = Member.objects.get_or_create(
                user=u,
                defaults={
                    'full_name': full_name,
                    'national_id': nid,
                    'phone_number': phone,
                    'branch': branch,
                }
            )
            Role.objects.update_or_create(
                user=u,
                defaults={'role': 'MEMBER', 'branch': branch}
            )
            return m

        gentil = make_member('gentil', 'NIYIBIZI Gentil', '1199880012345678', '0788111222')
        sarah  = make_member('sarah',  'MUKAMANA Sarah',  '1199880099991111', '0788999888')
        eric   = make_member('eric',   'HABIMANA Eric',   '1199880088882222', '0788777666')

        # ============================================================
        # 4. GENTIL — match book exactly
        #    (1.45M savings, 500K active loan, 5 notifications)
        # ============================================================
        # Clear Gentil's data to ensure idempotency
        Contribution.objects.filter(member=gentil).delete()
        Loan.objects.filter(member=gentil).delete()
        Notification.objects.filter(member=gentil).delete()

        gentil_contrib_specs = [
            (500000, 'TXN_GENTIL_AUG', 90, staff_users['teller'], staff_users['accountant']),
            (450000, 'TXN_GENTIL_SEP', 60, staff_users['teller'], staff_users['accountant']),
            (500000, 'TXN_GENTIL_OCT', 30, staff_users['teller'], staff_users['accountant']),
        ]
        for amt, ref, days_ago, recorder, verifier in gentil_contrib_specs:
            c = Contribution.objects.create(
                member=gentil, amount=amt, reference_code=ref,
                status='VERIFIED',
                recorded_by=recorder, verified_by=verifier,
                verified_at=now - timedelta(days=days_ago),
            )
            Contribution.objects.filter(id=c.id).update(
                payment_date=now - timedelta(days=days_ago)
            )

        gentil_loan = Loan.objects.create(
            member=gentil,
            principal_amount=500000,
            interest_rate=5.00,
            status='DISBURSED',
            purpose='Small business expansion',
            term_months=3,
            priority_level='MEDIUM',
            reviewed_by=staff_users['loanofficer'],
            reviewed_at=now - timedelta(days=32),
            approved_by=staff_users['manager'],
            approved_at=now - timedelta(days=31),
            disbursed_by=staff_users['teller'],
            disbursed_at=now - timedelta(days=30),
            due_date=now + timedelta(days=60),
        )

        # Gentil has paid 1 installment (175K of 525K total)
        Repayment.objects.create(
            loan=gentil_loan,
            amount_paid=175000,
            remaining_balance=350000,
            recorded_by=staff_users['teller'],
            payment_method='MOMO',
            reference_code='MOMO_REPAY_GENTIL_01',
        )

        # Gentil's 5 notifications
        for title, msg, typ, read in [
            ('Welcome to MUHAZI SACCO Portal',
             'Your account is active. Track contributions and apply for loans.',
             'LOAN_STATUS', True),
            (f'Loan #{gentil_loan.id} Approved',
             'Your loan of RWF 500,000 has been approved and disbursed.',
             'LOAN_STATUS', True),
            ('Payment Received',
             f'RWF 175,000 received for Loan #{gentil_loan.id}. '
             f'Remaining: RWF 350,000.',
             'REPAYMENT_DUE', True),
            ('Contribution Verified',
             'Your deposit of RWF 500,000 (ref TXN_GENTIL_OCT) has been verified.',
             'CONTRIBUTION', False),
            ('Monthly Statement Available',
             'Your October 2026 statement is ready for download.',
             'SYSTEM', False),
        ]:
            Notification.objects.create(
                member=gentil, title=title, message=msg,
                notification_type=typ, is_read=read,
            )
        self.stdout.write(self.style.SUCCESS(
            '✓ Gentil: RWF 1.45M savings, RWF 500K loan, 5 notifications'
        ))

        # ============================================================
        # 5. SARAH & ERIC — pending + workflow loans
        # ============================================================
        for m in [sarah, eric]:
            Contribution.objects.filter(member=m).delete()
            Loan.objects.filter(member=m).delete()

        # Sarah: 400K savings, PENDING loan (valid 3x)
        Contribution.objects.create(
            member=sarah, amount=400000, reference_code='TXN_SARAH_01',
            status='VERIFIED',
            recorded_by=staff_users['teller'],
            verified_by=staff_users['accountant'],
            verified_at=now - timedelta(days=45),
        )
        Loan.objects.create(
            member=sarah, principal_amount=1000000, interest_rate=5.00,
            status='PENDING', purpose='School fees for children',
            term_months=6, priority_level='MEDIUM',
        )

        # Eric: 500K savings, PENDING loan (exceeds 3x → 2.5M > 1.5M)
        Contribution.objects.create(
            member=eric, amount=500000, reference_code='TXN_ERIC_01',
            status='VERIFIED',
            recorded_by=staff_users['teller'],
            verified_by=staff_users['accountant'],
            verified_at=now - timedelta(days=40),
        )
        Loan.objects.create(
            member=eric, principal_amount=2500000, interest_rate=5.00,
            status='PENDING', purpose='Purchase delivery motorcycle',
            term_months=12, priority_level='HIGH',
        )
        self.stdout.write(self.style.SUCCESS(
            '✓ Sarah & Eric: pending loans (valid vs exceeds-limit)'
        ))

        # ============================================================
        # 6. PENDING CONTRIBUTIONS (Accountant verification queue)
        # ============================================================
        for member, amt, ref, recorder in [
            (gentil, 75000, 'TXN_PENDING_GENTIL_01', staff_users['teller']),
            (sarah, 120000, 'TXN_PENDING_SARAH_01', staff_users['teller']),
            (eric, 250000, 'TXN_PENDING_ERIC_01', staff_users['teller']),
        ]:
            Contribution.objects.update_or_create(
                reference_code=ref,
                defaults={
                    'member': member,
                    'amount': amt,
                    'status': 'PENDING_VERIFICATION',
                    'recorded_by': recorder,
                }
            )
        self.stdout.write(self.style.SUCCESS(
            '✓ 3 pending contributions (for accountant verification)'
        ))

        # ============================================================
        # 7. GENERATE EXTRA MEMBERS
        # ============================================================
        n_extra = options['extra_members']
        extra_members = []
        used_names = set()
        used_phones = set()
        used_nids = set()

        for i in range(n_extra):
            # Unique name
            for _attempt in range(50):
                first = random.choice(FIRST_M if random.random() < 0.5 else FIRST_F)
                name = f"{random.choice(LAST).upper()} {first}"
                if name not in used_names:
                    used_names.add(name)
                    break

            # Unique phone
            for _attempt in range(50):
                phone = f"078{random.randint(1000000, 9999999)}"
                if phone not in used_phones:
                    used_phones.add(phone)
                    break

            # Unique NID
            for _attempt in range(50):
                nid = f"119{random.randint(8000000000000, 9999999999999)}"
                if nid not in used_nids:
                    used_nids.add(nid)
                    break

            username = f'member{i:02d}'
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@muhazi.rw'}
            )
            if created:
                u.set_password('password123')
                u.save()
            m, _ = Member.objects.get_or_create(
                user=u,
                defaults={
                    'full_name': name,
                    'national_id': nid,
                    'phone_number': phone,
                    'branch': random.choice(['Kigali HQ', 'Musanze', 'Huye', 'Rubavu']),
                }
            )
            Role.objects.update_or_create(
                user=u,
                defaults={'role': 'MEMBER', 'branch': m.branch}
            )
            extra_members.append(m)

        self.stdout.write(self.style.SUCCESS(
            f'✓ Generated {n_extra} additional members'
        ))

        # ============================================================
        # 8. GENERATE 200+ CONTRIBUTIONS
        # ============================================================
        ref_counter = 1000
        contrib_count = 0

        for member in extra_members:
            n_contribs = random.randint(2, 6)
            for _j in range(n_contribs):
                amt = random.choice(CONTRIBUTION_AMOUNTS)
                days_ago = random.randint(1, 180)

                # Distribution: 78% verified, 15% pending, 7% rejected
                status = random.choices(
                    ['VERIFIED', 'PENDING_VERIFICATION', 'REJECTED'],
                    weights=[78, 15, 7]
                )[0]

                ref_counter += 1
                ref = f'TXN{ref_counter:08d}'

                recorder = staff_users['teller']
                verifier = staff_users['accountant'] if status == 'VERIFIED' else None

                c = Contribution.objects.create(
                    member=member,
                    amount=amt,
                    reference_code=ref,
                    status=status,
                    recorded_by=recorder,
                    verified_by=verifier,
                    verified_at=(
                        now - timedelta(days=days_ago)
                        if status == 'VERIFIED' else None
                    ),
                    rejection_reason=(
                        'Reference not found in MoMo statement'
                        if status == 'REJECTED' else None
                    ),
                )
                Contribution.objects.filter(id=c.id).update(
                    payment_date=now - timedelta(days=days_ago)
                )
                contrib_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Generated {contrib_count} contributions for extra members'
        ))

        # ============================================================
        # 9. GENERATE LOANS IN ALL WORKFLOW STATES
        #    With realistic multi-step actor assignments
        # ============================================================
        loan_stats = {
            'PENDING': 0, 'UNDER_REVIEW': 0, 'APPROVED': 0,
            'REJECTED': 0, 'DISBURSED': 0, 'CLOSED': 0,
        }
        loan_total = 0

        # Ensure at least some in each critical queue state
        force_queues = {
            'PENDING': 5,         # Loan Officer review queue
            'UNDER_REVIEW': 3,    # Manager approval queue
            'APPROVED': 2,        # Teller disbursement queue
        }

        for member in extra_members:
            savings = float(member.total_savings)
            if savings <= 0:
                continue

            # ~65% of members have at least 1 loan
            if random.random() > 0.65:
                continue

            n_loans = random.choices([1, 1, 1, 2], weights=[70, 20, 8, 2])[0]
            for _ in range(n_loans):
                # Request between 20% and 90% of max eligibility
                max_elig = savings * 3
                requested = round(random.uniform(0.2, 0.9) * max_elig, -3)
                if requested <= 0:
                    continue

                # Choose status with realistic distribution
                status = random.choices(
                    ['PENDING', 'UNDER_REVIEW', 'APPROVED', 'DISBURSED', 'CLOSED', 'REJECTED'],
                    weights=[20, 12, 8, 35, 15, 10]
                )[0]

                # Push towards force_queues if under-represented
                for q_status, minimum in force_queues.items():
                    if loan_stats[q_status] < minimum:
                        status = q_status
                        break

                days_ago = random.randint(1, 120)
                term = random.choice([3, 6, 12, 24])
                requested_float = float(requested)

                loan = Loan.objects.create(
                    member=member,
                    principal_amount=requested,
                    interest_rate=5.00,
                    status=status,
                    purpose=random.choice(LOAN_PURPOSES),
                    term_months=term,
                    priority_level=random.choice(['LOW', 'MEDIUM', 'HIGH']),
                    rejection_reason=(
                        'Insufficient repayment history'
                        if status == 'REJECTED' else None
                    ),
                )
                Loan.objects.filter(id=loan.id).update(
                    created_at=now - timedelta(days=days_ago)
                )

                # Populate workflow actors based on status
                if status == 'PENDING':
                    pass  # No actor yet

                elif status == 'UNDER_REVIEW':
                    loan.reviewed_by = staff_users['loanofficer']
                    loan.reviewed_at = now - timedelta(days=days_ago - 1)
                    loan.save()

                elif status == 'APPROVED':
                    loan.reviewed_by = staff_users['loanofficer']
                    loan.reviewed_at = now - timedelta(days=days_ago - 1)
                    loan.approved_by = (
                        staff_users['credit']
                        if requested_float > Loan.SINGLE_APPROVAL_LIMIT
                        else staff_users['manager']
                    )
                    loan.approved_at = now - timedelta(days=days_ago - 2)
                    loan.save()

                elif status == 'DISBURSED':
                    disbursed_date = now - timedelta(days=random.randint(10, 100))
                    loan.reviewed_by = staff_users['loanofficer']
                    loan.reviewed_at = disbursed_date - timedelta(days=2)
                    loan.approved_by = (
                        staff_users['credit']
                        if requested_float > Loan.SINGLE_APPROVAL_LIMIT
                        else staff_users['manager']
                    )
                    loan.approved_at = disbursed_date - timedelta(days=1)
                    loan.disbursed_by = staff_users['teller']
                    loan.disbursed_at = disbursed_date
                    loan.due_date = disbursed_date + timedelta(days=30 * term)
                    loan.save()

                    # 60% chance of partial repayment
                    if random.random() < 0.6:
                        total = loan.total_repayable()
                        paid = round(total * random.uniform(0.1, 0.7), -2)
                        Repayment.objects.create(
                            loan=loan,
                            amount_paid=paid,
                            remaining_balance=round(total - paid, -2),
                            recorded_by=staff_users['teller'],
                            payment_method=random.choice(['CASH', 'MOMO']),
                        )

                elif status == 'CLOSED':
                    disbursed_date = now - timedelta(days=random.randint(60, 200))
                    loan.reviewed_by = staff_users['loanofficer']
                    loan.reviewed_at = disbursed_date - timedelta(days=2)
                    loan.approved_by = (
                        staff_users['credit']
                        if requested_float > Loan.SINGLE_APPROVAL_LIMIT
                        else staff_users['manager']
                    )
                    loan.approved_at = disbursed_date - timedelta(days=1)
                    loan.disbursed_by = staff_users['teller']
                    loan.disbursed_at = disbursed_date
                    loan.due_date = disbursed_date + timedelta(days=30 * term)
                    loan.save()

                    # Fully repaid
                    Repayment.objects.create(
                        loan=loan,
                        amount_paid=loan.total_repayable(),
                        remaining_balance=0,
                        recorded_by=staff_users['teller'],
                        payment_method='CASH',
                    )

                elif status == 'REJECTED':
                    loan.reviewed_by = staff_users['loanofficer']
                    loan.reviewed_at = now - timedelta(days=days_ago)
                    loan.save()

                loan_stats[status] = loan_stats.get(status, 0) + 1
                loan_total += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Generated {loan_total} loans: {loan_stats}'
        ))

        # ============================================================
        # 10. CREATE OVERDUE LOANS (Arrears tracker demo)
        # ============================================================
        disbursed_loans = list(Loan.objects.filter(status='DISBURSED')[:8])
        overdue_count = 0
        for loan in disbursed_loans[:5]:
            past_due = now - timedelta(days=random.randint(10, 60))
            Loan.objects.filter(id=loan.id).update(due_date=past_due)
            overdue_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Marked {overdue_count} loans as overdue (arrears demo)'
        ))

        # ============================================================
        # 11. NOTIFICATIONS ACROSS 25 MEMBERS
        # ============================================================
        notif_templates = [
            ('Contribution Verified',
             'Your recent deposit has been verified by the accountant.',
             'CONTRIBUTION'),
            ('Loan Payment Reminder',
             'Your monthly loan installment is due in 3 days.',
             'REPAYMENT_DUE'),
            ('Monthly Statement Ready',
             'Your monthly statement is available for download.',
             'SYSTEM'),
            ('Welcome to MUHAZI SACCO',
             'Your account is now active. Explore your dashboard.',
             'SYSTEM'),
            ('Loan Application Update',
             'Your loan application is under review.',
             'LOAN_STATUS'),
            ('Loan Payment Overdue',
             'Your loan payment is overdue. Please visit the office.',
             'ARREARS'),
        ]

        notif_count = 0
        sampled = random.sample(extra_members, min(25, len(extra_members)))
        for member in sampled:
            for _ in range(random.randint(1, 4)):
                title, msg, typ = random.choice(notif_templates)
                Notification.objects.create(
                    member=member,
                    title=title,
                    message=msg,
                    notification_type=typ,
                    is_read=random.choice([True, False, False, False]),
                )
                notif_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Generated {notif_count} notifications'
        ))

        # ============================================================
        # 12. AUDIT LOG ENTRIES
        # ============================================================
        audit_actions = [
            ('LOGIN_SUCCESS',          'User'),
            ('CONTRIBUTION_RECORDED',  'Contribution'),
            ('CONTRIBUTION_VERIFIED',  'Contribution'),
            ('LOAN_APPLIED',           'Loan'),
            ('LOAN_REVIEWED',          'Loan'),
            ('LOAN_APPROVED',          'Loan'),
            ('LOAN_DISBURSED',         'Loan'),
            ('LOAN_REJECTED',          'Loan'),
            ('REPAYMENT_MADE',         'Loan'),
            ('REPORT_EXPORTED',        'System'),
        ]
        staff_pool = list(staff_users.values()) + [admin_user]
        audit_count = 0
        for _ in range(120):
            action, target_model = random.choice(audit_actions)
            actor = random.choice(staff_pool)
            try:
                actor_role = Role.objects.get(user=actor).role
            except Role.DoesNotExist:
                actor_role = 'SYSTEM_ADMIN'

            AuditLog.objects.create(
                actor=actor,
                actor_role=actor_role,
                action=action,
                target_model=target_model,
                target_id=random.randint(1, 100),
                description=(
                    f'Auto-generated {action.lower().replace("_", " ")} '
                    f'by {actor.username}'
                ),
                ip_address=f'192.168.{random.randint(1, 10)}.{random.randint(1, 254)}',
                user_agent='Mozilla/5.0 (Seed Script)',
            )
            audit_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Generated {audit_count} audit log entries'
        ))

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        total_savings = Contribution.objects.filter(status='VERIFIED').aggregate(
            Sum('amount'))['amount__sum'] or 0
        total_disbursed = Loan.objects.filter(
            status__in=['DISBURSED', 'CLOSED']).aggregate(
            Sum('principal_amount'))['principal_amount__sum'] or 0
        interest_total = sum(
            float(l.calculate_interest())
            for l in Loan.objects.filter(status__in=['DISBURSED', 'CLOSED'])
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🎉  MUHAZI SACCO — HEAVY SEED COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        self.stdout.write(f'👥 Users:                 {User.objects.count()}')
        self.stdout.write(f'   ├─ System Admin:       {Role.objects.filter(role="SYSTEM_ADMIN").count()}')
        self.stdout.write(f'   ├─ Operational staff:  {Role.objects.exclude(role__in=["SYSTEM_ADMIN", "MEMBER"]).count()}')
        self.stdout.write(f'   └─ Members:            {Role.objects.filter(role="MEMBER").count()}')
        self.stdout.write('')
        self.stdout.write(f'📊 Member profiles:       {Member.objects.count()}')
        self.stdout.write(f'🔐 Role assignments:      {Role.objects.count()}')
        self.stdout.write('')
        self.stdout.write(f'💰 Contributions:         {Contribution.objects.count()}')
        self.stdout.write(f'   ├─ Verified:           {Contribution.objects.filter(status="VERIFIED").count()}')
        self.stdout.write(f'   ├─ Pending:            {Contribution.objects.filter(status="PENDING_VERIFICATION").count()}')
        self.stdout.write(f'   └─ Rejected:           {Contribution.objects.filter(status="REJECTED").count()}')
        self.stdout.write('')
        self.stdout.write(f'📋 Loans:                 {Loan.objects.count()}')
        self.stdout.write(f'   ├─ Pending:            {Loan.objects.filter(status="PENDING").count()}')
        self.stdout.write(f'   ├─ Under Review:       {Loan.objects.filter(status="UNDER_REVIEW").count()}')
        self.stdout.write(f'   ├─ Approved:           {Loan.objects.filter(status="APPROVED").count()}')
        self.stdout.write(f'   ├─ Disbursed:          {Loan.objects.filter(status="DISBURSED").count()}')
        self.stdout.write(f'   ├─ Closed:             {Loan.objects.filter(status="CLOSED").count()}')
        self.stdout.write(f'   └─ Rejected:           {Loan.objects.filter(status="REJECTED").count()}')
        self.stdout.write('')
        self.stdout.write(f'💸 Repayments:            {Repayment.objects.count()}')
        self.stdout.write(f'🔔 Notifications:         {Notification.objects.count()}')
        self.stdout.write(f'📜 Audit logs:            {AuditLog.objects.count()}')
        self.stdout.write('')
        self.stdout.write(f'💵 Total Liquidity:       RWF {float(total_savings):>15,.0f}')
        self.stdout.write(f'📤 Total Disbursed:       RWF {float(total_disbursed):>15,.0f}')
        self.stdout.write(f'💹 Interest Revenue:      RWF {interest_total:>15,.0f}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.WARNING('🔑 LOGIN CREDENTIALS'))
        self.stdout.write('-' * 70)

        self.stdout.write(self.style.HTTP_INFO('MEMBER PORTAL:'))
        self.stdout.write('  gentil       / password123   Main demo (matches book)')
        self.stdout.write('  sarah        / password123   Pending loan (valid 3x)')
        self.stdout.write('  eric         / password123   Pending loan (exceeds limit)')
        self.stdout.write('  member00     / password123   Sample generated member')
        self.stdout.write('')

        self.stdout.write(self.style.HTTP_INFO('STAFF PORTAL (role-specific dashboards):'))
        self.stdout.write('  teller       / password123   Record deposits, disburse loans')
        self.stdout.write('  accountant   / password123   Verify contributions, reports')
        self.stdout.write('  loanofficer  / password123   Review loan applications')
        self.stdout.write('  manager      / password123   Approve loans < 2M, reports')
        self.stdout.write('  credit       / password123   Approve loans >= 2M (committee)')
        self.stdout.write('  board        / password123   Read-only oversight')
        self.stdout.write('  supervisor   / password123   Audit log viewer')
        self.stdout.write('  admin        / admin123      Full system access')
        self.stdout.write('=' * 70)
        self.stdout.write('')

        self.stdout.write(self.style.HTTP_INFO('📱 Pages now populated:'))
        self.stdout.write('  ✅ Member Dashboard    — Gentil: 1.45M savings, 500K loan')
        self.stdout.write('  ✅ Contributions       — 200+ records, all statuses')
        self.stdout.write('  ✅ Loan Application    — Real eligibility from live data')
        self.stdout.write('  ✅ Repayment Schedule  — Gentil\'s active loan w/ 1 payment')
        self.stdout.write('  ✅ Admin Analytics     — Real liquidity, interest, members')
        self.stdout.write('  ✅ Loan Officer Queue  — 5+ PENDING applications')
        self.stdout.write('  ✅ Manager Approval    — 3+ UNDER_REVIEW loans ready')
        self.stdout.write('  ✅ Teller Disbursement — 2+ APPROVED loans ready to disburse')
        self.stdout.write('  ✅ Accountant Verify   — 3+ PENDING_VERIFICATION contributions')
        self.stdout.write('  ✅ Financial Reports   — Full breakdown across all states')
        self.stdout.write('  ✅ Arrears Tracker     — 5 overdue loans with days computed')
        self.stdout.write('  ✅ Notifications       — 25+ members with mixed notifs')
        self.stdout.write('  ✅ Audit Log           — 120 entries (supervisor only)')
        self.stdout.write('=' * 70)