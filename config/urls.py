from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from common.views import service_worker
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# CareConnect page routes. These serve the existing web-app pages from templates/.
PAGE_ROUTES = [
    path('service-worker.js', service_worker, name='service-worker'),
    path('', RedirectView.as_view(url='/login/', permanent=False), name='home'),
    path('home/', TemplateView.as_view(template_name='home.html'), name='home-page'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login-page'),
    path('login-page/', TemplateView.as_view(template_name='login.html'), name='login-page-alt'),
    path('register/', TemplateView.as_view(template_name='register.html'), name='register-page'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard-page'),
    path('sos/', TemplateView.as_view(template_name='sos.html'), name='sos-page'),
    path('location/', TemplateView.as_view(template_name='location.html'), name='location-page'),
    path('emergency-contacts/', TemplateView.as_view(template_name='emergency_contacts.html'), name='contacts-page'),
    path('emergency-history/', TemplateView.as_view(template_name='emergency-history.html'), name='history-page'),
    path('notifications/', TemplateView.as_view(template_name='notifications.html'), name='notifications-page'),
    path('admin-portal/', TemplateView.as_view(template_name='admin-portal.html'), name='admin-portal-page'),
]

urlpatterns = PAGE_ROUTES + [
    path('admin/', admin.site.urls),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('users.urls')),
    path('api/societies/', include('societies.urls')),
    path('api/residents/', include('residents.urls')),
    path('api/guardians/', include('guardians.urls')),
    path('api/volunteers/', include('volunteers.urls')),
    path('api/security/', include('security.urls')),
    path('api/visitors/', include('visitors.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/emergency-alerts/', include('emergency_alerts.urls')),
    path('api/', include('emergency_contacts.urls')),
    path('api/tracking/', include('tracking.urls')),
    path('api/response/', include('response.urls')),
    path('api/ai/', include('ai_assistant.urls')),
    path('api/safety-companion/', include('safety_companion.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
