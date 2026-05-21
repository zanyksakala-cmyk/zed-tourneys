from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from tournaments.models import Registration, Match


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def player_profile(request, pk):
    profile_user = get_object_or_404(User, pk=pk)
    registrations = Registration.objects.filter(
        player=profile_user
    ).select_related('tournament').order_by('-registered_at')

    wins_count = Match.objects.filter(
        winner__player=profile_user
    ).count()

    return render(request, 'tournaments/player_profile.html', {
        'profile_user': profile_user,
        'registrations': registrations,
        'wins_count': wins_count,
    })