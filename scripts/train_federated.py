import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Config
from app.federated.server import run_federated
from app.config import CLASS_NAMES, IMAGE_SIZE, PREPROCESSING_VERSION, SEED

parser = argparse.ArgumentParser()
parser.add_argument("--rounds", type=int, default=1)
parser.add_argument("--local-epochs", type=int, default=1)
parser.add_argument("--dp-noise", type=float, default=0.0)
parser.add_argument("--status-file", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
def progress(event):
    try:
        state = json.loads(args.status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    state.update({key: value for key, value in event.items() if key not in ("stage", "stage_status", "client", "client_status", "round_record")})
    stages = state.setdefault("stages", {})
    if event.get("stage"):
        state["current_stage"] = event["stage"]
        stages[event["stage"]] = {"status": event.get("stage_status", "running"), "message": event.get("message", "")}
    if event.get("client"):
        state["current_client"] = event["client"] if event.get("client_status") == "running" else None
        clients = state.setdefault("clients", [])
        client = next((row for row in clients if row.get("id") == event["client"]), None)
        if client is None:
            client = {"id": event["client"]}
            clients.append(client)
        client.update({key: value for key, value in event.items() if key not in ("stage", "stage_status", "client", "client_status", "round_record", "message")})
        client.update({"status": event.get("client_status", client.get("status", "pending")), "message": event.get("message", "")})
    if event.get("round_record"):
        history = state.setdefault("round_history", [])
        history.append(event["round_record"])
    if event.get("evaluation"):
        event["evaluation"]["run_id"] = state.get("run_id")
        evaluation_path = root / "reports" / "federated" / "evaluation.json"
        evaluation_path.parent.mkdir(parents=True, exist_ok=True)
        temp_evaluation = evaluation_path.with_suffix(".json.tmp")
        temp_evaluation.write_text(json.dumps(event["evaluation"], indent=2), encoding="utf-8")
        temp_evaluation.replace(evaluation_path)
    state["message"] = event.get("message", state.get("message", ""))
    state["status"] = "running"
    logs = state.setdefault("logs", [])
    if event.get("message"):
        logs.append(event["message"])
        del logs[:-100]
    rounds = max(state.get("rounds", 1), 1)
    done_rounds = state.get("completed_rounds", 0)
    stage = state.get("current_stage")
    if stage in ("client_training", "processing") and state.get("round", 0):
        round_number = state.get("round", done_rounds + 1)
        completed_clients = sum(1 for client in state.get("clients", []) if client.get("round") == round_number and client.get("status") == "completed")
        state["progress"] = min(85, int(5 + 80 * ((round_number - 1 + completed_clients / 4) / rounds)))
    else:
        state["progress"] = {"initialize": 1, "dataset": 2, "partition": 3, "distribute": 5, "processing": 86, "aggregation": 88, "checkpoint": 90, "evaluation": 94}.get(stage, min(90, int(5 + 80 * done_rounds / rounds)))
    state["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    temp = args.status_file.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(args.status_file)
model_path = root / "models" / "federated" / "edgeretina_federated.keras"
result = run_federated(root / "data" / "splits" / "train.csv", Config.IMAGE_DIR, Config.MODEL_PATH, model_path, root / "reports" / "federated" / "rounds.json", root / "reports" / "federated" / "client_distribution.csv", args.rounds, args.local_epochs, args.dp_noise, root / "data" / "splits" / "test.csv", root / "reports" / "federated" / "evaluation.json", progress)
(model_path.parent / "metadata.json").write_text(json.dumps({"architecture": "Federated MobileNetV3Small", "num_classes": len(CLASS_NAMES), "class_names": {str(k): v for k, v in CLASS_NAMES.items()}, "image_size": list(IMAGE_SIZE), "preprocessing_version": PREPROCESSING_VERSION, "training_seed": SEED, "trained": True, "federated": True, "dp_clip_norm": 1.0, "dp_noise_multiplier": args.dp_noise}, indent=2), encoding="utf-8")
print(result, flush=True)
