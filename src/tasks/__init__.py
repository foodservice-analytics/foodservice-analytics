"""Реестр задач"""
from src.tasks import task1_shares, task2_ratings, task3_dynamics, task4_reviews, task5_survival

TASKS = {
    1: task1_shares.run,
    2: task2_ratings.run,
    3: task3_dynamics.run,
    4: task4_reviews.run,
    5: task5_survival.run,
}