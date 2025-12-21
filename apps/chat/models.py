from django.db import models
from django.conf import settings
from django.utils import timezone

class Thread(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Thread {self.id}"

    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]
    
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    
    # Media files
    audio_file = models.FileField(upload_to='chat/audio/', blank=True, null=True)
    video_file = models.FileField(upload_to='chat/video/', blank=True, null=True)
    
    # Translation support
    original_language = models.CharField(max_length=10, blank=True, null=True, help_text="ISO language code")
    translated_content = models.JSONField(default=dict, blank=True, help_text="Translations: {lang_code: translated_text}")
    
    # Mentions
    mentions = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='mentioned_in_messages', blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # New field for read receipts
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, through='MessageReadReceipt', related_name='read_messages', blank=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['thread', '-timestamp']),
        ]

    def __str__(self):
        return f"Message from {self.sender} at {self.timestamp}"


class MessageReadReceipt(models.Model):
    """Tracks when a user has read a message."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'message')
        indexes = [
            models.Index(fields=['user', 'message']),
        ]
        ordering = ['-read_at']

    def __str__(self):
        return f"User {self.user.id} read message {self.message.id} at {self.read_at}"


class MessageReaction(models.Model):
    """Emoji reactions to messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=10, help_text="Emoji character or code")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user', 'emoji')
        indexes = [
            models.Index(fields=['message', 'emoji']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message {self.message.id}"

class ChatbotTopic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class ChatbotQuestionAnswer(models.Model):
    topic = models.ForeignKey(ChatbotTopic, on_delete=models.CASCADE, related_name='questions_answers')
    question_text = models.TextField(help_text="The question a user might ask (or a representative phrase)")
    answer_text = models.TextField(help_text="The chatbot's predefined answer")
    keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords for better matching")
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=0, help_text="Higher priority means this answer is preferred if multiple match")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['topic', '-priority', 'question_text']
        unique_together = ('topic', 'question_text')

    def __str__(self):
        return f"{self.topic.name}: {self.question_text[:50]}"