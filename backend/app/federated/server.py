from pathlib import Path

import json
import math
import numpy as np
import pandas as pd
import tensorflow as tf

from ..config import CLASS_NAMES
from ..services.evaluation_service import evaluate_predictions
from ..services.training_service import ImageSequence
from .differential_privacy import protect_update
from .fedavg import fedavg
from .partition import dirichlet_partition, save_distribution


def run_federated(train_csv: Path, image_dir: Path, base_model_path: Path, output_model_path: Path, metrics_path: Path, distribution_path: Path, rounds: int = 1, local_epochs: int = 1, dp_noise: float = 0.0, test_csv: Path | None = None, evaluation_path: Path | None = None, progress=None) -> dict:
    def report(**values):
        if progress:
            progress(values)

    clients = ["Hospital A", "Hospital B", "Hospital C", "Hospital D"]
    report(stage="initialize", stage_status="running", message="Validating the dataset, configuration and initial checkpoint.")
    if not train_csv.is_file() or not image_dir.is_dir() or not base_model_path.is_file():
        raise FileNotFoundError("Training CSV, retinal image directory, and initial global checkpoint are required.")
    if test_csv is not None and not test_csv.is_file():
        raise FileNotFoundError("Held-out test split is missing; final evaluation cannot run.")
    frame = pd.read_csv(train_csv)
    if frame.empty or "diagnosis" not in frame or not set(frame.diagnosis.dropna().astype(int)).issubset(set(CLASS_NAMES)):
        raise ValueError("Training data must be non-empty and use diagnosis labels 0 through 4.")
    report(stage="dataset", stage_status="completed", message=f"Validated {len(frame)} training records.", samples=len(frame))
    report(stage="partition", stage_status="running", message="Partitioning records across four simulated clients.")
    partitions = dirichlet_partition(frame, clients)
    save_distribution(partitions, distribution_path)
    report(stage="partition", stage_status="completed", clients=[{"id": client, "samples": len(partitions[client]), "status": "pending", "round": 0} for client in clients], message="Client partitions are ready.", participating_clients=len(clients))
    global_model = tf.keras.models.load_model(base_model_path, compile=False)
    report(stage="initialize", stage_status="completed", architecture=global_model.name, message="Initial global checkpoint loaded successfully.", checkpoint=str(base_model_path))
    report(stage="distribute", stage_status="completed", architecture=global_model.name, message="Initial global model is ready for local clients.", checkpoint=str(base_model_path))
    global_weights = global_model.get_weights()
    round_metrics = []
    for round_number in range(1, rounds + 1):
        report(round=round_number, stage="client_training", stage_status="running", message=f"Federated round {round_number}/{rounds} started.", round_status="running")
        local_weights, counts = [], []
        for client in clients:
            local_model = tf.keras.models.clone_model(global_model)
            local_model.set_weights(global_weights)
            report(stage="distribute", stage_status="completed", client=client, client_status="running", samples=len(partitions[client]), round=round_number, message=f"Current global weights copied to {client} for round {round_number}.")
            report(stage="client_training", stage_status="running", client=client, client_status="running", samples=len(partitions[client]), round=round_number, message=f"{client} local training started.")
            local_model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss="categorical_crossentropy", metrics=["accuracy"])
            history = local_model.fit(ImageSequence(partitions[client], image_dir, batch_size=16, shuffle=True), epochs=local_epochs, verbose=0)
            loss = float(history.history["loss"][-1])
            accuracy = float(history.history["accuracy"][-1])
            if not math.isfinite(loss) or not math.isfinite(accuracy):
                raise FloatingPointError(f"{client} training produced non-finite metrics; update was discarded.")
            report(stage="client_training", client=client, client_status="running", samples=len(partitions[client]), round=round_number, epoch=local_epochs, loss=loss, accuracy=accuracy, message=f"{client} completed local epoch {local_epochs}/{local_epochs}.")
            report(stage="client_training", client=client, client_status="running", round=round_number, loss=loss, accuracy=accuracy, message=f"{client} local training completed.")
            update = [new - old for new, old in zip(local_model.get_weights(), global_weights)]
            if any(not np.isfinite(value).all() for value in update):
                raise FloatingPointError(f"{client} training produced non-finite model weights; update was discarded.")
            report(stage="client_training", client=client, client_status="running", round=round_number, message=f"{client} generated a model-weight update; no retinal images are exchanged.")
            report(stage="update_transfer", stage_status="completed", client=client, client_status="running", round=round_number, message=f"Server received {client}'s simulated model update.")
            report(stage="processing", stage_status="running", client=client, client_status="running", round=round_number, message=f"Applying L2 clipping and configured Gaussian perturbation to {client}'s update.")
            protected, _ = protect_update(update, clip_norm=1.0, noise_multiplier=dp_noise)
            local_weights.append([old + delta for old, delta in zip(global_weights, protected)])
            report(stage="processing", stage_status="running", processed_updates=len(local_weights), client=client, client_status="running", round=round_number, message=f"Privacy-inspired processing completed for {client}'s update.")
            count = len(partitions[client])
            counts.append(count)
            report(stage="processing", client=client, client_status="completed", samples=count, round=round_number, loss=loss, accuracy=accuracy, update_produced=True, update_processed=True, message=f"{client}'s update was produced and processed.")
        report(stage="processing", stage_status="completed", processed_updates=len(clients), message=f"Applied norm clipping at 1.0 and Gaussian noise multiplier {dp_noise:g}.")
        report(stage="aggregation", stage_status="running", message=f"FedAvg is aggregating {len(clients)} client updates.", participating_clients=len(clients))
        global_weights = fedavg(local_weights, counts)
        if any(not np.isfinite(value).all() for value in global_weights):
            raise FloatingPointError("FedAvg produced non-finite global weights; checkpoint was not saved.")
        sample_weights = [count / sum(counts) for count in counts]
        report(stage="aggregation", stage_status="completed", aggregation={"status": "completed", "round": round_number, "participants": len(counts), "sample_counts": counts, "sample_weights": sample_weights}, message=f"FedAvg aggregation completed for round {round_number}.", participating_clients=len(counts), sample_weights=sample_weights)
        global_model.set_weights(global_weights)
        report(stage="aggregation", round=round_number, message=f"Global model weights updated from the round {round_number} FedAvg result.", architecture=global_model.name)
        output_model_path.parent.mkdir(parents=True, exist_ok=True)
        report(stage="checkpoint", stage_status="running", round=round_number, message=f"Saving the round {round_number} global checkpoint.")
        global_model.save(output_model_path)
        tf.keras.models.load_model(output_model_path, compile=False)
        record = {"round": round_number, "samples": sum(counts), "participants": len(counts), "status": "completed"}
        round_metrics.append(record)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(pd.DataFrame(round_metrics).to_json(orient="records", indent=2), encoding="utf-8")
        report(stage="checkpoint", stage_status="completed", round_record=record, completed_rounds=round_number, checkpoint="models/federated/edgeretina_federated.keras", message=f"Round {round_number} checkpoint saved and reload verified.")
    if test_csv is not None:
        report(stage="evaluation", stage_status="running", message="Evaluating the final saved global model on the held-out test split.")
        test = pd.read_csv(test_csv)
        if test.empty or "diagnosis" not in test or not set(test.diagnosis.dropna().astype(int)).issubset(set(CLASS_NAMES)):
            raise ValueError("Held-out test set is empty or contains invalid class labels.")
        final_model = tf.keras.models.load_model(output_model_path, compile=False)
        probabilities = final_model.predict(ImageSequence(test, image_dir, batch_size=16), verbose=0)
        if not np.isfinite(probabilities).all():
            raise FloatingPointError("Final global model produced non-finite predictions; evaluation was withheld.")
        predicted = np.argmax(probabilities, axis=1).tolist()
        evaluation = evaluate_predictions(test.diagnosis.astype(int).tolist(), predicted)
        prediction_counts = np.bincount(predicted, minlength=len(CLASS_NAMES)).tolist()
        evaluation.update({"prediction_counts": prediction_counts, "prediction_collapsed": sum(count > 0 for count in prediction_counts) == 1})
        evaluation.update({"evaluation_samples": len(test), "evaluation_dataset": "data/splits/test.csv", "architecture": final_model.name, "checkpoint": str(output_model_path)})
        if evaluation_path:
            evaluation_path.parent.mkdir(parents=True, exist_ok=True)
            temp = evaluation_path.with_suffix(evaluation_path.suffix + ".tmp")
            temp.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
            temp.replace(evaluation_path)
        evaluation["checkpoint"] = "models/federated/edgeretina_federated.keras"
        if evaluation_path:
            temp = evaluation_path.with_suffix(evaluation_path.suffix + ".tmp")
            temp.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
            temp.replace(evaluation_path)
        report(stage="evaluation", stage_status="completed", evaluation=evaluation, message="Final global model evaluation completed.")
    print(f"COMPLETE|model={output_model_path}", flush=True)
    return {"rounds": round_metrics, "classes": len(CLASS_NAMES)}
