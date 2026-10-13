import pathlib, tempfile, unittest
import install

class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def test_install_retains_foreign_hooks(self):
        install.runtime.write(self.home/'hooks.json', {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo unrelated'}]}]}})
        install.install(self.home)
        hooks = install.runtime.read(self.home/'hooks.json')['hooks']
        self.assertEqual(hooks['Stop'][0]['hooks'][0]['command'], 'echo unrelated')
        self.assertEqual(sum(install.owned(h) for gs in hooks.values() for g in gs for h in g['hooks']), 3)
    def test_reinstall_retains_cutoff_states_and_disable(self):
        root = install.install(self.home)
        cfg = install.runtime.read(root/'settings.json'); cfg['enabled'] = False; cfg['installed_at'] = 123
        install.runtime.write(root/'settings.json',cfg)
        install.runtime.write(root/'state/example-session.json', {'status':'named','title':'草稿箱｜写入稳定性'})
        install.install(self.home)
        self.assertEqual(install.runtime.read(root/'settings.json'),cfg)
        self.assertEqual(install.runtime.read(root/'state/example-session.json')['status'],'named')
        hooks = install.runtime.read(self.home/'hooks.json')['hooks']
        self.assertEqual(sum(install.owned(h) for gs in hooks.values() for g in gs for h in g['hooks']),3)
    def test_uninstall_is_scoped_and_retains_records(self):
        root=install.install(self.home)
        hooks=install.runtime.read(self.home/'hooks.json');hooks['hooks']['Stop'].insert(0,{'hooks':[{'command':'echo unrelated'}]});install.runtime.write(self.home/'hooks.json',hooks)
        install.uninstall(self.home)
        remaining=install.runtime.read(self.home/'hooks.json')['hooks']
        self.assertEqual(remaining,{'Stop':[{'hooks':[{'command':'echo unrelated'}]}]})
        self.assertFalse(install.runtime.read(root/'settings.json')['enabled'])
        self.assertTrue((root/'auto_title.py').exists())

if __name__=='__main__': unittest.main(verbosity=2)
