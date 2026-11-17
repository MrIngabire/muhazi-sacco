# backend/core/urls.py
from django.urls import path
from . import views


urlpatterns = [
    # ============================================================
    # AUTHENTICATION
    # ============================================================
    path('auth/login/', views.login_view, name='login'),
    path('auth/me/', views.me_view, name='me'),

    # ============================================================
    # MEMBER PORTAL — Fig 4.5 (Member Web Portal)
    # ============================================================

    # Dashboard (Fig 5.1.1)
    path(
        'member/dashboard/',
        views.get_member_dashboard,
        name='member-dashboard'
    ),

    # Contributions (Fig 5.1.2)
    path(
        'member/contributions/',
        views.contributions_view,
        name='member-contributions'
    ),

    # Loan Application (Fig 5.1.3)
    path(
        'member/loan/apply/',
        views.process_loan_application,
        name='member-loan-apply'
    ),

    # Repayment Schedule (Fig 5.1.4)
    path(
        'member/repayments/',
        views.get_repayment_schedule,
        name='member-repayments'
    ),

    # Pay Installment
    path(
        'member/pay-installment/',
        views.pay_installment,
        name='member-pay-installment'
    ),

    # Notifications (Activity Diagram: NotifyMember)
    path(
        'member/notifications/',
        views.notifications_view,
        name='member-notifications'
    ),

    # ============================================================
    # ADMIN PORTAL — Fig 4.3 (System Use Case)
    # ============================================================

    # Analytics Dashboard (Fig 5.1.6)
    path(
        'admin/analytics/',
        views.get_admin_analytics,
        name='admin-analytics'
    ),

    path('admin/analytics/charts/', views.get_analytics_charts, name='admin-analytics-charts'),

    # Financial Reports (Fig 4.3: "Generate Financial Reports")
    path(
        'admin/reports/',
        views.generate_financial_report,
        name='admin-reports'
    ),
    path(
        'admin/reports/export/',
        views.export_financial_statement,
        name='admin-reports-export'
    ),

    # ============================================================
    # LOAN WORKFLOW — Multi-step (Fig 4.3 + Activity Diagram 4.6)
    # ============================================================

    # Loan Officer review queue (PENDING loans)
    path(
        'admin/loans/review-queue/',
        views.loan_review_queue,
        name='loan-review-queue'
    ),

    # Manager / Committee approval queue (UNDER_REVIEW loans)
    path(
        'admin/loans/approval-queue/',
        views.approval_queue,
        name='loan-approval-queue'
    ),

    # Unified workflow endpoint (review / approve / disburse / reject / request_info)
    path(
        'admin/loans/workflow/',
        views.loan_workflow_action,
        name='loan-workflow-action'
    ),

    # ============================================================
    # CONTRIBUTION WORKFLOW — Teller records, Accountant verifies
    # ============================================================

    # Accountant: pending contributions queue
    path(
        'admin/contributions/pending/',
        views.pending_contributions,
        name='pending-contributions'
    ),

    # Accountant: verify or reject a contribution
    path(
        'admin/contributions/verify/',
        views.verify_contribution,
        name='verify-contribution'
    ),

    # Teller: record a deposit on behalf of a member
    path(
        'admin/contributions/record/',
        views.teller_record_contribution,
        name='teller-record-contribution'
    ),

    # ============================================================
    # ARREARS TRACKER — Fig 4.4 (Financial Logic Engine)
    # ============================================================
    path(
        'admin/arrears/',
        views.track_arrears,
        name='admin-arrears'
    ),

    # ============================================================
    # AUDIT LOG — Supervisor / System Admin only
    # ============================================================
    path(
        'admin/audit-log/',
        views.audit_log_view,
        name='admin-audit-log'
    ),

    # ============================================================
    # USER & ROLE MANAGEMENT — System Admin only
    # ============================================================
    path(
        'admin/users/',
        views.user_list_create,
        name='admin-users'
    ),
    path(
        'admin/users/<int:user_id>/',
        views.user_detail,
        name='admin-user-detail'
    ),
    path(
        'admin/roles/',
        views.role_list,
        name='admin-roles'
    ),
    path(
        'admin/members/',
        views.member_list,
        name='admin-members'
    ),
    path(
        'admin/members/<int:member_id>/',
        views.member_detail,
        name='admin-member-detail'
    ),
    
]