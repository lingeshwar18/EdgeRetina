import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const input = 'C:/Users/linge/capstoneproject/output/pptx/EdgeRetina_Project_Defense.pptx';
const out = 'C:/Users/linge/capstoneproject/tmp/previous-deck-inspect';
await fs.mkdir(out, { recursive: true });
const p = await PresentationFile.importPptx(await FileBlob.load(input));
console.log('slide count', p.slides.items.length);
const report = await p.inspect({ kind: 'slide,textbox,image,notes', maxChars: 50000 });
await fs.writeFile(`${out}/inspect.ndjson`, report.ndjson, 'utf8');
for (const [i, slide] of p.slides.items.entries()) {
  if ([0, 5, 6, 7, 8, 9].includes(i)) {
    const png = await p.export({ slide, format: 'png', scale: 1 });
    await fs.writeFile(`${out}/slide-${String(i + 1).padStart(2, '0')}.png`, new Uint8Array(await png.arrayBuffer()));
  }
}
