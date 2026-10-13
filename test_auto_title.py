import importlib.util,json,pathlib,tempfile,unittest,subprocess,sys
spec=importlib.util.spec_from_file_location('auto_title',pathlib.Path(__file__).with_name('auto_title.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=m.ROOT;m.ROOT=pathlib.Path(self.temp.name)
  m.write(m.ROOT/'settings.json',{'enabled':True,'installed_at':100,'protection':'first_default_once'})
  self.title='默认标题';self.calls=0;self.fail=False
  outer=self
  class Fake:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def call(self,method,params):
    if method=='thread/read':return {'thread':{'id':'test-session','createdAt':200,'cwd':'C:/projects/draftbox','name':outer.title,'projectId':None}}
    if method=='thread/name/set':
     outer.calls+=1
     if outer.fail:raise RuntimeError('deliberate rename failure')
     outer.title=params['name'];return {}
  self.rpc=Fake
 def tearDown(self):m.ROOT=self.old;self.temp.cleanup()
 def event(self,kind,turn='turn-1',prompt=''):
  return m.handle({'hook_event_name':kind,'session_id':'test-session','turn_id':turn,'prompt':prompt},self.rpc)
 def candidate(self,module='草稿箱',goal='写入稳定性',turn='turn-1'):
  p=m.ROOT/'state/test-session.json';s=m.read(p);s['candidate']={'module':module,'goal':goal,'turn_id':turn};m.write(p,s)
 def named(self):
  self.event('UserPromptSubmit',prompt='修复草稿箱写入失败的问题并补充测试。');self.candidate();self.event('Stop')
 def test_1_first_substantive_completion(self):
  self.named();self.assertEqual(self.title,'草稿箱｜写入稳定性');self.assertEqual(self.calls,1)
 def test_2_followup_test(self):
  self.named();self.event('UserPromptSubmit','turn-2','再跑一下测试');self.event('Stop','turn-2');self.assertEqual(self.calls,1)
 def test_3_commit(self):
  self.named();self.event('UserPromptSubmit','turn-3','提交git commit');self.event('Stop','turn-3');self.assertEqual(self.calls,1)
 def test_4_greeting_then_task(self):
  self.event('UserPromptSubmit',prompt='你好');self.event('Stop');self.assertEqual(self.calls,0)
  self.event('UserPromptSubmit','turn-2','修复草稿箱写入失败');self.candidate(turn='turn-2');self.event('Stop','turn-2');self.assertEqual(self.calls,1)
 def test_5_manual_after_naming(self):
  self.named();self.title='我的手动标题';self.event('SessionStart');self.event('Stop');self.assertEqual(self.title,'我的手动标题');self.assertEqual(self.calls,1)
 def test_6_resume_persisted_state(self):
  self.named();s=m.read(m.ROOT/'state/test-session.json');self.assertTrue(s['auto_named']);self.event('SessionStart');self.assertEqual(self.calls,1)
 def test_7_failure_is_nonblocking_no_retry(self):
  self.event('UserPromptSubmit');self.candidate();self.fail=True
  self.assertEqual(self.event('Stop'),{});self.event('Stop');self.assertEqual(self.calls,1);self.assertEqual(m.read(m.ROOT/'state/test-session.json')['status'],'failed')
 def test_module_cannot_repeat_project(self):
  with self.assertRaises(ValueError):m.valid_title('Alpha','证据评估',{'project':'Alpha示例项目','project_aliases':['Alpha']})
 def test_wrong_turn_and_repeated_stop(self):
  self.event('UserPromptSubmit');self.candidate(turn='wrong');self.event('Stop');self.assertEqual(self.calls,0)
  self.candidate();self.event('Stop');self.event('Stop');self.assertEqual(self.calls,1)
 def test_failure_exit_zero(self):
  r=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('auto_title.py')),'hook'],input='bad json',text=True,capture_output=True)
  self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout),{})
 def test_resume_changes_generation_and_clears_candidate(self):
  self.event('UserPromptSubmit');self.candidate()
  p=m.ROOT/'state/test-session.json';before=m.read(p)['generation']
  m.handle({'hook_event_name':'SessionStart','source':'resume','session_id':'test-session','cwd':'C:/projects/draftbox'},self.rpc)
  state=m.read(p);self.assertNotEqual(before,state['generation']);self.assertNotIn('candidate',state)
 def test_compact_keeps_generation_without_stale_turn_command(self):
  self.event('UserPromptSubmit');self.candidate();p=m.ROOT/'state/test-session.json';before=m.read(p)
  out=m.handle({'hook_event_name':'SessionStart','source':'compact','session_id':'test-session'},self.rpc)
  self.assertEqual(before,m.read(p));self.assertNotIn('--turn',out['hookSpecificOutput']['additionalContext'])
 def test_generation_candidate_allows_resumed_turn_id(self):
  self.event('UserPromptSubmit');p=m.ROOT/'state/test-session.json';state=m.read(p)
  state['candidate']={'module':'草稿箱','goal':'写入稳定性','generation':state['generation'],'turn_id':'turn-1'};m.write(p,state)
  self.event('Stop','resumed-turn');self.assertEqual(self.calls,1)
 def test_new_prompt_rejects_old_generation(self):
  self.event('UserPromptSubmit');p=m.ROOT/'state/test-session.json';old=m.read(p)['generation']
  self.event('UserPromptSubmit','turn-2');state=m.read(p);state['candidate']={'module':'草稿箱','goal':'写入稳定性','generation':old};m.write(p,state)
  self.event('Stop','turn-2');self.assertEqual(self.calls,0)
 def test_metadata_not_ready_is_nonblocking(self):
  class NotReady:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def call(self,*args):raise RuntimeError('thread not loaded: test-session')
  out=m.handle({'session_id':'test-session','hook_event_name':'SessionStart'},NotReady)
  self.assertEqual(out,{});self.assertFalse((m.ROOT/'state/test-session.json').exists())
 def test_context_fits_limit(self):
  out=self.event('UserPromptSubmit');text=out['hookSpecificOutput']['additionalContext']
  self.assertLessEqual(len(text),1000);self.assertIn('不必等长期Goal',text)

if __name__=='__main__':unittest.main(verbosity=2)
