import tensorflow as tf
import numpy as np
import time

from .ops import cov_layer, linear_layer
from .memory import Memory
from .environtment import Environment, State

class Agent(BaseModel):
    def __init__(self, config, sess):
        super(Agent, self).__init__(config)
        self.build_cnn_net(config, 'p_')
        self.build_cnn_net(config, 't_')
        self.build_dqn_net(config, 'p_')
        self.build_dqn_net(config, 't_')
        self.mem = Memory(config.mem_capacity)
        self.env = Environment(config)
        self.action_history = tf.placeholder('bool', [None, config.action_size], 'action_history')
        self.action_status = 0
        self.sess = sess

    def build_cnn_net(self, config, prefix):
        # initializer, rectifier and normalizer
        activation = tf.nn.relu
        w_initializer = tf.truncated_normal_initializer(config.ini_mean, config.ini_stddev)
        b_initializer = tf.constant_initializer(config.bias_starter)

        if target:
            scope_name = 't_CNN'
            cur_w = {}
            cur_w = self.p_cnn_w 
            inp = self.t_inp
            out = self.t_cnn_out
        else:
            scope_name = 'p_CNN'
            self.t_cnn_w = {}
            cur_w = self.t_cnn_w
            inp = self.p_inp
            out = self.p_cnn_out

        with tf.variable_scope(scope_name):
            # Input_Holder
            inp = tf.placeholder(config.imgDType, [None, 224, 224, 3], 'ZFNet_input')
            # CNN_l1(including pooling and normlization)
            l1, cur_w['l1_w'], cur_w['l1_b'] = cov_layer(inp, 96, [7, 7], [2, 2], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, name = 'cnn_conv1')
            pool1 = tf.nn.max_pool(l1, ksize = [1, 3, 3, 1], stride = [1, 2, 2, 1], padding = 'SAME', name = 'pool1')

            # CNN_l2(including pooling and normlization)
            l2, cur_w['l2_w'], cur_w['l2_b'] = cov_layer(pool1, 256, [5, 5], [2, 2], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, name = 'cnn_conv2')
            pool2 = tf.nn.max_pool(l2, ksize = [1, 3, 3, 1], stride = [1, 2, 2, 1], padding = 'SAME', name = 'pool2')
            
            # CNN_l3
            l3, cur_w['l3_w'], cur_w['l3_b'] = cov_layer(pool2, 384, [3, 3], [1, 1], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, name = 'cnn_conv3')

            # CNN_l4
            l4, cur_w['l4_w'], cur_w['l4_b'] = cov_layer(l3, 384, [3, 3], [1, 1], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, name = 'cnn_conv4')

            # CNN_l5
            l5, cur_w['l5_w'], cur_w['l5_b'] = cov_layer(l4, 256, [3, 3], [1, 1], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, name = 'cnn_conv5')
            pool5 = tf.nn.max_pool(l5, ksize = [1, 3, 3, 1], stride = [1, 2, 2, 1], padding = 'SAME', name = 'pool5')

            # CNN_l5 reshape
            l5_flat = tf.reshape(pool5, [config.batch_size, -1], name = 'l5_flat')
            
            # CNN_output
            out, cur_w['output_w'], cur_w['output_b'] = fc_layer(l5_flat, 4096, activation = activation, w_initializer = w_initializer, b_initializer = b_initializer, name = 'output')


    def build_dqn_net(self, config, target):
        # initializer and rectifier
        activation = tf.nn.relu
        w_initializer = tf.truncated_normal_initializer(config.ini_mean, config.ini_stddev)
        b_initializer = tf.constant_initializer(config.bias_start)

        inp_size = config.featureDimension + config.actionDimension
        
        if target:
            name_scope = 't_DQN'
            self.t_dqn_w = {}
            cur_w = self.t_dqn_w
            inp = self.t_cnn_out
            out = self.t_q
        else:
            name_scope = 'p_DQN'
            self.p_dqn_w = {}
            cur_w = self.p_dqn_w
            inp = self.p_cnn_out
            out = self.p_q

        inp = tf.concat(1, [inp, self.action_history], name = name_scope + '_concat')  

        with tf.variable_scope(name_scope):
            # DQN_fc1
            dqn_l1, cur_w['l1_w'], cur_w['l1_b'] = fc_layer(inp, 1024, activation = activation, w_initializer = w_initializer, b_initializer = b_initializer, name = 'dqn_l1')
            
            # DQN_fc2
            dqn_l2, cur_w['l2_w'], cur_w['l2_b'] = fc_layer(dqn_l1, 1024, w_initializer = w_initializer, b_initializer = b_initializer, name = 'dqn_l2')

            # DQN_output
            out, cur_w['output_w'], cur_w['output_b'] = fc_layer(dqn_l2, config.action_size, w_initializer = w_initializer, b_initializer = b_initializer, name = 'dqn_q')
            if not target:
                self.q_action = tf.argmax(out, dimension = 1, name = 'q_action')

        if not target:
            # optimizer
            with tf.variable_scope('dqn_optimizer'):
                self.dqn_gt_q = tf.placeholder('float32', [None], name = 'dqn_gt_q')
                self.action = tf.placeholder('int64', [None], name = 'action')

                action_one_hot = tf.one_hot(self.action, config.action_size, 1.0, 0.0, name = 'action_one_hot')
                q_acted = tf.reduce_sum(self.p_q * action_one_hot, reduction_indices = 1, name = 'q_acted')

                self.dqn_delta = self.dqn_gt_q - q_acted
                self.clipped_delta = tf.clip_by_value(self.delta, self.min_delta, self.max_delta, name = 'clipped_delta')
                self.global_step = tf.Varialbe(0, trainable = False)

                self.dqn_loss = tf.reduce_mean(tf.square(self.clipped_delta), name = 'dqn_loss')
                self.dqn_learning_rate_step = tf.placeholder('int64', None, name = 'learning_rate_step')
                self.dqn_learning_rate_op = tf.maximum(self.learning_rate_minimum,
                        tf.train.exponential_decay(
                            self.dqn_learning_rate_op,
                            self.dqn_learning_rate_step,
                            self.dqn_learning_rate_decay_step,
                            self.dqn_learning_rate_decay,
                            staircase = True))
                self.dqn_optim = tf.train.RMSPropOptimizer(self.learning_rate_op, momentum = config.dqn_momentum, epsilon = config.dqn_epsilon).minimize(self.loss)

    def train(self):
        # DQN initialization
        tf.initialize_all_variables().run()
        self.update_target_net()
        self.ep_rewards = []
        self.update_count = 0
        self.mem.reset()
        self.env.clear()

        start_time = time.time()

        for episode in xrange(config.epi_size):
            # initialize the environment for each episode
            state = self.env.reset()   
            state = State(state.img_id, state.height, state.width)
            for x in xrange(self.mem_capacity):
                self.mem.add(state)
            self.action_status = 0
            
            for stp in xrange(config.max_step):
                # predict
                action = self.predict(env.state)
                # act
                nxt_state, reward, terminal = self.env.act(action)
                # observe
                self.observe(state, action, reward, nxt_state, terminal)

                if terminal:
                    state = self.env.reset()
                    self.action_status = 0
                else:
                    state = nxt_state.copy()
                    self.action_status |= 1 << action

            if episode % self.test_point == 0:
                self.evaluation()

    def predict(self, state):
        if random.random() < self.epsilon:
            action = random.randrange(self.env.action_size)
        else:
            action = self.q_action.eval({self.p_inp : self.crop(state), self.action_history : self.actionArray(1)})
        return action

    def observe(self, state, action, reward, nxt_state, terminal):
        # clip reward
        reward = max(self.min_reward, min(self.max_reward, reward)) 

        self.mem.add(state, action, reward, nxt_state, terminal)
        if self.step < self.learning_start_point:
            return

        # gradient descent
        self.mini_batch_gradient_descent()
        # update target net every C steps
        if self.step % self.update_C:
            self.update_target_net()

    def mini_batch_gradient_descent(self):
        if self.mem.count < self.batch_size:
            return

        s, action, reward, s_nxt, terminal = self.mem.sample(self.batch_Size)

        q_nxt = self.t_q.eval({self.t_inp : self.crop(s_nxt), self.action_history : self.actionArray(self.batch_size)})
        
        terminal = np.array(terminal) + 0.
        max_q_nxt = np.max(q_nxt, axis = 1)
        ground_truth = (1. - terminal) * config.discont * max_q_nxt + reward

        _, q_t, loss = self.sess.run([self.dqn_optim, self.p_q, self.loss]){
                self.dqn_gt_q : ground_truth,
                self.action : action,
                self.p_inp : self.crop(s),
                self.dqn_learning_rate_step: self.step
                self.action_history: self.actionArray(self.batch_size)
                }

        self.update_count += 1

    def actionArray(self, sz):
        arr = np.zeros([sz, self.action_size], dtype = bool)
        act1d = np.empty([self.action_size], dtype = bool)
        for x in xrange(self.action_size):
            if (self.action_status >> x) & 1 == 1:
                act1d[x] = True
            else:
                act1d[x] = False
        return arr + act1d

    def evaluation(self):
        pass 

    def record(self):
        pass
