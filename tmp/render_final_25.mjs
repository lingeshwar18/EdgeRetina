import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const input = 'C:/Users/linge/capstoneproject/output/pptx/EdgeRetina_Second_Review_25_Slides_v5.pptx';
const out = 'C:/Users/linge/capstoneproject/tmp/edgeretina-final-render';
await fs.mkdir(out, { recursive: true });
const p = await PresentationFile.importPptx(await FileBlob.load(input));
if (p.slides.items.length !== 25) throw new Error(`Expected 25 slides, got ${p.slides.items.length}`);
for (let i = 0; i < p.slides.items.length; i++) {
  const blob = await p.export({ slide: p.slides.items[i], format: 'png', scale: 1 });
  await fs.writeFile(path.join(out, `slide-${String(i + 1).padStart(2, '0')}.png`), new Uint8Array(await blob.arrayBuffer()));
}
const montage = await p.export({ format: 'png', montage: true, scale: 0.35 });
await fs.writeFile(path.join(out, 'montage.png'), new Uint8Array(await montage.arrayBuffer()));
console.log('Rendered final deck:', p.slides.items.length, 'slides');
