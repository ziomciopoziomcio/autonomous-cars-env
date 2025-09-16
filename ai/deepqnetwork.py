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
            self.qnetwork.add(keras.layers.Dense(24, input_shape(17,), activation='relu'))
            self.qnetwork.add(keras.layers.Dense(24, activation='relu'))
            self.qnetwork.add(keras.layers.Dense(4, activation='linear'))
            self.qnetwork.compile(optimizer='adam', loss='mse')
        elif agent == "on":
            self.qnetwork = qnetwork
            self.counter = counter
        else:
            raise ValueError("Invalid agent type. Use 'on' or 'off'.")
        self.exploration_rate = exploration_rate
        self.discount = discount
        self.learning_rate = learning_rate

    def update(self, state, action, next_state, reward):
        state = state_correction(state)
        next_state = state_correction(next_state)
        result = self.qnetwork(state)
        next_result = self.qnetwork(next_state)
        target = tf.identity(result)
        max_next_q = tf.reduce_max(next_result[0])
        updated_value = reward + self.discount * max_next_q
        target = tf.tensor_scatter_nd_update(
            target,
            indices=[[0, action]],
            updates=[target[0, action] + self.learning_rate * (updated_value - target[0, action])]
        )
        self.qnetwork.fit(state, target, epochs=1, verbose=0)

    def get_action(self, state):
        state = state_correction(state)
        p = random.random()
        if p < self.exploration_rate:
            return random.randint(0, 3)
        else:
            result = self.qnetwork(state)
            index = tf.argmax(result[0])
            return int(index)

