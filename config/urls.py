from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from config.admin_views import platform_dashboard
from apps.identity.views import (
    FAQPageView,
    EmailVerificationView,
    LandingPageView,
    OrganizationJoinRequestApproveView,
    OrganizationJoinRequestListView,
    OrganizationJoinRequestRejectView,
    OrganizationTitularityTransferView,
    PrivacyPolicyPageView,
    SignUpView,
    TermsPageView,
)

urlpatterns = [
    path('admin/dashboard/', platform_dashboard, name='platform-dashboard'),
    path('admin/', admin.site.urls),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='identity/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='identity/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='identity/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='identity/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='identity/password_reset_complete.html'), name='password_reset_complete'),
    path('verificar-correo/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path('organizacion/solicitudes/', OrganizationJoinRequestListView.as_view(), name='organization-join-requests'),
    path('organizacion/solicitudes/<int:pk>/aprobar/', OrganizationJoinRequestApproveView.as_view(), name='organization-join-request-approve'),
    path('organizacion/solicitudes/<int:pk>/rechazar/', OrganizationJoinRequestRejectView.as_view(), name='organization-join-request-reject'),
    path('organizacion/titularidad/transferir/', OrganizationTitularityTransferView.as_view(), name='organization-titularity-transfer'),
    path('legal/terminos/', TermsPageView.as_view(), name='legal-terms'),
    path('legal/politica-de-datos/', PrivacyPolicyPageView.as_view(), name='legal-privacy-policy'),
    path('ayuda/preguntas-frecuentes/', FAQPageView.as_view(), name='faq'),
    path('marketplace/', include(('apps.marketplace.urls', 'marketplace'), namespace='marketplace')),
    path('evaluation/', include(('apps.evaluation.urls', 'evaluation'), namespace='evaluation')),
    path('notifications/', include(('apps.notifications.urls', 'notifications'), namespace='notifications')),
    path('', LandingPageView.as_view(), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
