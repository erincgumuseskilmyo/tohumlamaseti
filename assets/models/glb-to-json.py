"""Ham .glb sunamayan ortamlar (ör. Artifact yayını) için .glb -> .glb.json (base64) üretir.
Kullanım:  python glb-to-json.py            (bu klasördeki tüm .glb'ler)
           python glb-to-json.py tank.glb   (tek dosya)
Oyun önce x.glb'yi dener, bulamazsa x.glb.json'a düşer."""
import base64, json, sys, pathlib
here = pathlib.Path(__file__).parent
files = [here / a for a in sys.argv[1:]] or sorted(here.glob("*.glb"))
for f in files:
    out = f.with_suffix(".glb.json")
    out.write_text(json.dumps({"data": base64.b64encode(f.read_bytes()).decode("ascii")}))
    print(f"{f.name} -> {out.name} ({out.stat().st_size} B)")
