from django.contrib import admin
from .models import Thread, Message, MessageReaction

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'updated_at')
    inlines = [MessageInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'thread', 'message_type', 'timestamp', 'has_been_read')
    list_filter = ('message_type', 'timestamp')
    search_fields = ('content', 'sender__username')
    filter_horizontal = ('mentions',)
    date_hierarchy = 'timestamp'

    @admin.display(boolean=True, description="Read?")
    def has_been_read(self, obj):
        return obj.read_by.exists()


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'emoji', 'created_at')
    list_filter = ('emoji', 'created_at')
    search_fields = ('user__username', 'message__content')
