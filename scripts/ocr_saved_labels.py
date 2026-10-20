"""Run local Apple Vision OCR; never mark OCR as visually verified."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for image in sorted((ROOT/'data/products/labels').glob('*/*')):
 if image.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:continue
 out=image.with_suffix(image.suffix+'.ocr.json')
 if out.exists():continue
 r=subprocess.run(['/private/tmp/m2-ocr-label',str(image)],capture_output=True,text=True)
 if r.returncode==0:
  try:json.loads(r.stdout)
  except ValueError:continue
  out.write_text(r.stdout)
 else:out.with_suffix('.error.txt').write_text(r.stderr[-2000:])
print('OCR files:',len(list((ROOT/'data/products/labels').glob('*/*.ocr.json'))))
