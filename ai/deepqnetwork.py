import random
import json
import os
import keras
import tensorflow as tf

class DeepQNetwork:
    def __init__(self, qnetwork=None, counter=0, agent="off", exploration_rate=1.0, discount=0.9, learning_rate=0.1):
        if agent == "off":
            self.counter = counter
            self.load()
            self.qnetwork = keras.Sequential()
            self.qnetwork.add(keras.layers.Dense(24, input_shape=(5,), activation="relu"))
            self.qnetwork.add(keras.layers.Dense(24, activation="relu"))
            self.qnetwork.add(keras.layers.Dense(4, activation="linear"))
            self.qnetwork.compile(optimiser='adam', loss='mse')
        elif agent == "on":
            self.qnetwork = qnetwork
            self.counter = counter
        else:
            raise ValueError("Invalid agent type. Use 'on' or 'off'.")
        self.exploration_rate = exploration_rate
        self.discount = discount
        self.learning_rate = learning_rate
