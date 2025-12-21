from django.contrib import admin
from .models import Thread, Message, MessageReaction, ChatbotTopic, ChatbotQuestionAnswer

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0

class ChatbotQuestionAnswerInline(admin.StackedInline):
    model = ChatbotQuestionAnswer
    extra = 1
    fields = ('question_text', 'answer_text', 'keywords', 'is_active', 'priority')

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

@admin.register(ChatbotTopic)
class ChatbotTopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ChatbotQuestionAnswerInline]

@admin.register(ChatbotQuestionAnswer)
class ChatbotQuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ('topic', 'question_text', 'is_active', 'priority', 'created_at', 'updated_at')
    list_filter = ('topic', 'is_active', 'priority')
    search_fields = ('question_text', 'answer_text', 'keywords')

