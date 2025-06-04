from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('base.urls', namespace='base')),
    path('accounts/', include('django.contrib.auth.urls')),  # For login/logout
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])