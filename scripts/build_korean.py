"""ULUS10027 full CSV development build; originals and existing ISO are protected.
Requires project tools/python ziglang, pycdlib; host Pillow and fonttools.
"""
import csv, hashlib, json, math, os, re, struct, subprocess, sys
from pathlib import Path
from collections import Counter
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python'))
import pycdlib
import build_firstline_poc as poc
BUILD=ROOT/'build/005_full_csv_rasterfix_kyobo24'
FONT=poc.FONT
CSV=ROOT/'workspace/text/DeathJr_English_Script_Korean.csv'
BASE=0x314000
U32=lambda b,o:struct.unpack_from('<I',b,o)[0]
def align(n,a=16):return (n+a-1)//a*a
def sha(b):return hashlib.sha256(b).hexdigest()
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
def js(path,obj):save(path,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
def sections(b):
    shoff=U32(b,32);n=struct.unpack_from('<H',b,48)[0]
    ss=[list(struct.unpack_from('<10I',b,shoff+i*40)) for i in range(n)]
    names=ss[struct.unpack_from('<H',b,50)[0]]; strings=b[names[4]:names[4]+names[5]]
    return ss,[strings[s[0]:].split(b'\0')[0].decode() for s in ss]
def rawtext(s):
    return b''.join(bytes([int(p[6:8],16)]) if p.startswith('{BYTE_') else p.encode('ascii') for p in re.split(r'(\{BYTE_[0-9A-F]{2}\})',s))
def main(output_dir=None, iso_name='DeathJr_KR_005_FullCSV_RasterFix_Kyobo24.iso'):
    global BUILD
    if output_dir is not None: BUILD=Path(output_dir).resolve()
    BUILD.mkdir(parents=True,exist_ok=True)
    iso_out=BUILD/iso_name
    assert not iso_out.exists(),'Existing build is preserved'
    rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig',newline='')))
    baseline=json.loads((ROOT/'workspace/text/english_script_source.json').read_text(encoding='utf-8'))
    old={r['id']:r for r in baseline}
    assert len(rows)==len(old)==708 and len({r['id'] for r in rows})==708
    for r in rows:
        assert r['translation']
        for k,v in old[r['id']].items():
            if k not in ('translation','notes','status'):assert str(v)==r[k],(r['id'],k)
        assert sorted(re.findall(r'\{BYTE_[0-9A-F]{2}\}|%[ds]',r['translation']))==sorted(r['tokens'].split()),r['id']
    elf=(ROOT/'work/analysis/EBOOT.decrypted.elf').read_bytes()
    assert sha(elf)==poc.ELF_HASH and poc.digest(FONT)==poc.FONT_HASH
    inv=json.loads((ROOT/'docs/iso_inventory.json').read_text())['files'];by={r['path']:r for r in inv}
    original={poc.EBOOT:elf}
    for r in rows:
        name=poc.EBOOT if r['source_file']=='EBOOT.decrypted.elf' else r['source_file']
        if name not in original:
            original[name]=(ROOT/'extracted/iso'/name).read_bytes()
            assert sha(original[name])==by[name]['sha256']
    glob=(ROOT/'extracted/iso'/poc.GLOBAL).read_bytes()
    atlas=(ROOT/'extracted/iso'/poc.PXDS[0][0]).read_bytes()
    palette=atlas[169168:170192];pal=[tuple(palette[i:i+4]) for i in range(0,1024,4)]
    orig_idx=poc.unpack_indices(atlas[170192:170192+131072],256,512)
    orig_image=Image.frombytes('RGBA',(256,512),bytes(c for v in orig_idx for c in pal[v]))
    chars=sorted(set(''.join(re.sub(r'\{BYTE_[0-9A-F]{2}\}','',r['translation']) for r in rows))-set(map(chr,range(32,127))))
    with TTFont(FONT) as tf:assert all(ord(c) in tf.getBestCmap() for c in chars)
    font=ImageFont.truetype(str(FONT),24)
    # Keep original non-button glyphs, append Korean, then the 13 original buttons.
    glyphs=[]
    for ix in range(195):
        u,v,w=struct.unpack_from('<3f',glob,0x1caa0+ix*12);u*=256;v*=512;w*=256
        glyphs.append((orig_image.crop((math.floor(u),math.floor(v),math.floor(u)+math.ceil(w)+1,math.floor(v)+32)),w,'original_'+str(ix)))
    for c in chars:
        im=Image.new('RGBA',(64,32));ImageDraw.Draw(im).text((4,0),c,font=font,fill='white',stroke_width=1,stroke_fill='black')
        bb=im.getchannel('A').getbbox();assert bb and bb[1]>=0 and bb[3]<=31,(c,bb)
        crop=Image.new('RGBA',(bb[2]-bb[0]+2,32));crop.paste(im.crop((bb[0],0,bb[2],32)),(1,0))
        glyphs.append((crop,float(crop.width-1),c))
    button_start=len(glyphs)
    for ix in range(195,208):
        u,v,w=struct.unpack_from('<3f',glob,0x1caa0+ix*12);u*=256;v*=512;w*=256
        glyphs.append((orig_image.crop((math.floor(u),math.floor(v),math.floor(u)+math.ceil(w)+1,math.floor(v)+32)),w,'original_'+str(ix)))
    pages=[Image.new('RGBA',(512,512))]; placements=[];x=64;y=0
    for image,w,key in glyphs:
        if x+image.width+1>512:x=0;y+=32
        if y+32>512:pages.append(Image.new('RGBA',(512,512)));x=64;y=0
        pages[-1].paste(image,(x,y));placements.append((len(pages)-1,x+.5,y+.5,w,key));x+=image.width+1
    premul=[(r*a/255,g*a/255,b*a/255,a) for r,g,b,a in pal]
    @lru_cache(None)
    def quant(c):
        r,g,b,a=c;v=(r*a/255,g*a/255,b*a/255,a)
        return min(range(256),key=lambda i:sum((v[k]-premul[i][k])**2 for k in range(4)))
    pixels=bytearray()
    for i,image in enumerate(pages):
        data=bytes(quant(c) for c in image.getdata());packed=poc.pack_indices(data,512,512,bytes(262144))
        assert poc.unpack_indices(packed,512,512)==data
        pixels+=packed;Image.frombytes('RGBA',(512,512),bytes(c for v in data for c in pal[v])).save(BUILD/f'font_page_{i}.png')
    tokens={int(t[6:8],16) for r in rows for t in re.findall(r'\{BYTE_[0-9A-F]{2}\}',r['translation'])}
    lows=[v for v in range(1,255) if not 32<=v<=127 and v not in tokens]
    charcodes={c:((i//len(lows)+1)<<8)|lows[i%len(lows)] for i,c in enumerate(chars)}
    banks=max(v>>8 for v in charcodes.values())+1
    orig_map=struct.unpack_from('<256H',glob,0x1d470)
    maps=[]
    for bank in range(banks):
        for low in range(256):
            ix=orig_map[low];maps.append(ix if ix<195 else button_start+ix-195 if ix<208 else 0)
    for i,c in enumerate(chars):maps[charcodes[c]]=195+i
    def encode(s):
        result=bytearray(b'\xff\x01');bank=1
        for part in re.split(r'(\{BYTE_[0-9A-F]{2}\})',s):
            if part.startswith('{BYTE_'):result.append(int(part[6:8],16));continue
            for c in part:
                if ord(c)<128:result.append(ord(c))
                else:
                    code=charcodes[c]
                    if code>>8!=bank:bank=code>>8;result.extend([255,bank])
                    result.append(code&255)
        assert 0 not in result
        return bytes(result)
    # Every expanded glyph stream is independently decoded to source Unicode/tokens.
    def decode(data):
        reverse={v:k for k,v in charcodes.items()};out='';bank=0;i=0
        while i<len(data):
            c=data[i];i+=1
            if c==255:bank=data[i];i+=1;continue
            if (bank<<8)|c in reverse:out+=reverse[(bank<<8)|c]
            elif c in tokens:out+='{BYTE_%02X}'%c
            else:out+=chr(c)
        return out
    short=[0]*32;short_next=1; plans=[];text=bytearray();entries=[];seen=set()
    for index,r in enumerate(rows,1):
        name=poc.EBOOT if r['source_file']=='EBOOT.decrypted.elf' else r['source_file']
        off=int(r['file_offset_hex'],16);raw=bytes.fromhex(r['raw_hex']);src=original[name]
        assert src[off:off+len(raw)+1]==raw+b'\0'
        cap=int(r['fixed_buffer_bytes']) if r['fixed_buffer_bytes'] else (align(off+len(raw)+1,4)-off if name==poc.EBOOT else len(raw)+1)
        assert src[off+len(raw):off+cap]==bytes(cap-len(raw)),r['id']
        fmts=re.findall(rb'%[ds]',raw);assert len(fmts)<=3
        tail=b'\x1e'.join(fmts)
        marker=bytes([31,(index-1)//255+1,(index-1)%255+1])
        if len(marker+tail)+1>cap:
            assert short_next<30
            short[short_next]=index;marker=bytes([short_next]);short_next+=1
        replacement=marker+tail+b'\0'
        assert len(replacement)<=cap,(r['id'],len(replacement),cap)
        for pos in range(off,off+cap):assert (name,pos) not in seen;seen.add((name,pos))
        enc=encode(r['translation']);assert decode(enc)==r['translation']
        entries.append((len(text),len(fmts)));text+=enc+b'\0'
        plans.append({'id':r['id'],'file':name,'offset':off,'capacity':cap,'before_hex':src[off:off+cap].hex(),'after_hex':replacement.ljust(cap,b'\0').hex(),'encoded_hex':enc.hex()})
    # Header offsets, no persisted machine pointers in the data blob.
    blob=bytearray(72)
    def append(data,a=16):
        blob.extend(bytes(align(len(blob),a)-len(blob)));off=len(blob);blob.extend(data);return off
    entoff=append(b''.join(struct.pack('<2I',*v) for v in entries))
    textoff=append(text);shortoff=append(struct.pack('<32H',*short))
    mapoff=append(struct.pack('<%dH'%len(maps),*maps));metrics=bytearray()
    for page in range(len(pages)):
        for p,u,v,w,key in placements:metrics+=struct.pack('<3f',(u if p==page else .5)/512,(v if p==page else .5)/512,w/512)
    metoff=append(metrics);pixoff=append(pixels,64);paloff=append(palette,64)
    struct.pack_into('<12I',blob,0,0x324b4a44,entoff,textoff,shortoff,len(pages),len(rows),mapoff,metoff,pixoff,paloff,len(glyphs),banks)
    save(BUILD/'payload_data.bin',blob)
    native=bytearray(elf[0xcd194+128:0xcd658+128]);struct.pack_into('<I',native,0xcd3b8-0xcd194,0x29ce0000|button_start)
    save(BUILD/'native_draw.bin',native)
    asm=''' .set noreorder
 .set noat
 .text
 .globl dj_entry,dj_pc_anchor,dj_base_hi,dj_base_lo,dj_draw
dj_entry:
 lbu $at,0($a1)
 sltiu $at,$at,32
 beq $at,$zero,dj_fallback
 nop
 lbu $at,0($a1)
 beq $at,$zero,dj_fallback
 nop
 addiu $sp,$sp,-64
 sw $ra,60($sp)
 sw $a0,0($sp)
 sw $a1,4($sp)
 sw $a2,8($sp)
 sw $a3,12($sp)
 sw $t0,16($sp)
 sw $t1,20($sp)
 bal dj_pc_anchor
 nop
dj_pc_anchor:
dj_base_hi: lui $a0,0
dj_base_lo: ori $a0,$a0,0
 subu $a0,$ra,$a0
 move $a1,$sp
 jal dj_render
 nop
 lw $ra,60($sp)
 addiu $sp,$sp,64
 jr $ra
 nop
dj_fallback:
 ori $at,$zero,0xad40
 subu $sp,$sp,$at
 .globl dj_fallback_jump
dj_fallback_jump:
 j 0xcd19c
 nop
dj_draw:
 addiu $sp,$sp,-32
 sw $ra,28($sp)
 move $v0,$a0
 lw $a0,0($v0)
 lw $a1,4($v0)
 lw $a2,8($v0)
 lw $a3,12($v0)
 lw $t0,16($v0)
 lw $t1,20($v0)
 jal dj_native_draw
 nop
 lw $ra,28($sp)
 addiu $sp,$sp,32
 jr $ra
 nop
 .balign 16
 .globl dj_native_draw
dj_native_draw:
 .incbin "native_draw.bin"
 .section .rodata
 .balign 64
 .globl dj_data
dj_data:
 .incbin "payload_data.bin"
'''
    save(BUILD/'entry.S',asm.encode())
    save(BUILD/'link.ld',('ENTRY(dj_entry)\nSECTIONS { . = 0x%x; .text : { entry.o(.text) *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) *(.sdata*) } .bss : { *(.bss*) *(.sbss*) *(COMMON) } /DISCARD/ : { *(.MIPS.abiflags) *(.reginfo) *(.pdr) *(.comment) *(.note*) } }'%BASE).encode())
    zig=Path(os.environ.get('DEATHJR_ZIG', str(ROOT/'tools/python/ziglang/zig.exe')))
    # Assembly .incbin inputs are not tracked reliably by shared Zig caches.
    # Each new output directory owns its cache so updated text enters the ELF.
    compiler_env=os.environ.copy()
    compiler_env['ZIG_LOCAL_CACHE_DIR']=str(BUILD/'.zig-cache')
    compiler_env['ZIG_GLOBAL_CACHE_DIR']=str(BUILD/'.zig-global-cache')
    common=[str(zig),'cc','-target','mipsel-freestanding','-march=mips2','-mabi=32','-mfp32','-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-stack-protector','-fno-builtin','-O2']
    for args in [['-c','entry.S','-o','entry.o'],['-c',str(ROOT/'scripts/kr_runtime.c'),'-o','runtime.o']]:
        subprocess.run(common+args,cwd=BUILD,check=True,capture_output=False,env=compiler_env)
    subprocess.run([str(zig),'build-exe','entry.o','runtime.o','-target','mipsel-freestanding','-mcpu=mips2','-T','link.ld','-fentry=dj_entry','--emit-relocs','-fno-compiler-rt','-femit-bin=runtime.elf'],cwd=BUILD,check=True,env=compiler_env)
    linked=(BUILD/'runtime.elf').read_bytes();ss,names=sections(linked)
    syms={}
    for sec in ss:
        if sec[1]==2:
            st=ss[sec[6]];strings=linked[st[4]:st[4]+st[5]]
            for p in range(sec[4],sec[4]+sec[5],16):
                name,value,size,info,other,ndx=struct.unpack_from('<IIIBBH',linked,p)
                syms[strings[name:].split(b'\0')[0].decode()]=value
    allocated=[s for s in ss if s[2]&2]
    payload=bytearray(max(s[3]+s[5] for s in allocated)-BASE)
    for s in allocated:
        if s[1]!=8:payload[s[3]-BASE:s[3]-BASE+s[5]]=linked[s[4]:s[4]+s[5]]
    data_start=syms['dj_data']-BASE
    assert payload[data_start:data_start+len(blob)]==blob, 'Linked text/font data differs from current input; stale compiler cache'
    pc=syms['dj_pc_anchor']
    struct.pack_into('<I',payload,syms['dj_base_hi']-BASE,0x3c040000|(pc>>16))
    struct.pack_into('<I',payload,syms['dj_base_lo']-BASE,0x34840000|(pc&65535))
    oldsecs,oldnames=sections(elf);ph1=struct.unpack_from('<8I',elf,84);seg1va=ph1[2]
    extra=[]
    for sec in ss:
        if sec[1]==9 and ss[sec[7]][2]&2:
            for p in range(sec[4],sec[4]+sec[5],8):
                off,info=struct.unpack_from('<II',linked,p);kind=info&255
                if kind==10:continue # internal PC-relative branch; base cancels
                assert kind in (2,4,5,6),kind
                extra.append((off-seg1va,0x100|kind))
    extra.append((syms['dj_fallback_jump']-seg1va,0x104))
    # Copy source function's PSP relocation stream, retaining target-segment semantics.
    for sec in oldsecs:
        if sec[1]==0x700000a0:
            for p in range(sec[4],sec[4]+sec[5],8):
                off,info=struct.unpack_from('<II',elf,p)
                if (info>>8)&255==0 and 0xcd194<=off<0xcd658:
                    extra.append((syms['dj_native_draw']+off-0xcd194-seg1va,info|0x100))
    extra.append((0xcd194,4))
    patched={k:bytearray(v) for k,v in original.items()}
    for plan in plans:
        b=patched[plan['file']];off=plan['offset'];new=bytes.fromhex(plan['after_hex']);b[off:off+len(new)]=new
    b=patched[poc.EBOOT];assert b[0xcd214:0xcd21c]==elf[0xcd214:0xcd21c]
    struct.pack_into('<II',b,0xcd194+128,0x08000000|(syms['dj_entry']>>2),0)
    # Materialize original BSS unchanged as zeros, then append the new module payload.
    newelf=bytearray(b[:ph1[1]+ph1[4]])
    payload_file=ph1[1]+BASE-seg1va
    assert payload_file>=len(newelf)
    newelf+=bytes(payload_file-len(newelf))+payload
    newsize=len(newelf)-ph1[1]
    struct.pack_into('<II',newelf,84+16,newsize,newsize)
    struct.pack_into('<I',newelf,84+24,7)
    # _sbrk at VA 0x138CCC reads this KiB budget before sceKernelAllocPartitionMemory.
    # Preserve original aggregate module + user heap reservation (round module growth up to KiB).
    heap_offset=0x1d15d0
    heap_original=U32(elf,heap_offset); assert heap_original==20833
    heap_reduction=align(newsize-ph1[5],1024)//1024
    heap_kib=heap_original-heap_reduction; assert heap_kib>0
    struct.pack_into('<I',newelf,heap_offset,heap_kib)
    # Relocation and symbol metadata is not loadable; move it after the enlarged segment.
    for i,sec in enumerate(oldsecs):
        if i==0 or sec[2]&2:continue
        data=elf[sec[4]:sec[4]+sec[5]]
        if oldnames[i]=='.rel.text':data+=b''.join(struct.pack('<II',*x) for x in extra)
        newelf+=bytes(align(len(newelf),max(sec[8],1))-len(newelf));sec[4]=len(newelf);sec[5]=len(data);newelf+=data
    newelf+=bytes(align(len(newelf),4)-len(newelf));struct.pack_into('<I',newelf,32,len(newelf))
    for sec in oldsecs:newelf+=struct.pack('<10I',*sec)
    patched[poc.EBOOT]=newelf
    for name,data in patched.items():save(BUILD/'modified_files'/name,data)
    js(BUILD/'insertion_plan.json',plans);js(BUILD/'symbols.json',syms)
    js(BUILD/'font_mapping.json',{'chars':charcodes,'placements':placements,'pages':len(pages),'glyphs':len(glyphs),'button_start':button_start})
    # Static source restoration, payload reachability, and text roundtrip checks.
    for plan in plans:
        b=patched[plan['file']];off=plan['offset'];assert b[off:off+plan['capacity']].hex()==plan['after_hex']
    assert newelf[payload_file:payload_file+len(payload)]==payload
    save(BUILD/'payload.bin',payload)
    manifest=json.loads((ROOT/'original/source_manifest.json').read_text(encoding='utf-8-sig'))
    source=ROOT/manifest['source']['path'];assert poc.digest(source)==manifest['source']['sha256']
    iso=bytearray(source.read_bytes());newlba=len(iso)//2048;assert len(iso)%2048==0
    iso+=newelf+bytes(align(len(newelf),2048)-len(newelf))
    # Locate EBOOT's actual ISO9660 directory record, update both endian copies.
    reader=pycdlib.PyCdlib();reader.open(str(source));record=reader.get_record(iso_path='/PSP_GAME/SYSDIR')
    start=record.extent_location()*2048;size=record.data_length;p=start;changed_records=0
    while p<start+size:
        length=iso[p]
        if not length:p=align(p+1,2048);continue
        name=bytes(iso[p+33:p+33+iso[p+32]])
        if name.split(b';')[0]==b'EBOOT.BIN':
            struct.pack_into('<I',iso,p+2,newlba);struct.pack_into('>I',iso,p+6,newlba)
            struct.pack_into('<I',iso,p+10,len(newelf));struct.pack_into('>I',iso,p+14,len(newelf));changed_records+=1
        p+=length
    reader.close();assert changed_records==1
    for sector in range(16,64):
        p=sector*2048
        if iso[p+1:p+6]!=b'CD001':break
        if iso[p] in (1,2):struct.pack_into('<I',iso,p+80,len(iso)//2048);struct.pack_into('>I',iso,p+84,len(iso)//2048)
        if iso[p]==255:break
    for name,data in patched.items():
        if name==poc.EBOOT:continue
        assert len(data)==by[name]['size'];offset=by[name]['lba']*2048;iso[offset:offset+len(data)]=data
    save(iso_out,iso)
    reader=pycdlib.PyCdlib();reader.open(str(iso_out));checks=[]
    import io
    for item in inv:
        buffer=io.BytesIO();path='/'+item['path']
        try:reader.get_file_from_iso_fp(buffer,iso_path=path)
        except pycdlib.pycdlibexception.PyCdlibInvalidInput:reader.get_file_from_iso_fp(buffer,iso_path=path+';1')
        actual=sha(buffer.getvalue());expect=sha(patched[item['path']]) if item['path'] in patched else item['sha256']
        assert actual==expect,item['path'];checks.append({'path':item['path'],'sha256':actual})
    reader.close()
    report={'build':BUILD.name,'policy':'development, runtime unverified; not release candidate','csv_sha256':poc.digest(CSV),'iso_sha256':sha(iso),'iso_bytes':len(iso),'rows':len(rows),'hangul':len(chars),'font_pages':len(pages),'glyphs':len(glyphs),'payload_va':BASE,'payload_bytes':len(payload),'additional_module_memory':newsize-ph1[5],'heap_original_kib':heap_original,'heap_kib':heap_kib,'heap_reduction_kib':heap_reduction,'extra_relocations':len(extra),'static_text_roundtrip':'PASS','logical_file_readback':checks,'runtime':'NOT RUN','unresolved':['Native raster clone/texture page rendering needs target runtime proof.','Module growth changes available heap; test scene loads.','Source consumers outside renderer, including save descriptions, need runtime audit.','Full-game layout and transitions not verified.']}
    js(BUILD/'build_report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='logical_file_readback'},ensure_ascii=True,indent=2))
if __name__=='__main__':main()
