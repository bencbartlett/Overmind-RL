import torch
import torch.nn as nn


class SimplePolicy(nn.Module):

    def __init__(self, env, H = 20):
        super().__init__()
        self.state_space = env.observation_space.shape[0]
        self.action_space = env.action_space.n
        in_dim = 4  # two set of (x, y) coords
        out_dim = 8  # can move in 8 directions
        self.linear1 = torch.nn.Linear(in_dim, H)
        self.linear2 = torch.nn.Linear(H, out_dim)

    def forward(self, x):
        """Returns a size-8 vector of one-hot probabilities to move in whichever direction"""
        out = self.linear1(x)
        out = nn.ReLU()(out)
        out = self.linear2(out)
        out = nn.Softmax(out)
        return out


