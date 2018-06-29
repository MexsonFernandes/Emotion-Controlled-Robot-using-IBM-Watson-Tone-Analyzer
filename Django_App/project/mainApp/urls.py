
from django.conf.urls import url
from mainApp import views
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^$', views.index),
    url(r'^api/', views.set_API_credential, name='api'),
    url(r'^emotion_detection/', views.detectEmotion, name='detect'),
]
