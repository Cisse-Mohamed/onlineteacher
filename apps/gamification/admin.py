from django.contrib import admin
from .models import Badge, UserPoints, UserBadge, DailyChallenge, UserDailyChallenge

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_required', 'slug', 'created_at')
    list_filter = ('points_required', 'created_at')
    search_fields = ('name', 'description', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('points_required',)

@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_points', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__username', 'user__email')
    ordering = ('-total_points',)
    readonly_fields = ('updated_at',)

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'awarded_at')
    list_filter = ('badge', 'awarded_at')
    search_fields = ('user__username', 'badge__name')
    ordering = ('-awarded_at',)
    readonly_fields = ('awarded_at',)

@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_award', 'frequency', 'is_active', 'created_at')
    list_filter = ('frequency', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)

@admin.register(UserDailyChallenge)
class UserDailyChallengeAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'completed_date', 'is_completed')
    list_filter = ('challenge', 'is_completed', 'completed_date')
    search_fields = ('user__username', 'challenge__name')
    ordering = ('-completed_date',)
    readonly_fields = ('completed_date', 'is_completed')
