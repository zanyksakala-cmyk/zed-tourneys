import math
import random
from .models import Bracket, Match

def next_power_of_2(n):
    """Round up to nearest power of 2 (8, 16, 32...)"""
    return 2 ** math.ceil(math.log2(n)) if n > 1 else 2

def seed_players(players):
    """
    Seed players: 1 vs last, 2 vs second-to-last.
    Returns a list of (p1, p2) tuples for round 1.
    Bye slots are None.
    """
    size  = next_power_of_2(len(players))
    byes  = size - len(players)
    seeded = list(players) + [None] * byes  # pad with byes
    pairs = []
    for i in range(size // 2):
        pairs.append((seeded[i], seeded[size - 1 - i]))
    return pairs, size

def generate_bracket(tournament):
    """
    Main bracket generator. Call this once registrations are closed.
    Creates all Match objects, wires next_match references.
    """
    if tournament.bracket_generated:
        raise ValueError("Bracket already generated for this tournament.")

    regs = list(tournament.registrations.filter(checked_in=True))
    if len(regs) < 2:
        raise ValueError("Need at least 2 checked-in players to generate bracket.")

    # Shuffle for fairness (or use seed field if you want seeded draws)
    random.shuffle(regs)

    pairs, size    = seed_players(regs)
    total_rounds   = int(math.log2(size))
    best_of_finals = tournament.finals_best_of
    best_of_normal = tournament.best_of

    # Create the Bracket record
    bracket = Bracket.objects.create(
        tournament=tournament,
        total_rounds=total_rounds,
        size=size
    )

    # Build ALL matches for all rounds (empty first, fill R1)
    all_matches = {}   # {(round, match_num): Match object}

    for rnd in range(1, total_rounds + 1):
        num_matches = size // (2 ** rnd)
        is_final    = (rnd == total_rounds)
        bo          = best_of_finals if is_final else best_of_normal

        for m in range(1, num_matches + 1):
            match = Match.objects.create(
                bracket=bracket,
                round_number=rnd,
                match_number=m,
                best_of=bo,
                status='pending'
            )
            all_matches[(rnd, m)] = match

    # Wire round 1 players
    for i, (p1, p2) in enumerate(pairs, start=1):
        match = all_matches[(1, i)]
        match.player1 = p1
        match.player2 = p2

        # Auto-advance byes
        if p1 is None and p2 is not None:
            match.winner = p2
            match.status = 'bye'
        elif p2 is None and p1 is not None:
            match.winner = p1
            match.status = 'bye'

        match.save()

    # Wire next_match references for all rounds
    for rnd in range(1, total_rounds):
        num_matches = size // (2 ** rnd)
        for m in range(1, num_matches + 1):
            current    = all_matches[(rnd, m)]
            next_m_num = math.ceil(m / 2)
            next_match = all_matches[(rnd + 1, next_m_num)]
            next_slot  = 1 if m % 2 == 1 else 2

            current.next_match = next_match
            current.next_slot  = next_slot
            current.save()

    # Advance all byes immediately
    for match in all_matches.values():
        if match.status == 'bye' and match.winner:
            match.advance_winner()

    # Mark tournament bracket as generated
    tournament.bracket_generated = True
    tournament.status = 'live'
    tournament.save()

    return bracket

def get_bracket_data(tournament):
    """
    Returns bracket as dict for template rendering.
    Structure: { round_number: [Match, ...], ... }
    """
    try:
        bracket = tournament.bracket
    except Bracket.DoesNotExist:
        return None

    matches = bracket.matches.select_related(
        'player1', 'player2', 'winner'
    ).order_by('round_number', 'match_number')

    rounds = {}
    for match in matches:
        rounds.setdefault(match.round_number, []).append(match)

    return {
        'bracket': bracket,
        'rounds':  rounds,
        'total_rounds': bracket.total_rounds,
    }