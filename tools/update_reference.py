"""Refresh the public parameter snapshot without importing Blender or the add-on."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path, help='Path to zhb_physx/__init__.py')
args = parser.parse_args()
raw = args.source.read_bytes()
tree = ast.parse(raw)
constants = {node.targets[0].id: node.value for node in tree.body if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}


def literal(node, fallback=''):
    if isinstance(node, ast.Name) and node.id in constants:
        node = constants[node.id]
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return fallback


info = literal(constants['bl_info'])
version = '.'.join(map(str, info['version']))
if version != '0.57.0':
    raise SystemExit('Review the guide before changing its source version: ' + version)
groups = {
    'ZHB_PHYSX_PG_body': 'Тела, эмиттеры, триггеры и инструменты',
    'ZHB_PHYSX_PG_joint': 'Соединения',
    'ZHB_PHYSX_PG_fracture': 'Разрушение',
    'ZHB_PHYSX_PG_settings': 'Симуляция и результат',
    'ZhbphysxArt': 'Качество',
}
output = {'version': version, 'source_sha256': hashlib.sha256(raw).hexdigest(), 'operators': [], 'groups': []}
for cls in tree.body:
    if not isinstance(cls, ast.ClassDef):
        continue
    values = {node.targets[0].id: literal(node.value) for node in cls.body if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
    if str(values.get('bl_idname', '')).startswith('zhb_physx.'):
        output['operators'].append({'id': values['bl_idname'], 'name': values.get('bl_label', ''), 'description': values.get('bl_description') or ast.get_docstring(cls) or ''})
    if cls.name not in groups:
        continue
    fields = []
    for prop in cls.body:
        if not isinstance(prop, ast.AnnAssign) or not isinstance(prop.target, ast.Name) or not isinstance(prop.annotation, ast.Call):
            continue
        kwargs = {kw.arg: kw.value for kw in prop.annotation.keywords}
        name = literal(kwargs.get('name')) if 'name' in kwargs else ''
        desc = literal(kwargs.get('description')) if 'description' in kwargs else ''
        options = literal(kwargs['options'], set()) if 'options' in kwargs else set()
        if not name or 'HIDDEN' in options or desc.startswith('Внутреннее'):
            continue
        default = literal(kwargs['default'], 'Вычисляется при создании') if 'default' in kwargs else 'Не задано явно'
        if isinstance(default, bool):
            default = 'Включено' if default else 'Выключено'
        items = literal(kwargs['items'], []) if 'items' in kwargs else []
        fields.append({'id': prop.target.id, 'name': name, 'description': desc, 'default': default, 'options': [f'{x[1]}: {x[2]}' for x in items if isinstance(x, tuple) and len(x) == 3]})
    output['groups'].append({'name': groups[cls.name], 'properties': fields})
path = Path(__file__).resolve().parents[1] / 'data' / 'physx-reference.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{version}: {len(output["operators"])} operators, {sum(len(x["properties"]) for x in output["groups"])} named parameters')
