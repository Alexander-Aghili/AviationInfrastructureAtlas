"""Adopt a newer FAA NASR release: fetch, rebuild, test and write a change report for review.

Run by hand; nothing is committed. Any failure restores the previous sources, build and README.
"""
import argparse,datetime,json,pathlib,re,shutil,subprocess,sys,urllib.request
from release import BASE,cycle_on,is_cycle,next_cycle,retained_cycle
from release_diff import diff,markdown,summary
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw';OUT=ROOT/'public/data';BACKUP=ROOT/'data/.update-backup'
TRACKED=['data/supplemental/airport-reference-manifest.json','data/boundaries/manifest.json','data/coverage/terrain-manifest.json','README.md']
def published(cycle):
    request=urllib.request.Request(BASE+cycle+'/README.txt',headers={'User-Agent':'AirwaysAtlas/1.0 public-source-import'})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:return response.status==200
    except OSError:return False
def run(command,label):
    print('·',label,flush=True)
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(f'{label} failed:\n'+(result.stdout+result.stderr)[-4000:])
def update_readme(text,cycle,audit,features):
    replacements=[(r'FAA NASR cycle \*\*[\d-]+\*\*',f'FAA NASR cycle **{cycle}**')]
    missing=[]
    for pattern,value in replacements:
        text,count=re.subn(pattern,value,text)
        if not count:missing.append(pattern)
    return text,missing
def restore(current):
    try:swapped=retained_cycle(RAW)!=current
    except (OSError,ValueError):swapped=(ROOT/'data/raw.previous').exists()
    if swapped:
        shutil.rmtree(RAW,ignore_errors=True);(ROOT/'data/raw.previous').rename(RAW)
    if (BACKUP/'public-data').exists():
        shutil.rmtree(OUT);shutil.copytree(BACKUP/'public-data',OUT)
    for name in TRACKED:
        if (BACKUP/name).exists():shutil.copy2(BACKUP/name,ROOT/name)
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cycle',help='adopt this NASR effective date (YYYY-MM-DD) instead of the latest effective one')
    parser.add_argument('--upcoming',action='store_true',help='adopt the next cycle once FAA has posted it, before it takes effect')
    parser.add_argument('--check',action='store_true',help='only report whether a newer cycle is available')
    parser.add_argument('--keep-boundaries',action='store_true',help='do not refresh FAA chart boundary polygons')
    args=parser.parse_args(argv)
    current=retained_cycle(RAW);today=datetime.date.today()
    target=args.cycle or (next_cycle(cycle_on(today)) if args.upcoming else cycle_on(today))
    if not is_cycle(target):parser.error(target+' is not a NASR 28-day effective date')
    if target==current or (target<current and not args.cycle):
        print(f'Already on NASR {current}; nothing newer is effective. Use --upcoming for {next_cycle(cycle_on(today))}.');return 0
    if not published(target):print(f'NASR {target} is not posted by FAA yet (retained: {current}).');return 0
    if args.check:print(f'NASR {target} is available (retained: {current}). Run without --check to adopt it.');return 0
    old=json.loads((OUT/'facilities.json').read_text());old_audit=json.loads((OUT/'audit.json').read_text())
    if BACKUP.exists():shutil.rmtree(BACKUP)
    shutil.copytree(OUT,BACKUP/'public-data')
    for name in TRACKED:(BACKUP/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,BACKUP/name)
    report_path=ROOT/'data/releases'/f'{target}.md'
    try:
        print(f'· Fetching NASR {target} (retained: {current})',flush=True)
        import acquire_faa;acquire_faa.main(target)
        if not args.keep_boundaries:
            print('· Refreshing FAA chart boundaries',flush=True)
            import acquire_boundaries;acquire_boundaries.main()
        run([sys.executable,'scripts/import_faa.py'],'Rebuilding normalized data')
        run([sys.executable,'scripts/build_coverage.py'],'Rebuilding modeled radar coverage')
        new=json.loads((OUT/'facilities.json').read_text());new_audit=json.loads((OUT/'audit.json').read_text())
        report=diff(old,new)
        report_path.parent.mkdir(exist_ok=True);report_path.write_text(markdown(report,current,target,old_audit,new_audit))
        readme,missing=update_readme((ROOT/'README.md').read_text(),target,new_audit,new);(ROOT/'README.md').write_text(readme)
        run(['npm','test'],'Running unit tests')
    except BaseException as error:
        restore(current);report_path.unlink(missing_ok=True);shutil.rmtree(BACKUP,ignore_errors=True)
        print(f'\nUpdate to {target} failed; previous sources and build restored.\n{error}',file=sys.stderr);return 1
    shutil.rmtree(BACKUP)
    print(f"\nNASR {current} → {target}: {summary(report)}")
    print(f"Records {old_audit['records']:,} → {new_audit['records']:,}; report: {report_path.relative_to(ROOT)}")
    for pattern in missing:print('README: no match for',pattern,'— update that statement by hand.')
    print('Previous raw files: data/raw.previous. Review the report and `git diff`, then run `npm run test:browser` and commit.')
    return 0
if __name__=='__main__':sys.exit(main())
