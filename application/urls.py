"""application URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

import dataradar_webviewer.views

# Examples:
# url(r'^$', 'settings.views.home', name='home'),
# url(r'^blog/', include('blog.urls')),

urlpatterns = [
    url(r'^$', dataradar_webviewer.views.index, name='index'),
    url(r'^rss/', dataradar_webviewer.views.rss_feed, name='rss_feed'),
    url(r'^atom/', dataradar_webviewer.views.atom_feed, name='atom_feed'),
    url(r'^admin/', include(admin.site.urls)),
]
