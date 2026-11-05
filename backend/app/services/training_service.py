import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

from ..config import CLASS_NAMES, IMAGE_SIZE, PREPROCESSING_VERSION, SEED
from ..models.mobilenet_model import build_model
from .evaluation_service import evaluate_predictions
from .preprocessing import load_and_preprocess


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


class ImageSequence(tf.keras.utils.Sequence):
    def __init__(self, frame: pd.DataFrame, image_dir: Path, batch_size: int = 16, shuffle: bool = False, augment: bool = False):
        super().__init__()
        self.frame = frame.reset_index(drop=True)
        self.image_dir = image_dir
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.augment = augment
        self.indices = np.arange(len(self.frame))
        self.on_epoch_end()

    def __len__(self):
        return int(np.ceil(len(self.frame) / self.batch_size))

    def __getitem__(self, index):
        selected = self.indices[index * self.batch_size:(index + 1) * self.batch_size]
        images, labels = [], []
        image_column = "id" if "id" in self.frame.columns else "id_code"
        for row_index in selected:
            image_id = str(self.frame.iloc[row_index][image_column])
            matches = list(self.image_dir.glob(f"{image_id}.*"))
            if not matches:
                raise FileNotFoundError(f"Image not found for {image_id}")
            image, _ = load_and_preprocess(matches[0])
            if self.augment:
                image_tensor = tf.convert_to_tensor(image, dtype=tf.float32)
                image_tensor = tf.image.random_flip_left_right(image_tensor)
                image_tensor = tf.image.random_brightness(image_tensor, max_delta=0.08)
                image_tensor = tf.image.random_contrast(image_tensor, lower=0.9, upper=1.1)
                image = tf.clip_by_value(image_tensor, -1.0, 1.0).numpy()
            images.append(image)
            labels.append(int(self.frame.iloc[row_index]["diagnosis"]))
        return np.asarray(images, dtype=np.float32), tf.keras.utils.to_categorical(labels, len(CLASS_NAMES))

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)


class ValidationCheckpoint(tf.keras.callbacks.Callback):
    def __init__(self, validation_sequence: ImageSequence, path: Path, criterion: str = "macro_f1"):
        super().__init__()
        self.validation_sequence = validation_sequence
        self.path = path
        self.criterion = criterion
        self.best = -np.inf

    def on_epoch_end(self, epoch, logs=None):
        probabilities = self.model.predict(self.validation_sequence, verbose=0)
        predictions = np.argmax(probabilities, axis=1)
        truth = np.argmax(np.concatenate([self.validation_sequence[index][1] for index in range(len(self.validation_sequence))]), axis=1)
        metrics = evaluate_predictions(truth.tolist(), predictions.tolist())
        score = metrics["accuracy"] if self.criterion == "accuracy" else metrics["macro_f1"]
        if score > self.best:
            self.best = score
            self.model.save(self.path)
        print(f" - val_{self.criterion}: {score:.4f}")


class TrainingHistoryWriter(tf.keras.callbacks.Callback):
    def __init__(self, path: Path, stage: str):
        super().__init__()
        self.path = path
        self.stage = stage
        self.history = []

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        self.history.append({"stage": self.stage, "epoch": epoch + 1, **{key: float(value) for key, value in logs.items() if value is not None}})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.history, indent=2), encoding="utf-8")


def focal_loss(gamma: float = 1.5):
    def loss(y_true, y_pred):
        y_pred = tf.clip_by_value(y_pred, tf.keras.backend.epsilon(), 1.0 - tf.keras.backend.epsilon())
        cross_entropy = -y_true * tf.math.log(y_pred)
        return tf.reduce_sum(tf.pow(1.0 - y_pred, gamma) * cross_entropy, axis=-1)

    return loss


def train_centralized(csv_dir: Path, image_dir: Path, model_path: Path, metadata_path: Path, metrics_path: Path, epochs: int = 2, batch_size: int = 16, fine_tune: bool = True, loss_type: str = "weighted_crossentropy", architecture: str = "MobileNetV3Small", criterion: str = "macro_f1", history_path: Path | None = None) -> dict:
    seed_everything()
    split_dir = csv_dir
    train = pd.read_csv(split_dir / "train.csv")
    validation = pd.read_csv(split_dir / "val.csv")
    test = pd.read_csv(split_dir / "test.csv")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    model = build_model("imagenet", architecture)
    loss = focal_loss() if loss_type == "focal" else "categorical_crossentropy"
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss=loss, metrics=["accuracy"])
    validation_sequence = ImageSequence(validation, image_dir, batch_size)
    labels = train["diagnosis"].to_numpy()
    weights = compute_class_weight("balanced", classes=np.arange(len(CLASS_NAMES)), y=labels)
    class_weights = {index: float(weight) for index, weight in enumerate(weights)}
    checkpoint = ValidationCheckpoint(validation_sequence, model_path, criterion)
    history_writer = TrainingHistoryWriter(history_path or metrics_path.with_name(f"{architecture}_history.json"), "head")
    training_weights = class_weights if loss_type == "weighted_crossentropy" and criterion != "accuracy" else None
    model.fit(ImageSequence(train, image_dir, batch_size, shuffle=True, augment=True), validation_data=validation_sequence, epochs=epochs, class_weight=training_weights, callbacks=[checkpoint, history_writer], verbose=1)
    if fine_tune:
        backbone = next(layer for layer in model.layers if isinstance(layer, tf.keras.Model))
        backbone.trainable = True
        for layer in backbone.layers[:-20]:
            layer.trainable = False
        model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss=loss, metrics=["accuracy"])
        history_writer.stage = "fine_tune"
        model.fit(ImageSequence(train, image_dir, batch_size, shuffle=True, augment=True), validation_data=validation_sequence, epochs=max(1, epochs // 2), class_weight=training_weights, callbacks=[checkpoint, history_writer], verbose=1)
    model = tf.keras.models.load_model(model_path, compile=False)
    test_sequence = ImageSequence(test, image_dir, batch_size)
    probabilities = model.predict(test_sequence, verbose=0)
    truth = test["diagnosis"].astype(int).to_numpy()
    metrics = evaluate_predictions(truth.tolist(), np.argmax(probabilities, axis=1).tolist(), metrics_path)
    metadata = {"architecture": architecture, "num_classes": len(CLASS_NAMES), "class_names": {str(key): value for key, value in CLASS_NAMES.items()}, "image_size": list(IMAGE_SIZE), "preprocessing_version": PREPROCESSING_VERSION, "training_seed": SEED, "trained": True, "loss": loss_type, "criterion": criterion, "augmentation": ["horizontal_flip", "brightness", "contrast"], "class_weights": training_weights, "test_metrics": metrics}
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metrics
