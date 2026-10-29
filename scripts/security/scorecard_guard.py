#!/usr/bin/env python3
"""Offline checks for selected Scorecard regressions. Not a YAML/SAST replacement."""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

@dataclass(frozen=True)
class Finding:
    path: str
    rule: str
    scope: str
    evidence: str
    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

def scan_text(path: str, text: str) -> list[Finding]:
    result = []
    def add(rule, scope, evidence):
        result.append(Finding(path, rule, scope, evidence.strip()))
    workflow = path.startswith('.github/workflows/') and path.endswith(('.yml', '.yaml'))
    lines = text.splitlines()
    if workflow:
        # The conservative supported shape uses block mappings with two-space jobs.
        # Unsupported permissions syntax fails, rather than silently passing.
        tops = [(i, line) for i, line in enumerate(lines) if re.match(r'^permissions\s*:', line)]
        if len(tops) != 1:
            add('top-level-permissions', 'workflow', 'expected exactly one top-level permissions mapping')
        job = 'workflow'
        if re.search(r'(?m)^\s*(?:on:.*)?\bpull_request_target\s*:', text) and re.search(r'(?m)^\s*-?\s*uses:\s*actions/checkout@', text):
            add('privileged-pr-checkout', 'workflow', 'pull_request_target combined with actions/checkout')
        for i, line in enumerate(lines):
            if line.lstrip().startswith('#'):continue
            m = re.match(r'^  ([A-Za-z_][\w-]*):\s*(?:#.*)?$', line)
            if m:
                # Only treat keys under jobs: as job identifiers.
                prior = next((s for s in reversed(lines[:i]) if s and not s.startswith((' ', '#'))), '')
                if prior.strip() == 'jobs:': job = m[1]
            if '\t' in line[:len(line) - len(line.lstrip())]:
                add('unsupported-yaml', job, 'tab indentation: ' + line)
            if re.match(r'^\s*permissions\s*:', line):
                indent = len(line) - len(line.lstrip())
                scope = 'workflow' if indent == 0 else job
                value = line.split(':', 1)[1].split('#', 1)[0].strip()
                if value not in ('', '{}', 'read-all'):
                    add('permissions-shape', scope, line)
                if indent not in (0, 4):
                    add('permissions-location', scope, line)
                for child in lines[i+1:]:
                    if not child.strip() or child.lstrip().startswith('#'):continue
                    child_indent = len(child) - len(child.lstrip())
                    if child_indent <= indent:break
                    p = re.fullmatch(r'\s*([\w-]+):\s*(read|write|none)\s*(?:#.*)?', child)
                    if not p:
                        add('permissions-shape', scope, child);continue
                    if p[2] == 'write':
                        add('top-level-write' if indent == 0 else 'job-write', scope, child)
            # Any action/reusable workflow reference, including docker actions.
            m = re.search(r'(?:^|\s)uses:\s*(\S+)', line)
            if m:
                ref = m[1].strip('\"\'')
                if ref.startswith('./'):continue
                if ref.startswith('docker://'):
                    good = re.search(r'@sha256:[a-fA-F0-9]{64}$', ref)
                else:good = re.search(r'@[a-fA-F0-9]{40}$', ref)
                if not good:add('unpinned-action', job, ref)
    if Path(path).name.startswith('Dockerfile') or Path(path).suffix == '.dockerfile':
        stages = set()
        logical = re.sub(r'\\\s*\n\s*', ' ', text)
        for line in logical.splitlines():
            m = re.match(r'^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?', line, re.I)
            if not m:continue
            image = m[1]
            if image.lower() not in stages and image != 'scratch' and not re.search(r'@sha256:[a-fA-F0-9]{64}$', image):
                add('unpinned-container', 'docker', line)
            if m[2]:stages.add(m[2].lower())
    # Detect pip invocation on each logical shell line, including pip3/python -m pip.
    logical = re.sub(r'\\\s*\n\s*', ' ', text)
    for line in logical.splitlines():
        if line.lstrip().startswith('#'):continue
        m = re.search(r'\b(?:pip(?:3)?|python(?:3(?:\.\d+)?)?\s+-m\s+pip)(?:\s+--[\w-]+(?:=[^\s]+)?)*\s+install\b(.*)', line)
        if not m:
            m = re.search(r'\bpipx(?:\s+--[\w-]+(?:=[^\s]+)?)*\s+install\b(.*)', line)
            if m:add('unhashed-pipx-install', 'dependencies', m[0].strip())
            continue
        args = re.split(r'\s*(?:&&|\|\||;)\s*', m[1], maxsplit=1)[0].strip()
        # Local installs are safe only when transitive resolution/build isolation are off.
        offline = ('--no-deps' in args and '--no-build-isolation' in args
                   and not re.search(r'https?://|git\+', args)
                   and bool(re.search(r'(?:^|\s)[\"\']?(?:\./|/wheels/)', args)))
        hashed = '--require-hashes' in args and re.search(r'(?:^|\s)(?:-r\s*|--requirement(?:=|\s))\S+', args)
        if not (offline or hashed):add('unhashed-pip-install', 'dependencies', re.split(r'\s*(?:&&|\|\||;)\s*', m[0], maxsplit=1)[0].strip())
        if hashed:
            try:tokens = shlex.split(args)
            except ValueError:
                add('pip-command-shape', 'dependencies', args);continue
            reqs=[]
            for idx,t in enumerate(tokens):
                if t in ('-r','--requirement') and idx+1<len(tokens):reqs.append(tokens[idx+1])
                elif t.startswith('--requirement='):reqs.append(t.split('=',1)[1])
                elif t.startswith('-r') and t!='-r':reqs.append(t[2:])
            for req in reqs:
                if '$' in req or req.startswith('/') or '..' in Path(req).parts:
                    add('requirements-path', 'dependencies', req)
    return list(dict.fromkeys(result))

def scan(root: Path) -> list[Finding]:
    files = set()
    for p in (root/'.github/workflows').glob('*'):
        if p.suffix in ('.yml','.yaml'):files.add(p)
    for p in root.rglob('*'):
        if any(x in ('.git','.venv','venv','node_modules','vendor','build','dist') for x in p.relative_to(root).parts):continue
        if p.is_file() and (p.name.startswith('Dockerfile') or p.suffix == '.dockerfile' or (p.suffix == '.sh' and 'scripts' in p.relative_to(root).parts)):
            files.add(p)
    findings=[]
    for p in sorted(files):
        if p.is_symlink():
            findings.append(Finding(p.relative_to(root).as_posix(),'symlink-input','filesystem','symlink not scanned'));continue
        findings.extend(scan_text(p.relative_to(root).as_posix(), p.read_text(encoding='utf-8')))
    # Requirements hash verification, only for static -r files named by guarded inputs.
    for p in sorted(files):
        if p.is_symlink():continue
        for req in re.findall(r'\bpip(?:3)?\s+install[^\n]*(?:-r\s+|--requirement(?:=|\s+))([\w./-]+)', re.sub(r'\\\s*\n\s*',' ',p.read_text(encoding='utf-8'))):
            target=root/req
            if not target.is_file() or target.is_symlink():
                findings.append(Finding(p.relative_to(root).as_posix(),'requirements-missing','dependencies',req));continue
            content=re.sub(r'\\\s*\n\s*',' ',target.read_text())
            for line in content.splitlines():
                line=line.strip()
                if not line or line.startswith('#'):continue
                if not re.match(r'^[A-Za-z0-9_.-]+(?:\[[\w,.-]+\])?==[^\s;]+',line) or not re.search(r'--hash=sha256:[a-f0-9]{64}(?:\s|$)',line):
                    findings.append(Finding(req,'unhashed-requirement','dependencies',line))
    return list(dict.fromkeys(findings))

def evaluate(findings, baseline):
    entries=baseline.get('findings',[])
    if baseline.get('version') != 1:raise ValueError('baseline version must be 1')
    allowed={}
    for e in entries:
        f=Finding(**{k:e[k] for k in ('path','rule','scope','evidence')})
        if not e.get('issue') or not e.get('reason'):raise ValueError('each baseline entry needs issue and reason')
        if f.fingerprint in allowed:raise ValueError('duplicate baseline entry')
        allowed[f.fingerprint]=e
    current={f.fingerprint:f for f in findings}
    return [f for key,f in current.items() if key not in allowed], [e for key,e in allowed.items() if key not in current]

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--baseline',type=Path,default=Path('.github/scorecard-baseline.json'))
    parser.add_argument('--inventory',action='store_true',help='print findings; never writes/updates a baseline')
    args=parser.parse_args(argv)
    findings=scan(args.root.resolve())
    if args.inventory:
        print(json.dumps([asdict(f) for f in findings],indent=2));return bool(findings)
    path=args.root/args.baseline
    try:
        baseline=json.loads(path.read_text()) if path.exists() else {'version':1,'findings':[]}
        if not isinstance(baseline,dict):raise ValueError('baseline must be an object')
        new,stale=evaluate(findings,baseline)
    except (OSError,ValueError,KeyError,TypeError) as e:print('Invalid baseline:',e,file=sys.stderr);return 2
    for f in new:print(f'{f.path}: {f.rule} [{f.scope}]: {f.evidence}')
    for e in stale:print(f'Stale baseline entry: {e["path"]}: {e["rule"]}; remove after fixing')
    print(f'Scorecard guard: {len(findings)} findings, {len(new)} new, {len(stale)} stale baseline entries')
    return bool(new or stale)

if __name__=='__main__':sys.exit(main())
