# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Run an isolated libretro GBA core; never writes ROM or source saves."""
import ctypes as C
import json
from pathlib import Path
import zipfile
import numpy as np
import struct
import hashlib
from PIL import Image

G = Path(__file__).resolve().parents[1]
OUT = G / 'data/runtime_trace'
ROM = G.parent.parent / '宝可梦水银FC~致150年后的你 Version 1.1 (1).gba'
SAVE = G.parent.parent / 'Pokemon_Mercury_FC.srm'

class Variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]
class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]
class Descriptor(C.Structure):
    _fields_ = [('flags', C.c_uint64), ('ptr', C.c_void_p), ('offset', C.c_size_t), ('start', C.c_size_t), ('select', C.c_size_t), ('disconnect', C.c_size_t), ('len', C.c_size_t), ('addrspace', C.c_char_p)]
class MemoryMap(C.Structure):
    _fields_ = [('descriptors', C.POINTER(Descriptor)), ('count', C.c_uint)]
ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL = C.CFUNCTYPE(None)
INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

class Core:
    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        dll = OUT / 'mgba_libretro.dll'
        if not dll.exists():
            with zipfile.ZipFile(OUT / 'mgba_libretro.dll.zip') as z:
                dll.write_bytes(z.read('mgba_libretro.dll'))
        self.lib = C.CDLL(str(dll))
        self.options = {}
        self.directory = str(OUT).encode()
        self.pixel_format = 0
        self.descriptors = []
        self.pressed = set()
        self.last_frame = None
        self.callbacks = [ENV(self.environment), VIDEO(self.video), AUDIO(lambda l,r:None), BATCH(lambda data,n:n), POLL(lambda:None), INPUT(lambda port,dev,index,key:int(key in self.pressed))]
        for name, cb in zip(('environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'),self.callbacks):
            fn=getattr(self.lib,'retro_set_'+name);fn.argtypes=[type(cb)];fn(cb)
        self.lib.retro_get_memory_data.argtypes=[C.c_uint];self.lib.retro_get_memory_data.restype=C.c_void_p
        self.lib.retro_get_memory_size.argtypes=[C.c_uint];self.lib.retro_get_memory_size.restype=C.c_size_t
        self.lib.retro_load_game.argtypes=[C.POINTER(GameInfo)];self.lib.retro_load_game.restype=C.c_bool
        self.lib.retro_serialize_size.restype=C.c_size_t
        self.lib.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];self.lib.retro_serialize.restype=C.c_bool
        self.lib.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];self.lib.retro_unserialize.restype=C.c_bool
        self.lib.retro_init()
        self.rom = C.create_string_buffer(ROM.read_bytes())
        self.info = GameInfo(str(ROM).encode(),C.addressof(self.rom),len(self.rom)-1,None)
        if not self.lib.retro_load_game(C.byref(self.info)):raise RuntimeError('ROM load failed')
        save=SAVE.read_bytes();size=self.lib.retro_get_memory_size(0)
        if len(save)!=size:raise RuntimeError(f'SRAM size {size} != source {len(save)}')
        C.memmove(self.lib.retro_get_memory_data(0),save,len(save))

    def environment(self, command, data):
        command &= 0xffff
        if command in (9,30,31):C.cast(data,C.POINTER(C.c_char_p))[0]=self.directory;return True
        if command==10:self.pixel_format=C.cast(data,C.POINTER(C.c_uint))[0];return True
        if command==6:C.cast(data,C.POINTER(C.c_bool))[0]=True;return True
        if command==16:
            a=C.cast(data,C.POINTER(Variable));i=0
            while a[i].key:
                self.options[a[i].key]=a[i].value.split(b'; ',1)[-1].split(b'|')[0];i+=1
            return True
        if command==15:
            a=C.cast(data,C.POINTER(Variable));a[0].value=self.options.get(a[0].key);return a[0].value is not None
        if command==17:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
        if command==36:
            m=C.cast(data,C.POINTER(MemoryMap))[0]
            self.descriptors=[{k:getattr(m.descriptors[i],k) for k in ('ptr','offset','start','select','disconnect','len')} for i in range(m.count)]
            return True
        return command in (8,11,18,35,37)

    def video(self, data, width, height, pitch):
        if data:self.last_frame=(C.string_at(data,pitch*height),width,height,pitch,self.pixel_format)

    def memory(self,address,size):
        for d in self.descriptors:
            if d['ptr'] and d['start']<=address and address+size<=d['start']+d['len']:
                return d['ptr']+d['offset']+address-d['start']
        if 0x02000000<=address and address+size<=0x02040000:
            return self.lib.retro_get_memory_data(2)+address-0x02000000
        raise ValueError(f'Address not exposed: {address:08X}')

    def read(self,address,size):return C.string_at(self.memory(address,size),size)
    def write(self,address,data):C.memmove(self.memory(address,len(data)),data,len(data))

    def restore(self, path):
        data=Path(path).read_bytes();buf=C.create_string_buffer(data)
        if not self.lib.retro_unserialize(buf,len(data)):raise RuntimeError('Restore failed')

    def enter(self, group, num, x, y):
        # Only the isolated core's ROM buffer receives this call bridge.
        # Calls WarpIntoMap and SetMainCallback2(CB2_LoadMap2), bypassing only
        # the departure animation (which requires a live warp animation task).
        base=0x09FFFF00
        def bl(pc,target):
            delta=target-(pc+4)
            return struct.pack('<HH',0xF000|((delta>>12)&0x7FF),0xF800|((delta>>1)&0x7FF))
        bridge=bytes.fromhex('00b5054b')+bl(base+4,base+20)+bytes.fromhex('0448054b')+bl(base+12,base+20)+bytes.fromhex('00bdc0461847c046')+struct.pack('<III',0x08055379,0x0805674D,0x08000545)
        self.write(base,bridge)
        self.write(0x02031DBC,struct.pack('<bbbxhh',group,num,-1,x,y))
        self.write(0x030030F0,bytes(4))
        self.write(0x030030F4,struct.pack('<I',base|1))
        self.frames(180)

    def export_scene(self, mid):
        """Freeze engine-selected data after the native load loop has completed."""
        name='map_'+mid.replace(':','_')
        callback=struct.unpack('<I',self.read(0x030030F4,4))[0]
        if callback!=0x080565B5:
            raise RuntimeError(f'{mid}: still outside overworld callback: {callback:08X}')
        sb=struct.unpack('<I',self.read(0x03005008,4))[0]
        group,num=self.read(sb+4,2)
        if f'{group}:{num}'!=mid:raise RuntimeError('Scene redirected to a different map')
        header=self.read(0x02036DFC,28)
        lp=struct.unpack_from('<I',header)[0]
        w,h,border,blocks,primary,secondary,bw,bh=struct.unpack('<iiIIIIBB',self.read(lp,26))
        rw,rh,rp=struct.unpack('<III',self.read(0x03005040,12))
        if (rw,rh)!=(w+15,h+14):raise RuntimeError('Runtime map padding changed')
        grid=np.frombuffer(self.read(rp,rw*rh*2),dtype='<u2').reshape(rh,rw)
        cells=grid[7:7+h,7:7+w].copy().tobytes()
        graphics=self.read(0x06000000,32768)
        palette=self.read(0x020371F8,512)
        blobs={'cells':cells,'graphics':graphics,'palette_unfaded':palette}
        paths={}
        for kind,data in blobs.items():
            path=OUT/(name+'.'+kind+'.bin');path.write_bytes(data)
            paths[kind]={'file':str(path.relative_to(G)).replace('\\','/'),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        source=self.read(blocks,w*h*2)
        record={'map_id':mid,'method':'isolated native WarpIntoMap + CB2_LoadMap2; departure animation bypassed',
                'state_source':'data/runtime_trace/entry_3.state','load_complete':True,'callback':hex(callback),
                'rom_sha256':hashlib.sha256(self.rom.raw[:self.info.size]).hexdigest(),
                'source_save_sha256':hashlib.sha256(SAVE.read_bytes()).hexdigest(),
                'header':header.hex(),'layout':{'address':hex(lp),'width':w,'height':h,'border':hex(border),'map':hex(blocks),'primary_tileset':hex(primary),'secondary_tileset':hex(secondary),'border_width':bw,'border_height':bh},
                'tileset_headers':{hex(p):self.read(p,24).hex() for p in (primary,secondary)},
                'changed_cell_count':sum(a!=b for a,b in zip(struct.iter_unpack('<H',source),struct.iter_unpack('<H',cells))),
                'buffers':paths}
        (OUT/(name+'.native.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        return record

    def snapshot(self,name):
        if self.last_frame:
            raw,w,h,pitch,fmt=self.last_frame
            if fmt==1:
                pix=np.frombuffer(raw,dtype='<u4').reshape(h,pitch//4)[:,:w]
                rgb=np.stack([(pix>>s)&255 for s in (16,8,0)],axis=-1).astype('uint8')
            else:
                pix=np.frombuffer(raw,dtype='<u2').reshape(h,pitch//2)[:,:w]
                shifts,bits=((11,5,0),(31,63,31)) if fmt==2 else ((10,5,0),(31,31,31))
                rgb=np.stack([((pix>>s)&b)*255//b for s,b in zip(shifts,bits)],axis=-1).astype('uint8')
            Image.fromarray(rgb).save(OUT/(name+'.png'))
        (OUT/(name+'.ewram')).write_bytes(self.read(0x02000000,0x40000))
        for suffix,address,size in [('iwram',0x03000000,0x8000),('vram',0x06000000,0x18000),('palette',0x05000000,0x400)]:
            (OUT/(name+'.'+suffix)).write_bytes(self.read(address,size))
        size=self.lib.retro_serialize_size();buf=C.create_string_buffer(size)
        if not self.lib.retro_serialize(buf,size):raise RuntimeError('Snapshot serialization failed')
        (OUT/(name+'.state')).write_bytes(buf.raw)
        sb=struct.unpack('<I',self.read(0x03005008,4))[0]
        result={'name':name,'header':self.read(0x02036dfc,28).hex(),'saveblock':hex(sb),'location':self.read(sb,12).hex(),'memory_regions':[{k:v for k,v in d.items() if k!='ptr'} for d in self.descriptors]}
        (OUT/(name+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)

    def frames(self,count,keys=()):
        self.pressed=set(keys)
        for _ in range(count):self.lib.retro_run()
        self.pressed=set()

if __name__=='__main__':
    c=Core()
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--maps',nargs='*');args=parser.parse_args()
    if args.maps:
        for mid in args.maps:
            c.restore(OUT/'entry_3.state')
            g,n=map(int,mid.split(':'))
            c.enter(g,n,20,15);c.snapshot('map_'+mid.replace(':','_'))
            print(json.dumps(c.export_scene(mid),ensure_ascii=False),flush=True)
    else:
        c.frames(180);c.snapshot('boot')
        for i in range(8):
            c.frames(2,[3,8]);c.frames(118)
            c.snapshot(f'entry_{i}')
    c.lib.retro_unload_game();c.lib.retro_deinit()
