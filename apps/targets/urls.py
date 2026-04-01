from django.urls import path
from . import views

urlpatterns = [
    path('', views.SalesTargetViewSet.as_view(), name='target-list'),
    path('progress/', views.TargetProgressView.as_view(), name='target-progress'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('achievements/', views.AchievementListView.as_view(), name='achievement-list'),
    path('achievements/mine/', views.CashierAchievementsView.as_view(), name='my-achievements'),
]
