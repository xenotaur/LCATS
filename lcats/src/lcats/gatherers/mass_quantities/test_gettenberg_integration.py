"""Self-contained integration checks with mocked LCATS dependencies."""
import importlib.util
import pathlib
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = pathlib.Path(__file__).resolve().parent

def install_stubs():
    for n in ('lcats','lcats.utils','lcats.gatherers','lcats.gatherers.mass_quantities',
              'lcats.analysis','lcats.analysis.corpus','lcats.gettenberg'):
        m=types.ModuleType(n); m.__path__=[]; sys.modules[n]=m
    def mod(name, **props):
        m=types.ModuleType(name); m.__dict__.update(props); sys.modules[name]=m; return m
    mod('lcats.constants', FILE_SUFFIX='.json')
    mod('lcats.utils.names', title_and_author_to_filename=lambda t,a,**kw:'story__author.json')
    mod('lcats.gatherers.normalization', normalize_story_dict=lambda data,**kw:None)
    mod('lcats.gatherers.story_output', existing=lambda p:pathlib.Path(p).is_file(), publish=lambda p,d:True)
    mod('lcats.analysis.corpus.discovery',CANONICAL_STORY_FILENAME='story.json')
    mod('lcats.gatherers.mass_quantities.storymap',
        TITLE_EXCEPTIONS=[], EXCLUDED_SUBJECTS=[], EXCLUDED_TITLE_PART_WORDS=[],
        EXCLUDED_TITLE_WORDS=[], STORIES_TO_EXCLUDE=[], TARGET_DIRECTORY='test', SINGLE_STORIES=[])
    mod('lcats.utils.env',data_root=lambda:'/tmp/data',corpora_root=lambda:'/tmp/corpora')
    mod('lcats.utils.paths',find_pyproject_root=lambda _:pathlib.Path('/tmp/project'))
    class Log:
        def __init__(self,*a,**kw): self.events=[]
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def event(self,*a,**kw): self.events.append((a,kw))
    mod('lcats.utils.run_log',RunLog=Log)
    class TransportError(Exception): pass
    class DecodeError(Exception): pass
    mod('lcats.gettenberg.resources',ResourceTransportError=TransportError,ResourceDecodeError=DecodeError)
    mod('lcats.gatherers.downloaders',DataGatherer=lambda *a,**kw:None)
    mod('tqdm', tqdm=lambda x:x)
    spec=importlib.util.spec_from_file_location('lcats.gatherers.mass_quantities.gutenberg_extractor', ROOT/'gutenberg_extractor.py')
    extractor=importlib.util.module_from_spec(spec);sys.modules[spec.name]=extractor;spec.loader.exec_module(extractor)
    spec=importlib.util.spec_from_file_location('lcats.gatherers.parser',ROOT/'parser_gettenberg.py')
    parser=importlib.util.module_from_spec(spec);sys.modules[spec.name]=parser;spec.loader.exec_module(parser)
    spec=importlib.util.spec_from_file_location('lcats.gatherers.mass_quantities.gatherer',ROOT/'gatherer_gettenberg.py')
    gatherer=importlib.util.module_from_spec(spec);sys.modules[spec.name]=gatherer;spec.loader.exec_module(gatherer)
    return parser,gatherer

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser,cls.gatherer=install_stubs()
    def test_real_extractor_called_via_source(self):
        text=(ROOT/'Pasted markdown(2).md').read_text()
        metadata=SimpleNamespace(titles=['Wolf\'s Head'],authors=['Murfree, Mary Noailles'],
             aliases=['Charles Egbert Craddock'],subjects=['PS','Short stories'],languages=['en'])
        prepared=SimpleNamespace(cleaned=SimpleNamespace(text=text),
             provenance=lambda:{'source_uri':'https://example.com/ebook.txt'})
        source=SimpleNamespace(metadata=Mock(return_value=metadata),read=Mock(return_value=prepared))
        report=self.parser.inspect_story(123,source=source)
        self.assertIsNone(report['rejection'])
        self.assertTrue(report['body'].startswith('It might well be called the country of the outlaw'))
        self.assertNotIn('Produced by David Widger',report['body'])
        self.assertNotIn('1911\n',report['body'][:150])
        source.read.assert_called_once_with(metadata)
    def test_ineligible_does_not_download(self):
        metadata=SimpleNamespace(titles=['Any'],authors=['Smith, John'],aliases=[],subjects=[],languages=['en'])
        source=SimpleNamespace(metadata=Mock(return_value=metadata),read=Mock())
        report=self.parser.inspect_story(2,source=source)
        self.assertIsNotNone(report['rejection'])
        source.read.assert_not_called()
    def test_gatherer_passes_explicit_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=object()
            self.gatherer.downloaders.DataGatherer=lambda *a,**kw:SimpleNamespace(path=tmp)
            original=self.gatherer.parser.gather_story_result
            self.gatherer.parser.gather_story_result=lambda gatherer,story,*,source:SimpleNamespace(
                story=story,path='/tmp/story.json',rejection=None,disposition='written')
            try:
                result=self.gatherer.gather_batch([1],log_dir=pathlib.Path(tmp)/'logs',source=source)
                self.assertEqual(result.ready,{1:'/tmp/story.json'})
                self.assertEqual(result.written,{1:'/tmp/story.json'})
            finally:
                self.gatherer.parser.gather_story_result=original

if __name__=='__main__':unittest.main()
