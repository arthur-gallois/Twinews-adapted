#-*-coding:utf-8-*-
import os
import sys

#sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from twinews.yfnotebooks.dssm.graph import Graph
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
from twinews.yfnotebooks.dssm.load_data import load_hashed_data

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TF_CPP_MIN_LOG_LEVEL’"] = "3"

p, h, y = load_hashed_data('/home/yuting/PycharmProjects/data/dssm_test_dev_sub.csv', data_size=None)

model = Graph()
saver = tf.train.Saver()

with tf.Session()as sess:
    sess.run(tf.global_variables_initializer())
    saver.restore(sess, '/home/yuting/PycharmProjects/Twinews/twinews/yfnotebooks/dssm/output/dssm_9.ckpt')
    loss, logits = sess.run([model.loss, model.logits],
                         feed_dict={model.p: p,
                                    model.h: h,
                                    model.y: y,
                                    model.keep_prob: 1})

    print('loss: ', loss, ' acc:', logits)
