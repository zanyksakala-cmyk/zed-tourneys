from django.urls import path
from . import views

urlpatterns = [
    path('signup/',          views.signup,         name='signup'),
    path('player/<int:pk>/', views.player_profile, name='player_profile'),
]