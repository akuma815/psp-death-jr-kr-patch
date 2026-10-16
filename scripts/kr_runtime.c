/* Death Jr ULUS10027 development renderer. Build-specific data lives in dj_data.
 * Original string slots contain stable IDs, preserving their addresses/capacity.
 * All texture pages are immutable and resident for queued GPU consumption.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
extern u8 dj_data[];
extern void dj_draw(u32 *args);
typedef struct { u32 off, argc; } Entry;
typedef struct {
    u32 magic, entries, text, shortids, pages, count, maps, metrics, pixels, palette;
    u32 nonbuttons, bankcount, diagnostics[6];
} Header;
typedef struct {
    u32 font[8], holder[8], resource[8], texture[24], raster[256];
} Page;
static Page runtime_pages[8];
static void copy(void *dst, const void *src, u32 n) {
    u8 *d=dst; const u8 *s=src; while(n--) *d++=*s++;
}
static u32 put(u8 *out, u32 n, u8 c) {
    if(n<510) out[n++]=c;
    return n;
}
static u32 expand(const u8 **input, u8 *out, u32 n, u32 depth, u32 stop) {
    Header *h=(Header*)dj_data;
    Entry *entries=(Entry*)(dj_data+h->entries);
    const u8 *s=*input;
    while(*s && (!stop || *s!=30) && n<510) {
        u32 id=0;
        if(*s==31 && s[1] && s[2]) { id=(s[1]-1)*255+s[2]; s+=3; }
        else if(*s>0 && *s<30) { id=((u16*)(dj_data+h->shortids))[*s++]; }
        if(id && id<=h->count && depth<6) {
            const u8 *params[4]; u32 lengths[4];
            u32 argc=entries[id-1].argc;
            for(u32 i=0;i<argc && i<4;i++) {
                params[i]=s;
                while(*s && *s!=30) s++;
                lengths[i]=(u32)(s-params[i]);
                if(*s==30) s++;
            }
            const u8 *t=dj_data+h->text+entries[id-1].off;
            u32 arg=0;
            while(*t && n<510) {
                if(*t=='%' && (t[1]=='d'||t[1]=='s') && arg<argc) {
                    const u8 *p=params[arg++];
                    n=expand(&p,out,n,depth+1,1); t+=2;
                } else n=put(out,n,*t++);
            }
        } else if(!id) { n=put(out,n,*s++); }
        else { h->diagnostics[1]++; }
    }
    *input=s; out[n]=0;
    if(n>=510) h->diagnostics[2]++;
    return n;
}
void dj_render(u32 base, u32 *args) {
    Header *h=(Header*)dj_data;
    u8 text[512]; const u8 *s=(const u8*)args[1];
    expand(&s,text,0,0,0);
    h->diagnostics[0]++;
    u32 *font=(u32*)args[0];
    u32 *resource;
    /* Live capture: resource[4] is RwRaster, whose first word is its parent. */
    resource=*(u32**)(font[0]);
    u32 *raster=(u32*)resource[4];
    /* 176D48/176D4C relocations target segment 1: 0x12ffa4 + 0x1e3e60. */
    u32 extension=*(u32*)(base+0x313e04);
    if(extension+88>sizeof(runtime_pages[0].raster) || h->pages>8) {h->diagnostics[3]++;return;}
    u32 callargs[6]; copy(callargs,args,24); callargs[1]=(u32)text;
    for(u32 p=0;p<h->pages;p++) {
        Page *page=&runtime_pages[p];
        copy(page->font,font,32);
        copy(page->raster,raster,extension+88);
        page->font[0]=(u32)page->holder;
        page->holder[0]=(u32)page->resource;
        page->resource[4]=(u32)page->raster;
        page->raster[0]=(u32)page->raster; /* root raster parent is itself */
        page->font[1]=(u32)(dj_data+h->maps);
        page->font[2]=(u32)(dj_data+h->metrics+p*h->nonbuttons*12);
        page->font[4]=0x44000000; page->font[5]=0x44000000; /* 512.0 */
        page->font[6]=h->nonbuttons;
        page->raster[1]=(u32)(dj_data+h->pixels+p*262144);
        page->raster[2]=(u32)(dj_data+h->palette);
        page->raster[3]=512;page->raster[4]=512;page->raster[5]=8;page->raster[6]=512;
        ((u8*)page->raster)[35]&=0x7f; /* no mipmap table: use base-level pixels */
        u32 *native=(u32*)((u8*)page->raster+extension);
        native[20]=5; /* PSP GU_PSM_T8 */
        native[21]=1; /* swizzled */
        callargs[0]=(u32)page->font;
        dj_draw(callargs);
    }
}
