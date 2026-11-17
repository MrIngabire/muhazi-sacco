# backend/backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def api_root(request):
    """
    API root endpoint — returns a directory of available endpoints.
    Useful for quick discovery and Postman exploration.
    """
    return JsonResponse({
        'name': 'MUHAZI SACCO API',
        'version': '1.0.0',
        'documentation': '/api/',
        'endpoints': {
            'authentication': {
                'login': '/api/auth/login/',
                'me': '/api/auth/me/',
            },
            'member_portal': {
                'dashboard': '/api/member/dashboard/',
                'contributions': '/api/member/contributions/',
                'loan_apply': '/api/member/loan/apply/',
                'repayments': '/api/member/repayments/',
                'pay_installment': '/api/member/pay-installment/',
                'notifications': '/api/member/notifications/',
            },
            'admin_portal': {
                'analytics': '/api/admin/analytics/',
                'loan_review_queue': '/api/admin/loans/review-queue/',
                'approval_queue': '/api/admin/loans/approval-queue/',
                'loan_workflow': '/api/admin/loans/workflow/',
                'pending_contributions': '/api/admin/contributions/pending/',
                'verify_contribution': '/api/admin/contributions/verify/',
                'teller_record': '/api/admin/contributions/record/',
                'financial_reports': '/api/admin/reports/',
                'export_statement': '/api/admin/reports/export/',
                'arrears': '/api/admin/arrears/',
                'audit_log': '/api/admin/audit-log/',
            },
        },
    })


urlpatterns = [
    # Django admin (used only by System Admin for low-level DB access)
    path('django-admin/', admin.site.urls),

    # API root
    path('api/', api_root, name='api-root'),

    # All app routes
    path('api/', include('core.urls')),
]


# ============================================================
# DEVELOPMENT-ONLY: Serve media & static files
# ============================================================
# In production, use nginx/Apache to serve these.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# ============================================================
# ADMIN SITE BRANDING
# ============================================================
admin.site.site_header = 'MUHAZI SACCO — System Administration'
admin.site.site_title = 'MUHAZI SACCO Admin'
admin.site.index_title = 'Database Management'