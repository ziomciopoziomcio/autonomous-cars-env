import json
import os
import sys

import keras
import tensorflow as tf
import numpy as np

from game import GameEngine
import time

class Learning_agent:
    def __init__(self):
        self.counter = None
        self.qnetwork = None
        self.endless_mode = None
        self.endless_mode_query()
        if not self.endless_mode:
            self.beetween_saves = 0
            self.saves_value = 0
            self.saves_parameters()
        self.load()
        if self.endless_mode:
            self.endless_mode_func()
        else:
            self.regular_mode_func()

    def endless_mode_func(self):
        while True:
            for _ in range(200):
                self.qnetwork, self.counter = GameEngine.run_game(self.qnetwork, self.counter, agent="on")
            self.save()

    def regular_mode_func(self):
        for _ in range(self.saves_value):
            for __ in range(self.beetween_saves):
                self.qnetwork, self.counter = GameEngine.run_game(self.qnetwork, self.counter, agent="on")
            self.save()

    def saves_parameters(self):
        while True:
            try:
                saves_value = int(input("Enter after how many saves you want to save the model (minimum 1): "))
                if saves_value < 1:
                    print("Value must be at least 1.")
                else:
                    self.saves_value = saves_value
                    break
            except ValueError:
                print("Invalid input. Please enter an integer.")
        while True:
            try:
                beetween_saves = int(input("Enter how many games you want to play between saves (minimum 1): "))
                if beetween_saves < 1:
                    print("Value must be at least 1.")
                else:
                    self.beetween_saves = beetween_saves
                    break
            except ValueError:
                print("Invalid input. Please enter an integer.")


    def endless_mode_query(self):
        endless_mode = None
        while endless_mode is None:
            question = input("Do you want to run in endless mode? (y/n): ").strip().lower()
            if question == 'y':
                endless_mode = True
            elif question == 'n':
                endless_mode = False
            else:
                print("Invalid input.")
        self.endless_mode = endless_mode



