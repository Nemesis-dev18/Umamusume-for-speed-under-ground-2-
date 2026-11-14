"""Build and exercise the module in independent D3D9 hosts; never launch NFSU2."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = Path('/home/nemesis/Documents/Codex/2026-11-13/tu-x20/work')
RUNTIME = ROOT / 'modding/runtime'
CC = WORK / 'mingw/usr/bin/i686-w64-mingw32-gcc'
FLAGS = [f'--sysroot={WORK}/mingw/usr/i686-w64-mingw32/sys-root', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static-libgcc']
WINE = Path('/home/nemesis/.local/share/Steam/steamapps/common/Proton - Experimental/files/bin/wine')


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], cwd=ROOT, check=True, timeout=60, **kwargs)


def main():
    build = RUNTIME / 'test-build'
    build.mkdir(exist_ok=True)
    for name in ('renderer', 'runner_integration', 'runner_load'):
        run([CC, *FLAGS, RUNTIME / f'{name}_test.c', '-o', build / f'{name}-test.exe', '-ld3d9', '-luser32', '-lm'])
    run([CC, *FLAGS, '-shared', RUNTIME / 'uma_runner.c', '-o', RUNTIME / 'UmaRunner.asi', '-ld3d9', '-luser32', '-lm'])
    run(['gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', RUNTIME / 'scene_speed_test.c', '-o', build / 'scene-speed-test', '-lm'])
    run([build / 'scene-speed-test'])
    fixture = RUNTIME / 'runner-load-test'
    (fixture / 'scripts').mkdir(exist_ok=True)
    (fixture / 'modding/runtime').mkdir(parents=True, exist_ok=True)
    for name in ('kitasan.umab', 'atlas.dds'):
        shutil.copyfile(RUNTIME / name, fixture / 'modding/runtime' / name)
    shutil.copyfile(RUNTIME / 'UmaRunner.asi', fixture / 'scripts/UmaRunner.asi')
    (fixture / 'modding/uma-runner.log').unlink(missing_ok=True)
    env = dict(os.environ, WINEPREFIX=str(WORK / 'proton-prefix/pfx'), WINEDEBUG='-all')
    for name in ('renderer', 'runner_integration', 'runner_load'):
        run([WINE, build / f'{name}-test.exe'], env=env)
    results = {}
    for name, folder in (('renderer', 'gpu-test'), ('integration', 'integration-test')):
        lines = (RUNTIME / folder / 'result.txt').read_text().splitlines()
        if not lines or not lines[-1].startswith('PASS'):
            raise RuntimeError(f'{name} did not finish successfully')
        results[name] = lines[-1]
    hashes = {name: hashlib.sha256((RUNTIME / name).read_bytes()).hexdigest() for name in ('UmaRunner.asi', 'kitasan.umab', 'atlas.dds')}
    report = {'scope': 'Independent test hosts, not NFSU2 gameplay', 'results': results, 'sha256': hashes, 'gameplay_verified': False}
    (RUNTIME / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
