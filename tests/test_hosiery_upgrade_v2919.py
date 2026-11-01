from pathlib import Path
root=Path(__file__).resolve().parents[1]
a=(root/'references/SKILL-legacy-v2.9.19.md').read_text('utf-8')
b=(root/'references/visual-direction-v2.9.19.md').read_text('utf-8')
for term in ('delicate floral-patterned black tights', 'elegant lace-trimmed sheer black stockings', 'fine lace-top black thigh-high stockings with tasteful garter straps'):
    assert term in a and term in b
assert 'consider_sheer_black' in a and 'leave_to_role_design' in a
assert '不改' in a and '不改变镜头' in b or '不能为了让吊带可见而拉远镜头' in b
print('PASS: refined stockings optional, garter alternatives and camera safeguards')

import sys,json,tempfile
sys.path.insert(0,str(root/'scripts'))
from fast_start import stage_draw, stage_finish
examples=[
    'Fine ivory jacket, navy skirt, delicate floral-patterned black tights and ankle boots.',
    'Elegant fitted blouse, dark skirt, elegant lace-trimmed sheer black stockings and lace-up boots.',
    'Cropped embroidered jacket, pleated skirt, fine lace-top black thigh-high stockings with tasteful garter straps and boots.',
]
with tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp)
    for i,w in enumerate(examples):
        pending=base/f'pending-{i}'
        # A fixed empty history and non-original career draws keep this clothing test reproducible.
        stage_draw(pending,base/'empty-history.jsonl',lane='career',seed=(0,1,3)[i])
        design={
            'subject':'An adult East Asian heroine maintaining the ancient tower clock in a fictional coastal city.',
            'setting':'Inside an ancient coastal clocktower, behind its monumental bronze dial, with clockwork gears and hand tools.',
            'action':'She aligns a slipping brass escapement with a precision spanner while watching the pendulum swing in the shaft.',
            'cue1':'A toothed bronze escapement, pendulum and open brass clockwork clearly show the specialized repair.',
            'cue2':'Her clockkeeper badge and the tower mechanism service panel identify her as the responsible technician.',
            'wardrobe':w,
            'composition':'Her face and hands guide the eye to the clockwork.',
        }
        assert len(w)<=155
        inp=base/f'design-{i}.json';inp.write_text(json.dumps(design),encoding='utf-8')
        result=stage_finish(pending,inp)
        msg=(pending/'photo-creation-message.txt').read_text('utf-8')
        assert w in msg and result['button_label']=='打开小笨笨衣橱'
        assert len(msg)<=3650
print('PASS: all 3 refined hosiery types survive generation and handoff')
