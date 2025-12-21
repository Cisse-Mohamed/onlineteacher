from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Prefetch
from .models import Course, Lesson, Assignment, Submission, LessonProgress
from .forms import SubmissionForm, CourseForm, LessonForm, AssignmentForm
from apps.accounts.models import User

class InstructorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_instructor

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        user = self.request.user
        if user.is_instructor:
            return Course.objects.filter(instructors=user)
        return user.courses_enrolled.all()

class CourseCreateView(LoginRequiredMixin, InstructorRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        form.instance.instructors.add(self.request.user)
        return response

class CourseUpdateView(LoginRequiredMixin, InstructorRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    
    def get_success_url(self):
        return reverse_lazy('courses:course_detail', kwargs={'pk': self.object.pk})
    
    def get_queryset(self):
        return super().get_queryset().filter(instructors=self.request.user)

class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'courses/course_detail.html'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('lessons')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lessons = self.object.lessons.all() # Uses prefetched data
        context['lessons'] = lessons
        
        user = self.request.user
        if user.is_authenticated:
            # Calculate progress
            total_lessons = lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                student=user, 
                lesson__in=lessons, 
                is_completed=True
            ).count()
            
            context['progress_percentage'] = int((completed_lessons / total_lessons * 100)) if total_lessons > 0 else 0
            
            # Get list of completed lesson IDs for the template
            context['completed_lesson_ids'] = list(LessonProgress.objects.filter(
                student=user,
                lesson__course=self.object,
                is_completed=True
            ).values_list('lesson_id', flat=True))
            
        return context

class LessonCreateView(LoginRequiredMixin, InstructorRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context

    def form_valid(self, form):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('courses:course_detail', kwargs={'pk': self.kwargs['course_id']})

class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'courses/lesson_detail.html'
    pk_url_kwarg = 'lesson_id'

    def get_queryset(self):
        return super().get_queryset().select_related('course')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.course # Uses selected data
        context['course'] = course
        
        lessons = list(course.lessons.all())
        current_idx = lessons.index(self.object)
        context['previous_lesson'] = lessons[current_idx - 1] if current_idx > 0 else None
        context['next_lesson'] = lessons[current_idx + 1] if current_idx < len(lessons) - 1 else None
        
        return context

class AssignmentCreateView(LoginRequiredMixin, InstructorRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'courses/assignment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson'] = get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])
        return context

    def form_valid(self, form):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])
        form.instance.lesson = lesson
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('courses:lesson_detail', kwargs={'course_id': self.object.lesson.course.pk, 'lesson_id': self.object.lesson.pk})

class AssignmentDetailView(LoginRequiredMixin, DetailView):
    model = Assignment
    template_name = 'courses/assignment_detail.html'
    pk_url_kwarg = 'assignment_id'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('submissions__student')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_instructor:
            context['submissions'] = self.object.submissions.all() # Uses prefetched data
        else:
            context['user_submission'] = self.object.submissions.filter(student=self.request.user).first()
            context['submission_form'] = SubmissionForm()
        return context

    def post(self, request, *args, **kwargs):
        if request.user.is_instructor:
            return redirect(request.path)
        
        self.object = self.get_object()
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = self.object
            submission.student = request.user
            submission.save()
            return redirect(request.path)
        return self.render_to_response(self.get_context_data(submission_form=form))

class UserAssignmentsView(LoginRequiredMixin, ListView):
    template_name = 'courses/user_assignments.html'
    context_object_name = 'assignment_data'

    def get_queryset(self):
        user_pk = self.kwargs.get('user_id')
        if user_pk:
            self.view_user = get_object_or_404(User, pk=user_pk)
        else:
            self.view_user = self.request.user
            
        if self.view_user != self.request.user and not self.request.user.is_instructor:
            return []

        courses = self.view_user.courses_enrolled.all()
        
        # Optimized query using Prefetch to avoid N+1
        submission_prefetch = Prefetch(
            'submissions',
            queryset=Submission.objects.filter(student=self.view_user),
            to_attr='user_submission_list'
        )

        assignments = Assignment.objects.filter(
            lesson__course__in=courses
        ).select_related(
            'lesson__course'
        ).prefetch_related(
            submission_prefetch
        ).order_by('due_date')
        
        # Structure the data as before
        data = []
        for assign in assignments:
            submission = assign.user_submission_list[0] if assign.user_submission_list else None
            data.append({
                'assignment': assign,
                'submission': submission
            })
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_user'] = self.view_user
        return context

from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def toggle_lesson_completion(request, lesson_id):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=403)
        
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    
    if not request.user.courses_enrolled.filter(pk=lesson.course.pk).exists() and not request.user.is_instructor:
         return JsonResponse({'status': 'error', 'message': 'Not enrolled'}, status=403)

    progress, created = LessonProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson
    )
    
    progress.is_completed = not progress.is_completed
    progress.save()
    
    return JsonResponse({
        'status': 'success', 
        'is_completed': progress.is_completed,
        'lesson_id': lesson_id
    })
