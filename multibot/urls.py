"""
URL configuration for multibot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from bots.views import system_status

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('bots.urls')),  # 所有 API 放到 bots.urls 里
    path("system-status/", system_status),
    path("api/", include("bots.urls")),  # ⬅️ 确保你这行包含了 bots.urls
]
