import fs from 'node:fs/promises';
import path from 'node:path';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
import { applyPresentationChartFont } from 'file:///C:/Users/linge/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/Presentations/container_tools/artifact_tool_utils.mjs';

const root = process.cwd();
const build = path.join(root, 'tmp', 'edgeretina-pptx-build');
const assets = path.join(build, 'assets');
const renderDir = path.join(build, 'rendered');
const candidate = path.join(build, 'candidate.pptx');
await fs.mkdir(renderDir, { recursive: true });
const C = { navy:'#102A3A', ink:'#162C3A', teal:'#118C8E', teal2:'#57B9B2', orange:'#D8843D', pale:'#F4F7F6', soft:'#E7EFED', white:'#FFFFFF', muted:'#5C6F7B', gray:'#CFD9D9', dark:'#0A1D2A', blue:'#436B8A', red:'#AE514A' };
const FONT = 'Arial';
const ppt = Presentation.create({slideSize:{width:1280,height:720}});
let shapeIndex=0;
function text(slide, value, x, y, w, h, o={}) {
  const sh=slide.shapes.add({geometry:'textbox',name:`text-${++shapeIndex}`,position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});
  sh.text=value;
  sh.text.style={typeface:FONT,fontSize:o.size??24,color:o.color??C.ink,bold:o.bold??false,italic:o.italic??false,alignment:o.align??'left',verticalAlignment:o.valign??'top',wrap:'square',autoFit:'shrinkText',insets:0,lineSpacing:o.lineSpacing};
  return sh;
}
function box(slide,x,y,w,h,fill,line='none',radius=0){
  return slide.shapes.add({geometry:radius?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,line:{style:'solid',fill:line,width:line==='none'?0:1},...(radius?{borderRadius:radius}:{})});
}
async function img(slide,file,x,y,w,h,alt,fit='contain'){
  const p=path.join(assets,file);const bytes=await fs.readFile(p);const type=file.endsWith('.png')?'image/png':'image/jpeg';
  return slide.images.add({blob:new Uint8Array(bytes),contentType:type,alt,fit,position:{left:x,top:y,width:w,height:h}});
}
function base(section,title,num,subtitle=''){
  const s=ppt.slides.add();s.background.fill=C.pale;
  text(s,section.toUpperCase(),58,26,500,24,{size:15,bold:true,color:C.teal});
  text(s,title,58,57,1160,62,{size:46,bold:true,color:C.navy});
  box(s,58,132,74,5,C.teal);
  if(subtitle) text(s,subtitle,58,150,1120,38,{size:20,color:C.muted});
  box(s,58,678,1164,1,C.gray);
  text(s,'EDGERETINA  ·  PROJECT DEFENSE',58,687,500,19,{size:13,color:C.muted,bold:true});
  text(s,String(num).padStart(2,'0'),1173,685,48,22,{size:15,color:C.muted,bold:true,align:'right'});
  return s;
}
function notes(slide,script,sources){slide.speakerNotes.text=`${script}\n\nSources: ${sources}`;}
async function blob(pathOut,content){await fs.writeFile(pathOut,new Uint8Array(await content.arrayBuffer()));}

// 1 — Cover
{
 const s=ppt.slides.add();s.background.fill=C.navy;
 text(s,'SWE3004  ·  SOFTWARE DESIGN AND DEVELOPMENT',64,62,570,28,{size:15,bold:true,color:C.teal2});
 text(s,'EdgeRetina',64,122,570,78,{size:62,bold:true,color:C.white});
 text(s,'Privacy-Aware Diabetic Retinopathy Classification',64,208,550,122,{size:40,bold:true,color:C.white});
 text(s,'Simulated federated learning and explainable deep learning',66,354,525,58,{size:23,color:'#D6E2E6'});
 box(s,66,435,78,5,C.teal2);
 text(s,'Lingeshwar G  ·  22MIS0558',66,466,480,32,{size:22,bold:true,color:C.white});
 text(s,'M.Tech Software Engineering  |  VIT, Vellore',66,506,510,28,{size:18,color:'#D6E2E6'});
 text(s,'Guide: Dr. Asha N  ·  October 2026',66,542,510,28,{size:18,color:'#D6E2E6'});
 await img(s,'fundus-sample.png',674,100,542,465,'APTOS 2019 fundus training image, sample 38f1901f214a, labelled No DR','cover');
 text(s,'APTOS 2019 training sample · No DR',674,578,540,24,{size:15,color:'#C2D3D8'});
 notes(s,'Introduce the project as a research prototype that brings classification, a simulated federated workflow and visual explanations into one application. The photograph is a real example from the project training split.','Supplied final project report, title page and executive summary, pp. i and vi; project dataset data/raw/train_images/38f1901f214a.png.');
}

// 2 — Motivation
{
 const s=base('Context','Why EdgeRetina?',2);
 text(s,'Retinal photographs can support earlier review of diabetic retinopathy.',64,184,670,105,{size:40,bold:true,color:C.navy});
 text(s,'But a central training pool can require sensitive images to be collected in one place. A practical prototype should also explain what the model attends to and show where its results are weak.',66,310,630,122,{size:23,color:C.muted});
 text(s,'PROJECT AIM',66,468,280,24,{size:15,bold:true,color:C.teal});
 text(s,'Build a five-grade classifier and demonstrate local training, processed model updates and Grad-CAM explanations in a web application.',66,502,635,84,{size:24,bold:true,color:C.ink});
 box(s,772,180,440,430,C.navy,'none',18);
 text(s,'3,662',812,226,360,94,{size:72,bold:true,color:C.white});
 text(s,'labelled retinal fundus images',817,317,340,37,{size:22,color:'#D6E2E6'});
 box(s,812,378,350,1,'#49616D');
 text(s,'5',812,412,110,90,{size:68,bold:true,color:C.teal2});
 text(s,'DR severity grades',908,438,260,42,{size:24,bold:true,color:C.white});
 text(s,'Research prototype · not a clinical diagnostic device',812,549,345,45,{size:18,color:'#D6E2E6'});
 notes(s,'Frame the need: retinal images are useful for screening research, while data sharing and trust matter. State that EdgeRetina is a research prototype and does not claim clinical readiness.','Supplied final project report, Executive Summary and Chapters 1–2, pp. vi and 1–11.');
}

// 3 — Dataset and imbalance
{
 const s=base('Data','APTOS 2019: five grades, uneven counts',3,'Class imbalance makes accuracy alone an incomplete measure.');
 text(s,'Image count by diagnosis grade',66,206,650,28,{size:20,bold:true,color:C.ink});
 s.charts.add('bar',{position:{left:58,top:238,width:730,height:380},categories:['No DR','Mild DR','Moderate DR','Severe DR','Proliferative DR'],series:[{name:'Images',values:[1805,370,999,193,295],fill:C.teal,points:[{idx:3,fill:C.orange}]}],barOptions:{direction:'bar',grouping:'clustered',gapWidth:48},hasLegend:false,dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:16,fill:C.ink}},xAxis:{min:0,max:2000,majorUnit:500,textStyle:{fontSize:14,fill:C.muted},majorGridlines:{style:'solid',fill:'#DCE4E3',width:1}},chartFill:C.pale,chartLine:{style:'solid',fill:'none',width:0},plotAreaFill:C.pale,plotAreaLine:{style:'solid',fill:'none',width:0}});
 text(s,'TRAIN / VALIDATION / TEST',846,239,340,24,{size:15,bold:true,color:C.teal});
 text(s,'2,563',846,282,340,64,{size:50,bold:true,color:C.navy});text(s,'train',846,342,300,26,{size:19,color:C.muted});
 text(s,'549',846,392,340,64,{size:50,bold:true,color:C.navy});text(s,'validation',846,452,300,26,{size:19,color:C.muted});
 text(s,'550',846,502,340,64,{size:50,bold:true,color:C.navy});text(s,'held-out test images',846,562,300,30,{size:19,color:C.muted});
 text(s,'No DR : Severe DR = 9.35 : 1',68,629,600,27,{size:19,bold:true,color:C.orange});
 notes(s,'APTOS 2019 contains 3,662 labelled images. The No DR class is the largest; Severe DR is the smallest. The split used here is 2,563 train, 549 validation and 550 test. Emphasize the 9.35-to-1 imbalance and why macro-F1 and per-class recall matter.','Supplied final project report, Chapter 5.1 and 5.4, pp. 26–29; reports/validation/dataset_analysis.json.');
}

// 4 — Methodology / preprocessing
{
 const s=base('Method','From fundus image to prediction',4);
 await img(s,'methodology.jpg',60,172,600,480,'Project report figure showing the EdgeRetina end-to-end methodology');
 text(s,'A consistent input pipeline',714,192,500,38,{size:28,bold:true,color:C.navy});
 text(s,'Validate image and label files',714,256,490,40,{size:23,color:C.ink});
 text(s,'Resize to the model input; apply CLAHE where configured; normalize pixel values.',714,305,490,78,{size:21,color:C.muted});
 box(s,714,400,460,1,C.gray);
 text(s,'Train in two stages',714,430,490,37,{size:28,bold:true,color:C.navy});
 text(s,'1  Train the five-class classification head\n2  Fine-tune the pretrained backbone',714,480,490,82,{size:21,color:C.ink});
 text(s,'Same preprocessing is used at training and prediction time.',714,594,490,49,{size:18,bold:true,color:C.teal});
 notes(s,'Walk through the project pipeline from validation and preprocessing to training, prediction and Grad-CAM. Input processing resizes images, applies CLAHE where configured, and normalizes values. Explain head training followed by fine-tuning.','Supplied final project report, Fig. 4.2 and Chapters 5.2–5.7, pp. 19 and 27–32.');
}

// 5 — Models
{
 const s=base('Models','Two transfer-learning backbones',5,'Both models produce five softmax outputs for the DR severity grades.');
 text(s,'MobileNetV3Small',72,235,510,64,{size:42,bold:true,color:C.teal});
 text(s,'Designed for efficient computation and a smaller memory footprint.',72,314,475,77,{size:25,color:C.ink});
 text(s,'Use case',72,427,140,24,{size:15,bold:true,color:C.muted});
 text(s,'A lightweight model suited to constrained devices.',72,460,455,60,{size:21,color:C.ink});
 box(s,625,222,2,330,C.gray);
 text(s,'EfficientNetB0',680,235,520,64,{size:42,bold:true,color:C.navy});
 text(s,'Balances model depth, width and input resolution through compound scaling.',680,314,510,77,{size:25,color:C.ink});
 text(s,'Use case',680,427,140,24,{size:15,bold:true,color:C.muted});
 text(s,'A stronger accuracy result in this project’s centralized comparison.',680,460,500,63,{size:21,color:C.ink});
 box(s,72,566,1116,1,C.gray);
 text(s,'Training strategy',72,588,185,25,{size:16,bold:true,color:C.teal});
 text(s,'Transfer learning  →  train head  →  fine-tune  →  evaluate on the held-out test set',272,584,900,44,{size:22,bold:true,color:C.ink});
 notes(s,'Both backbones use transfer learning and a five-output head. MobileNetV3Small prioritizes efficiency. EfficientNetB0 has higher reported accuracy in the centralized comparison, while MobileNetV3Small has slightly higher macro-F1. Save the comparison values for the results slide.','Supplied final project report, Chapter 5.5 and Table 5.4, pp. 29–30.');
}

// 6 — System architecture
{
 const s=base('Implementation','One Flask application connects the workflow',6);
 text(s,'Web interface',70,190,430,34,{size:26,bold:true,color:C.teal});
 text(s,'Upload an image, view prediction probabilities and confidence, review Grad-CAM, and browse prediction history.',70,235,470,104,{size:22,color:C.ink});
 text(s,'Model and data services',70,373,430,34,{size:26,bold:true,color:C.teal});
 text(s,'MobileNetV3Small and EfficientNetB0 run with shared image preprocessing. Training results and prediction records are stored locally.',70,418,470,105,{size:22,color:C.ink});
 text(s,'Technology',70,555,430,28,{size:15,bold:true,color:C.muted});
 text(s,'Flask  ·  TensorFlow/Keras  ·  SQLite',70,588,460,32,{size:22,bold:true,color:C.navy});
 await img(s,'architecture.jpg',650,163,565,495,'Project system architecture diagram for EdgeRetina');
 notes(s,'Use the diagram to explain the main layers: Flask UI, backend services, deep-learning models, dataset/model artifacts and the local SQLite store. The project runs locally as a research prototype.','Supplied final project report, Fig. 4.1 and Chapter 4, pp. 18–24.');
}

// 7 — Federated setup
{
 const s=base('Federated learning','Four simulated clients, one global model',7);
 await img(s,'federated.jpg',58,188,685,450,'Project figure showing one simulated federated round with four clients and clipping plus noise');
 text(s,'What the experiment simulates',790,196,412,42,{size:27,bold:true,color:C.navy});
 text(s,'Four client partitions train locally. Each produces a model update; the server processes updates and combines them with sample-weighted FedAvg.',790,250,410,123,{size:22,color:C.ink});
 box(s,790,405,395,1,C.gray);
 text(s,'What it does not simulate',790,430,412,38,{size:24,bold:true,color:C.orange});
 text(s,'The clients run on one machine and split one dataset. There is no real hospital network or cross-institution data heterogeneity.',790,480,410,110,{size:21,color:C.ink});
 text(s,'The client model update is the difference between local weights and the global weights.',790,602,410,45,{size:17,color:C.muted,italic:true});
 notes(s,'Explain the single round: distribute the current global model; train locally; process each update; aggregate. State precisely that clients are software simulations on the same machine using partitions of one dataset.','Supplied final project report, Fig. 6.1 and Sections 6.2–6.4, pp. 34–36.');
}

// 8 — Clipping and Gaussian noise
{
 const s=base('Privacy-inspired processing','Clip large updates, then add Gaussian noise',8,'These operations apply to model-weight updates, not to retinal pixels.');
 text(s,'1  Measure the update',70,215,500,34,{size:26,bold:true,color:C.teal});
 text(s,'Δ = w_local − w_global\n‖Δ‖₂ summarizes the update’s overall size.',70,258,500,74,{size:22,color:C.ink});
 text(s,'2  Clip to the norm limit',70,364,500,34,{size:26,bold:true,color:C.teal});
 text(s,'Δ_clip = Δ × min(1, C / ‖Δ‖₂)',70,410,535,46,{size:25,bold:true,color:C.navy});
 text(s,'Report example: [3, 4] has norm 5. With C = 1, scale by 0.2 → [0.6, 0.8].',70,465,540,77,{size:20,color:C.ink});
 box(s,652,205,2,382,C.gray);
 text(s,'3  Add zero-mean Gaussian noise',700,215,505,67,{size:26,bold:true,color:C.teal});
 text(s,'Δ_processed = Δ_clip + η,   η ~ N(0, σ²I)',700,305,490,50,{size:24,bold:true,color:C.navy});
 text(s,'Current implementation: C = 1.0, noise multiplier = 0.10. Per-weight noise scale = C × 0.10 / √M, where M is the number of update parameters.',700,376,490,112,{size:21,color:C.ink});
 text(s,'4  Aggregate processed updates',700,510,500,35,{size:25,bold:true,color:C.teal});
 text(s,'FedAvg weights each client by its share of training samples.',700,553,490,47,{size:20,color:C.ink});
 box(s,70,618,1140,42,'#FFF2E5','none',8);
 text(s,'Privacy caveat: no (ε, δ) privacy accountant or formal guarantee; secure aggregation and encryption are also absent.',84,626,1110,30,{size:17,bold:true,color:'#80501E'});
 notes(s,'Use the exact [3,4] example from the report to make clipping tangible. Then explain that Gaussian noise perturbs each update entry. The current code scales per-weight noise as C times the configured multiplier divided by the square root of the parameter count. Be clear that this prototype does not compute a privacy budget, has no secure aggregation or encryption, and makes no formal differential privacy claim.','Supplied final project report, Sections 6.5.1–6.5.4, pp. 36–38; current backend/app/federated/differential_privacy.py and backend/app/federated/server.py.');
}

// 9 — Explainability
{
 const s=base('Explainability','Grad-CAM highlights influential image regions',9);
 await img(s,'gradcam.jpg',60,178,580,456,'Grad-CAM heatmap overlay from the project report on a retinal fundus image');
 text(s,'Prediction',718,205,450,34,{size:16,bold:true,color:C.teal});
 text(s,'Five-class output',718,246,480,47,{size:32,bold:true,color:C.navy});
 text(s,'The model returns a DR grade with confidence and class probabilities.',718,305,478,82,{size:22,color:C.ink});
 text(s,'Visual explanation',718,414,450,34,{size:16,bold:true,color:C.teal});
 text(s,'Grad-CAM overlays a coarse heatmap to show regions that influenced the selected prediction.',718,455,478,87,{size:22,color:C.ink});
 text(s,'A heatmap is not a lesion segmentation and was not validated against clinician annotations.',718,570,480,57,{size:19,bold:true,color:C.orange});
 notes(s,'Explain that Grad-CAM is used as a visual aid to understand regions that influenced a model output. It does not prove that the model is correct and does not mark lesions with pixel-level accuracy.','Supplied final project report, Fig. 8.10 and Section 6.7, pp. 39 and 54; Grad-CAM screenshot embedded from the report.');
}

// 10 — Web application
{
 const s=base('Demonstration','The web app connects prediction, training and evidence',10);
 await img(s,'evidence-dashboard.jpg',58,207,625,337,'Evidence dashboard screenshot from the EdgeRetina project report');
 text(s,'Application features',755,197,450,39,{size:28,bold:true,color:C.navy});
 text(s,'Image upload with file validation',755,252,445,34,{size:22,color:C.ink});
 text(s,'Prediction grade, confidence and class probabilities',755,303,445,55,{size:22,color:C.ink});
 text(s,'Grad-CAM explanation and prediction history',755,378,445,55,{size:22,color:C.ink});
 text(s,'Training control, federated status and saved evaluation artifacts',755,453,445,65,{size:22,color:C.ink});
 text(s,'The dashboard reports metrics from saved artifacts, not live batch accuracy.',755,558,435,66,{size:18,bold:true,color:C.teal});
 notes(s,'Briefly demo the application: upload an image, review the grade and probabilities, inspect a Grad-CAM heatmap, and view saved records and metrics. The screenshot comes from the report’s evidence dashboard.','Supplied final project report, Chapter 8, pp. 49–56, including Fig. 8.13; screenshot embedded from the report.');
}

// 11 — Results
{
 const s=base('Evaluation','Accuracy and macro-F1 tell different stories',11,'All three values below use the 550-image held-out test split.');
 s.charts.add('bar',{position:{left:55,top:216,width:775,height:390},categories:['MobileNetV3Small · centralized','EfficientNetB0 · centralized','MobileNetV3Small · 5-round FL'],series:[{name:'Accuracy',values:[0.633,0.711,0.670909],fill:C.teal},{name:'Macro-F1',values:[0.420,0.409,0.400758],fill:C.orange}],barOptions:{direction:'column',grouping:'clustered',gapWidth:82},hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:15,fill:C.ink}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:13,fill:C.ink}},xAxis:{textStyle:{fontSize:14,fill:C.ink}},yAxis:{min:0,max:0.8,majorUnit:0.2,numberFormatCode:'0%',textStyle:{fontSize:14,fill:C.muted},majorGridlines:{style:'solid',fill:'#DCE4E3',width:1}},chartFill:C.pale,chartLine:{style:'solid',fill:'none',width:0},plotAreaFill:C.pale,plotAreaLine:{style:'solid',fill:'none',width:0}});
 text(s,'71.1%',880,234,300,65,{size:49,bold:true,color:C.navy});
 text(s,'Best centralized accuracy\nEfficientNetB0',880,300,300,57,{size:19,color:C.ink});
 text(s,'42.0%',880,386,300,59,{size:43,bold:true,color:C.teal});
 text(s,'Best centralized macro-F1\nMobileNetV3Small',880,445,300,55,{size:19,color:C.ink});
 text(s,'Minority-grade performance remains weak. Interpret accuracy alongside macro-F1 and per-class recall.',880,526,300,88,{size:17,bold:true,color:C.orange});
 text(s,'FL result: saved 5-round dashboard evaluation (67.1% accuracy, 40.1% macro-F1, QWK 0.687). This later run was not in the report’s original results section.',62,630,1137,34,{size:15,color:C.muted});
 notes(s,'The centralized comparison in the final report has EfficientNetB0 at 71.1% accuracy and 40.9% macro-F1; MobileNetV3Small at 63.3% and 42.0%. The current project’s saved five-round federated evaluation file contains 67.09% accuracy, 40.08% macro-F1, QWK 0.687 and MAE 0.547 on the same 550-image test split. The report’s Chapter 9 says federated metrics were not available when it was written; present the federated metric as a later saved dashboard evaluation, not as a figure from the submitted report. Severe-class recall is zero in this saved federated run, so do not imply robust five-class performance.','Supplied final project report, Tables 9.3 and 9.7, pp. 59 and 66; current reports/federated/evaluation.json, run_id 68688c55a1864640ab728b6f2032341c (five rounds, 550 test samples).');
}

// 12 — Conclusion, limitations and next steps
{
 const s=base('Conclusion','A complete research workflow, with clear next steps',12);
 text(s,'Demonstrated',68,190,470,42,{size:29,bold:true,color:C.teal});
 text(s,'Five-grade DR classification on APTOS 2019',68,248,500,37,{size:22,color:C.ink});
 text(s,'Centralized model comparison and a saved five-round FL run',68,299,500,54,{size:22,color:C.ink});
 text(s,'A working Flask application with prediction and Grad-CAM',68,371,500,54,{size:22,color:C.ink});
 text(s,'Federated workflow with four simulated clients',68,443,500,44,{size:22,color:C.ink});
 text(s,'Next steps',666,190,500,42,{size:29,bold:true,color:C.orange});
 text(s,'Improve Mild and Severe recall; evaluate across more splits and an external dataset.',666,248,510,69,{size:21,color:C.ink});
 text(s,'Use non-identical client data and test realistic multi-institution settings.',666,333,510,63,{size:21,color:C.ink});
 text(s,'Add privacy accounting and secure aggregation; validate explanations with clinicians.',666,412,510,69,{size:21,color:C.ink});
 box(s,68,552,1110,1,C.gray);
 text(s,'Takeaway',68,578,160,26,{size:15,bold:true,color:C.teal});
 text(s,'EdgeRetina demonstrates the workflow; it is not a clinically validated system or a formal privacy guarantee.',235,572,930,55,{size:23,bold:true,color:C.navy});
 notes(s,'Close by describing EdgeRetina as a research prototype. The most important next steps are improving minority-grade recall, external testing, realistic client heterogeneity, formal privacy accounting and clinical validation. Invite questions.','Supplied final project report, Chapters 9–11, pp. 64–68; report’s limitations and future-work sections.');
}

for (const slide of ppt.slides.items) for (const chart of slide.charts.items) applyPresentationChartFont(chart,{fontFamily:FONT});
const pptx=await PresentationFile.exportPptx(ppt);
await pptx.save(candidate);
for(let i=0;i<ppt.slides.items.length;i++){
 const s=ppt.slides.items[i];const num=String(i+1).padStart(2,'0');
 await blob(path.join(renderDir,`slide-${num}.png`),await ppt.export({slide:s,format:'png',scale:1}));
}
await blob(path.join(renderDir,'montage.webp'),await ppt.export({format:'webp',montage:true}));
console.log(JSON.stringify({candidate,slides:ppt.slides.items.length,renderDir}));