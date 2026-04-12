class EloSystem:
    def __init__(self, k: int = 32, initial_rating: float = 1500.0):
        self.k = k
        self.initial_rating = initial_rating

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def update(
        self, winner_rating: float, loser_rating: float, k: int | None = None
    ) -> tuple[float, float]:
        k = k if k is not None else self.k
        expected_w = self.expected_score(winner_rating, loser_rating)
        expected_l = self.expected_score(loser_rating, winner_rating)
        new_winner = winner_rating + k * (1.0 - expected_w)
        new_loser = loser_rating + k * (0.0 - expected_l)
        return new_winner, new_loser
