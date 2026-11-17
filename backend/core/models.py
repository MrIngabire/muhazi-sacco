# backend/core/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Sum


# ============================================================
# ROLE — RBAC layer (9 roles for BNR compliance)
# ============================================================
class Role(models.Model):
    """
    Extended roles beyond Django's is_staff flag.
    Enforces separation of duties required by BNR regulations for SACCOs.

    Role hierarchy & permissions:
      - MEMBER              : deposits, borrows, repays (self-service portal)
      - TELLER              : records deposits & disburses cash
      - ACCOUNTANT          : verifies contributions, generates reports
      - LOAN_OFFICER        : reviews loan applications, escalates
      - MANAGER             : approves loans < 2M, oversees branch
      - BOARD_MEMBER        : read-only oversight, strategy
      - SUPERVISOR          : read-only audit, compliance checks
      - CREDIT_COMMITTEE    : approves loans >= 2M (multi-signature)
      - SYSTEM_ADMIN        : full access, user management, IT

    Separation of duties enforced:
      - Teller records contribution  ≠  Accountant verifies it
      - Loan Officer reviews         ≠  Manager approves
      - Manager approves             ≠  Teller disburses
    """
    ROLE_CHOICES = [
        ('MEMBER', 'Member'),
        ('TELLER', 'Teller / Cashier'),
        ('ACCOUNTANT', 'Accountant'),
        ('LOAN_OFFICER', 'Loan Officer'),
        ('MANAGER', 'Branch Manager'),
        ('BOARD_MEMBER', 'Board of Directors'),
        ('SUPERVISOR', 'Supervisory Committee'),
        ('CREDIT_COMMITTEE', 'Credit Committee'),
        ('SYSTEM_ADMIN', 'System Administrator'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='role_profile'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    branch = models.CharField(
        max_length=100, blank=True, default='Kigali HQ',
        help_text='e.g. Kigali HQ, Musanze, Huye'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role', 'user__username']
        verbose_name = 'Role Assignment'
        verbose_name_plural = 'Role Assignments'

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()} ({self.branch})"

    # ---- Permission predicates (used throughout views) ----

    @property
    def is_member(self):
        return self.role == 'MEMBER'

    @property
    def is_operational_staff(self):
        return self.role in (
            'TELLER', 'ACCOUNTANT', 'LOAN_OFFICER', 'MANAGER', 'SYSTEM_ADMIN'
        )

    @property
    def can_record_contribution(self):
        """Teller records deposits at the counter."""
        return self.role in ('TELLER', 'ACCOUNTANT', 'SYSTEM_ADMIN')

    @property
    def can_verify_contribution(self):
        """Accountant reconciles against MoMo statement. Not the same person who recorded."""
        return self.role in ('ACCOUNTANT', 'MANAGER', 'SYSTEM_ADMIN')

    @property
    def can_review_loan(self):
        """Loan officer reviews applications before approval."""
        return self.role in ('LOAN_OFFICER', 'MANAGER', 'SYSTEM_ADMIN')

    @property
    def can_approve_loan(self):
        """Manager approves small loans; committee approves large ones."""
        return self.role in ('MANAGER', 'CREDIT_COMMITTEE', 'SYSTEM_ADMIN')

    @property
    def can_approve_large_loan(self):
        """Only Credit Committee or System Admin can approve >= threshold."""
        return self.role in ('CREDIT_COMMITTEE', 'SYSTEM_ADMIN')

    @property
    def can_disburse_funds(self):
        """Teller or Accountant hands out cash after approval."""
        return self.role in ('TELLER', 'ACCOUNTANT', 'SYSTEM_ADMIN')

    @property
    def can_view_reports(self):
        """Managers, accountants, board, supervisor, admin see reports."""
        return self.role in (
            'MANAGER', 'ACCOUNTANT', 'BOARD_MEMBER',
            'SUPERVISOR', 'SYSTEM_ADMIN'
        )

    @property
    def can_view_analytics(self):
        return self.role in (
            'MANAGER', 'ACCOUNTANT', 'BOARD_MEMBER',
            'SUPERVISOR', 'SYSTEM_ADMIN'
        )

    @property
    def can_view_audit_log(self):
        """Only Supervisory Committee & System Admin see the audit trail."""
        return self.role in ('SUPERVISOR', 'SYSTEM_ADMIN')

    @property
    def can_manage_users(self):
        """Only System Admin manages user accounts."""
        return self.role == 'SYSTEM_ADMIN'

    @property
    def can_view_all_members(self):
        """Staff can look up members; members cannot."""
        return self.is_operational_staff or self.role in (
            'BOARD_MEMBER', 'SUPERVISOR', 'CREDIT_COMMITTEE'
        )


# ============================================================
# MEMBER
# ============================================================
class Member(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='member_profile'
    )
    full_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=16, unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    branch = models.CharField(max_length=100, default='Kigali HQ')
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive members cannot apply for loans or contribute.'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['national_id']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.full_name

    # ---- Financial computed properties ----

    @property
    def total_savings(self):
        """Sum of VERIFIED contributions only."""
        return self.contributions.filter(status='VERIFIED').aggregate(
            Sum('amount'))['amount__sum'] or 0

    @property
    def active_loan_balance(self):
        """Sum of principal for loans that are APPROVED or DISBURSED (not closed)."""
        return self.loans.filter(
            status__in=['APPROVED', 'DISBURSED']
        ).aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0

    @property
    def outstanding_repayments(self):
        """Total remaining to be paid across all active loans."""
        total = 0
        for loan in self.loans.filter(status='DISBURSED'):
            total += loan.outstanding_balance()
        return total

    @property
    def max_loan_eligibility(self):
        """3x verified savings MINUS existing outstanding obligations."""
        return max(0, float(self.total_savings) * 3 - float(self.active_loan_balance))

    @property
    def has_active_loan(self):
        return self.loans.filter(status__in=['APPROVED', 'DISBURSED']).exists()

    @property
    def is_in_arrears(self):
        """True if any of this member's loans are in arrears."""
        return any(loan.is_in_arrears() for loan in self.loans.filter(status='DISBURSED'))


# ============================================================
# CONTRIBUTION — with verification workflow & separation of duties
# ============================================================
class Contribution(models.Model):
    STATUS_CHOICES = [
        ('PENDING_VERIFICATION', 'Pending Verification'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='contributions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_code = models.CharField(max_length=50, unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default='PENDING_VERIFICATION'
    )

    # Separation of duties: who recorded vs who verified
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contributions_recorded',
        help_text='Teller who recorded the deposit at the counter'
    )
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contributions_verified',
        help_text='Accountant who verified against MoMo statement'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['reference_code']),
        ]

    def __str__(self):
        return f"{self.member.full_name} - RWF {self.amount} ({self.status})"

    @property
    def is_verified(self):
        return self.status == 'VERIFIED'

    @property
    def needs_verification(self):
        return self.status == 'PENDING_VERIFICATION'


# ============================================================
# LOAN — with multi-step workflow & committee approval
# ============================================================
class Loan(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('DISBURSED', 'Disbursed'),
        ('CLOSED', 'Closed'),
    ]

    # Threshold for committee approval (RWF)
    SINGLE_APPROVAL_LIMIT = 2_000_000

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='loans'
    )
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text='Annual interest rate as percentage'
    )
    priority_level = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )
    purpose = models.TextField(blank=True, null=True)
    term_months = models.IntegerField(default=3)
    rejection_reason = models.TextField(blank=True, null=True)

    # Multi-step workflow — separation of duties
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='loans_reviewed',
        help_text='Loan officer who reviewed the application'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='loans_approved',
        help_text='Manager or Credit Committee who approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='loans_disbursed',
        help_text='Teller/Accountant who disbursed the cash'
    )
    requires_committee = models.BooleanField(
        default=False,
        help_text='True if amount exceeds single-manager approval threshold'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['requires_committee']),
        ]

    def __str__(self):
        return f"Loan #{self.id} — {self.member.full_name} ({self.status})"

    def save(self, *args, **kwargs):
        # Auto-flag loans that exceed single-manager approval threshold
        self.requires_committee = (
            float(self.principal_amount) > self.SINGLE_APPROVAL_LIMIT
        )
        super().save(*args, **kwargs)

    # ---- Financial computed methods ----

    def calculate_interest(self):
        """Total simple interest for the full term."""
        return (self.principal_amount * self.interest_rate) / 100

    def total_repayable(self):
        """Principal + total interest."""
        return float(self.principal_amount) + float(self.calculate_interest())

    def monthly_installment(self):
        """Total repayable divided by term months."""
        return self.total_repayable() / (self.term_months or 3)

    def amount_paid(self):
        """Sum of all repayments made on this loan."""
        return float(self.repayments.aggregate(
            Sum('amount_paid'))['amount_paid__sum'] or 0)

    def outstanding_balance(self):
        """Remaining amount to be paid."""
        return max(0, self.total_repayable() - self.amount_paid())

    def is_in_arrears(self):
        """True if due date passed and amount paid < total repayable."""
        if self.status != 'DISBURSED' or not self.due_date:
            return False
        return (timezone.now() > self.due_date
                and self.amount_paid() < self.total_repayable())

    def days_overdue(self):
        """Number of days past due (0 if not overdue)."""
        if not self.is_in_arrears():
            return 0
        return (timezone.now() - self.due_date).days

    @property
    def progress_percent(self):
        """Percentage of total repayable already paid."""
        total = self.total_repayable()
        if total <= 0:
            return 0
        return min(100, round(self.amount_paid() / total * 100, 1))


# ============================================================
# REPAYMENT
# ============================================================
class Repayment(models.Model):
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name='repayments'
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='repayments_recorded',
        help_text='Teller who received the payment'
    )
    payment_method = models.CharField(
        max_length=20, default='CASH',
        choices=[
            ('CASH', 'Cash'),
            ('MOMO', 'Mobile Money'),
            ('BANK', 'Bank Transfer'),
        ]
    )
    reference_code = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_date']),
            models.Index(fields=['loan']),
        ]

    def __str__(self):
        return f"Repayment #{self.id} — RWF {self.amount_paid} on Loan #{self.loan_id}"


# ============================================================
# NOTIFICATION (Activity Diagram: NotifyMember)
# ============================================================
class Notification(models.Model):
    TYPE_CHOICES = [
        ('LOAN_STATUS', 'Loan Status'),
        ('REPAYMENT_DUE', 'Repayment Due'),
        ('CONTRIBUTION', 'Contribution'),
        ('ARREARS', 'Arrears'),
        ('SYSTEM', 'System'),
    ]

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='SYSTEM'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"


# ============================================================
# AUDIT LOG — who did what, when, from where
# ============================================================
class AuditLog(models.Model):
    """
    Immutable audit trail required by BNR for financial institutions.
    Every sensitive action (approval, rejection, disbursement, verification)
    must be logged here for regulatory review.
    """
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='audit_actions'
    )
    actor_role = models.CharField(
        max_length=20, blank=True,
        help_text='Snapshot of actor role at time of action'
    )
    action = models.CharField(max_length=50)
    target_model = models.CharField(max_length=50)
    target_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['actor', 'action']),
            models.Index(fields=['target_model', 'target_id']),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor} — {self.action}"