from pathlib import Path
import csv
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid
from threading import Lock, Thread

from flask import jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from .config import CLASS_NAMES, Config
from .database.database import add_prediction, list_predictions
from .federated.server import run_federated
from .services.dataset_validator import validate_dataset
from .services.prediction_service import predict_image
from .services.report_service import load_reports
from .services.training_service import train_centralized
from .services.gemini_service import GeminiUnavailable, review_image

training_state = {"status": "idle", "message": "Training has not started.", "metrics": None}
ensemble_state = {"status": "idle", "message": "Ensemble training has not started.", "metrics": None, "progress": 0, "current_model": None, "output": ""}
training_lock = Lock()
ensemble_lock = Lock()
pipeline_start_lock = Lock()
federated_state = {"status": "idle", "message": "Federated learning has not started.", "progress": 0, "round": 0, "rounds": 1, "client": None, "dp_noise": 0.0, "output": ""}
federated_lock = Lock()


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value



def _federated_training_example(root: Path):
    split_path = root / "data" / "splits" / "train.csv"
    image_dir = Config.IMAGE_DIR
    try:
        with split_path.open("r", encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                sample_id = (row.get("id_code") or "").strip()
                try:
                    diagnosis = int(row.get("diagnosis", ""))
                except (TypeError, ValueError):
                    continue
                if not sample_id or Path(sample_id).name != sample_id or diagnosis not in CLASS_NAMES:
                    continue
                for suffix in (".png", ".jpg", ".jpeg"):
                    image_path = image_dir / f"{sample_id}{suffix}"
                    if image_path.is_file():
                        return {"id": sample_id, "diagnosis": diagnosis, "label": CLASS_NAMES[diagnosis], "path": image_path}
    except OSError:
        return None
    return None

def _write_json_atomic(path: Path, value):
    """Write JSON through a per-write temp file and tolerate transient Windows locks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.stem}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(json.dumps(_json_safe(value), indent=2, allow_nan=False), encoding="utf-8")
        for attempt in range(8):
            try:
                os.replace(temp_path, path)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        temp_path.unlink(missing_ok=True)



def _run_training(root: Path, epochs: int, batch_size: int):
    global training_state
    try:
        with training_lock:
            training_state = {"status": "running", "message": "Centralized training is running.", "metrics": None}
        metrics = train_centralized(root / "data" / "splits", Config.IMAGE_DIR, Config.MODEL_PATH, Config.MODEL_METADATA_PATH, root / "reports" / "metrics" / "centralized.json", epochs, batch_size, False)
        with training_lock:
            training_state = {"status": "completed", "message": "Training completed and the model was verified.", "metrics": metrics}
    except Exception as exc:
        with training_lock:
            training_state = {"status": "failed", "message": str(exc), "metrics": None}


def _run_ensemble(root: Path, epochs: int, batch_size: int):
    global ensemble_state
    output = []
    try:
        with ensemble_lock:
            ensemble_state = {"status": "running", "message": "Starting multi-model training.", "metrics": None, "progress": 1, "current_model": "Preparing", "output": ""}
        command = [sys.executable, "-u", str(root / "scripts" / "train_ensemble.py"), "--epochs", str(epochs), "--batch-size", str(batch_size)]
        process = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout or []:
            output.append(line.rstrip())
            text = line.strip()
            with ensemble_lock:
                if text.startswith("Training MobileNetV3Small"):
                    ensemble_state["current_model"] = "MobileNetV3Small"
                    ensemble_state["progress"] = 5
                elif text.startswith("Training EfficientNetB0"):
                    ensemble_state["current_model"] = "EfficientNetB0"
                    ensemble_state["progress"] = 55
                match = re.search(r"(\d+)/(\d+) .*accuracy: ([0-9.]+).*val_accuracy: ([0-9.]+)", text)
                if match:
                    completed, total = int(match.group(1)), int(match.group(2))
                    base = 5 if ensemble_state["current_model"] == "MobileNetV3Small" else 55
                    span = 45 if ensemble_state["current_model"] == "MobileNetV3Small" else 45
                    ensemble_state["progress"] = min(99, int(base + span * completed / max(total, 1)))
                    ensemble_state["message"] = f"{ensemble_state['current_model']} training batch {completed}/{total} | live batch accuracy {float(match.group(3)) * 100:.1f}% | validation accuracy pending"
                ensemble_state["output"] = "\n".join(output[-8:])
        return_code = process.wait()
        if return_code:
            raise RuntimeError("Ensemble training failed. Check the latest training output.")
        saved_state = _saved_ensemble_state(root)
        if not saved_state:
            raise RuntimeError("Ensemble training finished without producing both verified checkpoints.")
        with ensemble_lock:
            ensemble_state = {**saved_state, "output": "\n".join(output[-20:])}
    except Exception as exc:
        with ensemble_lock:
            ensemble_state = {"status": "failed", "message": str(exc), "metrics": None, "progress": 0, "current_model": None, "output": "\n".join(output[-20:])}


def _saved_ensemble_state(root: Path):
    ensemble_dir = root / "models" / "ensemble"
    checkpoints = ("mobilenetv3small", "efficientnetb0")
    if not all((ensemble_dir / f"{name}.keras").exists() and (ensemble_dir / f"{name}.json").exists() for name in checkpoints):
        return None
    metrics = {name: json.loads((ensemble_dir / f"{name}.json").read_text(encoding="utf-8")).get("test_metrics", {}) for name in checkpoints}
    return {"status": "completed", "message": "Verified multi-model ensemble is ready.", "metrics": metrics, "progress": 100, "current_model": "Complete", "output": "Saved MobileNetV3Small and EfficientNetB0 checkpoints detected."}


def _ensemble_status_file(root: Path) -> Path:
    return root / "reports" / "metrics" / "ensemble_status.json"


def _read_ensemble_state(root: Path):
    status_file = _ensemble_status_file(root)
    if status_file.exists():
        try:
            state = json.loads(status_file.read_text(encoding="utf-8"))
            if state.get("status") in ("queued", "running") and state.get("pid"):
                try:
                    os.kill(int(state["pid"]), 0)
                except OSError:
                    state.update({"status": "failed", "message": "The ensemble training process stopped unexpectedly. Start it again to retry.", "progress": 0})
                    status_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
            log_file = root / "reports" / "metrics" / "ensemble_training.log"
            if log_file.exists():
                state["output"] = log_file.read_text(encoding="utf-8", errors="replace")[-6000:]
            return state
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return _saved_ensemble_state(root) or ensemble_state


def _start_ensemble_process(root: Path):
    status_file = _ensemble_status_file(root)
    log_file = root / "reports" / "metrics" / "ensemble_training.log"
    initial_state = {"status": "queued", "message": "Multi-model ensemble queued.", "metrics": {}, "progress": 0, "current_model": "Queued", "output": "", "pid": None}
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")
    log_file.write_text("", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    with log_file.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, "-u", str(root / "scripts" / "train_ensemble.py"), "--epochs", "2", "--batch-size", "64", "--status-file", str(status_file)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    return initial_state


def _run_federated(root: Path, rounds: int, local_epochs: int, dp_noise: float):
    global federated_state
    status_path = root / "reports" / "federated" / "status.json"

    def progress(event):
        try:
            state = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
        state.update({key: value for key, value in event.items() if key not in ("event_type", "event_status", "stage", "stage_status", "client", "client_status", "round_record")})
        stages = state.setdefault("stages", {})
        if event.get("stage"):
            state["current_stage"] = event["stage"]
            stages[event["stage"]] = {"status": event.get("stage_status", "running"), "message": event.get("message", "")}
        if event.get("client"):
            state["current_client"] = event["client"] if event.get("client_status") == "running" else None
            clients = state.setdefault("clients", [])
            client = next((item for item in clients if item.get("id") == event["client"]), None)
            if client is None:
                client = {"id": event["client"]}
                clients.append(client)
            client.update({key: value for key, value in event.items() if key not in ("event_type", "event_status", "stage", "stage_status", "client", "client_status", "round_record", "message")})
            client.update({"status": event.get("client_status", client.get("status", "pending")), "message": event.get("message", "")})
        if event.get("round_record"):
            state.setdefault("round_history", []).append(event["round_record"])
        if event.get("evaluation"):
            event["evaluation"]["run_id"] = state.get("run_id")
            evaluation_path = root / "reports" / "federated" / "evaluation.json"
            evaluation_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json_atomic(evaluation_path, event["evaluation"])
        state["message"] = event.get("message", state.get("message", ""))
        state["status"] = "running"
        logs = state.setdefault("logs", [])
        if event.get("message"):
            logs.append(event["message"])
            del logs[:-100]
        total = max(state.get("rounds", 1), 1)
        stage = state.get("current_stage")
        if stage in ("client_training", "processing") and state.get("round", 0):
            current_round = state.get("round", state.get("completed_rounds", 0) + 1)
            complete_clients = sum(1 for item in state.get("clients", []) if item.get("round") == current_round and item.get("status") == "completed")
            state["progress"] = min(85, int(5 + 80 * ((current_round - 1 + complete_clients / 4) / total)))
        else:
            state["progress"] = {"initialize": 1, "dataset": 2, "partition": 3, "distribute": 5, "processing": 86, "aggregation": 88, "checkpoint": 90, "evaluation": 94}.get(stage, min(90, int(5 + 80 * state.get("completed_rounds", 0) / total)))
        state["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        state = _json_safe(state)
        _write_json_atomic(status_path, state)
        with federated_lock:
            federated_state = state

    try:
        run_federated(root / "data" / "splits" / "train.csv", Config.IMAGE_DIR, Config.MODEL_PATH, root / "models" / "federated" / "edgeretina_federated.keras", root / "reports" / "federated" / "rounds.json", root / "reports" / "federated" / "client_distribution.csv", rounds, local_epochs, dp_noise, root / "data" / "splits" / "test.csv", root / "reports" / "federated" / "evaluation.json", progress)
        state = json.loads(status_path.read_text(encoding="utf-8"))
        state.update({"status": "completed", "progress": 100, "message": "Federated training and final evaluation completed.", "completed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
        _write_json_atomic(status_path, state)
        with federated_lock:
            federated_state = state
    except Exception as exc:
        try:
            state = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
        stages = state.get("stages", {})
        current_stage = state.get("current_stage")
        if current_stage:
            stages[current_stage] = {"status": "failed", "error": str(exc).replace(str(root), "[project]")}
        current_client = state.get("current_client")
        for client in state.get("clients", []):
            if client.get("id") == current_client:
                client.update({"status": "failed", "error": "Local client training or update processing failed."})
        if state.get("round") and state.get("round") > state.get("completed_rounds", 0):
            state.setdefault("round_history", []).append({"round": state["round"], "status": "failed", "error": str(exc).replace(str(root), "[project]")})
        error = str(exc).replace(str(root), "[project]")
        state.update({"status": "failed", "message": error, "error": error, "stages": stages})
        status_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(status_path, state)
        with federated_lock:
            federated_state = state


def register_routes(app):
    upload_dir = Path(app.root_path).parents[1] / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def dashboard():
        return render_template("index.html", class_names=CLASS_NAMES, reports=load_reports(Path(app.root_path).parents[1] / "reports"))

    @app.get("/history")
    def history():
        class_id = request.args.get("class", type=int)
        rows = list_predictions(Config.DATABASE_PATH, request.args.get("q", ""), class_id)
        return render_template("history.html", rows=rows, class_names=CLASS_NAMES)

    @app.get("/reports")
    def reports():
        return render_template("reports.html", reports=load_reports(Path(app.root_path).parents[1] / "reports"), class_names=CLASS_NAMES)

    @app.get("/training")
    def training():
        return render_template("training.html")

    @app.get("/federated")
    def federated_dashboard():
        return render_template("federated.html")

    @app.post("/api/predict")
    def api_predict():
        upload = request.files.get("image")
        if not upload or not upload.filename:
            return jsonify({"error": "Choose a retinal image first."}), 400
        filename = secure_filename(upload.filename)
        path = upload_dir / filename
        upload.save(path)
        try:
            result = predict_image(path)
        except (ValueError, RuntimeError, OSError) as exc:
            return jsonify({"error": str(exc)}), 422
        except Exception as exc:
            return jsonify({"error": f"Prediction failed: {exc}"}), 500
        result["prediction_id"] = add_prediction(Config.DATABASE_PATH, filename, result["class_id"], result["class_name"], result["confidence"], result["model_source"], result.get("gradcam_path"))
        if result.get("gradcam_path"):
            result["gradcam_url"] = url_for("gradcam_file", filename=Path(result["gradcam_path"]).name)
        return jsonify(result)

    @app.post("/api/gemini-review")
    def api_gemini_review():
        upload = request.files.get("image")
        if not upload or not upload.filename:
            return jsonify({"error": "Choose an image first."}), 400
        path = upload_dir / f"gemini_{secure_filename(upload.filename)}"
        upload.save(path)
        try:
            return jsonify(review_image(path, predict_image(path)))
        except GeminiUnavailable as exc:
            return jsonify({"error": str(exc)}), 503
        except (ValueError, RuntimeError, OSError) as exc:
            return jsonify({"error": str(exc)}), 422

    @app.get("/api/gradcam/<filename>")
    def gradcam_file(filename):
        return send_from_directory(Path(app.root_path).parents[1] / "reports" / "gradcam", filename)

    @app.post("/api/validate-dataset")
    def api_validate_dataset():
        try:
            return jsonify(validate_dataset(Config.CSV_PATH, Config.IMAGE_DIR, Path(app.root_path).parents[1] / "reports" / "validation"))
        except (ValueError, OSError) as exc:
            return jsonify({"error": str(exc)}), 422

    @app.get("/api/status")
    def api_status():
        root = Path(app.root_path).parents[1]
        ensemble = _saved_ensemble_state(root)
        return jsonify({"dataset": Config.CSV_PATH.exists() and Config.IMAGE_DIR.exists(), "model": bool(ensemble), "demo_mode": Config.DEMO_MODE, "ensemble": ensemble})

    @app.post("/api/training/start")
    def api_training_start():
        global training_state
        with pipeline_start_lock:
            with ensemble_lock:
                if ensemble_state["status"] in ("queued", "running"):
                    return jsonify({"status": "failed", "message": "Multi-model training is already running. Wait for it to finish before starting baseline training."}), 409
            with training_lock:
                if training_state["status"] == "running":
                    return jsonify(training_state), 409
                if not (Path(app.root_path).parents[1] / "data" / "splits" / "train.csv").exists():
                    return jsonify({"status": "failed", "message": "Create dataset splits before training."}), 422
                training_state = {"status": "queued", "message": "Training queued.", "metrics": None}
        root = Path(app.root_path).parents[1]
        Thread(target=_run_training, args=(root, request.json.get("epochs", 1) if request.is_json else 1, request.json.get("batch_size", 16) if request.is_json else 16), daemon=True).start()
        return jsonify(training_state), 202

    @app.get("/api/training/status")
    def api_training_status():
        with training_lock:
            return jsonify(training_state)

    @app.get("/api/training/history")
    def api_training_history():
        root = Path(app.root_path).parents[1]
        history_files = (
            ("Centralized MobileNetV3Small", root / "reports" / "metrics" / "MobileNetV3Small_history.json"),
            ("Ensemble MobileNetV3Small", root / "reports" / "experiments" / "mobilenetv3small_history.json"),
            ("Ensemble EfficientNetB0", root / "reports" / "experiments" / "efficientnetb0_history.json"),
        )
        history = []
        for model, history_path in history_files:
            if not history_path.exists():
                continue
            try:
                history.extend({"model": model, **row} for row in json.loads(history_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return jsonify({"history": history, "message": "No training history has been generated yet." if not history else ""})

    @app.post("/api/ensemble/start")
    def api_ensemble_start():
        root = Path(app.root_path).parents[1]
        if not (root / "data" / "splits" / "train.csv").exists():
            return jsonify({"status": "failed", "message": "Create dataset splits before starting multi-model training."}), 422
        with pipeline_start_lock:
            with training_lock:
                if training_state["status"] in ("queued", "running"):
                    return jsonify({"status": "failed", "message": "Baseline training is already running. Wait for it to finish before starting multi-model training."}), 409
            current_state = _read_ensemble_state(root)
            if current_state["status"] in ("queued", "running"):
                return jsonify(current_state), 409
            state = _start_ensemble_process(root)
        return jsonify(state), 202

    @app.get("/api/ensemble/status")
    def api_ensemble_status():
        root = Path(app.root_path).parents[1]
        return jsonify(_read_ensemble_state(root))

    @app.post("/api/federated/start")
    def api_federated_start():
        global federated_state
        payload = request.get_json(silent=True) or {}
        try:
            rounds = max(1, min(20, int(payload.get("rounds", 5))))
        except (TypeError, ValueError):
            return jsonify({"status": "failed", "message": "Rounds must be a whole number between 1 and 20."}), 400
        root = Path(app.root_path).parents[1]
        status_path = root / "reports" / "federated" / "status.json"
        if not (root / "data" / "splits" / "train.csv").is_file() or not (root / "data" / "splits" / "test.csv").is_file():
            return jsonify({"status": "failed", "message": "Create train and held-out test splits before starting federated training."}), 422
        if not Config.MODEL_PATH.is_file():
            return jsonify({"status": "failed", "message": "The configured initial global checkpoint is missing."}), 422
        with federated_lock:
            try:
                existing = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = federated_state
            if existing.get("status") in ("queued", "running"):
                return jsonify(existing), 409
            federated_state = {"status": "queued", "run_id": __import__("uuid").uuid4().hex, "message": "Federated training queued.", "progress": 0, "round": 0, "rounds": rounds, "current_stage": "initialize", "current_client": None, "clients": [], "round_history": [], "stages": {}, "dp_clip_norm": 1.0, "dp_noise_multiplier": 0.10, "started_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "logs": []}
            status_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json_atomic(status_path, federated_state)
        Thread(target=_run_federated, args=(root, rounds, 1, 0.10), daemon=True).start()
        return jsonify(federated_state), 202

    @app.get("/api/federated/status")
    def api_federated_status():
        global federated_state
        root = Path(app.root_path).parents[1]
        try:
            state = json.loads((root / "reports" / "federated" / "status.json").read_text(encoding="utf-8"))
            if state.get("status") in ("queued", "running") and state.get("pid"):
                try:
                    os.kill(int(state["pid"]), 0)
                except (OSError, ValueError):
                    state.update({"status": "failed", "message": "The federated training worker stopped unexpectedly. Start a new run to retry.", "error": "Worker process is no longer active."})
                    _write_json_atomic(root / "reports" / "federated" / "status.json", state)
            with federated_lock:
                federated_state = state
            return jsonify(_json_safe(state))
        except (OSError, json.JSONDecodeError):
            with federated_lock:
                return jsonify(federated_state)

    @app.get("/api/federated/results")
    def api_federated_results():
        root = Path(app.root_path).parents[1]
        path = root / "reports" / "federated" / "evaluation.json"
        if not path.is_file():
            return jsonify({"status": "pending", "message": "Global model evaluation pending"})
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
            result.update({"status": "completed", "evaluated_at": __import__("datetime").datetime.fromtimestamp(path.stat().st_mtime, __import__("datetime").timezone.utc).isoformat()})
            return jsonify(result)
        except (OSError, json.JSONDecodeError):
            return jsonify({"status": "failed", "message": "Global model evaluation failed"}), 500

    @app.get("/api/federated/example-sample")
    def api_federated_example_sample():
        root = Path(app.root_path).parents[1]
        sample = _federated_training_example(root)
        if sample is None:
            return jsonify({"error": "No matching retinal image was found for the federated training split."}), 404
        return jsonify({"id": sample["id"], "diagnosis": sample["diagnosis"], "label": sample["label"], "image_url": url_for("api_federated_example_sample_image")})

    @app.get("/api/federated/example-sample/image")
    def api_federated_example_sample_image():
        root = Path(app.root_path).parents[1]
        sample = _federated_training_example(root)
        if sample is None:
            return jsonify({"error": "No matching retinal image was found for the federated training split."}), 404
        return send_from_directory(sample["path"].parent, sample["path"].name, conditional=True)

    @app.get("/api/federated/logs")
    def api_federated_logs():
        root = Path(app.root_path).parents[1]
        try:
            state = json.loads((root / "reports" / "federated" / "status.json").read_text(encoding="utf-8"))
            return jsonify(_json_safe({"logs": state.get("logs", []), "error": state.get("error")}))
        except (OSError, json.JSONDecodeError):
            return jsonify({"logs": [], "error": None})

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="Page not found"), 404
