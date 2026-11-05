import path from 'node:path';
import { pathToFileURL } from 'node:url';
process.env.RUNTIME_NODE_MODULES='C:/Users/linge/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const workspaceDir=process.cwd();
const skillDir='C:/Users/linge/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/Presentations';
const build=path.join(workspaceDir,'tmp','edgeretina-pptx-build');
const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools','artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
 workspaceDir,
 candidatePath:path.join(build,'candidate.pptx'),
 finalPath:path.join(workspaceDir,'output','pptx','EdgeRetina_Project_Defense.pptx'),
 pythonExecutable:'C:/Users/linge/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(skillDir,'container_tools','inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skillDir,'container_tools','inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 requiredNativeChartOwnerSlides:[3,11],
 requiredNativeTableOwnerSlides:[],
 materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'design',families:['Arial']},
 verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json'),
});
console.log(JSON.stringify(result));