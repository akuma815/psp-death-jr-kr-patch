"""MIPS CPU tests, not a PSP GPU or scene test. Execute final relocated ISO ELF code."""
import csv,json,struct,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python'))
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
import build_korean as build
B=build.BUILD
elf=(B/'modified_files/PSP_GAME/SYSDIR/EBOOT.BIN').read_bytes()
symbols=json.loads((B/'symbols.json').read_text());plans=json.loads((B/'insertion_plan.json').read_text())
rows=list(csv.DictReader(build.CSV.open(encoding='utf-8-sig')))
ss,names=build.sections(elf)
def load(base):
    mem=bytearray(0x700000)
    segments=[]
    for i in range(2):
        ph=struct.unpack_from('<8I',elf,52+i*32);segments.append(ph[2]);mem[ph[2]:ph[2]+ph[4]]=elf[ph[1]:ph[1]+ph[4]]
    for sec in ss:
        if sec[1]!=0x700000a0:continue
        rel=[struct.unpack_from('<II',elf,p) for p in range(sec[4],sec[4]+sec[5],8)]
        ops=[build.U32(mem,o+segments[(i>>8)&255]) for o,i in rel]
        for k,(o,i) in enumerate(rel):
            typ=i&255;dest=o+segments[(i>>8)&255];to=base+segments[(i>>16)&255];op=ops[k]
            if typ==2:op=(op+to)&0xffffffff
            elif typ==4:op=(op&0xfc000000)|(((op&0x3ffffff)+(to>>2))&0x3ffffff)
            elif typ==5:
                j=next(j for j in range(k+1,len(rel)) if rel[j][1]&255==6)
                lo=struct.unpack('<h',struct.pack('<H',ops[j]&65535))[0]
                op=(op&0xffff0000)|((((op&65535)*65536+lo+to+0x8000)>>16)&65535)
            elif typ==6:op=(op&0xffff0000)|((op+to)&65535)
            else:raise AssertionError(typ)
            struct.pack_into('<I',mem,dest,op)
    return mem
def cstr(uc,address):
    out=bytearray()
    for i in range(1024):
        c=uc.mem_read(address+i,1)[0]
        if not c:return bytes(out)
        out.append(c)
    raise AssertionError('unterminated')
mapping=json.loads((B/'font_mapping.json').read_text(encoding='utf-8'))
reverse={v:k for k,v in mapping['chars'].items()}
tokens={int(t[6:8],16) for r in rows for t in re.findall(r'\{BYTE_[0-9A-F]{2}\}',r['translation'])}
def decode(data):
    result='';bank=0;p=0
    while p<len(data):
        c=data[p];p+=1
        if c==255:bank=data[p];p+=1;continue
        if ((bank<<8)|c) in reverse:result+=reverse[(bank<<8)|c]
        elif c in tokens:result+='{BYTE_%02X}'%c
        else:result+=chr(c)
    return result
results=[]
for base in [0x08804000,0x08814000]:
    mem=load(base);uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(base,len(mem));uc.mem_write(base,bytes(mem))
    fixture=base+0x600000;font=fixture;holder=fixture+0x100;resource=fixture+0x200;texture=fixture+0x300;raster=fixture+0x500
    def w(addr,*values):uc.mem_write(addr,struct.pack('<%dI'%len(values),*values))
    w(font,holder,0,0,0x41f80000,0x44000000,0x43800000,208,0);w(holder,resource);w(resource+16,raster);w(raster,raster)
    # Derive the plugin-global address from original relocated consumer instructions.
    hi=build.U32(mem,0x176d48)&65535;lo=struct.unpack('<h',struct.pack('<H',build.U32(mem,0x176d4c)&65535))[0]
    extension_address=(hi<<16)+lo
    w(extension_address,64);uc.mem_write(raster+35,b'\xa5')
    calls=[];vertices=[]
    driver=fixture+0x3000;bind=fixture+0x4000
    w(base+0x1de724,driver);w(driver+0x20,bind)
    def hook(uc,addr,size,user):
        calls.append({'text':decode(cstr(uc,uc.reg_read(UC_MIPS_REG_A1))),'font':uc.reg_read(UC_MIPS_REG_A0)})
    uc.hook_add(UC_HOOK_CODE,hook,begin=base+symbols['dj_native_draw'],end=base+symbols['dj_native_draw'])
    def external(uc,addr,size,user):
        if addr==bind:
            ra=uc.reg_read(UC_MIPS_REG_A1)
            assert build.U32(uc.mem_read(ra,4),0)==ra
            assert build.U32(uc.mem_read(ra+12,4),0)==512
            assert build.U32(uc.mem_read(ra+64+80,4),0)==5
            assert build.U32(uc.mem_read(ra+64+84,4),0)==1
        if addr==base+0x195fe8:
            vp=uc.reg_read(UC_MIPS_REG_A0);n=uc.reg_read(UC_MIPS_REG_A1)
            assert n%6==0 and 0<n<1024
            raw=uc.mem_read(vp,n*36)
            vert=[struct.unpack_from('<2fI3f3f',raw,i*36) for i in range(n)]
            assert all(0<=v[0]<=1 and 0<=v[1]<=1 for v in vert)
            vertices.append(vert)
        uc.reg_write(UC_MIPS_REG_V0,1)
        uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
    for addr in [bind,base+0x20d0,base+0x195fe8,base+0x196480,base+0x1960dc]:
        uc.hook_add(UC_HOOK_CODE,external,begin=addr,end=addr)
    stop=fixture+0x1000;sp=base+0x6ff000
    cases=list(zip(rows,plans))
    for source_id,arg_id in [('ELF_001C389C','ELF_001C38A4'),('ELF_001CC010','ELF_001C35B8'),('ELF_001CC1D0','ELF_001C2A48')]:
        row=dict(next(r for r in rows if r['id']==source_id));plan=next(p for p in plans if p['id']==source_id)
        argrow=next(r for r in rows if r['id']==arg_id);argplan=next(p for p in plans if p['id']==arg_id)
        row['_string_param']=bytes.fromhex(argplan['after_hex']).split(b'\0')[0]
        row['_expected_param']=argrow['translation'];row['id']+='__nested'
        cases.append((row,plan))
    for row,plan in cases:
        data=bytes.fromhex(plan['after_hex']).split(b'\0')[0]
        # Simulate original sprintf on its compact marker and distinct arguments.
        params=[]
        for token in re.findall(rb'%[ds]',bytes.fromhex(row['raw_hex'])):
            params.append(b'27' if token==b'%d' else row.get('_string_param',b'TEST'))
        k=0
        def sub(m):
            global k
            v=params[k];k+=1;return v
        data=re.sub(rb'%[ds]',sub,data)
        expected=row['translation'];k=0
        def subst(m):
            global k
            v=row.get('_expected_param','TEST') if m.group()=='%s' else params[k].decode();k+=1;return v
        expected=re.sub(r'%[ds]',subst,expected)
        source=fixture+0x2000;uc.mem_write(source,data+b'\0');calls.clear();vertices.clear()
        uc.reg_write(UC_MIPS_REG_SP,sp);uc.reg_write(UC_MIPS_REG_RA,stop)
        preserved=[UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S3,UC_MIPS_REG_S4,UC_MIPS_REG_S5,UC_MIPS_REG_S6,UC_MIPS_REG_S7,UC_MIPS_REG_FP,UC_MIPS_REG_GP]
        for i,reg in enumerate(preserved):uc.reg_write(reg,0x13570000+i)
        for reg,val in [(UC_MIPS_REG_A0,font),(UC_MIPS_REG_A1,source),(UC_MIPS_REG_A2,0),(UC_MIPS_REG_A3,0xffffffff),(UC_MIPS_REG_T0,1),(UC_MIPS_REG_T1,0)]:uc.reg_write(reg,val)
        try:uc.emu_start(base+0xcd194,stop,count=200000)
        except Exception as e:raise RuntimeError((row['id'],hex(uc.reg_read(UC_MIPS_REG_PC)),str(e)))
        assert uc.reg_read(UC_MIPS_REG_PC)==stop,(row['id'],'instruction budget')
        assert uc.reg_read(UC_MIPS_REG_SP)==sp,(row['id'],'stack')
        assert all(uc.reg_read(reg)==0x13570000+i for i,reg in enumerate(preserved)),(row['id'],'callee-saved registers')
        assert len(calls)==mapping['pages'],(row['id'],len(calls))
        assert len(vertices)==mapping['pages']
        assert [[v[6:9] for v in vs] for vs in vertices][0]==[[v[6:9] for v in vs] for vs in vertices][1],row['id']
        assert all(c['text']==expected for c in calls),(row['id'],[c['text'] for c in calls],expected)
        for c in calls:
            f=c['font'];h=build.U32(uc.mem_read(f,32),0);r=build.U32(uc.mem_read(h,4),0);ra=build.U32(uc.mem_read(r+16,4),0)
            assert build.U32(uc.mem_read(ra+12,4),0)==512
        results.append({'base':hex(base),'id':row['id'],'draws':len(calls),'pass':True})
build.js(B/'mips_runtime_verification.json',{'cases':len(results),'all_pass':True,'scope':'Actual MIPS wrapper/format expansion/relocation/font clone and native glyph/vertex generation. External texture bind and transform/draw submission are mocked; no PSP GPU proof.','results':results})
print('PASS:',len(results),'MIPS input cases at two load bases; native vertices included, GPU excluded')
