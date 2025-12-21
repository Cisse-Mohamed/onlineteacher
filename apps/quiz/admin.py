from django.contrib import admin
from .models import Quiz, Question, Choice, QuizSubmission, QuestionBank, QuizQuestionAttempt

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(QuestionBank)
class QuestionBankAdmin(admin.ModelAdmin):
    list_display = ('title', 'course')
    inlines = [QuestionInline]
    search_fields = ('title', 'course__title')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'question_bank', 'duration', 'created_at')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    fields = ('course', 'question_bank', 'title', 'description', 'due_date', 'duration', 'number_of_questions', 'points_per_question')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question_bank', 'question_type')
    inlines = [ChoiceInline]
    list_filter = ('question_bank', 'question_type')
    search_fields = ('text', 'question_bank__title')

@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'total_score', 'total_questions', 'score_percentage', 'start_time', 'end_time')
    list_filter = ('quiz', 'start_time')
    search_fields = ('student__username', 'quiz__title')
    date_hierarchy = 'start_time'
    readonly_fields = ('start_time', 'end_time')

    @admin.display(description='Score (%)')
    def score_percentage(self, obj):
        if obj.total_questions > 0:
            return f"{(obj.score / obj.total_questions) * 100:.2f}%"
        return "N/A"

@admin.register(QuizQuestionAttempt)
class QuizQuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('submission', 'question', 'is_correct', 'points_earned')
    list_filter = ('submission__quiz', 'is_correct')
    search_fields = ('submission__student__username', 'question__text')
