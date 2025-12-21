from django.contrib import admin
from .models import Course, Lesson, Assignment, Submission, PlagiarismReport

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1

class PlagiarismReportInline(admin.StackedInline):
    model = PlagiarismReport
    extra = 0
    readonly_fields = ('score', 'report_url', 'checked_at', 'is_plagiarized')
    can_delete = False

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_instructors', 'created_at')
    list_filter = ('instructors',)
    search_fields = ('title', 'description')
    inlines = [LessonInline]

    def display_instructors(self, obj):
        return ", ".join([instructor.username for instructor in obj.instructors.all()])
    display_instructors.short_description = "Instructors"

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course',)

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'due_date')
    list_filter = ('lesson__course',)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'submitted_at', 'grade', 'has_plagiarism_report')
    list_filter = ('assignment', 'student', 'plagiarism_report__is_plagiarized')
    inlines = [PlagiarismReportInline]

    def has_plagiarism_report(self, obj):
        return hasattr(obj, 'plagiarism_report')
    has_plagiarism_report.boolean = True
    has_plagiarism_report.short_description = "Plagiarism Checked"

@admin.register(PlagiarismReport)
class PlagiarismReportAdmin(admin.ModelAdmin):
    list_display = ('submission', 'score', 'is_plagiarized', 'checked_at')
    list_filter = ('is_plagiarized', 'checked_at')
    search_fields = ('submission__assignment__title', 'submission__student__username')
    readonly_fields = ('submission', 'score', 'report_url', 'checked_at', 'is_plagiarized')

