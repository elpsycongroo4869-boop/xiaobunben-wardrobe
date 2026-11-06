"""B3.2 role-first costume direction: scene/climate -> role -> occupational garment -> fabrics -> attractive adaptation."""
VERSION = '3.5.2-B3.2-role-first-costume-test'
MATERIALS = ('linen','cotton','silk','velvet','satin','brocade','leather','suede','wool',
             'fur','denim','nylon','polyester','canvas','steel','metal','chainmail',
             'chiffon','organza','lace','latex','neoprene','rubber','tweed','knit')

def validate_costume_plan(plan, wardrobe, texture):
    if not isinstance(plan, dict):
        raise ValueError('B3.2 requires a costume_plan chosen after scene, climate, role and profession')
    for name in ('climate_context','occupational_basis','structural_silhouette','feminine_adaptation'):
        value=plan.get(name)
        if not isinstance(value,str) or not 18<=len(value.strip())<=260 or value!=value.strip():
            raise ValueError('B3.2 costume_plan requires specific '+name)
    mats=plan.get('primary_materials')
    if not isinstance(mats,list) or not 1<=len(mats)<=5 or any(not isinstance(m,str) or not 3<=len(m.strip())<=36 for m in mats):
        raise ValueError('B3.2 primary_materials must list 1..5 real garment materials')
    low=wardrobe.lower()
    for material in mats:
        if material.lower().strip() not in low:
            raise ValueError('B3.2 outfit must actually name chosen garment material: '+material)
    # Camera texture must not invent a new textile: a known failure in past looks.
    text=texture.lower()
    for material in MATERIALS:
        if material in text and material not in low:
            raise ValueError('B3.2 camera texture introduces a material absent from outfit: '+material)
    return {k:plan[k] for k in ('climate_context','occupational_basis','structural_silhouette','primary_materials','feminine_adaptation')}

COSTUME_DIRECTION = ("Keep the role's actual costume structure and named materials; refine its fit, cutouts, or sheer layers only when apt.")
