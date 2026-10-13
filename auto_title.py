"""User-level Codex lifecycle naming. Never touches transcripts or databases."""
import argparse, contextlib, datetime, json, os, pathlib, queue, re, subprocess, sys, threading, time, uuid

ROOT = pathlib.Path(__file__).resolve().parent

def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)

def log(event, sid='', error=''):
    try:
        with (ROOT/'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,'session_id':sid,'error':str(error)[:350]},ensure_ascii=False)+'\n')
    except OSError: pass

@contextlib.contextmanager
def lock(sid):
    import msvcrt
    path=ROOT/'state'/f'{sid}.lock'; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        f.seek(0); f.write(b'0'); f.flush(); f.seek(0)
        msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        try: yield
        finally: f.seek(0); msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

class RPC:
    def __enter__(self):
        candidates=list((pathlib.Path(os.environ['LOCALAPPDATA'])/'OpenAI/Codex/bin').glob('*/codex.exe'))
        if not candidates: raise RuntimeError('Codex Desktop executable unavailable')
        core=max(candidates,key=lambda p:p.stat().st_mtime)
        self.p=subprocess.Popen([str(core),'app-server','--listen','stdio://'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=0x08000000)
        self.q=queue.Queue();self.n=0
        def receive():
            for line in self.p.stdout:
                try:self.q.put(json.loads(line))
                except ValueError:pass
        threading.Thread(target=receive,daemon=True).start()
        try:
            self.call('initialize',{'clientInfo':{'name':'codex_once_title','version':'1.0'},'capabilities':{'experimentalApi':True}})
            self.p.stdin.write('{"method":"initialized"}\n');self.p.stdin.flush()
            return self
        except Exception:
            self.__exit__(None,None,None);raise
    def call(self, method, params):
        self.n+=1;n=self.n
        self.p.stdin.write(json.dumps({'id':n,'method':method,'params':params})+'\n');self.p.stdin.flush()
        deadline=time.monotonic()+8
        while True:
            r=self.q.get(timeout=max(.01,deadline-time.monotonic()))
            if r.get('id')==n:
                if 'error' in r:raise RuntimeError(r['error'].get('message','RPC failed'))
                return r['result']
    def __exit__(self,*args):
        self.p.terminate();self.p.wait(timeout=3)

def valid_title(module, goal, state):
    for value in (module,goal):
        if not isinstance(value,str) or not value.strip() or len(value)>22 or re.search(r'[\r\n｜|]|\d{4}[-/]\d',value):raise ValueError('Invalid short title')
    module=module.strip();goal=goal.strip()
    aliases=[state.get('project',''),pathlib.Path(state.get('cwd','')).name,*state.get('project_aliases',[])]
    if module.casefold() in [a.casefold() for a in aliases if a]:raise ValueError('Module repeats Project; select an internal module')
    return module+'｜'+goal

def handle(event, rpc_factory=RPC):
    config=read(ROOT/'settings.json',{})
    if not config.get('enabled',False):return {}
    sid=event.get('session_id','')
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,80}',sid):return {}
    path=ROOT/'state'/f'{sid}.json'
    with lock(sid):
        state=read(path)
        kind=event.get('hook_event_name')
        if state and state.get('status') in ('named','failed','skipped','protected'):
            if state.get('status')=='named' and event.get('hook_event_name')=='UserPromptSubmit':
                return {'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':'本会话已完成一次命名，不再自动改名。若用户彻底切换到与原长期目标无关的任务，建议新开会话。'}}
            return {}
        if not state:
            with rpc_factory() as rpc:
                try:t=rpc.call('thread/read',{'threadId':sid,'includeTurns':False})['thread']
                except RuntimeError as error:
                    if 'thread not loaded' in str(error):
                        log('metadata_not_ready',sid,kind);return {}
                    raise
                if t.get('parentThreadId') or t.get('createdAt',0)<config['installed_at']:
                    write(path,{'session_id':sid,'status':'skipped','reason':'preexisting_or_subagent'});return {}
                project=pathlib.Path(t['cwd']).name
                if t.get('projectId'):
                    project=rpc.call('project/read',{'projectId':t['projectId']})['project']['name']
                aliases=[pathlib.Path(t['cwd']).name.split('-')[0],*re.findall(r'^[A-Za-z]+\d*',project)]
                state={'session_id':sid,'status':'pending','cwd':t['cwd'],'project':project,'project_aliases':aliases,'initial_title':t.get('name'),'auto_named':False,'manual_title_detected':False}
                write(path,state)
        if kind in ('SessionStart','UserPromptSubmit'):
            if kind=='UserPromptSubmit' or (kind=='SessionStart' and event.get('source') in ('startup','resume','clear')):
                state['turn_id']=event.get('turn_id');state['generation']=uuid.uuid4().hex;state.pop('candidate',None);write(path,state)
            command=f'py -3 "{ROOT / "auto_title.py"}" propose --session {sid} --module "模块" --goal "持续目标"'
            instruction=(f'一次性会话命名（辅助功能，不得影响主任务）：Project={state["project"]}，工作目录={state["cwd"]}。'
              '首次有明确目标的一轮实质工作完成后、最终答复前命名；不必等长期Goal/整个研究完成。产出分析、代码、方案或报告即算完成本轮，长期目标WAITING/尚缺外部数据不妨碍命名。'
              'Project已经承担项目层，不得把项目名或目录名默认作为模块；继续找数据集、癌种、功能、研究子方向、工作流或论文部分。'
              '使用中文短标题“模块｜持续目标”，不加日期或瞬时步骤。只有问候、测试、帮我看看、点号、空泛检查、尚未产出实质工作时不命名。'
              '若本轮是首个实质任务且已完成实质工作，调用以下命令并替换module/goal；否则不调用：'+command+'. '
              '不要自行调用set_thread_title；Stop负责一次性官方改名。用户明确要求保持/手动命名时运行同脚本 protect --session '+sid+'，不要提交自动标题。'
              '今后彻底切换无关任务时建议新开会话，不更改旧标题。此辅助命令失败只记录，不延误交付。')
            return {'hookSpecificOutput':{'hookEventName':kind,'additionalContext':instruction}}
        if kind=='Stop':
            candidate=state.get('candidate')
            if not candidate:
                log('awaiting_candidate',sid,event.get('turn_id',''));return {}
            if candidate.get('generation'):
                if candidate['generation']!=state.get('generation'):return {}
            elif candidate.get('turn_id')!=event.get('turn_id'):return {}
            title=valid_title(candidate['module'],candidate['goal'],state)
            # Reserve permanently before mutation; crash/repeat must never overwrite later titles.
            state.update(status='failed',attempted_title=title,attempted_at=time.time());write(path,state)
            try:
                with rpc_factory() as rpc:
                    current=rpc.call('thread/read',{'threadId':sid,'includeTurns':False})['thread']
                    if config.get('protection')=='strict' and current.get('name'):
                        state.update(status='protected',manual_title_detected=True,reason='existing_title');write(path,state);return {}
                    state['old_title']=current.get('name');write(path,state)
                    rpc.call('thread/name/set',{'threadId':sid,'name':title})
                    actual=rpc.call('thread/read',{'threadId':sid,'includeTurns':False})['thread'].get('name')
                    if actual!=title:raise RuntimeError('Rename readback mismatch')
                    state.update(status='named',auto_named=True,title=title);write(path,state);log('named',sid)
            except Exception as error:log('rename_failed',sid,error)
        return {}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['hook','propose','protect','disable','enable'])
    parser.add_argument('--session');parser.add_argument('--turn');parser.add_argument('--module');parser.add_argument('--goal');args=parser.parse_args()
    if args.action in ('disable','enable'):
        cfg=read(ROOT/'settings.json');cfg['enabled']=args.action=='enable';write(ROOT/'settings.json',cfg);return
    if args.action=='hook':
        event=json.load(sys.stdin);print(json.dumps(handle(event),ensure_ascii=False));return
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,80}',args.session or ''):raise ValueError('Invalid session id')
    with lock(args.session):
        path=ROOT/'state'/f'{args.session}.json';state=read(path)
        if not state or state.get('status')!='pending':return
        if args.action=='protect':state.update(status='protected',manual_title_detected=True)
        else:
            if args.turn is not None and args.turn!=state.get('turn_id'):raise ValueError('Turn does not match')
            title=valid_title(args.module,args.goal,state)
            state['candidate']={'module':args.module.strip(),'goal':args.goal.strip(),'turn_id':args.turn or state.get('turn_id'),'title':title,'generation':state.get('generation') if args.turn is None else None}
        write(path,state)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
    try:main()
    except Exception as error:
        log('auxiliary_failed',sid=locals().get('sid',''),error=error)
        if 'hook' in sys.argv:print('{}')
    # Always exit zero; naming is optional and must not block Codex.
