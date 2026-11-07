"""Реестр задач"""
from src.tasks import task1_shares, task2_ratings, task4_reviews

TASKS = {
    1: task1_shares.run,
    2: task2_ratings.run,
    4: task4_reviews.run,
}