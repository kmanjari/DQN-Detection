import tensorflow as tf
import numpy as np
import time
import random

from .ops import cov_layer, fc_layer
from .memory import Memory
from .environtment import Environment, State
from .base import BaseModel
from config import Config
from scipy.misc import imresize

class Agent(BaseModel):
    def __init__(self, config, sess):
        """Agent initialization
            
            initialize the agent, including mem, env, action_history, action_status, session

        """
        super(Agent, self).__init__(config)
        # self.build_cnn_net(False)
        # self.build_cnn_net(True)
        self.build_vgg()
        self.action_history = tf.placeholder('float32', [None, config.action_size], 'action_history')
        self.loss_logger = None
        self.action_logger = None
        self.build_dqn_net(False)
        self.build_dqn_net(True)
        self.mem = Memory(config.mem_capacity)
        self.env = Environment(config, sess)
        self.action_status = np.zeros(config.act_his_len, dtype = np.uint8) 
        self.action_his_code = 0
        self.sess = sess

    def build_vgg(self):
        with open(self.pretrained_model, mode = 'rb') as f:
            model = f.read()

        graph_def = tf.GraphDef()
        graph_def.ParseFromString(model)


        self.img_inp = tf.placeholder('float32', [None, 224, 224, 3])
        tf.import_graph_def(graph_def, input_map = {'images': self.img_inp})

        self.vgg_output = tf.get_default_graph().get_tensor_by_name('import/Relu_1:0')

    # def build_cnn_net(self, target):
    #     """build cnn_net part

    #     build the 5 conv layers cnn to extract features.

    #     """
    #     # initializer, rectifier and normalizer
    #     activation = tf.nn.relu
    #     w_initializer = tf.truncated_normal_initializer(self.ini_mean, self.ini_stddev)
    #     b_initializer = tf.constant_initializer(self.bias_starter)

        
    #     if target:
    #         scope_name = 't_CNN'
    #         self.t_cnn_w = {}
    #         cur_w = self.t_cnn_w 
    #         self.t_inp = tf.placeholder('float32', [None, 224, 224, 3], name = 't_inp')
    #         inp = self.t_inp
    #     else:
    #         scope_name = 'p_CNN'
    #         self.p_cnn_w = {}
    #         cur_w = self.p_cnn_w
    #         self.p_inp = tf.placeholder('float32', [None, 224, 224, 3], name = 'p_inp')
    #         inp = self.p_inp


    #     with tf.variable_scope(scope_name):
    #         # CNN_l1(including pooling and normlization)
    #         l1, cur_w['l1_w'], cur_w['l1_b'] = cov_layer(inp, 96, [7, 7], [2, 2], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, padding = 'VALID', name = 'cnn_conv1')
    #         pool1 = tf.nn.max_pool(l1, ksize = [1, 3, 3, 1], strides = [1, 2, 2, 1], padding = 'VALID', name = 'pool1')

    #         # CNN_l2(including pooling and normlization)
    #         l2, cur_w['l2_w'], cur_w['l2_b'] = cov_layer(pool1, 256, [5, 5], [2, 2], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, padding = 'VALID', name = 'cnn_conv2')
    #         pool2 = tf.nn.max_pool(l2, ksize = [1, 3, 3, 1], strides = [1, 2, 2, 1], padding = 'VALID', name = 'pool2')
            
    #         # CNN_l3
    #         l3, cur_w['l3_w'], cur_w['l3_b'] = cov_layer(pool2, 384, [3, 3], [1, 1], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, padding = 'VALID', name = 'cnn_conv3')

    #         # CNN_l4
    #         l4, cur_w['l4_w'], cur_w['l4_b'] = cov_layer(l3, 384, [3, 3], [1, 1], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, padding = 'VALID', name = 'cnn_conv4')

    #         # CNN_l5
    #         l5, cur_w['l5_w'], cur_w['l5_b'] = cov_layer(l4, 256, [3, 3], [1, 1], w_initializer = w_initializer, b_initializer = b_initializer, activation = activation, padding = 'VALID', name = 'cnn_conv5')
    #         pool5 = tf.nn.max_pool(l5, ksize = [1, 3, 3, 1], strides = [1, 2, 2, 1], padding = 'VALID', name = 'pool5')

    #         # CNN_l5 reshape
    #         shape = pool5.get_shape().as_list()
    #         l5_flat = tf.reshape(pool5, [-1, reduce(lambda x, y: x * y, shape[1:])], name = 'l5_flat')
            
    #         # CNN_output
    #         out, cur_w['output_w'], cur_w['output_b'] = fc_layer(l5_flat, 4096, activation = activation, w_initializer = w_initializer, b_initializer = b_initializer, name = 'output')

    #         if target:
    #             self.t_cnn_out = out
    #         else:
    #             self.p_cnn_out = out

    #     if target:
    #         with tf.variable_scope('cnn_transfer'):
    #             self.cnn_assign_inp = {}
    #             self.cnn_assign_op = {}

    #             for key in self.p_cnn_w.keys():
    #                 self.cnn_assign_inp[key] = tf.placeholder('float32', self.p_cnn_w[key].get_shape().as_list(), name = key)
    #                 self.cnn_assign_op[key] = self.t_cnn_w[key].assign(self.cnn_assign_inp[key])


    def build_dqn_net(self, target):
        """build dqn part

        build the 2 fc layers dqn to q_function.

        """
        # initializer and rectifier
        activation = tf.nn.relu
        w_initializer = tf.truncated_normal_initializer(self.ini_mean, self.ini_stddev)
        b_initializer = tf.constant_initializer(self.bias_starter)

        # inp_size = config.featureDimension + config.actionDimension
        
        if target:
            name_scope = 't_DQN'
            self.t_dqn_w = {}
            cur_w = self.t_dqn_w
            inp = self.vgg_output
        else:
            name_scope = 'p_DQN'
            self.p_dqn_w = {}
            cur_w = self.p_dqn_w
            self.keep_prob = tf.placeholder(tf.float32)
            inp = self.vgg_output

        inp = tf.concat(1, [inp, self.action_history], name = name_scope + '_concat')  
        if not target:
            inp = tf.nn.dropout(inp, self.keep_prob)

        with tf.variable_scope(name_scope):
            # dqn_fc1
            l1, cur_w['l1_w'], cur_w['l1_b'] = fc_layer(inp, 1024, activation = activation, w_initializer = w_initializer, b_initializer = b_initializer, name = 'dqn_l1')
            if not target:
                l1 = tf.nn.dropout(l1, self.keep_prob) 

            # DQN_fc2
            l2, cur_w['l2_w'], cur_w['l2_b'] = fc_layer(l1, 1024, activation = activation, w_initializer = w_initializer, b_initializer = b_initializer, name = 'dqn_l2')
            if not target:
                l2 = tf.nn.dropout(l2, self.keep_prob) 

            # DQN_output
            out, cur_w['output_w'], cur_w['output_b'] = fc_layer(l2, self.action_size, w_initializer = w_initializer, b_initializer = b_initializer, name = 'dqn_q')
        
            if target:
                self.t_q = out
            else:
                self.p_q = out

            if not target:
                self.q_action = tf.argmax(out, dimension = 1, name = 'q_action')

        if not target:
            # optimizer
            with tf.variable_scope('dqn_optimizer'):
                self.dqn_gt_q = tf.placeholder('float32', [None], name = 'dqn_gt_q')
                self.action = tf.placeholder('int64', [None], name = 'action')

                action_one_hot = tf.one_hot(self.action, self.action_size, 1.0, 0.0, name = 'action_one_hot')
                q_acted = tf.reduce_sum(self.p_q * action_one_hot, reduction_indices = 1, name = 'q_acted')

                self.dqn_delta = self.dqn_gt_q - q_acted
                self.clipped_delta = tf.clip_by_value(self.dqn_delta, self.min_delta, self.max_delta, name = 'clipped_delta')
                # self.global_step = tf.Varialbe(0, trainable = False)

                self.dqn_loss = tf.reduce_mean(tf.square(self.clipped_delta), name = 'dqn_loss')
                self.dqn_learning_rate_step = tf.placeholder('int64', None, name = 'learning_rate_step')
                self.dqn_learning_rate_op = tf.maximum(self.learning_rate_minimum,
                        tf.train.exponential_decay(
                            self.dqn_learning_rate,
                            self.dqn_learning_rate_step,
                            self.dqn_learning_decay_step,
                            self.dqn_learning_decay_rate,
                            staircase = True))
                self.dqn_optim = tf.train.GradientDescentOptimizer(self.dqn_learning_rate_op, name = 'optimizer').minimize(self.dqn_loss)
        else:
            with tf.variable_scope('dqn_transfer'):
                self.dqn_assign_inp = {}
                self.dqn_assign_op = {}

                for key in self.p_dqn_w.keys():
                    self.dqn_assign_inp[key] = tf.placeholder('float32', self.p_dqn_w[key].get_shape().as_list(), name = key)
                    self.dqn_assign_op[key] = self.t_dqn_w[key].assign(self.dqn_assign_inp[key])

    def train(self):
        # timer
        st = time.time()

        if self.isLoadFromModel:
            self.load_model()
        else:
            self.sess.run(tf.initialize_all_variables())
            self.update_target_net()

        self.update_count = 0
        self.mem.reset()
        self.step = 0

        data_size = self.env.get_size('train')
        if self.epi_size > data_size - self.train_start_point:
            self.epi_size = data_size - self.train_start_point

        # Debug
        # print data_size
        # exit(0)
        #

        self.ep_decay_step = (self.act_ep - self.act_ep_threshold) / (1. * data_size / self.tot_epoches * self.decay_epoches)
        self.guide_period = self.guide_epoches * (data_size / self.tot_epoches)
        self.act_ep -= self.ep_decay_step * max(0., self.train_start_point - self.guide_period)
        if self.act_ep < self.act_ep_threshold:
            self.act_ep = self.act_ep_threshold

        # start the env.dataset.readerqueue
        self.env.start()

        # logging loss
        self.loss_logger = open(self.loss_log_file, 'w')
        self.action_logger = open(self.action_log_file, 'w')
        
        avg_rwd_per_epi = 0.

        for episode in xrange(self.train_start_point + 1, self.epi_size, 1):
            # initialize the environment for each episode
            state = self.env.reset()   
            state = State(state.img, state.height, state.width)
            self.his_reset()
            cur_sum_reward = 0
            # used to demonstrate the actual action.
            act_dic = np.array(['left', 'right', 'up', 'down', 'bigger', 'smaller', 'fatter', 'taller', 'trigger'])
            
            for stp in xrange(self.step_size):
                self.step += 1
                # predict
                action = self.predict(np.array([state]))
                # act
                nxt_state, reward, terminal = self.env.act(action)
                # Debug
                self.action_logger.write("Done action %s: Ep %d, Epsilon %.3f, Step %d\n" % (act_dic[action], episode, self.act_ep, stp))
                #
                # observe
                self.observe(state, action, reward, nxt_state, terminal, self.action_his_code)

                if terminal:
                    cur_sum_reward += reward
                    break
                else:
                    state = nxt_state
                    self.his_add(action)

                # Debug 
                cur_sum_reward += reward

            avg_rwd_per_epi = avg_rwd_per_epi + (cur_sum_reward - avg_rwd_per_epi) / (episode + 0.)

            # Demonstrate the final result concerning the task
            # print "Epoch %d, IoU = %.4f" % (episode, self.env.IoU)
            # Debug
            print "Trained on episode %d:" % (episode)
            print "\tsum reward = %d\n\tcurrent IoU = %.4f" % (cur_sum_reward, self.env.IoU)
            print "\taverage reward per epi = %.4f" % avg_rwd_per_epi

            if episode and episode % self.check_point == self.check_point - 1:
                self.record(episode)

            # epsilon decay
            if episode >= self.guide_period and self.act_ep > self.act_ep_threshold:
                self.act_ep -= self.ep_decay_step

        # close the env.dataset.readerqueue
        self.env.end()
        # close loss_logger
        self.update_target_net()
        self.loss_logger.close()
        self.action_logger.close()

    def play(self):
        ac = 0
        total = self.env.get_size('test')
        self.env.accept_rate = 1.
        
        # load model
        self.load_model()

        # action logger
        self.action_logger = open(self.action_log_file, 'w')

        self.env.start()
        print "[*] Starting test..."
        for epi in xrange(total):
            state = self.env.reset(isTrain = False)   
            state = State(state.img, state.height, state.width)
            self.his_reset()
            # Debug
            total_step = -1

            for stp in xrange(self.step_size):
                # predict
                action = self.predict(np.array([state]))
                # Debug
                self.action_logger.write(str(self.env.state.box) + '\n')
                # act
                state, reward, terminal = self.env.act(action)
                self.action_logger.write(str(action) + '\n')

                if terminal:
                    total_step = stp + 1
                    break
                else:
                    self.his_add(action)
            
            print self.env.state.box
            if self.env.IoU >= self.test_accept_rate:
                print "[*] Accepted! IoU = %.4f, total_step = %d" % (self.env.IoU, total_step)
                ac += 1
            else:
                print "[!] Missed. IoU = %.4f, total_step = %d" % (self.env.IoU, total_step)

            print "[*] Tested %d of %d, current AP = %.4f (%d/%d)" % (epi + 0, total, ac * 1. / (epi + 0.), ac, epi + 1)

        self.env.end()
        print "[*] Finish test."
        print "[*] Final Ap = %.4f (%d/%d)" % (ac * 1. / (total + 0.), ac, total)

    def predict(self, states):
        if self.isTrain and random.random() <= self.act_ep:
            # Debug
            if self.action_logger != None:
                self.action_logger.write("[x] Not Q-Greedy...")
            #
            action = self.env.get_random_positive() 
        else:
            # Debug
            if self.action_logger != None:
                self.action_logger.write("[*] Yes Q-Greedy...") 
            #
            [action, q_out] = self.sess.run([self.q_action, self.p_q], {self.action_history : self.actionArray(1, [self.action_his_code]), self.img_inp: self.crop(states), self.keep_prob : self.dropout_prob if self.isTrain else 1.})
            # Debug
            self.action_logger.write(str(q_out) + '\n')
            #
            action = action[0]
        return action

    def observe(self, state, action, reward, nxt_state, terminal, his_code):
        self.mem.add(state, action, reward, nxt_state, terminal, his_code)

        # gradient descent
        self.stochastic_gradient_descent()
        # update target net every C steps
        if self.step % self.update_C == 0:
            self.update_target_net()

    def stochastic_gradient_descent(self):
        if self.mem.count < self.batch_size:
            return

        s, action, reward, s_nxt, terminal, his_code = self.mem.sample(self.batch_size)

        q_nxt = self.sess.run(self.t_q, {self.img_inp : self.crop(s_nxt), self.action_history : self.actionArray(self.batch_size, his_code | (1 << action))})
        
        terminal = np.array(terminal) + 0.
        max_q_nxt = np.max(q_nxt, axis = 1)
        ground_truth = (1. - terminal) * self.discount * max_q_nxt + reward

        _, q_t, loss = self.sess.run([self.dqn_optim, self.p_q, self.dqn_loss], {
                self.dqn_gt_q : ground_truth,
                self.action : action,
                self.img_inp : self.crop(s),
                self.dqn_learning_rate_step: self.step,
                self.action_history: self.actionArray(self.batch_size, his_code),
                self.keep_prob: self.dropout_prob
                })

        self.update_count += 1
        # DEBUG
        self.loss_logger.write("[i] Update_count: %d, loss = %.4f\n" % (self.update_count, loss))

    def actionArray(self, sz, act_his):
        arr = np.zeros([sz, self.action_size], dtype = float)
        for i in xrange(sz):
            for j in xrange(self.action_size):
                if (act_his[i] >> j) & 1 == 1:
                    arr[i][j] = 1.0
                else:
                    arr[i][j] = 0.0 
        return arr

    def update_target_net(self):
        print "Now we start update..."

        # timer
        st = time.time()
        # for key in self.p_cnn_w.keys():
        #     self.sess.run(self.cnn_assign_op[key], {self.cnn_assign_inp[key] : self.sess.run(self.p_cnn_w[key])})
        for key in self.p_dqn_w.keys():
            self.sess.run(self.dqn_assign_op[key], {self.dqn_assign_inp[key] : self.sess.run(self.p_dqn_w[key])})

        # timer
        if self.loss_logger != None:
            self.loss_logger.write("Spent %.4fsecs assigning...\n" % (time.time() - st))
        st = time.time()
        #

    def his_reset(self):
        self.his_head = 0
        self.his_cnt = 0
    def his_add(self, action):
        if self.his_cnt >= 8:
            self.action_status[self.his_head] = action
            self.his_head = (self.his_head + 1) % self.act_his_len
        else:
            self.action_status[self.his_head + self.his_cnt] = action
        self.his_cnt += 1
        self.action_his_code = 0
        for x in xrange(min(8, self.his_cnt)):
            self.action_his_code |= 1 << self.action_status[(self.his_head + x) % self.act_his_len]

    def context_crop(self, img, up, left, down, right):
        up = max(0, up - 1 - 16)
        left = max(0, left - 1 - 16)
        down = min(img.shape[0], down + 16)
        right = min(img.shape[1], right + 16)
        return img[int(up): int(down), int(left): int(right), :]

    def crop(self, states):
        cropped = np.empty([states.shape[0], 224, 224, 3], dtype = np.float32)
        cnt = 0

        for s in states:
            img = s.img
            up = s.box[0]
            left = s.box[1]
            down = s.box[2]
            right = s.box[3]
            cropped[cnt] = imresize(self.context_crop(img, up, left, down, right), (224, 224), interp = 'bicubic') / 255.
            cnt += 1
    
        return cropped

    def record(self, epi_step):
        self.save_model(step = epi_step)
