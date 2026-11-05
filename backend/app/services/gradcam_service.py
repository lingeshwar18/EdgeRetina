import numpy as np
import tensorflow as tf
from PIL import Image


def find_target_layer(model: tf.keras.Model) -> tf.keras.layers.Layer:
    candidates = []

    def collect(layer):
        if isinstance(layer, tf.keras.layers.Conv2D):
            candidates.append(layer)
        if isinstance(layer, tf.keras.Model):
            for child in layer.layers:
                collect(child)

    for layer in model.layers:
        collect(layer)
    if not candidates:
        raise ValueError("No convolutional layer is available for Grad-CAM")
    return candidates[-1]


def gradcam(model: tf.keras.Model, image: np.ndarray, class_index: int | None = None) -> np.ndarray:
    layer = find_target_layer(model)
    backbone_index = next((index for index, value in enumerate(model.layers) if isinstance(value, tf.keras.Model)), None)
    if backbone_index is None:
        raise ValueError("Model backbone is unavailable for Grad-CAM")
    backbone = model.layers[backbone_index]
    feature_model = tf.keras.Model(backbone.input, [layer.output, backbone.output])
    with tf.GradientTape() as tape:
        features, backbone_output = feature_model(image, training=False)
        predictions = backbone_output
        for head_layer in model.layers[backbone_index + 1:]:
            predictions = head_layer(predictions, training=False)
        index = int(tf.argmax(predictions[0]).numpy()) if class_index is None else class_index
        score = predictions[:, index]
    gradients = tape.gradient(score, features)
    weights = tf.reduce_mean(gradients, axis=(1, 2))
    heatmap = tf.reduce_sum(features * weights[:, None, None, :], axis=-1)
    heatmap = tf.maximum(heatmap, 0)
    heatmap /= tf.reduce_max(heatmap) + tf.keras.backend.epsilon()
    return heatmap[0].numpy()


def save_gradcam_overlay(original: Image.Image, heatmap: np.ndarray, output_path) -> None:
    heatmap_image = Image.fromarray(np.uint8(np.clip(heatmap, 0, 1) * 255)).resize(original.size, Image.Resampling.BICUBIC)
    values = np.asarray(heatmap_image, dtype=np.float32) / 255.0
    high_activation = np.percentile(values, 80)
    alpha = np.uint8(np.clip((values - high_activation) / max(1.0 - high_activation, 1e-6), 0.0, 0.78) * 255)
    red = np.uint8(255 * np.clip(values * 1.5, 0, 1))
    green = np.uint8(255 * np.clip(1.7 * values * (1.0 - values), 0, 1))
    blue = np.uint8(255 * (1.0 - values))
    color = Image.fromarray(np.stack([red, green, blue], axis=-1), mode="RGB")
    overlay = Image.composite(color, original.convert("RGB"), Image.fromarray(alpha, mode="L"))
    overlay.save(output_path)
