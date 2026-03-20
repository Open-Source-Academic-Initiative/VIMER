from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.identity.views import LandingPageView, SignUpView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='identity/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('marketplace/', include(('apps.marketplace.urls', 'marketplace'), namespace='marketplace')),
    path('evaluation/', include(('apps.evaluation.urls', 'evaluation'), namespace='evaluation')),
    path('notifications/', include(('apps.notifications.urls', 'notifications'), namespace='notifications')),
    path('', LandingPageView.as_view(), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
