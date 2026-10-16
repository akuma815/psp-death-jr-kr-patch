"""Preview actual quantized atlas glyphs; this is not an emulator screenshot."""
import csv,json,re,math,struct
from PIL import Image,ImageDraw
import build_korean as m
p=m.BUILD
mp=json.loads((p/'font_mapping.json').read_text(encoding='utf-8'))
lookup={v[4]:v for v in mp['placements']}
rows=list(csv.DictReader(m.CSV.open(encoding='utf-8-sig')))
ids=['ELF_001CADBC','ELF_001CAAE0','ELF_001D4F51','ELF_001D4FBD','ELF_001DB665']
selected=[next(r for r in rows if r['id']==i) for i in ids]
selected.append(max((r for r in rows if '{BYTE_' not in r['translation']),key=lambda x:len(x['translation'])))
canvas=Image.new('RGBA',(800,len(selected)*62),(35,35,40,255))
draw=ImageDraw.Draw(canvas)
pages=[Image.open(p/f'font_page_{i}.png') for i in range(mp['pages'])]
glob=(m.ROOT/'extracted/iso'/m.poc.GLOBAL).read_bytes()
original_map=struct.unpack_from('<256H',glob,0x1d470)
for index,row in enumerate(selected):
    y=index*62;draw.text((8,y+2),row['id'],fill='white');x=8
    for part in re.split(r'(\{BYTE_[0-9A-F]{2}\})',row['translation']):
        keys=['original_'+str(original_map[int(part[6:8],16)])] if part.startswith('{BYTE_') else [c if ord(c)>127 else 'original_'+str(original_map[ord(c)]) for c in part]
        for key in keys:
            pg,u,v,w,_=lookup[key]
            tile=pages[pg].crop((int(u),int(v),int(u)+math.ceil(w)+1,int(v)+32))
            canvas.alpha_composite(tile,(round(x),y+19));x+=w
canvas.save(p/'translation_preview.png')
print('Actual atlas preview saved')
