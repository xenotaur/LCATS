"""Regression checks for the high-precision front-matter rule."""
import json
import unittest
from pathlib import Path
from study_frontmatter import predict
from evaluate import reference_line
from frontmatter_precision import refine_promotional_blurb_boundary

DATA={r['gutenberg_id']:r for r in json.loads((Path(__file__).parent/'training.json').read_text())}

class TeaserBoundaryTests(unittest.TestCase):
    def test_recovers_known_training_teasers(self):
        for id in (32143,31841,33969,31736,32040,32104):
            with self.subTest(gutenberg_id=id):
                r=DATA[id]
                before,_=predict(r,apply_precision=False)
                after,_=predict(r,apply_precision=True)
                self.assertLess(before,after)
                self.assertEqual(after,reference_line(r))

    def test_genuine_italic_prologues_not_deleted(self):
        for id in (59224,64963):
            with self.subTest(gutenberg_id=id):
                r=DATA[id]
                before,_=predict(r,apply_precision=False)
                after,_=predict(r,apply_precision=True)
                self.assertEqual(before,after)

    def test_blank_lines_alone_do_not_trigger(self):
        lines=['TITLE','', '', 'An opening paragraph that should not be removed.', '',
               '* * * * *', '', 'The text is continuing from the earlier paragraph.']
        self.assertEqual(refine_promotional_blurb_boundary(lines,3,len(lines)),3)

    def test_no_change_for_long_prologue(self):
        lines=['BY SOME WRITER', '', '_We watched the ship land at dawn._', '',
               '_The crowds were silent as it touched the ground._', '',
               '_Nobody moved until the door opened._', '', '* * * * *', '',
               'This is the continuation of the fictional prologue with prose.']
        self.assertEqual(refine_promotional_blurb_boundary(lines,2,len(lines)),2)

    def test_never_passes_narrative_on_training_set(self):
        for r in DATA.values():
            ref=reference_line(r)
            if ref is None:continue
            before,_=predict(r,apply_precision=False)
            after,_=predict(r,apply_precision=True)
            with self.subTest(id=r['gutenberg_id']):
                self.assertLessEqual(after,max(before,ref))

if __name__=='__main__':unittest.main()
