from django.contrib import admin
from .models import Course, Lesson, Assignment, Submission

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1

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
    list_display = ('assignment', 'student', 'submitted_at', 'grade')
    list_filter = ('assignment', 'student')
