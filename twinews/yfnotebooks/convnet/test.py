#-*-coding:utf-8-*-
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from twinews.yfnotebooks.convnet.graph import Graph
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
from twinews.yfnotebooks.load_data import load_char_data

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

p, h, y = load_char_data('/home/yuting/PycharmProjects/data/dssm_title_dev.csv', data_size=None)

model = Graph()
saver = tf.train.Saver()

with tf.Session()as sess:
    sess.run(tf.global_variables_initializer())
    saver.restore(sess, '/home/yuting/PycharmProjects/Twinews/twinews/yfnotebooks/convnet/output/convnet_49.ckpt')
    loss, acc, logits, prediction = sess.run([model.loss, model.acc, model.logits, model.prediction],
                         feed_dict={model.p: p,
                                    model.h: h,
                                    model.y: y,
                                    model.keep_prob: 1})

    print('loss: ', loss, ' acc:', acc, 'logits:', logits, 'pre:',prediction)
