from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tournaments/', views.tournament_list, name='tournament_list'),
    path('tournaments/<int:pk>/', views.tournament_detail, name='tournament_detail'),
    path('tournaments/<int:pk>/join/', views.join_tournament, name='join_tournament'),
    path('tournaments/<int:pk>/bracket/', views.bracket_view, name='bracket_view'),
    path('matches/<int:match_id>/result/', views.report_result, name='report_result'),
]