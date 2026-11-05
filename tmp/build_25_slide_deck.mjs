import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import JSZip from 'jszip';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';
import { pathToFileURL } from 'node:url';

const workspaceDir = 'C:/Users/linge/capstoneproject';
const sourcePath = 'C:/Users/linge/AppData/Local/Packages/5319275A.WhatsAppDesktop_cv1g1gvanyjgm/LocalState/sessions/FB754F599DDCCC6DFD0F0C4D66F8F68913DA5298/transfers/2026-41/22MIS0558_INHOUSE.pptx';
const reportPath = 'C:/Users/linge/AppData/Local/Packages/5319275A.WhatsAppDesktop_cv1g1gvanyjgm/LocalState/sessions/FB754F599DDCCC6DFD0F0C4D66F8F68913DA5298/transfers/2026-43/22MIS558final_document.pdf';
const projectRoot = 'C:/Users/linge/capstoneproject';
const buildDir = path.join(workspaceDir, 'tmp', 'edgeretina-review25-v5');
const outputDir = path.join(workspaceDir, 'output', 'pptx');
const candidatePath = path.join(buildDir, 'candidate.pptx');
const finalPath = path.join(outputDir, 'EdgeRetina_Second_Review_25_Slides_v5.pptx');
const font = 'Garamond';
const ink = '#262626';
const teal = '#28685F';
const muted = '#5D5D5D';
const warm = '#EFEFE9';
const white = '#FFFFFF';
const W = 1280;
const H = 720;
const nodeModules = 'C:/Users/linge/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES = nodeModules;

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });
if (await exists(finalPath)) throw new Error(`Output already exists: ${finalPath}`);

const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
if (presentation.slides.items.length !== 16) throw new Error('Expected the supplied 16-slide review deck');
const originalSlides = [...presentation.slides.items];

function addText(slide, name, text, pos, opts = {}) {
  return slide.shapes.add({
    geometry: 'textbox', name, position: pos, fill: 'none',
    line: { style: 'solid', fill: 'none', width: 0 }, insets: 0,
    text: { text, style: {
      fontSize: opts.size ?? 22, typeface: opts.font ?? font,
      color: opts.color ?? ink, bold: opts.bold ?? false,
      alignment: opts.align ?? 'left',
    } },
  });
}

function addRule(slide, name, x, y, width, color = '#A79D8C') {
  return slide.shapes.add({
    geometry: 'line', name, position: { left: x, top: y, width, height: 0 },
    fill: 'none', line: { style: 'solid', fill: color, width: 1.2 },
  });
}

function addSlide(title, index, notes) {
  const slide = presentation.slides.add({ layout: 'Title and Content' });
  addText(slide, `title_${index}`, title, { left: 105, top: 66, width: 1070, height: 92 }, { size: 48, bold: true, align: 'center' });
  slide.speakerNotes.text = notes;
  slide.speakerNotes.setVisible(true);
  return slide;
}

async function readImage(pathname) {
  return new Uint8Array(await fs.readFile(pathname));
}

// Keep the source deck's Garamond, textured white template and side ornaments.
// Correct privacy language that overstated the prototype's guarantee.
const edits = [
  ['sh/547294r6', 'Privacy-Preserving', 'Privacy-Aware'],
  ['sh/ozy1ofad', 'Privacy-Preserving Model Updates', 'Privacy-Inspired Update Processing'],
  ['sh/xc3mho32', 'PRIVACY-PRESERVING MECHANISM', 'PRIVACY-INSPIRED UPDATE PROCESSING'],
  ['sh/xcryxg7y', 'Formula used for privacy preserving', 'UPDATE CLIPPING FORMULA'],
  ['sh/k3y5ov21', 'privacy-preserving model updates', 'privacy-inspired update processing'],
];
for (const [id, from, to] of edits) {
  const shape = presentation.resolve(id);
  shape.text.replace(from, to);
}
const clipFormula = presentation.resolve('sh/wbih4b6d');
clipFormula.text.replace(clipFormula.text.toString(), 'Update clipping\n\nΔₖᶜˡⁱᵖ = Δₖ × min(1, C / ‖Δₖ‖₂)');
const noiseBlock = presentation.resolve('sh/0f2lgnmp');
// Rebuild the two original privacy slides because the supplied formula and
// diagram overlapped and displayed raw LaTeX in the source deck.
presentation.delete(['sh/cbu58j2h', 'sh/zelojyl8', 'sh/wbih4b6d', 'im/0juh0bih', 'tb/up4zmdcb', 'sh/0f2lgnmp', 'im/721szuh0', 'im/943a14fq']);
const clipDiagram = presentation.slides.getItem(9);
addText(clipDiagram, 'clip_explain_heading', 'CLIPPING', { left: 175, top: 275, width: 400, height: 42 }, { size: 27, color: teal, bold: true, align: 'center' });
addText(clipDiagram, 'clip_explain_body', 'Measure the L2 norm of the full client update. If it exceeds C, scale the update down to the bound.', { left: 165, top: 335, width: 420, height: 125 }, { size: 23, align: 'center' });
addText(clipDiagram, 'noise_explain_heading', 'GAUSSIAN NOISE', { left: 700, top: 275, width: 400, height: 42 }, { size: 27, color: teal, bold: true, align: 'center' });
addText(clipDiagram, 'noise_explain_body', 'Add zero-mean random noise to the clipped update before the server aggregates it.', { left: 690, top: 335, width: 420, height: 125 }, { size: 23, align: 'center' });
addText(clipDiagram, 'clip_noise_formula', 'Δprocessed = Δclip + η', { left: 285, top: 500, width: 710, height: 45 }, { size: 29, bold: true, align: 'center' });
addText(clipDiagram, 'clip_noise_caveat', 'Privacy-inspired processing. This prototype does not calculate a formal privacy budget.', { left: 235, top: 575, width: 810, height: 38 }, { size: 17, color: '#7A5136', align: 'center' });
clipDiagram.speakerNotes.text = 'Clipping limits the influence of an update by bounding its L2 norm. Gaussian perturbation is added after clipping and before FedAvg. This implementation does not include a privacy accountant or formal (ε, δ) guarantee. Source: backend/app/federated/differential_privacy.py; final report §§6.5.1–6.5.4, printed pp. 36–38.';
clipDiagram.speakerNotes.setVisible(true);

const formulaSlide = presentation.slides.getItem(10);
addText(formulaSlide, 'clip_formula_explain', 'Clipping bounds the L2 norm of the full update.', { left: 155, top: 260, width: 970, height: 44 }, { size: 26, bold: true, align: 'center' });
addText(formulaSlide, 'clip_formula_math', 'Δclip = Δ × min(1, C / ‖Δ‖₂)', { left: 155, top: 330, width: 970, height: 60 }, { size: 34, color: teal, bold: true, align: 'center' });
addText(formulaSlide, 'clip_formula_example', 'Example: Δ = [3, 4], ‖Δ‖₂ = 5, C = 1\nScale = 1 / 5, so Δclip = [0.6, 0.8]', { left: 230, top: 420, width: 820, height: 100 }, { size: 25, align: 'center' });
addText(formulaSlide, 'clip_formula_definition', 'C is the maximum allowed L2 norm for one client update.', { left: 220, top: 545, width: 840, height: 38 }, { size: 19, color: muted, align: 'center' });
formulaSlide.speakerNotes.text = 'Walk through the small vector example, stressing that it makes the norm calculation visible. The actual model update contains many parameter arrays, and the code computes one global L2 norm across all of them. Source: backend/app/federated/differential_privacy.py and final report §6.5.1, printed p. 36.';
formulaSlide.speakerNotes.setVisible(true);

const gaussianSlide = presentation.slides.getItem(11);
addText(gaussianSlide, 'noise_title', 'GAUSSIAN NOISE IN THIS PROTOTYPE', { left: 115, top: 90, width: 1050, height: 80 }, { size: 45, bold: true, align: 'center' });
addText(gaussianSlide, 'noise_formula', 'Δprocessed = Δclip + η\nηᵢ ~ N(0, σ²)\n\nσ = C × 0.10 / √M', { left: 170, top: 220, width: 940, height: 245 }, { size: 34, color: ink, bold: true, align: 'center' });
addText(gaussianSlide, 'noise_definition', 'M is the number of model parameters. The code scales noise per parameter so the expected full-update noise norm remains bounded.', { left: 205, top: 495, width: 870, height: 70 }, { size: 20, align: 'center' });
addText(gaussianSlide, 'noise_warning', 'No accountant or formal (ε, δ) differential-privacy guarantee is implemented.', { left: 190, top: 580, width: 900, height: 34 }, { size: 18, color: '#7A5136', bold: true, align: 'center' });
gaussianSlide.speakerNotes.text = 'η is a zero-mean Gaussian perturbation. In this implementation, the standard deviation per model parameter is clip_norm × noise_multiplier / sqrt(parameter_count); the current dashboard sets noise_multiplier to 0.10. This is an experimental privacy-inspired operation, not a formal guarantee. Source: backend/app/federated/differential_privacy.py, backend/app/routes.py, README.md, final report §§6.5.2–6.5.4.';
gaussianSlide.speakerNotes.setVisible(true);

const limitationsText = presentation.resolve('sh/wbydknq1');
limitationsText.text.replace('\\((\\epsilon,\\delta)\\)', '(ε, δ)');

const added = [];

// 1. Literature findings from the supplied final report.
{
  const s = addSlide('FINDINGS FROM THE LITERATURE', 'lit_findings',
    'Explain that these are the report’s synthesis of prior studies, not results from EdgeRetina. Deep learning papers establish task feasibility; FL supports data locality but brings client and communication issues; formal DP needs an accountant; Grad-CAM is a coarse visual explanation. Sources: final report §§2.3–2.4, printed pp. 8–10. Key studies: Gulshan et al. (2016), Ting et al. (2017), McMahan et al. (2017), Rieke et al. (2020), Sheller et al. (2020), Abadi et al. (2016), Dwork and Roth (2014), Zhu et al. (2019), Selvaraju et al. (2017).');
  const rows = [
    ['DEEP LEARNING', 'Fundus-image studies show that automated DR analysis is feasible. Strong results often use large, centrally collected datasets.'],
    ['FEDERATED LEARNING', 'FedAvg gives institutions a way to train on local data. Client differences and communication remain practical challenges.'],
    ['PRIVACY', 'Updates can reveal information. Clipping and noise can reduce exposure, while formal differential privacy also needs calibrated accounting.'],
    ['EXPLAINABILITY', 'Grad-CAM highlights image regions related to a class score. Its heatmap is coarse and does not segment lesions.'],
  ];
  rows.forEach(([label, body], i) => {
    const y = 190 + i * 93;
    addText(s, `lit_label_${i}`, label, { left: 98, top: y, width: 260, height: 34 }, { size: 20, color: teal, bold: true });
    addText(s, `lit_body_${i}`, body, { left: 355, top: y - 2, width: 815, height: 70 }, { size: 21 });
    if (i < rows.length - 1) addRule(s, `lit_rule_${i}`, 98, y + 77, 1074, '#C7C2B7');
  });
  added.push(s);
}

// 2. Position the prototype against the research gap described in the report.
{
  const s = addSlide('PROJECT GAP AND POSITIONING', 'research_gap',
    'The report positions EdgeRetina as a student-scale integration prototype. It does not claim state-of-the-art performance, formal privacy protection or clinical validation. Source: final report §2.5, printed p. 11, plus project README and current application modules.');
  addText(s, 'gap_statement', 'One runnable application connects five-grade classification, simulated federation, update processing and visual explanation.', { left: 110, top: 190, width: 1060, height: 82 }, { size: 29, bold: true, align: 'center' });
  addText(s, 'gap_heading_a', 'WHAT THE PROJECT DEMONSTRATES', { left: 115, top: 315, width: 480, height: 34 }, { size: 20, color: teal, bold: true });
  addText(s, 'gap_body_a', 'APTOS validation and preprocessing\nTwo transfer-learning backbones\nFour simulated clients with FedAvg\nClipping and Gaussian-noise processing\nFlask interface, prediction history and Grad-CAM', { left: 115, top: 360, width: 510, height: 205 }, { size: 22 });
  addText(s, 'gap_heading_b', 'HOW TO INTERPRET IT', { left: 690, top: 315, width: 470, height: 34 }, { size: 20, color: '#7A5136', bold: true });
  addText(s, 'gap_body_b', 'A prototype, not a clinical device\nFour clients run as software simulations\nNo formal (ε, δ) privacy guarantee\nResults need stronger minority-grade recall\nExternal and multi-site validation remain future work', { left: 690, top: 360, width: 500, height: 205 }, { size: 22 });
  added.push(s);
}

// 3. A real training image, linked to its APTOS training record.
{
  const s = addSlide('TRAINING EXAMPLE: APTOS NO DR', 'training_sample',
    'This is an actual fundus photograph from the project training split, id_code 38f1901f214a, diagnosis 0 (No DR). Use it to explain the model input, not as a clinical example or diagnostic claim. Source: data/splits/train.csv and data/raw/train_images/38f1901f214a.png.');
  const imagePath = path.join(projectRoot, 'data', 'raw', 'train_images', '38f1901f214a.png');
  s.images.add({ blob: await readImage(imagePath), contentType: 'image/png', alt: 'APTOS training-set retinal fundus image, sample id 38f1901f214a, grade No DR', fit: 'contain', position: { left: 90, top: 185, width: 620, height: 420 } });
  addText(s, 'sample_record', 'TRAINING SPLIT', { left: 775, top: 235, width: 360, height: 35 }, { size: 19, color: teal, bold: true });
  addText(s, 'sample_label', 'No DR\nGrade 0', { left: 775, top: 282, width: 380, height: 112 }, { size: 38, bold: true });
  addText(s, 'sample_id', 'Sample id\n38f1901f214a', { left: 775, top: 405, width: 390, height: 74 }, { size: 22 });
  addText(s, 'sample_process', 'The pipeline validates and resizes the image before model input. The original image remains in the local project dataset.', { left: 775, top: 505, width: 390, height: 92 }, { size: 20, color: muted });
  added.push(s);
}

// 4. Centralized test comparison as an editable native chart.
{
  const s = addSlide('CENTRALIZED TEST RESULTS', 'central_results',
    'These centralized values come from the report’s held-out 550-image test set. EfficientNetB0 has the best accuracy (71.1%); MobileNetV3Small has slightly better macro-F1 (42.0% vs 40.9%). Accuracy and macro-F1 differ because class performance is uneven. Source: final report, Chapter 9, Table 9.3 and §9.11, printed pp. 61–66; reports/experiments/mobilenetv3small.json and efficientnetb0.json.');
  addText(s, 'central_caption', 'Held-out test set: 550 images  |  higher is better', { left: 120, top: 175, width: 1040, height: 34 }, { size: 20, color: muted, align: 'center' });
  const chart = s.charts.add('bar', {
    position: { left: 100, top: 220, width: 760, height: 360 },
    categories: ['Accuracy', 'Macro-F1'],
    series: [
      { name: 'MobileNetV3Small', values: [0.6327, 0.4201], fill: '#28685F' },
      { name: 'EfficientNetB0', values: [0.7109, 0.4092], fill: '#9B7950' },
    ],
    barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 90 },
    hasLegend: true,
    legend: { position: 'bottom', textStyle: { typeface: font, fontSize: 15, fill: ink } },
    xAxis: { textStyle: { typeface: font, fontSize: 17, fill: ink }, majorGridlines: null },
    yAxis: { min: 0, max: 0.8, majorUnit: 0.2, numberFormatCode: '0%', textStyle: { typeface: font, fontSize: 15, fill: muted }, majorGridlines: { style: 'solid', fill: '#D8D4CC', width: 1 } },
    dataLabels: { showValue: true, position: 'outEnd', numberFormatCode: '0.0%', textStyle: { typeface: font, fontSize: 14, fill: ink, bold: true } },
    chartFill: 'none', chartLine: { style: 'solid', fill: 'none', width: 0 }, plotAreaFill: 'none', plotAreaLine: { style: 'solid', fill: 'none', width: 0 },
  });
  addText(s, 'central_takeaway', '71.1%\nEfficientNetB0 accuracy', { left: 900, top: 285, width: 300, height: 82 }, { size: 26, bold: true, align: 'center' });
  addText(s, 'central_macro', '42.0%\nMobileNetV3Small macro-F1', { left: 900, top: 410, width: 300, height: 82 }, { size: 25, color: teal, bold: true, align: 'center' });
  addText(s, 'central_note', 'Macro-F1 gives each of the five grades equal weight.', { left: 890, top: 520, width: 330, height: 58 }, { size: 18, color: muted, align: 'center' });
  added.push(s);
}

// 5. A later saved dashboard run, clearly distinguished from report results.
{
  const s = addSlide('SAVED FIVE-ROUND FEDERATED EVALUATION', 'federated_result',
    'The project now contains reports/federated/evaluation.json for run 68688c55a1864640ab728b6f2032341c: MobileNetV3Small, five completed rounds, 550 held-out test images, accuracy 67.1%, macro-F1 40.1% and QWK 0.687. The report’s original results chapter stated that FL test metrics were unavailable when it was written. Present this as a later saved dashboard evaluation, not as a controlled comparison against the centralized runs. Project files: reports/federated/evaluation.json and reports/federated/rounds.json.');
  addText(s, 'fl_summary', '4 simulated clients  |  5 completed rounds  |  550 held-out images', { left: 112, top: 185, width: 1055, height: 35 }, { size: 20, color: muted, align: 'center' });
  addText(s, 'fl_accuracy', '67.1%', { left: 150, top: 275, width: 300, height: 77 }, { size: 56, bold: true, align: 'center' });
  addText(s, 'fl_accuracy_label', 'Accuracy', { left: 150, top: 355, width: 300, height: 35 }, { size: 22, align: 'center' });
  addText(s, 'fl_f1', '40.1%', { left: 490, top: 275, width: 300, height: 77 }, { size: 56, color: teal, bold: true, align: 'center' });
  addText(s, 'fl_f1_label', 'Macro-F1', { left: 490, top: 355, width: 300, height: 35 }, { size: 22, align: 'center' });
  addText(s, 'fl_qwk', '0.687', { left: 830, top: 275, width: 300, height: 77 }, { size: 56, color: '#7A5136', bold: true, align: 'center' });
  addText(s, 'fl_qwk_label', 'Quadratic weighted kappa', { left: 830, top: 355, width: 300, height: 35 }, { size: 20, align: 'center' });
  addRule(s, 'fl_rule', 130, 430, 1020, '#C7C2B7');
  addText(s, 'fl_caveat', 'Later saved dashboard run. Its result is separate from the report’s centralized model comparison.', { left: 160, top: 470, width: 960, height: 70 }, { size: 22, bold: true, align: 'center' });
  addText(s, 'fl_runid', 'Run id: 68688c55a1864640ab728b6f2032341c', { left: 160, top: 550, width: 960, height: 30 }, { size: 16, color: muted, align: 'center' });
  added.push(s);
}

// 6. Interpret the results by grade rather than accuracy alone.
{
  const s = addSlide('CLASS IMBALANCE AND MODEL BEHAVIOUR', 'class_interpretation',
    'The held-out federated evaluation includes 271 No DR, 56 Mild, 150 Moderate, 29 Severe and 44 Proliferative cases. In the saved five-round checkpoint, severe DR recall is 0.0% (0 of 29), while No DR recall is 95.6%. This is the key caution behind reporting macro-F1 and per-class results alongside accuracy. These metrics describe this saved run only. Source: reports/federated/evaluation.json; report §9.9 and §9.11.');
  addText(s, 'class_intro', 'The held-out set is uneven. The saved federated checkpoint missed all 29 Severe DR cases.', { left: 125, top: 190, width: 1030, height: 66 }, { size: 27, bold: true, align: 'center' });
  const classRows = [
    ['No DR', '271', '95.6%'], ['Mild DR', '56', '21.4%'], ['Moderate DR', '150', '57.3%'], ['Severe DR', '29', '0.0%'], ['Proliferative DR', '44', '27.3%'],
  ];
  addText(s, 'class_header', 'GRADE', { left: 155, top: 292, width: 380, height: 28 }, { size: 17, color: teal, bold: true });
  addText(s, 'support_header', 'TEST SUPPORT', { left: 600, top: 292, width: 220, height: 28 }, { size: 17, color: teal, bold: true, align: 'center' });
  addText(s, 'recall_header', 'FEDERATED RECALL', { left: 835, top: 292, width: 250, height: 28 }, { size: 17, color: teal, bold: true, align: 'center' });
  classRows.forEach(([grade, n, recall], i) => {
    const y = 335 + i * 48;
    addText(s, `class_grade_${i}`, grade, { left: 155, top: y, width: 380, height: 35 }, { size: 21, bold: i === 3 });
    addText(s, `class_support_${i}`, n, { left: 600, top: y, width: 220, height: 35 }, { size: 21, align: 'center' });
    addText(s, `class_recall_${i}`, recall, { left: 835, top: y, width: 250, height: 35 }, { size: 21, color: i === 3 ? '#8C3A2B' : ink, bold: i === 3, align: 'center' });
    if (i < classRows.length - 1) addRule(s, `class_rule_${i}`, 145, y + 36, 970, '#D1CCC2');
  });
  addText(s, 'class_note', 'Accuracy can hide weak performance on less common grades. Macro-F1 and per-class recall show where the model needs work.', { left: 140, top: 590, width: 1000, height: 60 }, { size: 19, color: muted, align: 'center' });
  added.push(s);
}

// 7. A report Grad-CAM figure, framed as a limited explanation.
{
  const s = addSlide('GRAD-CAM: A VISUAL EXPLANATION', 'gradcam',
    'Explain that Grad-CAM highlights image regions that influence a selected class score. The displayed report screenshot is illustrative. It is not a lesion segmentation, proof of model correctness or clinician-validated explanation. Source: final report, Chapter 8, Grad-CAM figure, printed p. 62; project reports/gradcam assets.');
  s.images.add({ blob: await readImage(path.join(workspaceDir, 'tmp', 'reused-media', 'image4.jpeg')), contentType: 'image/jpeg', alt: 'Grad-CAM heatmap example over a retinal fundus image', fit: 'contain', position: { left: 100, top: 190, width: 650, height: 420 } });
  addText(s, 'gradcam_label', 'WHAT THE HEATMAP SHOWS', { left: 800, top: 255, width: 350, height: 34 }, { size: 19, color: teal, bold: true });
  addText(s, 'gradcam_text', 'Warmer regions receive stronger weight in the selected class explanation.\n\nThe overlay helps inspect a prediction. It does not locate or measure lesions.', { left: 800, top: 305, width: 355, height: 170 }, { size: 23 });
  addText(s, 'gradcam_caveat', 'Visual aid only\nNo clinical validation', { left: 800, top: 515, width: 350, height: 60 }, { size: 19, color: '#7A5136', bold: true });
  added.push(s);
}

// 8. New application evidence and the features visible to a faculty audience.
{
  const s = addSlide('EDGE RETINA WEB APPLICATION', 'application',
    'Use the screenshot to show that the project exposes saved experiment evidence in a local Flask interface. The system also provides image prediction, class probabilities, Grad-CAM, prediction history, training controls and a federated status page. Clarify that values come from saved artifacts and local simulated clients. Source: supplied final report, Chapter 8, dashboard figure, printed p. 64; current Flask routes and frontend templates.');
  s.images.add({ blob: await readImage(path.join(workspaceDir, 'tmp', 'reused-media', 'image5.jpeg')), contentType: 'image/jpeg', alt: 'EdgeRetina evidence dashboard screenshot from the project report', fit: 'contain', position: { left: 72, top: 220, width: 640, height: 335 } });
  addText(s, 'app_features_head', 'PROJECT FEATURES', { left: 790, top: 225, width: 360, height: 34 }, { size: 20, color: teal, bold: true });
  addText(s, 'app_features', 'Image upload and five-grade prediction\nPer-class probabilities and confidence\nGrad-CAM explanation\nTraining and federated run status\nPrediction history and saved reports', { left: 790, top: 270, width: 405, height: 240 }, { size: 21 });
  addText(s, 'app_note', 'The federated clients are software simulations running in this project environment.', { left: 790, top: 535, width: 405, height: 58 }, { size: 18, color: muted });
  added.push(s);
}

// 9. Four-step animated privacy-inspired update explanation.
let dpSlide;
{
  const s = addSlide('CLIPPING AND GAUSSIAN NOISE: CLICK TO EXPLAIN', 'dp_animation',
    'PowerPoint animation: click once to reveal each step in order. This example uses an illustrative two-number update, not a real neural-network weight tensor. Start with Δ=[3,4], whose L2 norm is 5. With clip bound C=1, the scale is 1/5, producing Δclip=[0.6,0.8]. Then the implementation adds a zero-mean Gaussian value to each parameter. The code sets per-parameter noise scale to C × noise multiplier / sqrt(M), with multiplier 0.10 and M the number of model parameters. Processed client updates then enter sample-weighted FedAvg. This is privacy-inspired processing, not a formal differential-privacy guarantee: there is no accountant, (ε,δ) budget, secure aggregation or encryption. Source: backend/app/federated/differential_privacy.py, backend/app/federated/fedavg.py, final report §§6.5.1–6.5.4, printed pp. 36–38.');
  const steps = [
    ['dp_step_1', 'CLIENT UPDATE\nΔ = [3, 4]\n‖Δ‖₂ = 5'],
    ['dp_step_2', 'CLIP TO C = 1\nScale = 1 / 5\nΔclip = [0.6, 0.8]'],
    ['dp_step_3', 'ADD GAUSSIAN NOISE\nΔprocessed = Δclip + η\nη ~ N(0, σ²I)'],
    ['dp_step_4', 'FEDAVG INPUT\nAggregate processed updates\nImages stay in local splits'],
  ];
  for (let i = 0; i < steps.length; i++) {
    const x = 48 + i * 296;
    s.shapes.add({
      geometry: 'roundRect', name: steps[i][0], position: { left: x, top: 235, width: 260, height: 205 },
      fill: i === 2 ? '#E7F0EC' : '#F1EFE9', line: { style: 'solid', fill: '#8C8171', width: 1.2 },
      text: { text: steps[i][1], style: { fontSize: 20, typeface: font, color: ink, bold: true, alignment: 'center' } },
    });
    if (i < 3) s.shapes.add({ geometry: 'rightArrow', name: `dp_arrow_${i + 1}`, position: { left: x + 264, top: 320, width: 28, height: 32 }, fill: '#806E58', line: { style: 'solid', fill: 'none', width: 0 } });
  }
  addText(s, 'dp_noise_formula', 'Per-parameter noise scale:  σ = C × 0.10 / √M', { left: 140, top: 475, width: 1000, height: 38 }, { size: 23, bold: true, align: 'center' });
  addText(s, 'dp_caveat', 'Prototype illustration only. No privacy accountant or formal (ε, δ) guarantee is implemented.', { left: 115, top: 545, width: 1050, height: 50 }, { size: 19, color: '#7A5136', bold: true, align: 'center' });
  dpSlide = s;
  added.push(s);
}

// Put literature before objectives, then the new project evidence before the source conclusion.
const slideRecords = await presentation.inspect({ kind: 'slide', maxChars: 30000 });
const canonicalSlideIds = slideRecords.ndjson.split('\n').filter(Boolean).map(line => JSON.parse(line)).filter(item => item.kind === 'slide').sort((a, b) => a.slideIndex - b.slideIndex).map(item => item.id);
const sourceIds = canonicalSlideIds.slice(0, 16);
const newIds = canonicalSlideIds.slice(16);
const order = [
  ...sourceIds.slice(0, 3),
  newIds[0], newIds[1],
  ...sourceIds.slice(3, 13),
  ...newIds.slice(2),
  ...sourceIds.slice(13),
];
presentation.slides.reorder(order);
if (presentation.slides.items.length !== 25) throw new Error(`Expected 25 slides, got ${presentation.slides.items.length}`);

const initialPptx = await PresentationFile.exportPptx(presentation);
await initialPptx.save(candidatePath);

// Add native PowerPoint entrance effects to four named editable diagram shapes.
const zip = await JSZip.loadAsync(await fs.readFile(candidatePath));
const dpIndex = 22;
const slideXmlPath = `ppt/slides/slide${dpIndex}.xml`;
let slideXml = await zip.file(slideXmlPath).async('string');
const targets = [];
for (let i = 1; i <= 4; i++) {
  const name = `dp_step_${i}`;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = slideXml.match(new RegExp(`<p:cNvPr\\b(?=[^>]*\\bname="${escaped}")[^>]*\\bid="(\\d+)"`));
  if (!match) throw new Error(`Could not find animation target ${name}`);
  targets.push(match[1]);
}
const anims = targets.map((spid, i) => {
  const parentId = 3 + i * 2;
  const behaviorId = parentId + 1;
  return `<p:par><p:cTn id="${parentId}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${behaviorId}" dur="500" fill="hold"/><p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr></p:animEffect></p:childTnLst></p:cTn></p:par>`;
}).join('');
const timing = `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>${anims}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst><p:bldLst/></p:timing>`;
if (/<p:timing\b/.test(slideXml)) throw new Error('Unexpected pre-existing timing element on the new animation slide');
slideXml = slideXml.replace(/<\/p:sld>\s*$/, `${timing}</p:sld>`);
zip.file(slideXmlPath, slideXml);
await fs.writeFile(candidatePath, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE', compressionOptions: { level: 6 } }));

// Render all slides for visual inspection before finalization.
const renderDir = path.join(buildDir, 'rendered');
await fs.mkdir(renderDir, { recursive: true });
for (let i = 0; i < presentation.slides.items.length; i++) {
  const slide = presentation.slides.items[i];
  const png = await presentation.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(path.join(renderDir, `slide-${String(i + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
const montage = await presentation.export({ format: 'png', montage: true, scale: 0.35 });
await fs.writeFile(path.join(renderDir, 'montage.png'), new Uint8Array(await montage.arrayBuffer()));
const inspect = await presentation.inspect({ kind: 'slide,textbox,shape,image,chart,table,notes', maxChars: 100000 });
await fs.writeFile(path.join(buildDir, 'inspect.ndjson'), inspect.ndjson, 'utf8');

const SKILL_DIR = 'C:/Users/linge/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/Presentations';
const sourceSha256 = crypto.createHash('sha256').update(await fs.readFile(sourcePath)).digest('hex');
const stagingDir = path.join(buildDir, '.codex-finalizer');
await fs.mkdir(stagingDir, { recursive: true });
const receiptPath = path.join(stagingDir, 'validation.json');
const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, 'container_tools/artifact_tool_utils.mjs')).href);
const result = await finalizePresentation({
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: 'C:/Users/linge/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  integrityValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit'],
  explicitTotalSlideCount: 25,
  requiredNativeChartOwnerSlides: [17],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: { basis: 'reference', families: [font], referencePath: sourcePath, referenceSha256: sourceSha256 },
  verifyArtifactToolImport: true,
  receiptPath,
});
await fs.writeFile(path.join(buildDir, 'finalizer-result.json'), JSON.stringify(result, null, 2), 'utf8');
// The finalizer's chart-workbook snapshot step re-exports the PPTX through the
// editing model, which drops PowerPoint timing nodes. Reapply the authored
// native click sequence to the finalized package, then validate the patched file.
const finalZip = await JSZip.loadAsync(await fs.readFile(finalPath));
let finalSlideXml = await finalZip.file(slideXmlPath).async('string');
const finalTargets = [];
for (let i = 1; i <= 4; i++) {
  const name = `dp_step_${i}`;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = finalSlideXml.match(new RegExp(`<p:cNvPr\\b(?=[^>]*\\bname="${escaped}")[^>]*\\bid="(\\d+)"`));
  if (!match) throw new Error(`Final animation target missing: ${name}`);
  finalTargets.push(match[1]);
}
const finalAnims = finalTargets.map((spid, i) => {
  const parentId = 3 + i * 2;
  const behaviorId = parentId + 1;
  return `<p:par><p:cTn id="${parentId}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${behaviorId}" dur="500" fill="hold"/><p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr></p:animEffect></p:childTnLst></p:cTn></p:par>`;
}).join('');
const finalTiming = `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>${finalAnims}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst><p:bldLst/></p:timing>`;
finalSlideXml = finalSlideXml.replace(/<p:timing\b[^>]*>[\s\S]*?<\/p:timing>/g, '');
finalSlideXml = finalSlideXml.replace(/<\/p:sld>\s*$/, `${finalTiming}</p:sld>`);
finalZip.file(slideXmlPath, finalSlideXml);
await fs.writeFile(finalPath, await finalZip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE', compressionOptions: { level: 6 } }));
const deliveredSha256 = crypto.createHash('sha256').update(await fs.readFile(finalPath)).digest('hex');
console.log(JSON.stringify({ finalPath, slideCount: presentation.slides.items.length, animationSlide: dpIndex, animationTargets: finalTargets, deliveredSha256, finalizer: result }, null, 2));

async function exists(p) { try { await fs.access(p); return true; } catch { return false; } }
