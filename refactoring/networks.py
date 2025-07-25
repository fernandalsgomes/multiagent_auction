import os
import numpy as np
import torch as T
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

class Network(nn.Module):
    """
    Provides common functionality for saving and loading model checkpoints.
    """
    def __init__(self, name: str, chkpt_dir: str) -> None:
        """
        Initialize the network with name and checkpoint directory.
        
        Args:
            name (str): The name of the network, used as part of the checkpoint filename.
            chkpt_dir (str): Directory path where checkpoint files will be saved.
        """
        super(Network, self).__init__()
        self.checkpoint_file = os.path.join(chkpt_dir, name)
        self.device = T.device('cuda:0' if T.cuda.is_available() else 'cpu')
        self.to(self.device)
        self.type = ''

    def save_checkpoint(self, name: str) -> None:
        """
        Save the current state of the model to a checkpoint file.
        
        Args:
            name (str): An identifier appended to the checkpoint filename.
        """
        T.save(self.state_dict(), f'{self.checkpoint_file}_{name}')

    def load_checkpoint(self, name: str) -> None:
        """
        Load a model's state from a previously saved checkpoint file.
        
        Args:
            name (str): The identifier of the checkpoint to load.
        """
        print(f'... Loading {self.type} model for {name} ...')
        self.load_state_dict(T.load(f'{self.checkpoint_file}_{name}', map_location=self.device))

class CriticNetwork(Network):
    """
    Critic network implementation.
    This network evaluates state-action pairs and estimates Q-values.
    """
    def __init__(self, 
                 beta: float, 
                 input_dims: int, 
                 fc1_dims: int, 
                 fc2_dims: int, 
                 n_actions: int, 
                 name: str, 
                 n_agents: int = 2, 
                 chkpt_dir: str ='models/critic', 
                 flag: bool = False, 
                 extra: int = 0) -> None:
        """
        Initialize the critic network.
        
        Args:
            beta (float): Learning rate for the Adam optimizer.
            input_dims (int): Dimensionality of the input state space.
            fc1_dims (int): Number of neurons in the first fully connected layer.
            fc2_dims (int): Number of neurons in the second fully connected layer.
            n_actions (int): Dimensionality of the action space.
            name (str): Name identifier for the network.
            n_agents (int, optional): Number of agents in the environment. Defaults is 2.
            chkpt_dir (str, optional): Directory for checkpoint files. Defaults is 'models/critic'.
            flag (bool, optional): Flag to modify input shape calculation. Defaults is False.
            extra (int, optional): Additional value to adjust input shape when flag is True. Defaults is 0.
        """
        super(CriticNetwork, self).__init__(name, chkpt_dir)
        self.type = 'critic'
        shape_of_input = n_agents*(input_dims + n_actions)
        if flag: shape_of_input = (n_agents + extra)*(input_dims + n_actions)

        self.fc1 = nn.Linear(shape_of_input, fc1_dims)
        self.fc2 = nn.Linear(fc1_dims, fc2_dims)
        self.q = nn.Linear(fc2_dims, 1)
        self.optimizer = optim.Adam(self.parameters(), lr=beta)

    def forward(self, state: T.Tensor, action: T.Tensor, others_states: T.Tensor, others_actions: T.Tensor) -> T.Tensor:
        """
        Perform the forward pass through the critic network.
        
        Args:
            state (T.Tensor): The current state of the agent.
            action (T.Tensor): The action taken by the agent.
            others_states (T.Tensor): States of other agents in the environment.
            others_actions (T.Tensor): Actions taken by other agents.
            
        Returns:
            T.Tensor: The estimated Q-value for the given state-action combination.
        """
        concatenated_inputs  = T.cat([state, action, others_states, others_actions], dim=1)
        x = F.relu(self.fc1(concatenated_inputs))
        x = F.relu(self.fc2(x))
        q_value = self.q(x)
        return q_value

class ActorNetwork(Network):
    """
    Actor network implementation.
    This network maps states to actions according to the current policy.
    """
    def __init__(self, 
                 alpha: float, 
                 input_dims: int, 
                 fc1_dims: int, 
                 fc2_dims: int, 
                 n_actions: int, 
                 name: str, 
                 n_agents: int = 2, 
                 chkpt_dir: str = 'models/actor') -> None:
        """
        Initialize the actor network.
        
        Args:
            alpha (float): Learning rate for the Adam optimizer.
            input_dims (int): Dimensionality of the input state space.
            fc1_dims (int): Number of neurons in the first fully connected layer.
            fc2_dims (int): Number of neurons in the second fully connected layer.
            n_actions (int): Dimensionality of the action space.
            name (str): Name identifier for the network.
            n_agents (int, optional): Number of agents in the environment. Defaults is 2.
            chkpt_dir (str, optional): Directory for checkpoint files. Defaults is 'models/actor'.
        """
        super(ActorNetwork, self).__init__(name, chkpt_dir)
        self.type = 'actor'
        self.n_agents = n_agents

        self.fc1 = nn.Linear(input_dims, fc1_dims)        
        self.fc2 = nn.Linear(fc1_dims, fc2_dims)
        self.mu = nn.Linear(fc2_dims, n_actions)

        self._init_layer(self.fc1)
        self._init_layer(self.fc2)
        self._init_layer(self.mu, scale=0.003)
        self.optimizer = optim.Adam(self.parameters(), lr=alpha)

    def _init_layer(self, layer: nn.Linear, scale: float = 1.0) -> None:
        """
        Initialize the weights and biases of the network layers.
        Uses uniform distribution with calculated scaling factors based on
        the size of each layer.
        """
        fan_in = layer.weight.data.size()[0]
        limit = scale / np.sqrt(fan_in)
        T.nn.init.uniform_(layer.weight.data, -limit, limit)
        T.nn.init.uniform_(layer.bias.data, -limit, limit)

    def forward(self, state: T.Tensor) -> T.Tensor:
        """
        Perform the forward pass through the actor network.
        
        Args:
            state (T.Tensor): The current state of the agent.
            
        Returns:
            T.Tensor: The action to be taken, with values normalized between 0 and 1.
        """
        x = F.relu(self.fc1(state))
        x = F.relu(self.fc2(x))
        return T.sigmoid(self.mu(x))