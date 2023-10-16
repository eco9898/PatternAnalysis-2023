"""
train.py

Author: Ethan Jones
Student ID: 44829531
COMP3710 OASIS brain StyleGAN project
Semester 2, 2023
"""

import os
import tensorflow as tf
from tensorflow import keras
from dataset import load_data
from modules import Generator, Discriminator
from util import FileSaver
import matplotlib.pyplot as plt

# File paths
dataset_path = "C:\\Users\\ethan\\Desktop\\COMP3710" \
               "\\keras_png_slices_train "
result_image_path = "figures"
result_weight_path = "figures"
result_image_count = 5

# Hyperparameters
SEQUENCE = 500
LEARNING_RATE = 0.0001
EPOCHS = 80
BATCH_SIZE = 32


class StyleGAN(keras.Model):
    """
    Implementation of the Style Generative Adversarial Network model using Keras
    """

    def __init__(self, epochs, batch_size):
        """
        Constructor for the StyleGAN class
        """
        super(StyleGAN, self).__init__()
        self.generator = Generator().generator()
        self.discriminator = Discriminator().discriminator()
        self.epochs = epochs
        self.batch_size = batch_size

    def compile(self):
        """
        Compile the StyleGAN model

        Sets up the optimisers, loss function and metrics
        """
        super(StyleGAN, self).compile()

        # initialise the optimisers
        self.generator_optimizer = tf.keras.optimizers.Adam(LEARNING_RATE)
        self.discriminator_optimizer = tf.keras.optimizers.Adam(LEARNING_RATE)

        # initialise the loss function
        self.loss = tf.keras.losses.BinaryCrossentropy()

        # initialise the metrics
        self.generator_loss_metric = \
            tf.keras.metrics.Mean(name="generator_loss")
        self.discriminator_loss_metric = \
            tf.keras.metrics.Mean(name="discriminator_loss")

    @property
    def metrics(self):
        """
        Return the metrics of the StyleGAN model
        """
        return [self.generator_loss_metric, self.discriminator_loss_metric]

    def generator_inputs(self):
        """
        Generate the inputs for the generator model
        """
        # Generate latent space noise tensors.
        z = [tf.random.normal((self.batch_size, 512)) for i in range(7)]

        # Generate noise tensors for unique resolutions.
        noise = [tf.random.normal((self.batch_size, res, res, 1))
                 for res in [4, 8, 16, 32, 64, 128, 256]]

        # Create a constant input tensor.
        input = tf.ones([self.batch_size, 4, 4, 512])
        return [input, z, noise]

    def train_generator(self):
        """
        Trains the generator model for one step.
        """
        # Get the inputs for the generator model.
        inputs = self.generator_inputs()

        # Record operations for automatic differentiation.
        with tf.GradientTape() as g_tape:
            # Generate fake images and get the discriminator's
            fake_images = self.generator(inputs)
            predictions = self.discriminator(fake_images)

            # Create labels indicating that the fake images are real.
            labels = tf.zeros([self.batch_size, 1])

            # Calculate the generator's loss.
            generator_loss = self.loss(labels, predictions)

            # Get the trainable variables of the generator and calculate
            # the gradients of the generator's loss with respect to the
            # trainable variables
            trainable_variables = self.generator.trainable_variables
            gradients = g_tape.gradient(generator_loss, trainable_variables)

            # Apply the gradients to the generator's optimiser.
            self.generator_optimizer.apply_gradients(zip(gradients,
                                                         trainable_variables))
        return generator_loss

    def train_discriminator(self, real_images):
        """
        Trains the discriminator model for one step using
        both real and generated images
        """
        # Generate fake images
        inputs = self.generator_inputs()
        generated_images = self.generator(inputs)

        # Create labels for the fake and real images and combine them.
        images = tf.concat([generated_images, real_images], axis=0)
        labels = tf.concat([tf.zeros([self.batch_size, 1]),
                            tf.ones([self.batch_size, 1])], axis=0)

        # Start recording operations for automatic differentiation.
        with tf.GradientTape() as d_tape:
            # Get the discriminator's predictions for the combined
            # batch of images and calculate the loss.
            predictions = self.discriminator(images)
            discriminator_loss = self.loss(labels, predictions)

            # Get the trainable variables of the discriminator and calculate
            # the gradients of the discriminator loss with respect to them.
            gradients = d_tape.gradient(discriminator_loss, trainable_variables)

            # Apply the gradients to the discriminator's optimiser.
            self.discriminator_optimizer.apply_gradients(zip(gradients,
                                                             trainable_variables))
        return discriminator_loss

    def train(self, dataset_path, result_image_path,
              result_weight_path, result_image_count):
        """
        Train the StyleGAN model using the given dataset
        """
        callbacks = []

        if result_image_path:
            training_hooks.append()

        if result_weight_path:
            training_hooks.append()

        dataset = load_data(dataset_path)
        self.compile()
        epoch_history = self.fit(dataset, self.epochs)

        if plot_loss:
            self.plot(epoch_history, result_image_path)

    @tf.function
    def train_step(self, real_images):
        """
        Executes a single training step for both the generator
        and discriminator models.
        """
        # Train the generator and discriminator models
        generator_loss = self.train_generator()
        discriminator_loss = self.train_discriminator(real_images)

        # Update the metrics with the current loss values
        self.generator_loss_metric.update_state(generator_loss)
        self.discriminator_loss_metric.update_state(discriminator_loss)

        # Return the updated loss values for the generator and discriminator
        return {
            "generator_loss": self.generator_loss_metric.result(),
            "discriminator_loss": self.discriminator_loss_metric.result()
        }

    def plot(self, epoch_history, filepath):
        """
        Visualise the loss values of the StyleGAN model by plotting the
        losses of the discriminator and generator against the number of epochs.
        """
        # Extract the discriminator and generator loss values
        # from the epoch_history object.
        discriminator_loss = epoch_history.epoch_history["discriminator_loss"]
        generator_loss = epoch_history.epoch_history["generator_loss"]

        # Plot the discriminator loss values against the number of epochs.
        minimum_value = min(min(discriminator_loss), min(generator_loss))
        maximum_value = max(max(discriminator_loss), max(generator_loss))

        # Plot the generator loss values against the number of epochs.
        plt.plot(discriminator_loss, label="Discriminator Loss")
        plt.plot(generator_loss, label="Generator Loss")

        # Set the title and labels of the plot
        plt.title("StyleGAN Loss")
        plt.xlabel("Epoch")
        plt.ylabel("Loss")

        # Set the y-axis limits to the minimum and maximum values
        plt.ylim([minimum_value, maximum_value])

        # If filepath is not None, save the plot to the filepath
        if filepath is not None:
            directory_name = os.path.dirname(filepath)
            filepath = os.path.join(directory_name, filepath)
            plt.savefig("{}\loss_plot.png".format(filepath))
