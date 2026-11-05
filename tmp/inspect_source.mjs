import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const input = 'C:/Users/linge/AppData/Local/Packages/5319275A.WhatsAppDesktop_cv1g1gvanyjgm/LocalState/sessions/FB754F599DDCCC6DFD0F0C4D66F8F68913DA5298/transfers/2026-41/22MIS0558_INHOUSE.pptx';
const out = 'C:/Users/linge/capstoneproject/tmp/source-inspect';
await fs.mkdir(out, { recursive: true });
const p = await PresentationFile.importPptx(await FileBlob.load(input));
const report = await p.inspect({ kind: 'slide,textbox,shape,image,table,chart,notes,layout', maxChars: 60000 });
await fs.writeFile(`${out}/inspect.ndjson`, report.ndjson, 'utf8');
console.log('slide count', p.slides.items.length);
for (const [i, slide] of p.slides.items.entries()) {
  const png = await p.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(`${out}/slide-${String(i + 1).padStart(2, '0')}.png`, new Uint8Array(await png.arrayBuffer()));
}
const montage = await p.export({ format: 'png', montage: true, scale: 0.3 });
await fs.writeFile(`${out}/montage.png`, new Uint8Array(await montage.arrayBuffer()));
