from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Thread, Message
from apps.accounts.models import User
from django.db.models import Q

@login_required
def chat_index(request):
    threads = request.user.chat_threads.all().order_by('-updated_at')
    return render(request, 'chat/chat.html', {'threads': threads})

@login_required
def chat_thread(request, thread_id):
    threads = request.user.chat_threads.all().order_by('-updated_at')
    active_thread = get_object_or_404(Thread, pk=thread_id, participants=request.user)
    
    # Mark unread messages from other participants as read
    unread_messages = active_thread.messages.exclude(sender=request.user).exclude(
        read_by=request.user
    )
    for message in unread_messages:
        message.read_by.add(request.user)
    
    return render(request, 'chat/chat.html', {
        'threads': threads,
        'active_thread': active_thread
    })

@login_required
def send_message(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id, participants=request.user)
    if request.method == 'POST':
        content = request.POST.get('content')
        audio_file = request.FILES.get('audio')
        
        if content or audio_file:
            Message.objects.create(
                thread=thread, 
                sender=request.user, 
                content=content if content else '',
                audio_file=audio_file
            )
            thread.save() # Update updated_at
    return redirect('chat_thread', thread_id=thread_id)

@login_required
def start_chat(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        return redirect('chat_index')
    
    # Check for existing thread with exactly these two participants
    # This is a bit complex in Django ORM without a through model custom query, 
    # but we can filter threads where both are participants and count is 2.
    
    threads = Thread.objects.filter(participants=request.user).filter(participants=target_user)
    
    existing_thread = None
    for thread in threads:
        if thread.participants.count() == 2:
            existing_thread = thread
            break
            
    if existing_thread:
        return redirect('chat_thread', thread_id=existing_thread.pk)
    else:
        # Create new thread
        new_thread = Thread.objects.create()
        new_thread.participants.add(request.user, target_user)
        return redirect('chat_thread', thread_id=new_thread.pk)
