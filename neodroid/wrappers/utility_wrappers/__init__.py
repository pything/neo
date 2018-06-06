#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from multiprocessing import Pipe, Process

import numpy as np
from baselines.common.atari_wrappers import make_atari, wrap_deepmind

from neodroid.utilities import logger

__author__ = 'cnheider'


def make_env(env_name, rank, seed):
  env = make_atari(env_name)
  env.seed(seed + rank)
  env = wrap_deepmind(env, episode_life=False, clip_rewards=False)
  return env


def worker(remote, parent_remote, env_fn_wrapper):
  parent_remote.close()
  env = env_fn_wrapper.x()
  while True:
    cmd, data = remote.recv()
    if cmd == 'step':
      ob, reward, done, info = env.step(data)
      if done:
        ob = env.reset()
      remote.send((ob, reward, done, info))
    elif cmd == 'reset':
      ob = env.reset()
      remote.send(ob)
    elif cmd == 'reset_task':
      ob = env.reset_task()
      remote.send(ob)
    elif cmd == 'close':
      remote.close()
      break
    elif cmd == 'get_spaces':
      remote.send((env.action_space, env.observation_space))
    elif cmd == 'render':
      env.render()
    else:
      raise NotImplementedError


class CloudpickleWrapper(object):
  """
  Uses cloudpickle to serialize contents (otherwise multiprocessing tries to use pickle)
  """

  def __init__(self, x):
    self.x = x

  def __getstate__(self):
    import cloudpickle
    return cloudpickle.dumps(self.x)

  def __setstate__(self, ob):
    import pickle
    self.x = pickle.loads(ob)



class VecEnv(ABC):

    def __init__(self, num_envs, observation_space, action_space):
        self.num_envs = num_envs
        self.observation_space = observation_space
        self.action_space = action_space

    """
    An abstract asynchronous, vectorized environment.
    """
    @abstractmethod
    def reset(self):
        """
        Reset all the environments and return an array of
        observations.

        If step_async is still doing work, that work will
        be cancelled and step_wait() should not be called
        until step_async() is invoked again.
        """
        pass

    @abstractmethod
    def step_async(self, actions):
        """
        Tell all the environments to start taking a step
        with the given actions.
        Call step_wait() to get the results of the step.

        You should not call this if a step_async run is
        already pending.
        """
        pass

    @abstractmethod
    def step_wait(self):
        """
        Wait for the step taken with step_async().

        Returns (obs, rews, dones, infos):
         - obs: an array of observations
         - rews: an array of rewards
         - dones: an array of "episode done" booleans
         - infos: an array of info objects
        """
        pass

    @abstractmethod
    def close(self):
        """
        Clean up the environments' resources.
        """
        pass

    def step(self, actions):
        self.step_async(actions)
        return self.step_wait()

    def render(self):
        logger.warn('Render not defined for %s'%self)

class VecEnvWrapper(VecEnv):
    def __init__(self, venv, observation_space=None, action_space=None):
        self.venv = venv
        VecEnv.__init__(self,
            num_envs=venv.num_envs,
            observation_space=observation_space or venv.observation_space,
            action_space=action_space or venv.action_space)

    def step_async(self, actions):
        self.venv.step_async(actions)

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def step_wait(self):
        pass

    def close(self):
        return self.venv.close()

    def render(self):
        self.venv.render()


class RenderSubprocVecEnv(VecEnv):
  def __init__(self, env_fns, render_interval):
    """ Minor addition to SubprocVecEnv, automatically renders environments
    envs: list of gym environments to run in subprocesses
    """
    self.closed = False
    nenvs = len(env_fns)
    self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(nenvs)])
    self.ps = [Process(target=worker, args=(work_remote, remote, CloudpickleWrapper(env_fn)))
               for (work_remote, remote, env_fn) in zip(self.work_remotes, self.remotes, env_fns)]
    for p in self.ps:
      p.daemon = True  # if the main process crashes, we should not cause things to hang
      p.start()
    for remote in self.work_remotes:
      remote.close()

    self.remotes[0].send(('get_spaces', None))
    self.action_space, self.observation_space = self.remotes[0].recv()

    self.render_interval = render_interval
    self.render_timer = 0

  def step(self, actions):
    for remote, action in zip(self.remotes, actions):
      remote.send(('step', action))
    results = [remote.recv() for remote in self.remotes]
    obs, rews, dones, infos = zip(*results)

    self.render_timer += 1
    if self.render_timer == self.render_interval:
      for remote in self.remotes:
        remote.send(('render', None))
      self.render_timer = 0

    return np.stack(obs), np.stack(rews), np.stack(dones), infos

  def reset(self):
    for remote in self.remotes:
      remote.send(('reset', None))
    return np.stack([remote.recv() for remote in self.remotes])

  def reset_task(self):
    for remote in self.remotes:
      remote.send(('reset_task', None))
    return np.stack([remote.recv() for remote in self.remotes])

  def close(self):
    if self.closed:
      return

    for remote in self.remotes:
      remote.send(('close', None))
    for p in self.ps:
      p.join()
    self.closed = True

  @property
  def num_envs(self):
    return len(self.remotes)