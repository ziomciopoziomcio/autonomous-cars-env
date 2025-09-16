import random
import json
import os
import keras
import tensorflow as tf

def state_correction(state):
    distances_to_walls = state[0]
    distances_to_cars = state[1]
    compass = state[3][0]
    state_np = np.concatenate([
        np.array(distances_to_walls, dtype=np.float32).flatten(),
        np.array(distances_to_cars, dtype=np.float32).flatten(),
        np.array(compass, dtype=np.float32)
    ])

    state_tensor = tf.convert_to_tensor(state_np, dtype=tf.float32)
    return state_tensor
    

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

    def save(self):
        file_path = os.path.join(os.path.dirname(__file__), "model_deep_q_network.keras")
        self.qnetwork.save(file_path)

        file_path = os.path.join(os.path.dirname(__file__), "counter_deep_q_network.json")
        with open(file_path, 'w') as f:
            json.dump({'counter': self.counter}, f)

    def load(self):
        model_path = os.path.join(os.path.dirname(__file__), "model_deep_q_network.keras")
        counter_path = os.path.join(os.path.dirname(__file__), "counter_deep_q_network.json")

        if os.path.exists(model_path):
            self.qnetwork = keras.models.load_model(model_path)
        else:
            self.qnetwork = keras.Sequential()
            self.qnetwork.add(keras.layers.Dense(24, input_shape=(17,), activation='relu'))
            self.qnetwork.add(keras.layers.Dense(24, activation='relu'))
            self.qnetwork.add(keras.layers.Dense(4, activation='linear'))
            self.qnetwork.compile(optimizer='adam', loss='mse')

        if os.path.exists(counter_path):
            with open(counter_path, 'r') as f:
                data = json.load(f)
                self.counter = data.get('counter', 0)
        else:
            self.counter = 0

