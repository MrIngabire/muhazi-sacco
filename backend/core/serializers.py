# backend/core/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Member, Contribution, Loan, Repayment,
    Notification, AuditLog, Role,
)


# ============================================================
# ROLE SERIALIZER
# ============================================================
class RoleSerializer(serializers.ModelSerializer):
    """
    Serializes Role with display names and computed permissions.
    Used for admin user management and /auth/me/ responses.
    """
    user_username = serializers.ReadOnlyField(source='user.username')
    user_email = serializers.ReadOnlyField(source='user.email')
    role_display = serializers.ReadOnlyField(source='get_role_display')

    # Expose all permission predicates for the frontend
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'user', 'user_username', 'user_email',
            'role', 'role_display', 'branch',
            'permissions', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_permissions(self, obj):
        return {
            'record_contribution': obj.can_record_contribution,
            'verify_contribution': obj.can_verify_contribution,
            'review_loan': obj.can_review_loan,
            'approve_loan': obj.can_approve_loan,
            'approve_large_loan': obj.can_approve_large_loan,
            'disburse_funds': obj.can_disburse_funds,
            'view_reports': obj.can_view_reports,
            'view_analytics': obj.can_view_analytics,
            'view_audit_log': obj.can_view_audit_log,
            'manage_users': obj.can_manage_users,
            'view_all_members': obj.can_view_all_members,
        }


class RoleMiniSerializer(serializers.ModelSerializer):
    """Compact version for embedding in User responses."""
    role_display = serializers.ReadOnlyField(source='get_role_display')

    class Meta:
        model = Role
        fields = ['role', 'role_display', 'branch']


# ============================================================
# USER SERIALIZER (for admin user management)
# ============================================================
class UserSerializer(serializers.ModelSerializer):
    """
    Full user serializer with role info. Used by System Admin to manage accounts.
    """
    role = RoleMiniSerializer(source='role_profile', read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'date_joined', 'last_login',
            'role', 'password',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ============================================================
# MEMBER SERIALIZER
# ============================================================
class MemberSerializer(serializers.ModelSerializer):
    """
    Full member serializer with computed financial properties.
    Used by admin dashboards and member lookup screens.
    """
    total_savings = serializers.ReadOnlyField()
    active_loan_balance = serializers.ReadOnlyField()
    outstanding_repayments = serializers.ReadOnlyField()
    max_loan_eligibility = serializers.ReadOnlyField()
    has_active_loan = serializers.ReadOnlyField()
    is_in_arrears = serializers.ReadOnlyField()
    username = serializers.ReadOnlyField(source='user.username')
    contribution_count = serializers.SerializerMethodField()
    loan_count = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            'id', 'user', 'username', 'full_name', 'national_id', 'phone_number',
            'branch', 'is_active', 'created_at',
            'total_savings', 'active_loan_balance', 'outstanding_repayments',
            'max_loan_eligibility', 'has_active_loan', 'is_in_arrears',
            'contribution_count', 'loan_count',
        ]
        read_only_fields = ['id', 'created_at']

    def get_contribution_count(self, obj):
        return obj.contributions.count()

    def get_loan_count(self, obj):
        return obj.loans.count()


class MemberMiniSerializer(serializers.ModelSerializer):
    """
    Compact version for embedding in Contribution/Loan responses.
    Avoids N+1 query bloat on list endpoints.
    """
    class Meta:
        model = Member
        fields = ['id', 'full_name', 'national_id', 'phone_number', 'branch']


# ============================================================
# CONTRIBUTION SERIALIZER
# ============================================================
class ContributionSerializer(serializers.ModelSerializer):
    """
    Full contribution serializer.
    - Member can submit (status forced to PENDING_VERIFICATION in view)
    - Workflow fields (recorded_by, verified_by, verified_at) are read-only
    - Rejection reason captured by accountant
    """
    member_name = serializers.ReadOnlyField(source='member.full_name')
    member_id = serializers.ReadOnlyField(source='member.id')
    recorded_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Contribution
        fields = [
            'id', 'member', 'member_id', 'member_name',
            'amount', 'reference_code', 'payment_date',
            'status', 'status_display',
            'recorded_by', 'recorded_by_name',
            'verified_by', 'verified_by_name', 'verified_at',
            'rejection_reason',
        ]
        read_only_fields = [
            'id', 'member', 'payment_date',
            'status', 'recorded_by', 'verified_by', 'verified_at',
            'rejection_reason',
        ]

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.username
        return None

    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return obj.verified_by.get_full_name() or obj.verified_by.username
        return None

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be positive.')
        if value > 10_000_000:
            raise serializers.ValidationError(
                'Amount exceeds maximum single contribution (RWF 10,000,000). '
                'Contact management for larger deposits.'
            )
        return value

    def validate_reference_code(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError(
                'Reference code must be at least 5 characters.'
            )
        # Uniqueness is enforced by DB, but give a friendly error
        qs = Contribution.objects.filter(reference_code=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(
                'This reference code has already been used. '
                'Each deposit must have a unique MoMo reference.'
            )
        return value


class ContributionMiniSerializer(serializers.ModelSerializer):
    """Compact version for embedding in Loan/member detail views."""
    class Meta:
        model = Contribution
        fields = ['id', 'amount', 'reference_code', 'status', 'payment_date']


# ============================================================
# LOAN SERIALIZER
# ============================================================
class LoanSerializer(serializers.ModelSerializer):
    """
    Full loan serializer with workflow actor names and computed financial fields.
    All workflow fields (reviewed_by, approved_by, disbursed_by, etc.) are
    READ-ONLY — they must be set via the /loan-workflow/ endpoint which
    enforces separation of duties.
    """
    member_name = serializers.ReadOnlyField(source='member.full_name')
    member_id = serializers.ReadOnlyField(source='member.id')
    current_savings = serializers.SerializerMethodField()
    max_eligible = serializers.SerializerMethodField()

    # Computed financial fields
    interest_amount = serializers.SerializerMethodField()
    total_repayable = serializers.SerializerMethodField()
    monthly_installment = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()
    progress_percent = serializers.ReadOnlyField()
    is_in_arrears = serializers.ReadOnlyField()
    days_overdue = serializers.SerializerMethodField()

    # Workflow actor names
    reviewed_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    disbursed_by_name = serializers.SerializerMethodField()

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'member', 'member_id', 'member_name',
            'principal_amount', 'interest_rate',
            'priority_level', 'status', 'status_display',
            'purpose', 'term_months', 'rejection_reason',
            'requires_committee',
            # Workflow tracking
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'approved_by', 'approved_by_name', 'approved_at',
            'disbursed_by', 'disbursed_by_name', 'disbursed_at',
            'due_date',
            # Computed
            'current_savings', 'max_eligible',
            'interest_amount', 'total_repayable', 'monthly_installment',
            'amount_paid', 'outstanding_balance',
            'progress_percent', 'is_in_arrears', 'days_overdue',
            # Metadata
            'created_at',
        ]
        read_only_fields = [
            'id', 'member', 'status', 'requires_committee',
            'reviewed_by', 'reviewed_at',
            'approved_by', 'approved_at',
            'disbursed_by', 'disbursed_at',
            'due_date', 'rejection_reason',
            'created_at',
        ]

    def get_current_savings(self, obj):
        return float(obj.member.total_savings)

    def get_max_eligible(self, obj):
        return obj.member.max_loan_eligibility

    def get_interest_amount(self, obj):
        return float(obj.calculate_interest())

    def get_total_repayable(self, obj):
        return obj.total_repayable()

    def get_monthly_installment(self, obj):
        return round(obj.monthly_installment(), 2)

    def get_amount_paid(self, obj):
        return obj.amount_paid()

    def get_outstanding_balance(self, obj):
        return obj.outstanding_balance()

    def get_days_overdue(self, obj):
        return obj.days_overdue()

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.username
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None

    def get_disbursed_by_name(self, obj):
        if obj.disbursed_by:
            return obj.disbursed_by.get_full_name() or obj.disbursed_by.username
        return None

    def validate_principal_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Loan amount must be positive.')
        if value > 20_000_000:
            raise serializers.ValidationError(
                'Loan amount exceeds maximum (RWF 20,000,000). '
                'Contact Credit Committee for larger loans.'
            )
        return value

    def validate_term_months(self, value):
        if value not in [3, 6, 12, 24]:
            raise serializers.ValidationError(
                'Term must be 3, 6, 12, or 24 months.'
            )
        return value

    def validate_interest_rate(self, value):
        if value < 0 or value > 30:
            raise serializers.ValidationError(
                'Interest rate must be between 0 and 30%.'
            )
        return value


class LoanMiniSerializer(serializers.ModelSerializer):
    """Compact version for embedding in member/repayment views."""
    class Meta:
        model = Loan
        fields = [
            'id', 'principal_amount', 'interest_rate', 'status',
            'term_months', 'created_at', 'due_date',
        ]


# ============================================================
# REPAYMENT SERIALIZER
# ============================================================
class RepaymentSerializer(serializers.ModelSerializer):
    """
    Repayment records. Member can create (pay installment),
    but the loan balance is validated in the view.
    """
    loan_id = serializers.ReadOnlyField(source='loan.id')
    member_name = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )

    class Meta:
        model = Repayment
        fields = [
            'id', 'loan', 'loan_id', 'member_name',
            'amount_paid', 'payment_date', 'remaining_balance',
            'recorded_by', 'recorded_by_name',
            'payment_method', 'payment_method_display',
            'reference_code',
        ]
        read_only_fields = [
            'id', 'payment_date', 'remaining_balance',
            'recorded_by',
        ]

    def get_member_name(self, obj):
        return obj.loan.member.full_name

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.username
        return None

    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError('Payment amount must be positive.')
        return value


# ============================================================
# NOTIFICATION SERIALIZER
# ============================================================
class NotificationSerializer(serializers.ModelSerializer):
    """
    Member notifications. Read-only except for is_read toggle.
    """
    type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'type_display',
            'is_read', 'created_at', 'time_ago',
        ]
        read_only_fields = [
            'id', 'title', 'message', 'notification_type', 'created_at',
        ]

    def get_time_ago(self, obj):
        """Human-readable relative time — '2 hours ago', '3 days ago'."""
        delta = timezone.now() - obj.created_at
        seconds = delta.total_seconds()

        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours} hour{"s" if hours > 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f'{days} day{"s" if days > 1 else ""} ago'
        else:
            return obj.created_at.strftime('%b %d, %Y')


# ============================================================
# AUDIT LOG SERIALIZER
# ============================================================
class AuditLogSerializer(serializers.ModelSerializer):
    """
    Immutable audit trail. All fields read-only.
    Only Supervisor and System Admin can view.
    """
    actor_name = serializers.SerializerMethodField()
    actor_role_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'actor_role', 'actor_role_display',
            'action', 'target_model', 'target_id',
            'description', 'ip_address', 'user_agent', 'timestamp',
        ]
        read_only_fields = '__all__'

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return 'System'

    def get_actor_role_display(self, obj):
        if obj.actor_role:
            role_map = dict(Role.ROLE_CHOICES)
            return role_map.get(obj.actor_role, obj.actor_role)
        return '—'


# ============================================================
# DASHBOARD / ANALYTICS SERIALIZERS (response-only)
# ============================================================
class MemberDashboardSerializer(serializers.Serializer):
    """
    Read-only response for GET /member/dashboard/.
    Documents the shape of the response for the frontend team.
    """
    member_name = serializers.CharField()
    total_savings = serializers.FloatField()
    active_loan_balance = serializers.FloatField()
    outstanding_repayments = serializers.FloatField()
    max_loan_eligibility = serializers.FloatField()
    has_active_loan = serializers.BooleanField()


class AdminAnalyticsSerializer(serializers.Serializer):
    """
    Read-only response for GET /admin/analytics/.
    """
    total_liquidity = serializers.FloatField()
    disbursed_loans = serializers.FloatField()
    interest_revenue = serializers.FloatField()
    pending_loans = serializers.IntegerField()
    pending_contributions = serializers.IntegerField()
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()


class FinancialReportSummarySerializer(serializers.Serializer):
    """Response shape for GET /admin/reports/ summary block."""
    total_contributions = serializers.FloatField()
    total_disbursed_loans = serializers.FloatField()
    total_loans_approved = serializers.IntegerField()
    total_loans_rejected = serializers.IntegerField()
    interest_revenue = serializers.FloatField()
    net_position = serializers.FloatField()


# ============================================================
# REPAYMENT SCHEDULE SERIALIZER (response-only)
# ============================================================
class RepaymentScheduleItemSerializer(serializers.Serializer):
    """One row in the repayment schedule."""
    due_date = serializers.CharField()
    principal = serializers.FloatField()
    interest = serializers.FloatField()
    total_due = serializers.FloatField()
    status = serializers.CharField()  # Cleared / Overdue / Pending


class RepaymentScheduleResponseSerializer(serializers.Serializer):
    """Full response for GET /member/repayments/."""
    loan_id = serializers.IntegerField()
    principal = serializers.FloatField()
    interest_rate = serializers.FloatField()
    term_months = serializers.IntegerField()
    remaining_balance = serializers.FloatField()
    total_paid = serializers.FloatField()
    progress_percent = serializers.FloatField()
    schedule = RepaymentScheduleItemSerializer(many=True)


# ============================================================
# LOGIN RESPONSE SERIALIZER (response-only)
# ============================================================
class LoginResponseSerializer(serializers.Serializer):
    """Response shape for POST /auth/login/."""
    refresh = serializers.CharField()
    access = serializers.CharField()
    is_admin = serializers.BooleanField()
    username = serializers.CharField()
    role_code = serializers.CharField()


class MeResponseSerializer(serializers.Serializer):
    """Response shape for GET /auth/me/."""
    username = serializers.CharField()
    email = serializers.EmailField()
    is_staff = serializers.BooleanField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    role_code = serializers.CharField()
    branch = serializers.CharField(required=False, allow_blank=True)
    permissions = serializers.DictField(required=False)
    member_id = serializers.IntegerField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)