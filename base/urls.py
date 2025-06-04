from django.urls import path
from . import views

app_name = 'base'

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('emails/', views.email_summarizer, name='email_summarizer'),
    path('google/callback/', views.google_callback, name='google_callback'),
]