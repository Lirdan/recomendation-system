import math
import random
import sqlite3

class MultiArmedBandit:
    def __init__(self, arms, alpha=0.75, db_path="C:/Users/skryn/OneDrive/Изображения/универ/диплом № 2/bookstore/books_db.sqlite"):
        self.arms = arms
        self.alpha = alpha
        self.db_path = db_path
        self.counts = {arm: 0 for arm in arms}  # Количество выборов каждого рычага
        self.values = {arm: 0.0 for arm in arms}  # Среднее значение награды для каждого рычага

    def select_arm(self):
        """
        Выбор рычага для тяги с использованием алгоритма UCB1.
        """
        total_counts = sum(self.counts.values())
        if total_counts == 0:
            return random.choice(self.arms)

        log_total_counts = math.log(total_counts)
        ucb_values = {arm: self._calculate_ucb(log_total_counts, arm) for arm in self.arms}
        return max(ucb_values, key=ucb_values.get)

    def _calculate_ucb(self, log_total_counts, arm):
        """
        Вычисление UCB для каждого рычага.
        """
        count = self.counts[arm]
        if count == 0:
            return float('inf')
        value = self.values[arm]
        return value + self.alpha * math.sqrt(log_total_counts / count)

    def update(self, chosen_arm, reward, lambda_val=0.8):
        """
        Обновление значения и счетчика выбранного рычага с использованием экспоненциального затухания.
        """
        self.counts[chosen_arm] += 1
        old_value = self.values[chosen_arm]
        new_value = lambda_val * old_value + (1 - lambda_val) * reward
        self.values[chosen_arm] = new_value
    def update_and_save_weights(self, user_id):
        """
        Сохранение обновленных весов в базе данных.
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
        Загрузка весов пользователя из базы данных.
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('SELECT collaborative_weight, content_weight, genre_weight FROM users WHERE userId = ?', (user_id,))
            weights = cur.fetchone()
            if weights:
                self.counts = {'collaborative': weights[0], 'content': weights[1], 'genre': weights[2]}

    def get_weights(self):
        """
        Получение текущих весов для каждого типа рекомендаций.
        """
        total_counts = sum(self.counts.values())
        if total_counts == 0:
            return {arm: 1 / len(self.arms) for arm in self.arms}
        return {arm: self.counts[arm] / total_counts for arm in self.arms}