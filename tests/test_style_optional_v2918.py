import sys,tempfile,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from fast_start import stage_draw,stage_finish
from visual_identity import FACE_EN,BODY_EN
assert len(FACE_EN)<560 and len(BODY_EN)<140
assert 'fine-boned' in FACE_EN and 'slim arms' in BODY_EN and 'fine legs' in BODY_EN
assert 'ponytail' not in FACE_EN.lower() and 'black tights' not in FACE_EN.lower()
with tempfile.TemporaryDirectory() as td:
    base=Path(td); hints=[]
    for i in range(64):
        d=stage_draw(base/f'draw-{i}',root/'references/history.jsonl',seed=3000+i)
        hints.append(d['hosiery_style_hint'])
    assert 'consider_sheer_black' in hints and 'leave_to_role_design' in hints
    assert 16<=hints.count('consider_sheer_black')<=48
    for j,w in enumerate(('A fitted blue jacket, pleated navy skort, fine sheer black tights and leather boots.',
                         'A fitted blue jacket, pleated navy skort and leather boots with harmonious accents.')):
        folder=base/f'integrated-{j}'
        d=stage_draw(folder,root/'references/history.jsonl',seed=201+j)
        design={
            'subject':'A clearly adult East Asian woman repairing an art gallery lighting circuit as a city electrician.',
            'setting':'A historic gallery service passage with stone walls, electrical access panels and a large scaffold under warm interior light.',
            'action':'She secures a detached cable lug on a service board with an insulated screwdriver while testing the connection at the metal panel.',
            'cue1':'An electrician identification patch and a specialized insulated screwdriver mark her as the site electrician.',
            'cue2':'A grounded copper busbar assembly and an opened breaker board show her particular electrical repair assignment.',
            'wardrobe':w,
            'composition':'Her face and active hands lead the service panel scene.'
        }
        path=base/f'scene-{j}.json';path.write_text(json.dumps(design),encoding='utf-8')
        out=stage_finish(folder,path)
        msg=(folder/'photo-creation-message.txt').read_text(encoding='utf-8')
        assert ('fine sheer black tights' in msg)==(j==0)
        assert 'slim arms and long, fine legs' in msg
        assert len(msg)<=3650 and out['button_label']=='打开小笨笨衣橱'
print('PASS: both accessory options, sealed 21-field prompts, petite adult face, slender body')
