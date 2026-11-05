document.addEventListener('DOMContentLoaded', () => {
	fetch('/api/status').then(r => r.json()).then(status => {
		const dataset = document.getElementById('dataset-status');
		const model = document.getElementById('model-status');
		const summary = document.getElementById('model-summary');
		if (dataset) dataset.textContent = status.dataset ? 'Ready' : 'Not configured';
		if (model) model.textContent = status.model ? '2 verified models' : 'Not trained';
		if (summary && status.ensemble && status.ensemble.metrics) {
			const models = Object.entries(status.ensemble.metrics);
			const best = models.reduce((winner, entry) => (entry[1].accuracy || 0) > (winner[1].accuracy || 0) ? entry : winner, models[0]);
			summary.textContent = `${models.map(([name, metric]) => `${name}: ${(metric.accuracy * 100).toFixed(1)}%`).join(' | ')}. Best: ${best[0]}.`;
		}
	}).catch(() => {});

	const input = document.getElementById('image-input');
	if (input) input.addEventListener('change', () => {
		const file = input.files && input.files[0];
		const preview = document.getElementById('image-preview');
		const label = document.getElementById('upload-label');
		if (!file) return;
		if (preview) { preview.src = URL.createObjectURL(file); preview.hidden = false; }
		if (label) label.textContent = file.name;
	});

	const form = document.getElementById('prediction-form');
	if (form) form.addEventListener('submit', async event => {
		event.preventDefault();
		const result = document.getElementById('prediction-result');
		if (!input || !input.files || !input.files[0]) { if (result) result.textContent = 'Choose an image first.'; return; }
		if (result) result.textContent = 'Validating image and running model...';
		try {
			const response = await fetch('/api/predict', {method: 'POST', body: new FormData(form)});
			const data = await response.json();
			if (!response.ok) throw new Error(data.error);
			const probabilities = Object.entries(data.probabilities).map(([name, value]) => `<div class="probability"><span>${name}</span><b>${(value * 100).toFixed(1)}%</b><i style="width:${value * 100}%"></i></div>`).join('');
			const models = (data.available_models || []).map(model => `${model.architecture}: ${typeof model.test_accuracy === 'number' ? (model.test_accuracy * 100).toFixed(1) + '%' : '--'}`).join(' | ');
			if (result) result.innerHTML = `<h3>${data.class_name}</h3><p>Confidence: ${(data.confidence * 100).toFixed(1)}%${data.uncertain ? ' - uncertain prediction' : ''}</p><p><b>Best verified model:</b> ${data.best_model || data.model_source}</p><small>Available models: ${models}</small><div>${probabilities}</div>${data.gradcam_url ? `<p class="label">GRAD-CAM EXPLANATION</p><img src="${data.gradcam_url}" alt="Grad-CAM explanation" style="max-width:100%">` : `<p>${data.gradcam_error || ''}</p>`}`;
		} catch (error) { if (result) result.textContent = error.message; }
	});

	const validate = document.getElementById('validate-dataset');
	if (validate) validate.addEventListener('click', async () => {
		const output = document.getElementById('training-output');
		if (output) output.textContent = 'Validating...';
		const response = await fetch('/api/validate-dataset', {method: 'POST'});
		if (output) output.textContent = JSON.stringify(await response.json(), null, 2);
	});

	const gemini = document.getElementById('gemini-review');
	if (gemini) gemini.addEventListener('click', async () => {
		const output = document.getElementById('gemini-result');
		if (!input || !input.files || !input.files[0]) { if (output) output.textContent = 'Choose an image first.'; return; }
		gemini.disabled = true;
		if (output) output.textContent = 'Requesting research second opinion...';
		try {
			const response = await fetch('/api/gemini-review', {method: 'POST', body: new FormData(form)});
			const body = await response.text();
			let data;
			try { data = JSON.parse(body); } catch (_) { throw new Error(`Gemini returned an invalid server response (${response.status}).`); }
			if (!response.ok) throw new Error(data.error);
			const observations = Array.isArray(data.possible_observations) ? data.possible_observations.join(' ') : String(data.possible_observations || '');
			if (output) output.innerHTML = `<p class="label">GEMINI SECOND OPINION</p><p>${observations}</p><p>${data.review_recommendation || ''}</p><small>${data.disclaimer || ''}</small>`;
		} catch (error) { if (output) output.textContent = error.message; } finally { gemini.disabled = false; }
	});

	const start = document.getElementById('start-training');
	const federated = document.getElementById('start-federated');
	if (federated) federated.addEventListener('click', async () => {
		const output = document.getElementById('federated-output');
		const progress = document.getElementById('federated-progress');
		const message = document.getElementById('federated-message');
		federated.disabled = true;
		const roundsInput = document.getElementById('federated-rounds');
		const rounds = Math.max(1, Math.min(20, Number(roundsInput && roundsInput.value) || 5));
		const response = await fetch('/api/federated/start', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({rounds})});
		if (output) output.textContent = JSON.stringify(await response.json(), null, 2);
		const poll = setInterval(async () => {
			const status = await (await fetch('/api/federated/status')).json();
			if (progress) progress.style.width = `${status.progress || 0}%`;
			const clientText = status.client ? `${status.client}: ` : '';
			const dpText = status.status === 'idle' ? 'DP mode: configured at start' : `DP noise=${status.dp_noise}`;
			if (message) message.textContent = `${clientText}${status.message || ''} (${status.progress || 0}%) ${dpText}`;
			if (output) output.textContent = status.output || JSON.stringify(status, null, 2);
			if (status.status === 'completed' || status.status === 'failed') { clearInterval(poll); federated.disabled = false; }
		}, 3000);
	});
	const ensemble = document.getElementById('start-ensemble');
	let ensemblePoll;
	const renderEnsemble = status => {
		const output = document.getElementById('ensemble-output');
		const progress = document.getElementById('ensemble-progress');
		const message = document.getElementById('ensemble-message');
		if (output) output.textContent = status.output || JSON.stringify(status, null, 2);
		if (progress) progress.style.width = `${status.progress || 0}%`;
		if (message) message.textContent = `${status.current_model ? `${status.current_model}: ` : ''}${status.message || ''} (${status.progress || 0}%)`;
		const metrics = document.getElementById('ensemble-metrics');
		if (metrics) metrics.innerHTML = Object.entries(status.metrics || {}).map(([model, values]) => {
			const accuracy = values && typeof values.accuracy === 'number' ? `${(values.accuracy * 100).toFixed(1)}%` : '--';
			const f1 = values && typeof values.macro_f1 === 'number' ? `${(values.macro_f1 * 100).toFixed(1)}%` : '--';
			return `<div class="metric-card"><b>${model}</b><span>Test accuracy: ${accuracy}</span><span>Macro F1: ${f1}</span></div>`;
		}).join('');
	};
	const stopEnsemblePolling = () => {
		if (ensemblePoll) clearInterval(ensemblePoll);
		ensemblePoll = undefined;
	};
	const refreshEnsemble = async () => {
		const response = await fetch('/api/ensemble/status');
		const status = await response.json();
		if (!response.ok) throw new Error(status.message || status.error || `Unable to read training status (${response.status}).`);
		renderEnsemble(status);
		if (status.status === 'completed' || status.status === 'failed') {
			stopEnsemblePolling();
			if (ensemble) ensemble.disabled = false;
		}
		return status;
	};
	const startEnsemblePolling = () => {
		stopEnsemblePolling();
		ensemblePoll = setInterval(async () => {
			try {
				await refreshEnsemble();
			} catch (error) {
				stopEnsemblePolling();
				if (ensemble) ensemble.disabled = false;
				const message = document.getElementById('ensemble-message');
				if (message) message.textContent = error.message;
			}
		}, 5000);
	};
	if (ensemble) {
		refreshEnsemble().then(status => {
			if (status.status === 'queued' || status.status === 'running') {
				ensemble.disabled = true;
				startEnsemblePolling();
			}
		}).catch(() => {});
	}
	if (ensemble) ensemble.addEventListener('click', async () => {
		ensemble.disabled = true;
		try {
			const response = await fetch('/api/ensemble/start', {method: 'POST'});
			const status = await response.json();
			if (!response.ok) throw new Error(status.message || status.error || `Unable to start training (${response.status}).`);
			renderEnsemble(status);
			startEnsemblePolling();
		} catch (error) {
			ensemble.disabled = false;
			const output = document.getElementById('ensemble-output');
			const message = document.getElementById('ensemble-message');
			if (message) message.textContent = error.message;
			if (output) output.textContent = error.message;
		}
	});
	const history = document.getElementById('training-history');
	if (history) fetch('/api/training/history').then(response => response.json()).then(data => {
		if (!data.history || !data.history.length) return;
		history.innerHTML = '<div class="history-grid"><b>Model</b><b>Stage</b><b>Epoch</b><b>Accuracy</b><b>Validation accuracy</b>' + data.history.map(row => `<span>${row.model}</span><span>${row.stage}</span><span>${row.epoch}</span><span>${row.accuracy === undefined ? '--' : (row.accuracy * 100).toFixed(1) + '%'}</span><span>${row.val_accuracy === undefined ? '--' : (row.val_accuracy * 100).toFixed(1) + '%'}</span>`).join('') + '</div>';
	}).catch(() => {});
	if (start) start.addEventListener('click', async () => {
		const output = document.getElementById('training-output');
		start.disabled = true;
		const response = await fetch('/api/training/start', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({epochs: 1, batch_size: 32})});
		if (output) output.textContent = JSON.stringify(await response.json(), null, 2);
		const poll = setInterval(async () => {
			const status = await (await fetch('/api/training/status')).json();
			if (output) output.textContent = JSON.stringify(status, null, 2);
			if (status.status === 'completed' || status.status === 'failed') { clearInterval(poll); start.disabled = false; }
		}, 3000);
	});
});
