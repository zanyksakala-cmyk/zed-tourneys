from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import math

# ─── CHOICES ───────────────────────────────────────────────

GAME_CHOICES = [
    ('fortnite', 'Fortnite'),
    ('codm',     'Call of Duty Mobile'),
    ('mk',       'Mortal Kombat'),
    ('fc',       'EA Sports FC'),
    ('apex',     'Apex Legends'),
]

FORMAT_CHOICES = [
    ('single_elim', 'Single Elimination'),
    ('double_elim', 'Double Elimination'),
    ('league',      'League / Round Robin'),
]

STATUS_CHOICES = [
    ('open',      'Open - Registering'),
    ('closed',    'Registration Closed'),
    ('live',      'Live'),
    ('complete',  'Complete'),
]

MATCH_STATUS = [
    ('pending',   'Pending'),
    ('live',      'Live'),
    ('complete',  'Complete'),
    ('bye',       'Bye (auto-advance)'),
]

# ─── TOURNAMENT ────────────────────────────────────────────

class Tournament(models.Model):
    title        = models.CharField(max_length=200)
    game         = models.CharField(max_length=20, choices=GAME_CHOICES)
    game_mode    = models.CharField(max_length=100, blank=True)
    format       = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='single_elim')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    max_players  = models.IntegerField(default=16)
    prize_pool   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prize_currency = models.CharField(max_length=10, default='ZMW')
    description  = models.TextField(blank=True)
    rules        = models.TextField(blank=True)
    discord_link = models.URLField(blank=True)
    best_of      = models.IntegerField(default=3)  # BO3 default
    finals_best_of = models.IntegerField(default=5)
    start_date   = models.DateTimeField()
    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    bracket_generated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.get_game_display()})"

    def player_count(self):
        return self.registrations.count()

    def is_full(self):
        return self.player_count() >= self.max_players

    class Meta:
        ordering = ['-start_date']

# ─── REGISTRATION ──────────────────────────────────────────

class Registration(models.Model):
    tournament   = models.ForeignKey(Tournament, on_delete=models.CASCADE,
                                     related_name='registrations')
    player       = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='registrations')
    seed         = models.IntegerField(null=True, blank=True)
    game_tag     = models.CharField(max_length=80)  # in-game name
    registered_at = models.DateTimeField(auto_now_add=True)
    checked_in   = models.BooleanField(default=False)

    class Meta:
        unique_together = ['tournament', 'player']

    def __str__(self):
        return f"{self.game_tag} → {self.tournament.title}"

# ─── BRACKET ───────────────────────────────────────────────

class Bracket(models.Model):
    tournament   = models.OneToOneField(Tournament, on_delete=models.CASCADE,
                                        related_name='bracket')
    total_rounds = models.IntegerField(default=0)
    size         = models.IntegerField(default=0)  # actual bracket size (power of 2)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bracket: {self.tournament.title}"

# ─── MATCH ─────────────────────────────────────────────────

class Match(models.Model):
    bracket      = models.ForeignKey(Bracket, on_delete=models.CASCADE,
                                     related_name='matches')
    round_number = models.IntegerField()       # 1 = first round
    match_number = models.IntegerField()       # position in round
    player1      = models.ForeignKey(Registration, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='p1_matches')
    player2      = models.ForeignKey(Registration, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='p2_matches')
    winner       = models.ForeignKey(Registration, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='won_matches')
    score_p1     = models.IntegerField(default=0)
    score_p2     = models.IntegerField(default=0)
    best_of      = models.IntegerField(default=3)
    status       = models.CharField(max_length=20, choices=MATCH_STATUS, default='pending')
    notes        = models.TextField(blank=True)
    played_at    = models.DateTimeField(null=True, blank=True)

    # Next match reference — where winner goes
    next_match   = models.ForeignKey('self', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='fed_by')
    next_slot    = models.IntegerField(default=1)  # 1=player1 slot, 2=player2 slot

    class Meta:
        ordering = ['round_number', 'match_number']
        unique_together = ['bracket', 'round_number', 'match_number']

    def __str__(self):
        p1 = self.player1.game_tag if self.player1 else 'TBD'
        p2 = self.player2.game_tag if self.player2 else 'TBD'
        return f"R{self.round_number} M{self.match_number}: {p1} vs {p2}"

    def advance_winner(self):
        """Push winner into next match after result is set."""
        if self.winner and self.next_match:
            if self.next_slot == 1:
                self.next_match.player1 = self.winner
            else:
                self.next_match.player2 = self.winner
            self.next_match.save()

    def set_result(self, winner_reg, score_p1, score_p2):
        """Set result and advance winner. Call from view."""
        self.winner  = winner_reg
        self.score_p1 = score_p1
        self.score_p2 = score_p2
        self.status  = 'complete'
        self.played_at = timezone.now()
        self.save()
        self.advance_winner()