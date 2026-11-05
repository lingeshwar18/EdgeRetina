# EdgeRetina

EdgeRetina is a local research application for five-class diabetic-retinopathy image classification using the APTOS 2019 Blindness Detection dataset. It combines a MobileNetV3Small baseline, explicit metadata validation, simulated FedAvg clients, and an experimental clip-and-noise privacy mechanism.

## Important scope

This is a research tool, not a clinical diagnostic system. A softmax confidence is not clinical certainty. The privacy module clips and perturbs updates but does not claim a formal epsilon/delta guarantee because no privacy accountant is included. No prediction or metric is fabricated: the UI shows unavailable until artifacts are generated.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Place the Kaggle APTOS files at `data/raw/train.csv` and `data/raw/train_images/`, or set `APTOS_CSV_PATH` and `APTOS_IMAGE_DIR` in `.env`. The CSV must contain `id` and `diagnosis`.

The canonical mapping is shared everywhere: 0 No DR, 1 Mild DR, 2 Moderate DR, 3 Severe DR, 4 Proliferative DR.

Train the two-model ensemble with `python scripts/train_ensemble.py --epochs 2 --batch-size 64`. Completed checkpoints with valid metadata are stored under `models/ensemble/` and automatically used by the prediction agent. Per-epoch training and validation accuracy is stored under `reports/metrics/` and displayed on the Training page.

## Prediction agent

`backend/app/services/prediction_agent.py` is the single prediction orchestration layer. It validates image quality, loads only metadata-compatible checkpoints, averages original and horizontal-flip TTA, supports additional verified checkpoints under `models/ensemble/`, calculates entropy and expected ordinal severity, and returns an explicit uncertainty flag. Grad-CAM is generated separately from the selected local model. The agent does not force low-confidence results into `No DR` and does not use Gemini as a classifier.

Run the dataset analysis before model experiments:

```powershell
python scripts/analyze_dataset.py
```

The analysis is saved to `reports/validation/dataset_analysis.json` and records the 9.35:1 majority/minority imbalance and class distribution in each deterministic split.

## Commands

```powershell
python scripts/validate_dataset.py
python scripts/make_splits.py
python -m pytest
python backend/run.py
```

Open `http://127.0.0.1:5000`. The prediction route refuses to run until a trained `.keras` file and matching `metadata.json` exist under `models/global/`. Metadata must identify five classes, image size `[224, 224]`, preprocessing version `edgeretina-preprocess-v1`, and `trained: true`.

Open `http://127.0.0.1:5000/federated` for the Federated Learning Dashboard. It requires `data/splits/train.csv`, the held-out `data/splits/test.csv`, the configured initial global checkpoint, and the APTOS image directory. Start training from the page. The final global model is saved to `models/federated/edgeretina_federated.keras`; its held-out evaluation is persisted at `reports/federated/evaluation.json`, with live job state in `reports/federated/status.json`.

## Architecture

The Flask UI calls one prediction service. That service validates image quality, applies the same central preprocessing function used by training, loads only a metadata-verified model, returns all five probabilities, and records the result in SQLite. Dataset validation writes JSON and CSV artifacts under `reports/validation/`; evaluation writes generated metrics under `reports/metrics/`.

The federated runner reuses `fedavg.py` for sample-weighted aggregation and `differential_privacy.py` for update clipping and parameter-count-normalized Gaussian perturbation. It rejects non-finite client updates and global weights before checkpointing, trains four simulated client partitions, saves and reloads each global checkpoint, then evaluates the final model on the held-out test split. The dashboard reports real run state and does not treat the prior federated checkpoint as a newly evaluated run.

## Limitations

CPU training on APTOS can take substantial time. The federated worker runs in a background thread and its status is persisted, but duplicate-job coordination is designed for the current single Flask process/development setup. Use one application process for training; a multi-worker deployment should use a shared task queue or cross-process lock. The app does not download Kaggle data or invent a checkpoint when prerequisites are absent. Grad-CAM is available as a service and requires a loaded convolutional model.

For stronger measured candidates, run the comparable experiment suite. It trains MobileNetV3Small with weighted cross-entropy and EfficientNetB0 with focal loss, keeping the test split untouched until each candidate is evaluated:

```powershell
python scripts/run_experiments.py --epochs 2 --batch-size 64
```

Results are written to `reports/experiments/results.json`. Select a checkpoint only from measured validation macro-F1/QWK and test metrics; Grad-CAM explains a selected model but does not increase its accuracy.
