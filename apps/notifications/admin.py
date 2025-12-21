from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'message', 'is_read', 'created_at', 'link')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message', 'link')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
