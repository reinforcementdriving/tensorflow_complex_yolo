# -*- coding: utf-8 -*-

import os
import tensorflow as tf
from dataset.dataset import ImageDataSet
from model.model import yolo_net, yolo_loss
SCALE = 32
GRID_W, GRID_H = 32, 24
N_CLASSES = 8
N_ANCHORS = 5
IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_DEPTH = GRID_H * SCALE, GRID_W * SCALE, 3
BATCH_SIZE = 2
NUM_ITERS = 100000
NUM_VAL_STEP = int(1000.0 / BATCH_SIZE)
MODEL_PATH, SAVE_INTERVAL = './weights', 1600
train_dataset = ImageDataSet(data_set='train', mode='train', load_to_memory=False)
test_dataset = ImageDataSet(data_set='test', mode='train', flip=False, aug_hsv=False, random_scale=False, load_to_memory=True)
# os.environ["CUDA_VISIBLE_DEVICES"] = "2"


def make_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def train(load_weights=False):
    max_val_loss = 99999999.0
    global_step = tf.Variable(0, trainable=False)
    learning_rate = tf.train.exponential_decay(0.001, global_step, 2000, 0.96, staircase=True)
    image = tf.placeholder(shape=[None, IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_DEPTH], dtype=tf.float32,
                           name='image_placeholder')
    label = tf.placeholder(shape=[None, GRID_H, GRID_W, N_ANCHORS, 8], dtype=tf.float32, name='label_palceholder')
    train_flag = tf.placeholder(dtype=tf.bool, name='flag_placeholder')

    with tf.variable_scope('net'):
        y = yolo_net(image, train_flag)
    with tf.name_scope('loss'):
        loss, loss_xy, loss_wh, loss_re, loss_im, loss_obj, loss_no_obj, loss_c = yolo_loss(y, label, BATCH_SIZE)

    loss_xy_sum = tf.summary.scalar("loss_xy_sum", loss_xy)
    loss_wh_sum = tf.summary.scalar("loss_wh_sum", loss_wh)
    loss_re_sum = tf.summary.scalar("loss_re_sum", loss_re)
    loss_im_sum = tf.summary.scalar("loss_im_sum", loss_im)
    loss_obj_sum = tf.summary.scalar("loss_obj_sum", loss_obj)
    loss_no_obj_sum = tf.summary.scalar("loss_no_obj_sum", loss_no_obj)
    loss_c_sum = tf.summary.scalar("loss_c", loss_c)
    loss_sum = tf.summary.scalar("loss", loss)
    loss_tensorboard_sum = tf.summary.merge(
        [loss_xy_sum, loss_wh_sum, loss_re_sum, loss_im_sum, loss_obj_sum, loss_no_obj_sum, loss_c_sum, loss_sum])
    opt = tf.train.AdamOptimizer(learning_rate=learning_rate)
    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        train_step = opt.minimize(loss, global_step=global_step)
    sess = tf.Session()
    sess.run(tf.global_variables_initializer())
    saver = tf.train.Saver()
    writer = tf.summary.FileWriter("./logs", sess.graph)

    if load_weights:
        saver = tf.train.import_meta_graph('./weights/yolo_tloss_4.664687156677246_vloss_5.552119486808777-60000.meta')
        saver.restore(sess, './weights/yolo_tloss_4.664687156677246_vloss_5.552119486808777-60000')
        print('load weights done!')

    for step, (train_image_data, train_label_data) in enumerate(train_dataset.get_batch(BATCH_SIZE)):
        _, lr, loss_data, data, summary_str = sess.run([train_step, learning_rate, loss, y, loss_tensorboard_sum],
                                                   feed_dict={train_flag: True, image: train_image_data,
                                                              label: train_label_data})
        # print summary_str
        writer.add_summary(summary_str, step)
        if step % 10 == 0:
            print('iter: %i, loss: %f, lr: %f' % (step, loss_data, lr))
        if (step + 1) % SAVE_INTERVAL == 0:
            val_loss = 0.0
            for val_step, (val_image_data, val_label_data) in enumerate(test_dataset.get_batch(BATCH_SIZE)):
                val_loss += sess.run(loss, feed_dict={train_flag: False, image: val_image_data, label: val_label_data})
                if val_step + 1 == NUM_VAL_STEP:
                    break
            val_loss /= NUM_VAL_STEP
            print("iter: {} val_loss: {}".format(step, val_loss))
            if val_loss < max_val_loss:
                make_dir(MODEL_PATH)
                saver.save(sess, os.path.join(MODEL_PATH, 'yolo_tloss_{}_vloss_{}'.format(loss_data, val_loss)),
                           global_step=global_step)
                max_val_loss = val_loss
        if step + 1 == NUM_ITERS:
            saver.save(sess, os.path.join(MODEL_PATH, 'yolo_tloss_{}_vloss_{}'.format(loss_data, val_loss)),
                       global_step=global_step)
            break


if __name__ == "__main__":
    train(load_weights=False)