from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Tournament, Registration, Match
from .bracket_engine import generate_bracket, get_bracket_data

def home(request):
    tournaments = Tournament.objects.filter(status__in=['open', 'live'])[:6]
    return render(request, 'tournaments/home.html', {'tournaments': tournaments})

def tournament_list(request):
    game   = request.GET.get('game')
    status = request.GET.get('status')
    qs = Tournament.objects.all()
    if game:   qs = qs.filter(game=game)
    if status: qs = qs.filter(status=status)
    return render(request, 'tournaments/tournament_list.html', {'tournaments': qs})

def tournament_detail(request, pk):
    t = get_object_or_404(Tournament, pk=pk)
    user_registered = False
    if request.user.is_authenticated:
        user_registered = t.registrations.filter(player=request.user).exists()
    return render(request, 'tournaments/tournament_detail.html', {
        'tournament': t,
        'user_registered': user_registered,
    })

@login_required
def join_tournament(request, pk):
    t = get_object_or_404(Tournament, pk=pk)
    if t.is_full():
        messages.error(request, "Tournament is full.")
    elif t.status != 'open':
        messages.error(request, "Registration is closed.")
    else:
        game_tag = request.POST.get('game_tag', request.user.username)
        reg, created = Registration.objects.get_or_create(
            tournament=t, player=request.user,
            defaults={'game_tag': game_tag}
        )
        if created:
            messages.success(request, f"You joined {t.title}! Game tag: {game_tag}")
        else:
            messages.info(request, "You are already registered.")
    return redirect('tournament_detail', pk=pk)

def bracket_view(request, pk):
    t    = get_object_or_404(Tournament, pk=pk)
    data = get_bracket_data(t)
    return render(request, 'tournaments/bracket_view.html', {
        'tournament': t, 'data': data
    })

@login_required
def report_result(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    if request.method == 'POST':
        winner_id = request.POST.get('winner')
        score_p1  = int(request.POST.get('score_p1', 0))
        score_p2  = int(request.POST.get('score_p2', 0))
        winner    = Registration.objects.get(pk=winner_id)
        match.set_result(winner, score_p1, score_p2)
        messages.success(request, "Result saved and bracket updated!")
        return redirect('bracket_view', pk=match.bracket.tournament.pk)
    return render(request, 'tournaments/report_result.html', {'match': match})
    