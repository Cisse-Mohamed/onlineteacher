from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from django.db.models import Prefetch
from apps.courses.models import Course, Assignment, Submission
from apps.chat.models import Message
from apps.quiz.models import QuizSubmission
from apps.videoconference.models import VideoSession
from django.http import JsonResponse

@login_required
def dashboard(request):
    user = request.user
    today = timezone.now()

    if user.is_instructor:
        courses = Course.objects.filter(instructors=user)
    else:
        courses = user.courses_enrolled.all()
    active_courses_count = courses.count()

    # 2. Pending Assignments (Context dependent)
    if user.is_instructor:
        # Ungraded submissions for instructor's courses
        pending_assignments_count = Submission.objects.filter(
            assignment__lesson__course__instructors=user,
            grade__isnull=True
        ).count()
        pending_label = "Ungraded Submissions"
    else:
        # Assignments due in future not yet submitted by student
        pending_assignments_count = Assignment.objects.filter(
            lesson__course__in=courses,
            due_date__gte=today
        ).exclude(
            submissions__student=user
        ).count()
        pending_label = "Pending Assignments"

    # 3. Unread Messages (FIXED: Using new read receipt model)
    unread_messages_count = Message.objects.filter(
        thread__participants=user
    ).exclude(
        sender=user
    ).exclude(
        read_receipts__user=user
    ).count()

    # 4. Learning Analytics (Quiz Performance) (FIXED: N+1 problem)
    recent_quizzes = QuizSubmission.objects.filter(
        student=user
    ).select_related('quiz').order_by('-start_time')[:5]
    
    quiz_labels = [q.quiz.title for q in recent_quizzes] # No extra queries
    quiz_scores = []
    for q in recent_quizzes:
        if q.total_questions > 0:
            # Here it was score / total_questions, now it should be total_score
            percentage = (q.total_score / q.total_questions) * 100
            quiz_scores.append(round(percentage))
        else:
            quiz_scores.append(0)

    context = {
        'active_courses_count': active_courses_count,
        'pending_assignments_count': pending_assignments_count,
        'pending_label': pending_label,
        'unread_messages_count': unread_messages_count,
        'quiz_labels': quiz_labels,
        'quiz_scores': quiz_scores,
    }

    return render(request, 'dashboard/dashboard.html', context)

@login_required
def calendar_view(request):
    return render(request, 'dashboard/calendar.html')

@login_required
def calendar_events_api(request):
    user = request.user
    events = []
    
    if user.is_instructor:
        courses = Course.objects.filter(instructors=user)
    else:
        courses = user.courses_enrolled.all()
        
    # 1. Assignments (Optimized query and using reverse())
    assignments = Assignment.objects.filter(lesson__course__in=courses).select_related('lesson__course')
    for assignment in assignments:
        events.append({
            'title': f"Deadline: {assignment.title}",
            'start': assignment.due_date.isoformat(),
            'url': reverse('courses:assignment_detail', kwargs={'pk': assignment.lesson.course.pk, 'assignment_id': assignment.pk}),
            'backgroundColor': '#ef4444', # Red
            'borderColor': '#ef4444'
        })
        
    # 2. Video Sessions (Optimized query)
    sessions = VideoSession.objects.filter(course__in=courses).select_related('course')
    for session in sessions:
        events.append({
            'title': f"Live: {session.title}",
            'start': session.start_time.isoformat(),
            'end': session.end_time.isoformat(),
            'url': session.meeting_url or '#',
            'backgroundColor': '#3b82f6', # Blue
            'borderColor': '#3b82f6'
        })
        
    return JsonResponse(events, safe=False)
