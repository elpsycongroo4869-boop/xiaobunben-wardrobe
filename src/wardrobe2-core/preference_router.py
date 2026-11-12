"""Typed optional owner preferences: routed to specialty only, never global story choice."""
from typing import Any

ROLES={'scene','wardrobe','performance','performance.expression','lighting','camera'}
STRENGTHS={'soft','this_time'}

def route_preferences(persona:dict[str,Any]) -> dict[str,list[str]]:
    per_role={key:[] for key in sorted(ROLES)}
    for i, item in enumerate(persona.get('preferences', [])):
        if not isinstance(item,dict):
            raise ValueError(f'preferences[{i}] must be an object')
        role=item.get('role')
        strength=item.get('strength','soft')
        note=item.get('note')
        if role not in ROLES:
            raise ValueError(f'preferences[{i}] has unknown specialty')
        if strength not in STRENGTHS:
            raise ValueError(f'preferences[{i}] has unknown strength')
        if not isinstance(note,str) or not note.strip():
            raise ValueError(f'preferences[{i}] missing note')
        mark='本次明确愿望' if strength=='this_time' else '长期可参考偏好（不是必选）'
        per_role[role].append(f'{mark}: {note.strip()}')
    return per_role
