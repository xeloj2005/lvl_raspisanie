from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tournament.urls')),
path('', include('match_protocol.urls')),
]