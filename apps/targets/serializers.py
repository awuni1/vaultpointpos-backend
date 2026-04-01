from rest_framework import serializers
from .models import SalesTarget, Achievement, CashierAchievement


class SalesTargetSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source='cashier.full_name', read_only=True, allow_null=True)

    class Meta:
        model = SalesTarget
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at')


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = '__all__'


class CashierAchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='achievement.name', read_only=True)
    badge_icon = serializers.CharField(source='achievement.badge_icon', read_only=True)
    cashier_name = serializers.CharField(source='cashier.full_name', read_only=True)

    class Meta:
        model = CashierAchievement
        fields = '__all__'
