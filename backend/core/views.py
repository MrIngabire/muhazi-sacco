# backend/core/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv

from .models import (
    Member, Contribution, Loan, Repayment,
    Notification, AuditLog, Role
)
from .serializers import (
    MemberSerializer, ContributionSerializer, LoanSerializer,
    RepaymentSerializer, NotificationSerializer, AuditLogSerializer,
    RoleSerializer
)
from .permissions import require_role, require_permission


# ============================================================
# HELPERS
# ============================================================
def get_client_ip(request):
    """Extract client IP, respecting X-Forwarded-For proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(request, action, target_model, target_id=None, description=''):
    """
    Centralized audit logging with role snapshot.
    Every sensitive action must call this.
    """
    actor_role = ''
    if request.user.is_authenticated:
        try:
            actor_role = Role.objects.get(user=request.user).role
        except Role.DoesNotExist:
            actor_role = 'ADMIN' if request.user.is_staff else 'MEMBER'

    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        actor_role=actor_role,
        action=action,
        target_model=target_model,
        target_id=target_id,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
    )


def notify(member, title, message, notif_type='SYSTEM'):
    """Create an in-app notification for a member."""
    return Notification.objects.create(
        member=member,
        title=title,
        message=message,
        notification_type=notif_type,
    )


def get_user_role(user):
    """Safe role lookup — returns None if no Role assigned."""
    try:
        return Role.objects.get(user=user)
    except Role.DoesNotExist:
        return None


# ============================================================
# AUTHENTICATION
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)

    if user:
        refresh = RefreshToken.for_user(user)
        role = get_user_role(user)
        log_action(request, 'LOGIN_SUCCESS', 'User', user.id,
                   f'User {username} logged in')
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'is_admin': user.is_staff,
            'username': user.username,
            'role_code': role.role if role else ('ADMIN' if user.is_staff else 'MEMBER'),
        })

    log_action(request, 'LOGIN_FAILED', 'User', None,
               f'Failed login attempt for {username}')
    return Response({'error': 'Invalid credentials'}, status=401)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Returns current user's identity + role + permissions.
    The frontend uses this to render the correct sidebar and gates buttons.
    """
    user = request.user
    profile = {
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
        'display_name': user.get_full_name() or user.username,
    }

    role = get_user_role(user)
    if role:
        profile.update({
            'role': role.get_role_display(),
            'role_code': role.role,
            'branch': role.branch,
            'permissions': {
                'record_contribution': role.can_record_contribution,
                'verify_contribution': role.can_verify_contribution,
                'review_loan': role.can_review_loan,
                'approve_loan': role.can_approve_loan,
                'approve_large_loan': role.can_approve_large_loan,
                'disburse_funds': role.can_disburse_funds,
                'view_reports': role.can_view_reports,
                'view_analytics': role.can_view_analytics,
                'view_audit_log': role.can_view_audit_log,
                'manage_users': role.can_manage_users,
                'view_all_members': role.can_view_all_members,
            }
        })
    else:
        profile.update({
            'role': 'Member' if not user.is_staff else 'Administrator',
            'role_code': 'MEMBER' if not user.is_staff else 'SYSTEM_ADMIN',
            'branch': '',
            'permissions': {},
        })

    # Add member-specific info if applicable
    if not user.is_staff:
        try:
            member = Member.objects.get(user=user)
            profile['display_name'] = member.full_name
            profile['member_id'] = member.id
            profile['phone'] = member.phone_number
        except Member.DoesNotExist:
            pass

    return Response(profile)


# ============================================================
# MEMBER PORTAL (Fig 4.5)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_dashboard(request):
    """Fig 5.1.1 — Member dashboard with savings, loan, eligibility."""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'Member profile not found'}, status=404)

    return Response({
        'member_name': member.full_name,
        'total_savings': float(member.total_savings),
        'active_loan_balance': float(member.active_loan_balance),
        'outstanding_repayments': float(member.outstanding_repayments),
        'max_loan_eligibility': member.max_loan_eligibility,
        'has_active_loan': member.has_active_loan,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def contributions_view(request):
    """Fig 5.1.2 — Member views history & submits new deposit."""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'Member profile not found'}, status=404)

    if request.method == 'GET':
        qs = member.contributions.all().order_by('-payment_date')
        return Response(ContributionSerializer(qs, many=True).data)

    # POST — member submits deposit for accountant verification
    serializer = ContributionSerializer(data=request.data)
    if serializer.is_valid():
        contribution = serializer.save(
            member=member,
            status='PENDING_VERIFICATION'
        )
        log_action(request, 'CONTRIBUTION_SUBMITTED', 'Contribution',
                   contribution.id,
                   f'{member.full_name} submitted RWF {contribution.amount} '
                   f'(ref {contribution.reference_code})')
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_loan_application(request):
    """Fig 5.1.3 — Member applies for loan (3x rule with subtraction)."""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'Member profile not found'}, status=404)

    try:
        requested_amount = float(request.data.get('requested_amount', 0))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=400)

    if requested_amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=400)

    purpose = request.data.get('purpose', '')
    term = int(request.data.get('term_months', 3))

    if term not in [3, 6, 12, 24]:
        return Response({'error': 'Invalid term. Choose 3, 6, 12, or 24 months'}, status=400)

    max_eligible = member.max_loan_eligibility

    if requested_amount <= max_eligible:
        loan = Loan.objects.create(
            member=member,
            principal_amount=requested_amount,
            status='PENDING',
            purpose=purpose,
            term_months=term,
        )
        log_action(request, 'LOAN_APPLIED', 'Loan', loan.id,
                   f'{member.full_name} applied for RWF {requested_amount:,.0f}')
        notify(member, 'Loan Application Received',
               f'Your loan request of RWF {requested_amount:,.0f} is pending review.',
               'LOAN_STATUS')

        return Response({
            'status': 'success',
            'reply': f'Your application for RWF {requested_amount:,.0f} has been received. '
                     f'Loan Ticket #{loan.id} is pending review.',
            'loan_id': loan.id,
        }, status=201)

    return Response({
        'status': 'rejected',
        'reply': f'Application denied. Requested amount exceeds maximum eligibility of '
                 f'RWF {max_eligible:,.0f} (based on savings minus existing obligations).'
    }, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_repayment_schedule(request):
    """Fig 5.1.4 — Member views active loan repayment schedule."""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'Member profile not found'}, status=404)

    active_loan = Loan.objects.filter(member=member, status='DISBURSED').first()
    if not active_loan:
        return Response({'message': 'No active loans'}, status=200)

    months = active_loan.term_months or 3
    principal_per_month = float(active_loan.principal_amount) / months
    interest_per_month = float(active_loan.calculate_interest()) / months

    schedule = []
    start_date = active_loan.disbursed_at or active_loan.created_at
    total_paid = active_loan.amount_paid()
    cumulative_expected = 0

    for i in range(months):
        due = start_date + timedelta(days=30 * (i + 1))
        is_past = due < timezone.now()
        cumulative_expected += principal_per_month + interest_per_month
        is_paid = total_paid >= cumulative_expected

        if is_paid:
            status = 'Cleared'
        elif is_past:
            status = 'Overdue'
        else:
            status = 'Pending'

        schedule.append({
            'due_date': due.strftime('%Y-%m-%d'),
            'principal': round(principal_per_month, 2),
            'interest': round(interest_per_month, 2),
            'total_due': round(principal_per_month + interest_per_month, 2),
            'status': status,
        })

    return Response({
        'loan_id': active_loan.id,
        'principal': float(active_loan.principal_amount),
        'interest_rate': float(active_loan.interest_rate),
        'term_months': months,
        'remaining_balance': active_loan.outstanding_balance(),
        'total_paid': total_paid,
        'progress_percent': active_loan.progress_percent,
        'schedule': schedule,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_installment(request):
    """
    Member pays an installment on their active loan.
    In production this would integrate with MoMo/Airtel; here it records the payment.
    """
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'Member profile not found'}, status=404)

    try:
        amount = float(request.data.get('amount', 0))
        loan_id = request.data.get('loan_id')
    except (ValueError, TypeError):
        return Response({'error': 'Invalid input'}, status=400)

    if amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=400)

    try:
        loan = Loan.objects.get(id=loan_id, member=member, status='DISBURSED')
    except Loan.DoesNotExist:
        return Response({'error': 'Active loan not found'}, status=404)

    remaining = loan.outstanding_balance()
    if amount > remaining:
        return Response({
            'error': f'Amount exceeds remaining balance (RWF {remaining:,.0f})'
        }, status=400)

    new_remaining = remaining - amount
    Repayment.objects.create(
        loan=loan,
        amount_paid=amount,
        remaining_balance=new_remaining,
        recorded_by=request.user,
        payment_method=request.data.get('payment_method', 'MOMO'),
        reference_code=request.data.get('reference_code', ''),
    )

    if new_remaining <= 0:
        loan.status = 'CLOSED'
        loan.save()
        notify(member, f'Loan #{loan.id} Fully Repaid',
               'Congratulations! Your loan has been fully repaid.', 'LOAN_STATUS')
        log_action(request, 'LOAN_CLOSED', 'Loan', loan.id,
                   f'Loan fully repaid by {member.full_name}')
    else:
        notify(member, 'Payment Received',
               f'RWF {amount:,.0f} received for Loan #{loan.id}. '
               f'Remaining: RWF {new_remaining:,.0f}.', 'REPAYMENT_DUE')
        log_action(request, 'REPAYMENT_MADE', 'Loan', loan.id,
                   f'{member.full_name} paid RWF {amount:,.0f}')

    return Response({
        'status': 'success',
        'amount_paid': amount,
        'new_remaining': new_remaining,
        'loan_closed': new_remaining <= 0,
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notifications_view(request):
    """Member views / marks notifications as read."""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response([])  # Staff without member profile

    if request.method == 'GET':
        qs = member.notifications.all()[:50]
        return Response(NotificationSerializer(qs, many=True).data)

    notif_id = request.data.get('id')
    if notif_id:
        Notification.objects.filter(id=notif_id, member=member).update(is_read=True)
    return Response({'status': 'marked_read'})


# ============================================================
# ADMIN / STAFF PORTAL (Fig 4.3, 4.4)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_view_analytics')
def get_admin_analytics(request):
    """Fig 5.1.6 — Real-time analytics (no hardcoded values)."""
    total_liquidity = Contribution.objects.filter(status='VERIFIED').aggregate(
        Sum('amount'))['amount__sum'] or 0
    disbursed_loans = Loan.objects.filter(
        status__in=['DISBURSED', 'CLOSED']).aggregate(
        Sum('principal_amount'))['principal_amount__sum'] or 0
    pending_loans = Loan.objects.filter(status='PENDING').count()
    pending_contributions = Contribution.objects.filter(
        status='PENDING_VERIFICATION').count()

    # Real interest revenue
    interest_revenue = sum(
        float(loan.calculate_interest())
        for loan in Loan.objects.filter(status__in=['DISBURSED', 'CLOSED'])
    )

    total_members = Member.objects.count()
    active_members = Member.objects.filter(is_active=True).count()

    return Response({
        'total_liquidity': float(total_liquidity),
        'disbursed_loans': float(disbursed_loans),
        'interest_revenue': round(interest_revenue, 2),
        'pending_loans': pending_loans,
        'pending_contributions': pending_contributions,
        'total_members': total_members,
        'active_members': active_members,
    })


# ============================================================
# LOAN WORKFLOW — Multi-step with separation of duties
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_review_loan')
def loan_review_queue(request):
    """
    Loan Officer sees all pending loans assigned for review.
    Shows current savings, eligibility, purpose, and committee flag.
    """
    pending = Loan.objects.filter(
        status='PENDING'
    ).select_related('member').order_by('created_at')

    data = []
    for loan in pending:
        data.append({
            'id': loan.id,
            'member_name': loan.member.full_name,
            'member_id': loan.member.id,
            'principal_amount': float(loan.principal_amount),
            'current_savings': float(loan.member.total_savings),
            'max_eligible': loan.member.max_loan_eligibility,
            'purpose': loan.purpose,
            'term_months': loan.term_months,
            'priority': loan.priority_level,
            'requires_committee': loan.requires_committee,
            'created_at': loan.created_at.isoformat(),
            'is_valid': float(loan.principal_amount) <= loan.member.max_loan_eligibility,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_approve_loan')
def approval_queue(request):
    """
    Manager / Credit Committee sees loans ready for approval (status=UNDER_REVIEW).
    Loans >= 2M flagged as requiring committee.
    """
    reviewable = Loan.objects.filter(
        status='UNDER_REVIEW'
    ).select_related('member', 'reviewed_by').order_by('created_at')

    # Filter by role: Manager can't approve large loans
    role = get_user_role(request.user)
    if role and role.role == 'MANAGER':
        reviewable = reviewable.filter(requires_committee=False)

    data = []
    for loan in reviewable:
        data.append({
            'id': loan.id,
            'member_name': loan.member.full_name,
            'principal_amount': float(loan.principal_amount),
            'current_savings': float(loan.member.total_savings),
            'purpose': loan.purpose,
            'term_months': loan.term_months,
            'priority': loan.priority_level,
            'requires_committee': loan.requires_committee,
            'reviewed_by': loan.reviewed_by.get_full_name() if loan.reviewed_by else None,
            'reviewed_at': loan.reviewed_at.isoformat() if loan.reviewed_at else None,
            'created_at': loan.created_at.isoformat(),
        })
    return Response(data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def loan_workflow_action(request):
    """
    Unified workflow endpoint:
      - review    : LOAN_OFFICER moves PENDING → UNDER_REVIEW
      - approve   : MANAGER/COMMITTEE moves UNDER_REVIEW → APPROVED
      - disburse  : TELLER/ACCOUNTANT moves APPROVED → DISBURSED
      - reject    : LOAN_OFFICER/MANAGER/COMMITTEE moves → REJECTED (with reason)
    """
    loan_id = request.data.get('loan_id')
    action = request.data.get('action')

    try:
        loan = Loan.objects.get(id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=404)

    role = get_user_role(request.user)
    if not role:
        return Response({'error': 'No role assigned'}, status=403)

    # -------- REVIEW --------
    if action == 'review':
        if not role.can_review_loan:
            return Response({'error': 'Only Loan Officers can review applications'}, status=403)
        if loan.status != 'PENDING':
            return Response({'error': f'Cannot review loan in {loan.status} state'}, status=400)

        loan.status = 'UNDER_REVIEW'
        loan.reviewed_by = request.user
        loan.reviewed_at = timezone.now()
        loan.save()

        notify(loan.member, f'Loan #{loan.id} Under Review',
               'A loan officer is reviewing your application.', 'LOAN_STATUS')
        log_action(request, 'LOAN_REVIEWED', 'Loan', loan.id,
                   f'Reviewed by {role.role}')
        return Response({'status': 'reviewed', 'loan_status': loan.status})

    # -------- APPROVE --------
    if action == 'approve':
        if not role.can_approve_loan:
            return Response({'error': 'Only Manager/Credit Committee can approve'}, status=403)
        if loan.status != 'UNDER_REVIEW':
            return Response({'error': 'Loan must be reviewed first'}, status=400)
        if not loan.reviewed_by:
            return Response({'error': 'Loan must have a reviewer before approval'}, status=400)
        if loan.requires_committee and not role.can_approve_large_loan:
            return Response({
                'error': f'This loan (RWF {loan.principal_amount:,.0f}) requires '
                         f'Credit Committee approval (threshold: RWF '
                         f'{Loan.SINGLE_APPROVAL_LIMIT:,.0f}).'
            }, status=403)

        # Separation of duties: reviewer cannot be the approver
        if loan.reviewed_by == request.user:
            return Response({
                'error': 'Separation of duties: you reviewed this loan, '
                         'a different manager must approve it.'
            }, status=403)

        loan.status = 'APPROVED'
        loan.approved_by = request.user
        loan.approved_at = timezone.now()
        loan.save()

        notify(loan.member, f'Loan #{loan.id} Approved',
               'Your loan has been approved. Awaiting disbursement.', 'LOAN_STATUS')
        log_action(request, 'LOAN_APPROVED', 'Loan', loan.id,
                   f'Approved by {role.role}')
        return Response({'status': 'approved', 'loan_status': loan.status})

    # -------- DISBURSE --------
    if action == 'disburse':
        if not role.can_disburse_funds:
            return Response({'error': 'Only Teller/Accountant can disburse'}, status=403)
        if loan.status != 'APPROVED':
            return Response({'error': 'Loan must be approved before disbursement'}, status=400)

        # Separation of duties: approver cannot be the disburser
        if loan.approved_by == request.user:
            return Response({
                'error': 'Separation of duties: you approved this loan, '
                         'a teller/accountant must disburse it.'
            }, status=403)

        loan.status = 'DISBURSED'
        loan.disbursed_by = request.user
        loan.disbursed_at = timezone.now()
        loan.due_date = timezone.now() + timedelta(days=30 * loan.term_months)
        loan.save()

        notify(loan.member, f'Loan #{loan.id} Disbursed',
               f'RWF {loan.principal_amount:,.0f} has been disbursed to you.',
               'LOAN_STATUS')
        log_action(request, 'LOAN_DISBURSED', 'Loan', loan.id,
                   f'Disbursed by {role.role}')
        return Response({'status': 'disbursed', 'loan_status': loan.status})

    # -------- REJECT --------
    if action == 'reject':
        if not (role.can_review_loan or role.can_approve_loan):
            return Response({'error': 'Insufficient permissions to reject'}, status=403)
        if loan.status not in ['PENDING', 'UNDER_REVIEW']:
            return Response({'error': f'Cannot reject loan in {loan.status} state'}, status=400)

        reason = request.data.get('reason', 'No reason provided')
        loan.status = 'REJECTED'
        loan.rejection_reason = reason
        loan.save()

        notify(loan.member, f'Loan #{loan.id} Rejected', f'Reason: {reason}', 'LOAN_STATUS')
        log_action(request, 'LOAN_REJECTED', 'Loan', loan.id,
                   f'Reason: {reason} | By: {role.role}')
        return Response({'status': 'rejected', 'reason': reason})

    # -------- REQUEST INFO --------
    if action == 'request_info':
        if not role.can_review_loan:
            return Response({'error': 'Insufficient permissions'}, status=403)
        note = request.data.get('note', 'Please provide additional documentation.')
        notify(loan.member, f'Additional Info Needed for Loan #{loan.id}', note, 'LOAN_STATUS')
        log_action(request, 'LOAN_INFO_REQUESTED', 'Loan', loan.id, f'Note: {note}')
        return Response({'status': 'info_requested'})

    return Response({'error': 'Unknown action'}, status=400)


# ============================================================
# CONTRIBUTION WORKFLOW — Teller records, Accountant verifies
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_verify_contribution')
def pending_contributions(request):
    """Accountant views contributions awaiting verification."""
    qs = Contribution.objects.filter(
        status='PENDING_VERIFICATION'
    ).select_related('member').order_by('payment_date')

    data = [{
        'id': c.id,
        'member_name': c.member.full_name,
        'member_id': c.member.id,
        'amount': float(c.amount),
        'reference_code': c.reference_code,
        'submitted_at': c.payment_date.isoformat(),
        'recorded_by': c.recorded_by.get_full_name() if c.recorded_by else 'Self-submitted',
    } for c in qs]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_permission('can_record_contribution')
def teller_record_contribution(request):
    """
    Teller records a deposit at the counter on behalf of a member.
    Status goes to PENDING_VERIFICATION (accountant verifies later).
    """
    member_id = request.data.get('member_id')
    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return Response({'error': 'Member not found'}, status=404)

    try:
        amount = float(request.data.get('amount', 0))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=400)

    if amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=400)

    ref_code = request.data.get('reference_code', '')
    if not ref_code:
        return Response({'error': 'Reference code required'}, status=400)

    try:
        c = Contribution.objects.create(
            member=member,
            amount=amount,
            reference_code=ref_code,
            status='PENDING_VERIFICATION',
            recorded_by=request.user,
        )
    except Exception as e:
        return Response({'error': f'Could not create contribution: {str(e)}'}, status=400)

    log_action(request, 'CONTRIBUTION_RECORDED', 'Contribution', c.id,
               f'Teller recorded RWF {amount:,.0f} for {member.full_name} '
               f'(ref {ref_code})')
    return Response({
        'status': 'recorded',
        'contribution_id': c.id,
        'message': 'Deposit recorded. Awaiting accountant verification.'
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@require_permission('can_verify_contribution')
def verify_contribution(request):
    """
    Accountant verifies or rejects a pending contribution.
    ENFORCES SEPARATION OF DUTIES: the person who recorded cannot verify.
    """
    contrib_id = request.data.get('contribution_id')
    action = request.data.get('action')
    reason = request.data.get('reason', '')

    try:
        c = Contribution.objects.get(id=contrib_id)
    except Contribution.DoesNotExist:
        return Response({'error': 'Contribution not found'}, status=404)

    if c.status != 'PENDING_VERIFICATION':
        return Response({
            'error': f'Cannot verify contribution in {c.status} state'
        }, status=400)

    # SEPARATION OF DUTIES
    if c.recorded_by and c.recorded_by == request.user:
        return Response({
            'error': 'Separation of duties: you recorded this contribution, '
                     'a different accountant must verify it.'
        }, status=403)

    if action == 'verify':
        c.status = 'VERIFIED'
        c.verified_by = request.user
        c.verified_at = timezone.now()
        c.save()

        notify(c.member, 'Contribution Verified',
               f'Your deposit of RWF {c.amount:,.0f} (ref {c.reference_code}) '
               f'has been verified.', 'CONTRIBUTION')
        log_action(request, 'CONTRIBUTION_VERIFIED', 'Contribution', c.id,
                   f'Verified RWF {c.amount:,.0f} for {c.member.full_name}')
        return Response({'status': 'verified'})

    elif action == 'reject':
        c.status = 'REJECTED'
        c.rejection_reason = reason or 'Could not be verified'
        c.save()

        notify(c.member, 'Contribution Rejected',
               f'Your deposit (ref {c.reference_code}) could not be verified. '
               f'Reason: {c.rejection_reason}', 'CONTRIBUTION')
        log_action(request, 'CONTRIBUTION_REJECTED', 'Contribution', c.id,
                   f'Reason: {c.rejection_reason}')
        return Response({'status': 'rejected', 'reason': c.rejection_reason})

    return Response({'error': 'Invalid action. Use "verify" or "reject"'}, status=400)


# ============================================================
# REPORTS & ARREARS (Fig 4.3, 4.4)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_view_reports')
def generate_financial_report(request):
    """Fig 4.3 — Aggregated financial summary for the cooperative."""
    period = request.query_params.get('period', 'monthly')

    total_contributions = Contribution.objects.filter(status='VERIFIED').aggregate(
        Sum('amount'))['amount__sum'] or 0
    total_disbursed = Loan.objects.filter(
        status__in=['DISBURSED', 'CLOSED']).aggregate(
        Sum('principal_amount'))['principal_amount__sum'] or 0
    total_rejected = Loan.objects.filter(status='REJECTED').count()
    total_approved = Loan.objects.filter(
        status__in=['APPROVED', 'DISBURSED', 'CLOSED']).count()

    interest_revenue = sum(
        float(loan.calculate_interest())
        for loan in Loan.objects.filter(status__in=['DISBURSED', 'CLOSED'])
    )

    return Response({
        'period': period,
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_contributions': float(total_contributions),
            'total_disbursed_loans': float(total_disbursed),
            'total_loans_approved': total_approved,
            'total_loans_rejected': total_rejected,
            'interest_revenue': round(interest_revenue, 2),
            'net_position': float(total_contributions) - float(total_disbursed) + interest_revenue,
        },
        'loan_breakdown': list(
            Loan.objects.values('status').annotate(count=Count('id'))
        ),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_view_reports')
def export_financial_statement(request):
    """Fig 4.4 — Export full financial statement as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="muhazi_financial_statement.csv"'

    writer = csv.writer(response)
    writer.writerow(['MUHAZI SACCO - FINANCIAL STATEMENT'])
    writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([f'Generated by: {request.user.get_full_name() or request.user.username}'])
    writer.writerow([])

    writer.writerow(['--- CONTRIBUTIONS ---'])
    writer.writerow(['Member', 'Amount', 'Reference', 'Date', 'Status', 'Verified By'])
    for c in Contribution.objects.select_related('member', 'verified_by').all():
        writer.writerow([
            c.member.full_name,
            float(c.amount),
            c.reference_code,
            c.payment_date.strftime('%Y-%m-%d'),
            c.status,
            c.verified_by.username if c.verified_by else '—',
        ])

    writer.writerow([])

    writer.writerow(['--- LOANS ---'])
    writer.writerow([
        'Loan ID', 'Member', 'Principal', 'Rate %', 'Interest',
        'Total Repayable', 'Paid', 'Outstanding', 'Status',
        'Reviewed By', 'Approved By', 'Disbursed By', 'Date',
    ])
    for loan in Loan.objects.select_related(
        'member', 'reviewed_by', 'approved_by', 'disbursed_by'
    ).all():
        writer.writerow([
            loan.id,
            loan.member.full_name,
            float(loan.principal_amount),
            float(loan.interest_rate),
            round(float(loan.calculate_interest()), 2),
            round(loan.total_repayable(), 2),
            round(loan.amount_paid(), 2),
            round(loan.outstanding_balance(), 2),
            loan.status,
            loan.reviewed_by.username if loan.reviewed_by else '—',
            loan.approved_by.username if loan.approved_by else '—',
            loan.disbursed_by.username if loan.disbursed_by else '—',
            loan.created_at.strftime('%Y-%m-%d'),
        ])

    writer.writerow([])

    writer.writerow(['--- SUMMARY ---'])
    total_contrib = Contribution.objects.filter(status='VERIFIED').aggregate(
        Sum('amount'))['amount__sum'] or 0
    total_disb = Loan.objects.filter(
        status__in=['DISBURSED', 'CLOSED']).aggregate(
        Sum('principal_amount'))['principal_amount__sum'] or 0
    interest = sum(
        float(l.calculate_interest())
        for l in Loan.objects.filter(status__in=['DISBURSED', 'CLOSED'])
    )
    writer.writerow(['Total Contributions', float(total_contrib)])
    writer.writerow(['Total Disbursed', float(total_disb)])
    writer.writerow(['Interest Revenue', round(interest, 2)])

    log_action(
        request,
        'REPORT_EXPORTED',
        'System',
        None,
        'Exported financial statement CSV'
    )

    return response

# backend/core/views.py — APPEND AT BOTTOM

# ============================================================
# USER & ROLE MANAGEMENT (System Admin only)
# ============================================================
from .serializers import UserSerializer, MemberSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_list_create(request):
    """
    GET: List all users with their roles
    POST: Create a new user with role assignment
    """
    role = get_user_role(request.user)
    if not role or not role.can_manage_users:
        return Response({'error': 'Only System Admin can manage users'}, status=403)

    if request.method == 'GET':
        users = User.objects.all().select_related('role_profile').order_by('username')
        data = []
        for u in users:
            try:
                r = u.role_profile
                role_data = {
                    'role': r.role,
                    'role_display': r.get_role_display(),
                    'branch': r.branch,
                }
            except Role.DoesNotExist:
                role_data = None
            data.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'is_active': u.is_active,
                'is_staff': u.is_staff,
                'date_joined': u.date_joined.isoformat(),
                'last_login': u.last_login.isoformat() if u.last_login else None,
                'role': role_data,
            })
        return Response(data)

    # POST — create new user
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    email = request.data.get('email', '')
    full_name = request.data.get('full_name', '')
    role_code = request.data.get('role', 'MEMBER')
    branch = request.data.get('branch', 'Kigali HQ')
    phone = request.data.get('phone_number', '')
    nid = request.data.get('national_id', '')

    if not username or not password:
        return Response({'error': 'Username and password required'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)
    if role_code not in dict(Role.ROLE_CHOICES):
        return Response({'error': f'Invalid role: {role_code}'}, status=400)

    # Create User
    is_staff = role_code not in ('MEMBER',)
    user = User.objects.create_user(
        username=username, password=password, email=email,
        is_staff=is_staff,
    )

    # Assign role
    Role.objects.create(user=user, role=role_code, branch=branch)

    # If MEMBER, create Member profile
    if role_code == 'MEMBER':
        if not full_name or not nid or not phone:
            user.delete()
            return Response({
                'error': 'Members require full_name, national_id, and phone_number'
            }, status=400)
        if Member.objects.filter(national_id=nid).exists():
            user.delete()
            return Response({'error': 'National ID already registered'}, status=400)
        if Member.objects.filter(phone_number=phone).exists():
            user.delete()
            return Response({'error': 'Phone number already registered'}, status=400)
        Member.objects.create(
            user=user, full_name=full_name,
            national_id=nid, phone_number=phone, branch=branch,
        )

    log_action(request, 'USER_CREATED', 'User', user.id,
               f'Created {role_code} user: {username}')
    return Response({
        'status': 'created',
        'user_id': user.id,
        'username': username,
        'role': role_code,
    }, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    """Get, update, or deactivate a user."""
    role = get_user_role(request.user)
    if not role or not role.can_manage_users:
        return Response({'error': 'Only System Admin can manage users'}, status=403)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    if request.method == 'GET':
        try:
            r = user.role_profile
            role_data = {
                'role': r.role,
                'role_display': r.get_role_display(),
                'branch': r.branch,
            }
        except Role.DoesNotExist:
            role_data = None
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'role': role_data,
        })

    if request.method == 'PATCH':
        # Update basic fields
        for field in ['email', 'first_name', 'last_name', 'is_active']:
            if field in request.data:
                setattr(user, field, request.data[field])
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
        user.save()

        # Update role if provided
        if 'role' in request.data:
            new_role = request.data['role']
            if new_role not in dict(Role.ROLE_CHOICES):
                return Response({'error': f'Invalid role: {new_role}'}, status=400)
            Role.objects.update_or_create(
                user=user,
                defaults={
                    'role': new_role,
                    'branch': request.data.get('branch', 'Kigali HQ')
                }
            )
            user.is_staff = new_role != 'MEMBER'
            user.save()

        log_action(request, 'USER_UPDATED', 'User', user.id,
                   f'Updated user: {user.username}')
        return Response({'status': 'updated'})

    if request.method == 'DELETE':
        if user == request.user:
            return Response({'error': 'You cannot delete your own account'}, status=400)
        if user.is_superuser:
            return Response({'error': 'Cannot delete superuser'}, status=400)

        username = user.username
        user.is_active = False  # Soft delete
        user.save()
        log_action(request, 'USER_DEACTIVATED', 'User', user.id,
                   f'Deactivated user: {username}')
        return Response({'status': 'deactivated'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_list(request):
    """List all available roles and their permission sets (for admin UI)."""
    role = get_user_role(request.user)
    if not role or not role.can_manage_users:
        return Response({'error': 'Only System Admin can view roles'}, status=403)

    # Build a permission matrix for each role
    roles_info = []
    for role_code, role_label in Role.ROLE_CHOICES:
        # Create a temporary in-memory Role to compute permissions
        temp_role = Role(role=role_code)
        roles_info.append({
            'code': role_code,
            'label': role_label,
            'permissions': {
                'record_contribution': temp_role.can_record_contribution,
                'verify_contribution': temp_role.can_verify_contribution,
                'review_loan': temp_role.can_review_loan,
                'approve_loan': temp_role.can_approve_loan,
                'approve_large_loan': temp_role.can_approve_large_loan,
                'disburse_funds': temp_role.can_disburse_funds,
                'view_reports': temp_role.can_view_reports,
                'view_analytics': temp_role.can_view_analytics,
                'view_audit_log': temp_role.can_view_audit_log,
                'manage_users': temp_role.can_manage_users,
            }
        })
    return Response(roles_info)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_list(request):
    """List all members (for staff lookup screens)."""
    role = get_user_role(request.user)
    if not role or not role.can_view_all_members:
        return Response({'error': 'Insufficient permissions'}, status=403)

    qs = Member.objects.all().select_related('user').order_by('full_name')

    # Optional search filter
    search = request.query_params.get('search', '').strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(full_name__icontains=search) |
            Q(national_id__icontains=search) |
            Q(phone_number__icontains=search)
        )

    return Response(MemberSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_detail(request, member_id):
    """Get detailed info on a specific member (for teller/accountant lookup)."""
    role = get_user_role(request.user)
    if not role or not role.can_view_all_members:
        return Response({'error': 'Insufficient permissions'}, status=403)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return Response({'error': 'Member not found'}, status=404)

    data = MemberSerializer(member).data

    # Add recent contributions and loans for context
    data['recent_contributions'] = [
        {
            'id': c.id, 'amount': float(c.amount),
            'reference_code': c.reference_code,
            'status': c.status,
            'payment_date': c.payment_date.isoformat(),
        }
        for c in member.contributions.all()[:5]
    ]
    data['recent_loans'] = [
        {
            'id': l.id, 'principal_amount': float(l.principal_amount),
            'status': l.status,
            'outstanding_balance': l.outstanding_balance(),
            'created_at': l.created_at.isoformat(),
        }
        for l in member.loans.all()[:5]
    ]

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_log_view(request):
    """Supervisor / System Admin only — view immutable audit trail."""
    role = get_user_role(request.user)
    if not role or not role.can_view_audit_log:
        return Response({'error': 'Only Supervisor/System Admin can view audit log'}, status=403)

    qs = AuditLog.objects.select_related('actor').order_by('-timestamp')

    # Optional filters
    action = request.query_params.get('action')
    if action:
        qs = qs.filter(action=action)

    target_model = request.query_params.get('target_model')
    if target_model:
        qs = qs.filter(target_model=target_model)

    # Limit to last 200 by default
    limit = int(request.query_params.get('limit', 200))
    qs = qs[:limit]

    return Response(AuditLogSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_arrears(request):
    """Track loans in arrears — Manager, Loan Officer, Supervisor, Admin."""
    role = get_user_role(request.user)
    if not role or role.role not in (
        'MANAGER', 'LOAN_OFFICER', 'SUPERVISOR', 'SYSTEM_ADMIN'
    ):
        return Response({'error': 'Insufficient permissions'}, status=403)

    arrears = []
    for loan in Loan.objects.filter(status='DISBURSED').select_related('member'):
        if loan.is_in_arrears():
            arrears.append({
                'loan_id': loan.id,
                'member_name': loan.member.full_name,
                'member_id': loan.member.id,
                'principal': float(loan.principal_amount),
                'amount_expected': loan.total_repayable(),
                'amount_paid': loan.amount_paid(),
                'outstanding': loan.outstanding_balance(),
                'due_date': loan.due_date.strftime('%Y-%m-%d') if loan.due_date else None,
                'days_overdue': loan.days_overdue(),
                'progress_percent': loan.progress_percent,
            })

    # Sort by most overdue first
    arrears.sort(key=lambda x: x['days_overdue'], reverse=True)

    return Response({
        'total_arrears': len(arrears),
        'total_outstanding': sum(a['outstanding'] for a in arrears),
        'arrears': arrears,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_view_analytics')
def get_analytics_charts(request):
    """
    Returns time-series data for the analytics dashboard charts:
      - Member growth over the last 12 months
      - Loan disbursements over the last 12 months
      - Contribution inflow over the last 12 months
      - Loan status distribution (pie chart)
      - Top 10 members by savings (bar chart)
    """
    from django.db.models.functions import TruncMonth

    # Helper: last 12 months from today (inclusive)
    now = timezone.now()
    months = []
    for i in range(11, -1, -1):
        # Walk back 11..0 months from today
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    # ---- Member growth (cumulative count at each month end) ----
    member_growth = []
    for year, month in months:
        # Last day of that month
        if month == 12:
            month_end = timezone.datetime(year + 1, 1, 1, tzinfo=timezone.UTC) - timedelta(seconds=1)
        else:
            month_end = timezone.datetime(year, month + 1, 1, tzinfo=timezone.UTC) - timedelta(seconds=1)
        count = Member.objects.filter(created_at__lte=month_end).count()
        member_growth.append({
            'month': f'{year}-{month:02d}',
            'label': month_end.strftime('%b %Y'),
            'count': count,
        })

    # ---- Loan disbursements per month (amount & count) ----
    loan_disbursements = []
    for year, month in months:
        qs = Loan.objects.filter(
            status__in=['DISBURSED', 'CLOSED'],
            disbursed_at__year=year,
            disbursed_at__month=month,
        )
        total = qs.aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0
        loan_disbursements.append({
            'month': f'{year}-{month:02d}',
            'label': timezone.datetime(year, month, 1).strftime('%b %Y'),
            'amount': float(total),
            'count': qs.count(),
        })

    # ---- Contributions per month ----
    contributions_by_month = []
    for year, month in months:
        qs = Contribution.objects.filter(
            status='VERIFIED',
            payment_date__year=year,
            payment_date__month=month,
        )
        total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
        contributions_by_month.append({
            'month': f'{year}-{month:02d}',
            'label': timezone.datetime(year, month, 1).strftime('%b %Y'),
            'amount': float(total),
        })

    # ---- Loan status distribution (pie chart) ----
    loan_status = list(
        Loan.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    status_label_map = dict(Loan.STATUS_CHOICES)
    loan_status_data = [
        {
            'status': row['status'],
            'label': status_label_map.get(row['status'], row['status']),
            'count': row['count'],
        }
        for row in loan_status
    ]

    # ---- Top 10 members by savings (horizontal bar) ----
    top_members = []
    for member in Member.objects.all().order_by('-id')[:200]:
        savings = float(member.total_savings)
        if savings > 0:
            top_members.append({
                'name': member.full_name,
                'savings': savings,
            })
    top_members.sort(key=lambda x: x['savings'], reverse=True)
    top_members = top_members[:10]

    return Response({
        'member_growth': member_growth,
        'loan_disbursements': loan_disbursements,
        'contributions_by_month': contributions_by_month,
        'loan_status_distribution': loan_status_data,
        'top_members': top_members,
    })