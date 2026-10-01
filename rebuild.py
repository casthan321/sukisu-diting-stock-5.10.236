"""Pinned source build; no identity edits to the compiled kernel image."""
import concurrent.futures, copy, gzip, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tarfile, urllib.request, zipfile
ROOT=pathlib.Path(__file__).resolve().parent
WORK=ROOT/'work';COMMON=WORK/'common';OUT=WORK/'out';ART=ROOT/'artifacts';CACHE=ROOT/'downloads'
RELEASE='5.10.236-android12-9-00003-gfb24cf99ad97-ab14313284'
VERSION='#1 SMP PREEMPT Tue Oct 21 03:03:12 UTC 2025'
KERNEL='fb24cf99ad973cd4c7c7fa375c6053f939ef3a89'
KSU='b88403d2561b6e00dff84a3c851e630c62f57fd0'
SUSFS='3469d88bdb12da8948131cc7032f4f37730bd3de'
PATCHES='547ae94bcaec53d030398f857950c64662043a5d'
SOURCES={
 'kernel.tar.gz':('https://github.com/casthan321/sukisu-diting-stock-5.10.236/releases/download/source-cache-20261002/kernel-fb24cf99ad973cd4c7c7fa375c6053f939ef3a89.tar.gz','ed35e45b0db97b3d0004c757f0e9e3af627a09f093bbc044e7e4166979386c13'),
 'clang.tar.gz':('https://github.com/casthan321/sukisu-diting-stock-5.10.236/releases/download/source-cache-20261002/clang-r416183b-linux.tar.gz','e1956d42bd6ef73d25a36c6e597b963cd4fd739f117e54038cd6e84abd3fec45'),
 'sukisu.tar.gz':('https://codeload.github.com/SukiSU-Ultra/SukiSU-Ultra/tar.gz/'+KSU,'af02f1214cfbe14f8f2c0fe6daa5609aa40907fe525d3248f77bdd08c5487c1d'),
 'susfs.tar.gz':('https://codeload.github.com/ShirkNeko/susfs4ksu/tar.gz/'+SUSFS,None),
 'patches.tar.gz':('https://codeload.github.com/ShirkNeko/SukiSU_patch/tar.gz/'+PATCHES,None),
 'template.zip':('https://github.com/ShirkNeko/GKI_KernelSU_SUSFS/releases/download/v2.1.0/android12-5.10.236-2025-05-AnyKernel3.zip','4f86b8eb96b7bdd6b84670aa198c10ac4d440e20916173f553dacb0ef800f58d'),
}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(args,cwd=None,env=None):
 print('+', ' '.join(map(str,args)),flush=True)
 subprocess.run(list(map(str,args)),cwd=cwd,env=env,check=True)
def download(item):
 name,(url,expected)=item;p=CACHE/name
 if not p.exists():
  run(['curl','--fail','--location','--retry','3','--retry-all-errors','--output',str(p)+'.partial',url])
  pathlib.Path(str(p)+'.partial').replace(p)
 digest=sha(p)
 assert expected is None or digest==expected,(name,digest,expected)
 print('Verified download',name,digest,flush=True)
 return {'file':name,'url':url,'sha256':digest}
def extract(name,dest,strip=False):
 dest.mkdir(parents=True,exist_ok=True)
 with tarfile.open(CACHE/name) as t:
  for member in t:
   if strip:
    pieces=member.name.split('/',1)
    if len(pieces)<2 or not pieces[1]:continue
    member.name=pieces[1]
   target=(dest/member.name).resolve()
   assert target==dest.resolve() or dest.resolve() in target.parents,member.name
   t.extract(member,dest)
def config_dict(text):
 d={}
 for ln in text.splitlines():
  if ln.startswith('CONFIG_'):k,v=ln.split('=',1);d[k]=v
  elif ln.startswith('# CONFIG_') and ln.endswith(' is not set'):d[ln.split()[1]]='n'
 return d
def protected_sources():
 roots=['kernel/sched','drivers/cpufreq','drivers/cpuidle','drivers/thermal','drivers/opp','kernel/power']
 paths=[COMMON/'kernel/power/energy_model.c']
 for root in roots:paths.extend(p for p in (COMMON/root).rglob('*') if p.is_file())
 return {str(p.relative_to(COMMON)):sha(p) for p in paths if p.exists()}
def apply_patch(path):
 run(['patch','--batch','-p1','--fuzz=0','--input',path],cwd=COMMON)
def prepare():
 CACHE.mkdir(exist_ok=True);WORK.mkdir(exist_ok=True);ART.mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:downloads=list(pool.map(download,SOURCES.items()))
 (ART/'sources.json').write_text(json.dumps(downloads,indent=2))
 extract('kernel.tar.gz',COMMON);extract('clang.tar.gz',WORK/'clang')
 extract('sukisu.tar.gz',WORK/'KernelSU',True);extract('susfs.tar.gz',WORK/'susfs',True);extract('patches.tar.gz',WORK/'patches',True)
 before=protected_sources()
 assert 'SUBLEVEL = 236' in (COMMON/'Makefile').read_text()
 run([WORK/'clang/bin/clang','--version'])
 # No kernel source revision replacement after this point.
 drivers=COMMON/'drivers';(drivers/'kernelsu').symlink_to('../..'+'/KernelSU/kernel')
 with (drivers/'Makefile').open('a') as f:f.write('\nobj-$(CONFIG_KSU) += kernelsu/\n')
 kc=drivers/'Kconfig';text=kc.read_text();assert text.endswith('endmenu\n')
 kc.write_text(text[:-len('endmenu\n')]+'source "drivers/kernelsu/Kconfig"\nendmenu\n')
 for src,dst in [(WORK/'susfs/kernel_patches/fs',COMMON/'fs'),(WORK/'susfs/kernel_patches/include/linux',COMMON/'include/linux')]:
  shutil.copytree(src,dst,dirs_exist_ok=True)
 apply_patch(WORK/'susfs/kernel_patches/50_add_susfs_in_gki-android12-5.10.patch')
 apply_patch(WORK/'patches/69_hide_stuff.patch')
 task=COMMON/'fs/proc/task_mmu.c';text=task.read_text()
 if 'if (!vma_pages(vma))' not in text and 'goto show_pad;' in text:task.write_text(text.replace('goto show_pad;','return 0;'))
 after=protected_sources();assert before==after,'Scheduler / CPUfreq / idle / thermal / power source changed'
 (ART/'protected-source-hashes.json').write_text(json.dumps(before,indent=2))
 # Freeze root ABI metadata instead of querying current upstream versions on every make invocation.
 makefile=WORK/'KernelSU/kernel/Makefile';text=makefile.read_text()
 start=text.index('MDIR    :=');end=text.index('$(info -- $(REPO_NAME) version:')
 text=text[:start]+'''REPO_NAME := SukiSU-Ultra
KSU_VERSION := 40811
KSU_VERSION_FULL := v4.1.3-b88403d2@builtin
'''+text[end:];makefile.write_text(text)
 # Generate all identity strings from source, including vermagic and startup banner.
 local=COMMON/'scripts/setlocalversion';local.write_text('#!/bin/sh\nprintf "%s\\n" "'+RELEASE[len('5.10.236'):]+'"\n');local.chmod(0o755)
 mk=COMMON/'scripts/mkcompile_h';text=mk.read_text()
 needle='UTS_VERSION="$(echo $UTS_VERSION $CONFIG_FLAGS $TIMESTAMP | cut -b -$UTS_LEN)"';assert text.count(needle)==1
 text=text.replace(needle,'UTS_VERSION="'+VERSION+'"')
 text=text.replace('UTS_VERSION="#$VERSION"','LINUX_COMPILE_BY="build-user"\nLINUX_COMPILE_HOST="build-host"\nUTS_VERSION="#$VERSION"');mk.write_text(text)
 # Retain vendor export lists from the same kernel commit, preserving module CRC machinery.
 symbols=set()
 for path in (COMMON/'android').glob('abi_gki_aarch64*'):
  if path.suffix=='.xml' or not path.is_file():continue
  for line in path.read_text().splitlines():
   line=line.strip()
   if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',line):symbols.add(line)
 assert len(symbols)>1000
 (OUT).mkdir(exist_ok=True);whitelist=OUT/'abi_symbollist.raw';whitelist.write_text('\n'.join(sorted(symbols))+'\n')
 cfg=(ROOT/'stock.config').read_text()
 cfg=re.sub(r'^CONFIG_UNUSED_KSYMS_WHITELIST=.*$', 'CONFIG_UNUSED_KSYMS_WHITELIST="'+str(whitelist)+'"',cfg,flags=re.M)
 # Root-specific features only; retain stock networking, compression, FullLTO and CPU policy.
 root_cfg=config_dict((ROOT/'sukisu-original.config').read_text())
 for key,val in root_cfg.items():
  if key.startswith('CONFIG_KSU') or key=='CONFIG_KPM':cfg+='\n'+(key+'='+val if val!='n' else '# '+key+' is not set')
 for key in ('CONFIG_TMPFS_XATTR','CONFIG_TMPFS_POSIX_ACL'):
  cfg=re.sub(r'^# '+key+r' is not set$',key+'=y',cfg,flags=re.M)
 (OUT/'.config').write_text(cfg+'\n')
 (ART/'provenance.json').write_text(json.dumps({'kernel':KERNEL,'sukisu':KSU,'susfs':SUSFS,'sukisu_patches':PATCHES,'template':'ShirkNeko v2.1.0 android12-5.10.236-2025-05','root_driver':40811,'notice':'Custom source build; stock identity and protected sources checked. Actual power consumption, module loading, and root authorization require device validation.'},indent=2))
def environment():
 env=os.environ.copy();env.update(PATH=str(WORK/'clang/bin')+':'+env['PATH'],KBUILD_BUILD_USER='build-user',KBUILD_BUILD_HOST='build-host',KBUILD_BUILD_TIMESTAMP='Tue Oct 21 03:03:12 UTC 2025',KBUILD_BUILD_VERSION='1',CCACHE_BASEDIR=str(WORK),CCACHE_NOHASHDIR='true',CCACHE_COMPILERCHECK='content')
 return env
def make_args():
 return ['make','-C',COMMON,'O='+str(OUT),'ARCH=arm64','LLVM=1','LLVM_IAS=1','CC=ccache clang','KCFLAGS=-D__ANDROID_COMMON_KERNEL__']
def check_config():
 original=config_dict((ROOT/'stock.config').read_text());actual=config_dict((OUT/'.config').read_text())
 differences={k:[original.get(k),actual.get(k)] for k in original.keys()|actual.keys() if original.get(k)!=actual.get(k)}
 allowed={'CONFIG_KPM','CONFIG_TMPFS_XATTR','CONFIG_TMPFS_POSIX_ACL','CONFIG_UNUSED_KSYMS_WHITELIST'}
 unexpected={k:v for k,v in differences.items() if not k.startswith('CONFIG_KSU') and k not in allowed}
 (ART/'config-differences.json').write_text(json.dumps(differences,indent=2))
 assert not unexpected,unexpected
 for k in ('CONFIG_KSU','CONFIG_KSU_SUSFS','CONFIG_KPM','CONFIG_LTO_CLANG_FULL','CONFIG_MODVERSIONS'):assert actual.get(k)=='y',(k,actual.get(k))
 shutil.copyfile(OUT/'.config',ART/'compiled.config')
def build():
 env=environment();run(make_args()+['olddefconfig'],env=env);check_config()
 run(make_args()+['-j'+str(os.cpu_count()),'Image'],env=env)
def verify(image):
 raw=image.read_bytes();assert raw[56:60]==b'ARMd'
 expected=json.loads((ROOT/'identity.json').read_text())['banner'].encode()
 banners=re.findall(rb'Linux version 5\.10\.236[^\x00\n]+',raw);assert banners==[expected],[x.decode(errors='replace') for x in banners]
 releases={x.decode() for x in re.findall(rb'5\.10\.236-android12-[A-Za-z0-9._+\-]+',raw)};assert releases=={RELEASE},releases
 valid=[]
 for m in re.finditer(rb'Linux\x00{1,64}[^\x00]{0,64}\x00',raw):
  o=m.start();fields=[raw[o+i*65:o+(i+1)*65].split(b'\0')[0].decode(errors='replace') for i in range(6)]
  if fields[4]=='aarch64':valid.append(fields)
 assert len(valid)==1 and valid[0][2:4]==[RELEASE,VERSION],valid
 assert b'v4.1.3-b88403d2@builtin' in raw
 start=raw.index(b'IKCFG_ST')+8;end=raw.index(b'IKCFG_ED',start)
 assert gzip.decompress(raw[start:end]).decode()==(OUT/'.config').read_text()
 return {'image_sha256':sha(image),'banner':expected.decode(),'uts':valid[0],'all_release_strings':sorted(releases)}
def package():
 image=OUT/'arch/arm64/boot/Image';before=verify(image)
 dist=WORK/'kpm-finalize';dist.mkdir(exist_ok=True);shutil.copyfile(image,dist/'Image')
 patch=dist/'patch';shutil.copyfile(WORK/'patches/kpm/patch_linux',patch);patch.chmod(0o755)
 run(['./patch'],cwd=dist);final=dist/'oImage';assert final.exists()
 result=verify(final);result['before_kpm_sha256']=before['image_sha256']
 output=ART/(RELEASE+'-diting-SukiSU-SUSFS-Rebuilt-AK3.zip')
 with zipfile.ZipFile(CACHE/'template.zip') as src,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
  for entry in src.infolist():
   data=src.read(entry.filename)
   if entry.filename=='Image':data=final.read_bytes()
   elif entry.filename=='anykernel.sh':
    text=data.decode().replace('kernel.string=Wild Kernels by TheWildJames aka Morgan Weedman','kernel.string='+RELEASE+' / SukiSU source rebuild')
    text=text.replace('do.devicecheck=0','do.devicecheck=1').replace('device.name1=\n','device.name1=diting\n').replace('supported.versions=\n','supported.versions=15\n')
    guard='rom_version=$(getprop ro.build.version.incremental)\n[ "$rom_version" = "OS3.0.3.0.VLFCNXM" ] || abort "Requires OS3.0.3.0.VLFCNXM; found $rom_version"\n'
    data=text.replace('. tools/ak3-core.sh\n','. tools/ak3-core.sh\n'+guard).encode()
   dst.writestr(copy.copy(entry),data)
 with zipfile.ZipFile(output) as check:assert check.testzip() is None and check.read('Image')==final.read_bytes()
 result.update(zip_sha256=sha(output),source_rebuild=True,protected_sources_unchanged=True,on_device_tested=False)
 (ART/'verification.json').write_text(json.dumps(result,indent=2))
 (ART/'SHA256SUMS.txt').write_text(sha(output)+'  '+output.name+'\n')
 for name in ('Module.symvers','System.map'): 
  if (OUT/name).exists():shutil.copyfile(OUT/name,ART/name)
 print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
