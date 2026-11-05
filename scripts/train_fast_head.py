"""Train a transfer-learning classifier head efficiently on cached CNN features."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import CLASS_NAMES, Config, IMAGE_SIZE, PREPROCESSING_VERSION, SEED
from app.models.mobilenet_model import build_model
from app.services.evaluation_service import evaluate_predictions
from app.services.training_service import ImageSequence, seed_everything

parser = argparse.ArgumentParser()
parser.add_argument("--epochs", type=int, default=12)
parser.add_argument("--batch-size", type=int, default=128)
args = parser.parse_args()

seed_everything(SEED)
root = Path(__file__).resolve().parents[1]
splits = {name: pd.read_csv(root / "data" / "splits" / f"{name}.csv") for name in ("train", "val", "test")}
model = build_model("imagenet", "MobileNetV3Small")
pooling = next(layer for layer in model.layers if isinstance(layer, tf.keras.layers.GlobalAveragePooling2D))
extractor = tf.keras.Model(model.input, pooling.output)


def extract(frame):
    sequence = ImageSequence(frame, Config.IMAGE_DIR, args.batch_size, shuffle=False, augment=False)
    features, labels = [], []
    for index in range(len(sequence)):
        images, values = sequence[index]
        features.append(extractor.predict(images, verbose=0))
        labels.append(values)
    return np.concatenate(features), np.concatenate(labels)


train_features, train_labels = extract(splits["train"])
val_features, val_labels = extract(splits["val"])
test_features, test_labels = extract(splits["test"])
head = tf.keras.Sequential([
    tf.keras.Input(shape=(train_features.shape[1],)),
    tf.keras.layers.Dropout(0.25),
    tf.keras.layers.Dense(len(CLASS_NAMES), activation="softmax"),
])
head.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="categorical_crossentropy", metrics=["accuracy"])
head.fit(train_features, train_labels, validation_data=(val_features, val_labels), epochs=args.epochs, batch_size=args.batch_size, verbose=1, callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True)])
dense = model.layers[-1]
dense.set_weights(head.layers[-1].get_weights())
probabilities = model.predict(test_features if False else ImageSequence(splits["test"], Config.IMAGE_DIR, args.batch_size), verbose=0)
truth = np.argmax(test_labels, axis=1)
predictions = np.argmax(probabilities, axis=1)
metrics_path = root / "reports" / "metrics" / "fast_head.json"
metrics = evaluate_predictions(truth.tolist(), predictions.tolist(), metrics_path)
model_path = root / "models" / "global" / "edgeretina_global.keras"
metadata_path = root / "models" / "global" / "metadata.json"
model.save(model_path)
metadata = {"architecture": "MobileNetV3Small", "num_classes": len(CLASS_NAMES), "class_names": {str(key): value for key, value in CLASS_NAMES.items()}, "image_size": list(IMAGE_SIZE), "preprocessing_version": PREPROCESSING_VERSION, "training_seed": SEED, "trained": True, "training_stage": "cached_feature_head", "criterion": "accuracy", "test_metrics": metrics}
metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))