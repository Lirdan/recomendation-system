import math
import random
import sqlite3

class MultiArmedBandit:
    """
    Multi-Armed Bandit algorithm using UCB1 strategy.
    Each 'arm' corresponds to a recommendation strategy (e.g. 'content', 'collaborative', 'genre').
    Dynamically updates the weight of each strategy based on user feedback.
    """

    def __init__(self, arms, alpha=0.75, db_path=None):
        """
        Initialize the bandit model.

        Parameters:
        - arms (list): List of strategy names (e.g., ['content', 'collaborative', 'genre']).
        - alpha (float): Confidence parameter for UCB1.
        - db_path (str): Path to SQLite database. If not specified, defaults to books_db.sqlite in the project root.
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "books_db.sqlite")
        self.db_path = db_path
        self.arms = arms
        self.alpha = alpha
        self.counts = {arm: 0 for arm in arms}
        self.values = {arm: 0.0 for arm in arms}

    def select_arm(self):
       """
        Select a strategy (arm) to use, based on the UCB1 algorithm.

        Returns:
            str: The name of the strategy with the highest UCB1 score.
            If no strategy has been selected yet, chooses randomly.
        """
        total_counts = sum(self.counts.values())
        if total_counts == 0:
        # Exploration: choose randomly if nothing tried yet
            return random.choice(self.arms)
        
        log_total_counts = math.log(total_counts)
        ucb_values = {arm: self._calculate_ucb(log_total_counts, arm) for arm in self.arms}
        # Exploitation: select the strategy with the highest UCB score
        return max(ucb_values, key=ucb_values.get)

    def _calculate_ucb(self, log_total_counts, arm):
        """
        Calculate the UCB1 score for the given strategy.

        Parameters:
            log_total_counts (float): Natural logarithm of total selection count.
            arm (str): Name of the strategy.

        Returns:
            float: UCB score. If arm has not been tried, returns infinity (forces exploration).
        """
        count = self.counts[arm]
        if count == 0:
            return float('inf')
        value = self.values[arm]
        return value + self.alpha * math.sqrt(log_total_counts / count)

    def update(self, chosen_arm, reward, lambda_val=0.8):
        """
        Update the average reward of the selected strategy after user interaction.

        Parameters:
            chosen_arm (str): The strategy that was used.
            reward (float): Reward value (1.0 if user purchased, 0.0 if not).
            lambda_val (float): Decay factor for exponential moving average (default: 0.8).
        """
        self.counts[chosen_arm] += 1
        old_value = self.values[chosen_arm]
        # Exponential moving average update: New value = λ * old + (1 - λ) * reward
        new_value = lambda_val * old_value + (1 - lambda_val) * reward
        self.values[chosen_arm] = new_value
    def update_and_save_weights(self, user_id):
       """
        Save updated strategy weights back to the database for the user.

        Parameters:
            user_id (int): User identifier.
        """
        new_weights = self.get_weights()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE users
                SET collaborative_weight = ?, content_weight = ?, genre_weight = ?
                WHERE userId = ?;
            ''', (new_weights['collaborative'], new_weights['content'], new_weights['genre'], user_id))

    def load_user_weights_from_db(self, user_id):
        """
        Load previously saved weights for a user from the database.

        Parameters:
            user_id (int): User identifier.
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('SELECT collaborative_weight, content_weight, genre_weight FROM users WHERE userId = ?', (user_id,))
            weights = cur.fetchone()
            if weights:
                # Multiply weights by 100 to convert to pseudo-counts for internal usage
                self.counts = {'collaborative': weights[0], 'content': weights[1], 'genre': weights[2]}

    def get_weights(self):
        """
        Calculate normalized weights for each strategy (arm) based on selection counts.

        Returns:
            dict: {strategy_name: weight}
        """
        total_counts = sum(self.counts.values())
        if total_counts == 0:
            # If no data, assign equal weights
            return {arm: 1 / len(self.arms) for arm in self.arms}
        return {arm: self.counts[arm] / total_counts for arm in self.arms}
