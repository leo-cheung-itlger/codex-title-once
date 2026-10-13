"""Install/uninstall only this package's Windows user-level Codex hooks."""
import argparse, json, os, pathlib, shutil, time
import auto_title as runtime

SOURCE = pathlib.Path(__file__).resolve().parent
COMMAND = 'py -3 -c "import os,runpy;runpy.run_path(os.path.join(os.environ.get(\'CODEX_HOME\',os.path.join(os.path.expanduser(\'~\'),\'.codex\')),\'thread-naming\',\'auto_title.py\'),run_name=\'__main__\')" hook'
EVENTS = ('SessionStart', 'UserPromptSubmit', 'Stop')

def owned(handler):
    command = handler.get('command', '')
    return 'auto_title.py' in command and 'thread-naming' in command

def install(home):
    root = home / 'thread-naming'
    root.mkdir(parents=True, exist_ok=True)
    backup = root / 'installation-backup'
    backup.mkdir(exist_ok=True)
    for name in ('hooks.json', 'config.toml'):
        original = home / name
        if original.exists() and not (backup / name).exists():
            shutil.copy2(original, backup / name)
    target = root / 'auto_title.py'
    if SOURCE / 'auto_title.py' != target:
        if target.exists():
            saved = backup / ('auto_title.before-' + str(time.time_ns()) + '.py')
            shutil.copy2(target, saved)
        shutil.copy2(SOURCE / 'auto_title.py', target)
    settings = runtime.read(root / 'settings.json', None)
    if settings is None:
        settings = {'enabled': True, 'installed_at': int(time.time()),
                    'protection': 'first_default_once', 'version': 1}
        runtime.write(root / 'settings.json', settings)
    # Existing applied/protected states and the original install cutoff are retained.
    hooks = runtime.read(home / 'hooks.json', {'hooks': {}})
    for event in EVENTS:
        groups = hooks.setdefault('hooks', {}).setdefault(event, [])
        for group in groups:
            group['hooks'] = [h for h in group.get('hooks', []) if not owned(h)]
        groups[:] = [g for g in groups if g.get('hooks')]
        handler = {'type': 'command', 'command': COMMAND, 'timeout': 30}
        if event != 'Stop':
            handler['additionalContextLimit'] = 1000
        groups.append({'hooks': [handler]})
    runtime.write(home / 'hooks.json', hooks)
    return root

def uninstall(home):
    root = home / 'thread-naming'
    settings = runtime.read(root / 'settings.json', {})
    if settings:
        settings['enabled'] = False
        runtime.write(root / 'settings.json', settings)
    path = home / 'hooks.json'
    hooks = runtime.read(path, None)
    if hooks is None:
        return
    for event, groups in list(hooks.get('hooks', {}).items()):
        for group in groups:
            group['hooks'] = [h for h in group.get('hooks', []) if not owned(h)]
        groups[:] = [g for g in groups if g.get('hooks')]
        if not groups:
            del hooks['hooks'][event]
    runtime.write(path, hooks)

def inspect_hooks():
    with runtime.RPC() as rpc:
        result = rpc.call('hooks/list', {'cwds': [str(SOURCE)]})
    return [h for group in result['data'] for h in group['hooks'] if owned(h)]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['install', 'check', 'enable', 'disable', 'uninstall'])
    args = p.parse_args()
    home = pathlib.Path(os.environ.get('CODEX_HOME', pathlib.Path.home() / '.codex')).resolve()
    if os.name != 'nt':
        p.error('This release supports Windows native Codex Desktop only.')
    if args.action == 'install':
        # Fail before changing configuration if the supported official interfaces are missing.
        inspect_hooks()
        root = install(home)
        print('Installed: ' + str(root))
        print('Review and trust the three naming hooks in Codex /hooks, then start a new chat.')
        print('Existing trusted hook definitions may need review after upgrade.')
        print('Existing named/protected states and unrelated hooks were retained.')
    elif args.action == 'check':
        rows = inspect_hooks()
        print(json.dumps([{'event': r['eventName'], 'enabled': r['enabled'],
                           'trust': r['trustStatus']} for r in rows], indent=2))
        if len(rows) != 3 or any(not r['enabled'] or r['trustStatus'] != 'trusted' for r in rows):
            raise SystemExit('Three enabled and trusted naming hooks are required; review /hooks.')
    elif args.action == 'uninstall':
        uninstall(home)
        print('Naming registrations disabled and removed. State, backups and unrelated hooks retained.')
    else:
        path = home / 'thread-naming/settings.json'
        settings = runtime.read(path, None)
        if settings is None:
            raise SystemExit('Install first.')
        settings['enabled'] = args.action == 'enable'
        runtime.write(path, settings)
        print(args.action)

if __name__ == '__main__':
    main()
