import time
import sys

import gym
import numpy as np
from gym import spaces

from control import Car, Environment, walls

INITIAL_POS = (100, 30)
MAX_FRAMES = 10000


class DriveEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, discrete_actions=True):
        super(DriveEnv, self).__init__()
        self.env = Environment()
        self.discrete_actions = discrete_actions

        # orientation, acceleration
        if self.discrete_actions:
            self.action_space = spaces.Discrete(4)
        else:
            self.action_space = spaces.Box(
                low=np.array([-10, -1]), high=np.array([+10, +1]))

        self.reset()
        self.render()

    def reset(self):
        car = Car(INITIAL_POS)
        self.env.reset(car, walls)
        self.observation_space = self.env.car.observe(walls)
        return self.observation_space

    def step(self, action):
        if self.discrete_actions:
            if action==0:
                action = (0,0.5)
            elif action==1:
                action = (0,-0.5)
            elif action==2:
                action = (10,0)
            elif action==3:
                action = (-10,0)
            elif action==4:
                action = (0,0)
            else:
                sys.exit('FATAL ERROR')
        else:
            angle, accel = action
        self.env.loop(action)
        reward = self.env.car.reward
        obs = self.env.car.observe(walls)
        done = self.env.car.age > MAX_FRAMES or self.env.car.reward < -1000
        return obs, reward, done, {}

    def render(self, mode="human", close=False):
        self.env.render()

    def close(self):
        self.env.close()


if __name__ == '__main__':
    env = DriveEnv()
    

    observation = env.reset()
    for i in range(1000):
        env.render()
        action = env.action_space.sample()
        observation, reward, done, info = env.step(action)

        if done:
            observation = env.reset()
        if i % 10 == 0:
            print(i)
            print(env.env.car.reward)
    env.close()
