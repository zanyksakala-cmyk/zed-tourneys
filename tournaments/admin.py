from django.contrib import admin
from django.contrib import messages
from .models import Tournament, Registration, Bracket, Match
from .bracket_engine import generate_bracket

class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0
    fields = ['player', 'game_tag', 'seed', 'checked_in']

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display  = ['title', 'game', 'status', 'player_count',
                     'max_players', 'prize_pool', 'start_date']
    list_filter   = ['game', 'status']
    search_fields = ['title']
    inlines       = [RegistrationInline]
    actions       = ['action_generate_bracket', 'action_close_registration']

    def action_generate_bracket(self, request, queryset):
        """Admin action: generate bracket for selected tournaments."""
        for t in queryset:
            try:
                generate_bracket(t)
                self.message_user(request,
                    f"✓ Bracket generated for {t.title}", messages.SUCCESS)
            except Exception as e:
                self.message_user(request,
                    f"✗ Error: {t.title} — {e}", messages.ERROR)
    action_generate_bracket.short_description = "⚡ Generate bracket"

    def action_close_registration(self, request, queryset):
        queryset.update(status='closed')
        self.message_user(request, "Registration closed.", messages.SUCCESS)
    action_close_registration.short_description = "🔒 Close registration"

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'status', 'score_p1', 'score_p2', 'winner']
    list_filter   = ['status', 'bracket__tournament']
    raw_id_fields = ['player1', 'player2', 'winner']

admin.site.register(Bracket)
admin.site.register(Registration)