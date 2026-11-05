import tensorflow as tf

from ..config import CLASS_NAMES, IMAGE_SIZE


def build_model(weights: str | None = "imagenet", architecture: str = "MobileNetV3Small") -> tf.keras.Model:
    if architecture == "EfficientNetB0":
        backbone = tf.keras.applications.EfficientNetB0(
            input_shape=(*IMAGE_SIZE, 3), include_top=False, weights=weights
        )
    elif architecture == "MobileNetV3Small":
        backbone = tf.keras.applications.MobileNetV3Small(
            input_shape=(*IMAGE_SIZE, 3), include_top=False, weights=weights, include_preprocessing=False
        )
    else:
        raise ValueError(f"Unsupported architecture: {architecture}")
    backbone.trainable = False
    inputs = tf.keras.Input(shape=(*IMAGE_SIZE, 3), name="fundus_input")
    backbone_input = (inputs + 1.0) * 127.5 if architecture == "EfficientNetB0" else inputs
    features = backbone(backbone_input, training=False)
    features = tf.keras.layers.GlobalAveragePooling2D()(features)
    features = tf.keras.layers.Dropout(0.25)(features)
    outputs = tf.keras.layers.Dense(len(CLASS_NAMES), activation="softmax", name="severity_output")(features)
    return tf.keras.Model(inputs, outputs, name=f"EdgeRetina{architecture}")
