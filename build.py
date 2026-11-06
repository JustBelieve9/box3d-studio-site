"""Build the static, dependency-free site from its content and pinned evidence."""
import ast
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def esc(value):
    return html.escape(str(value), quote=True)


def section(key, title, body, eyebrow=""):
    return f'<section id="{key}" data-title="{esc(title)}"><p class="eyebrow">{eyebrow}</p><h2>{title}</h2>{body}</section>'


def cards(items):
    return '<div class="cards">' + ''.join(f'<article><h3>{a}</h3><p>{b}</p></article>' for a, b in items) + '</div>'


def table(head, rows):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th scope="col">{x}</th>' for x in head) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{x}</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def bars(title, labels, values, unit):
    top = max(values)
    return '<figure class="chart"><figcaption>' + title + '</figcaption>' + ''.join(
        f'<div class="bar-row"><span>{label}</span><div class="track"><i style="width:{value/top*100:.3f}%"></i></div><b>{value:g} {unit}</b></div>'
        for label, value in zip(labels, values)) + '</figure>'


def benchmarks(en=False):
    historical = bars('Bake time' if en else 'Время бейка', ['Bullet', 'Keyframes · 1 thread' if en else 'Keyframes · 1 поток', 'Disk Cache', 'Instanced', 'Instanced · 10 substeps'], [8.08, .69, .60, .40, .30], 's' if en else 'с')
    historical += bars('Scrubbing · lower is better' if en else 'Скраб · меньше — лучше', ['Bullet', 'Keyframes', 'Disk Cache', 'Instanced', 'Instanced · originals excluded' if en else 'Instanced · оригиналы исключены'], [7.92, 12.26, 16.48, 7.66, .47], 'ms' if en else 'мс')
    title = 'Historical Bullet comparison' if en else 'Прежнее сравнение с Bullet'
    warning = ('Archive: the original site’s 0.38.1-era measurements, 3,000 cubes × 120 frames on Apple Silicon. Preserved for context; not rerun for 0.57.0. The old page did not specify a precise CPU model or complete run metadata.' if en else 'Архив: замеры прежнего сайта времён 0.38.1, 3000 кубов × 120 кадров на Apple Silicon. Сохранены для контекста; для 0.57.0 это сравнение не повторялось. Точная модель процессора и полный протокол запусков на старой странице не указаны.')
    result = f'<div class="callout"><strong>{title}.</strong> {warning}</div>' + historical
    result += '<p>' + ('The best ratios in that scene were about 20× for baking and 17× for scrubbing with originals excluded. These are scenario-specific results, not a universal speed claim. Keyframes and Disk Cache were slower than Bullet for scrubbing.' if en else 'В этой сцене получалось около 20× на бейке Instanced и 17× на скрабе с исключёнными оригиналами. Это результат конкретного сценария, а не обещание для любой сцены. Keyframes и Disk Cache скрабились медленнее Bullet.') + '</p>'
    result += '<h3>' + ('What changed with 0.57.0' if en else 'Что изменилось в 0.57.0') + '</h3><p>' + ('New comparison: old vs new bundled engine on Ryzen 9 5900X, Windows x86_64. 1,152 bodies × 150 frames, 12 workers, 8 substeps, median of 3 runs. Native stepping only, excluding Blender extraction, output and playback. Old and new builds also use different compilers, so the result does not isolate AVX2 or any single upstream change.' if en else 'Новое сравнение: прежняя и новая поставляемые библиотеки на Ryzen 9 5900X, Windows x86_64. 1152 тела × 150 кадров, 12 потоков, 8 подшагов, медиана 3 прогонов. Измерен только нативный шаг, без подготовки Blender, записи и воспроизведения. Компиляторы сборок также различаются: эти числа не выделяют вклад AVX2 или отдельной оптимизации.') + '</p>'
    options = [('awake', 'Sleep disabled' if en else 'Сон выключен'), ('sleep', 'Default sleep' if en else 'Штатный сон')]
    result += '<div class="segmented" role="group" aria-label="' + ('Sleep configuration' if en else 'Режим сна в замере') + '">' + ''.join(f'<button type="button" data-benchmark="{key}" aria-pressed="{"true" if key == "awake" else "false"}">{text}</button>' for key, text in options) + '</div>'
    for key, label in options:
        old = json.loads((ROOT / 'data' / f'benchmark-old{"-awake" if key == "awake" else ""}.json').read_text())
        new = json.loads((ROOT / 'data' / f'benchmark-new{"-awake" if key == "awake" else ""}.json').read_text())
        rows = []
        for a, b in zip(old['cases'], new['cases']):
            assert a['shape'] == b['shape']
            delta = (b['median'] / a['median'] - 1) * 100
            word = ('slower' if en else 'медленнее') if delta > 0 else ('faster' if en else 'быстрее')
            rows.append([a['shape'], f"{a['median']*1000:.2f}", f"{b['median']*1000:.2f}", f'{abs(delta):.1f}% {word}'])
        result += f'<div data-benchmark-panel="{key}" {"hidden" if key != "awake" else ""}>' + table(['Shape' if en else 'Форма', 'Old · ms' if en else 'Было · мс', 'New · ms' if en else 'Стало · мс', 'Change' if en else 'Изменение'], rows) + '</div>'
    result += '<p class="callout">' + ('Default sleep is a material trade-off: BOX became 2.26× slower, while SPHERE became faster and ended fully asleep. The awake set changed. Do not extrapolate these timings to an arbitrary production scene.' if en else 'Со штатным сном есть регрессия: BOX стал медленнее в 2,26 раза. SPHERE ускорился и полностью уснул к концу; набор активных тел изменился. Переносить этот результат на произвольный продакшен нельзя.') + '</p>'
    result += '<p class="muted">' + ('Reproducible evidence: ' if en else 'Исходные результаты: ') + ' · '.join(f'<a href="data/{name}.json">{name}</a>' for name in ['benchmark-old-awake', 'benchmark-new-awake', 'benchmark-old', 'benchmark-new']) + '</p>'
    return result


def physx(en=False):
    guide = 'Russian user guide' if en else 'Полная памятка'
    intro = ('Rigid bodies.<br>A workflow you control.' if en else 'Физика, которую<br>можно поставить в кадр.')
    desc = ('Box3D rigid bodies for Blender: simulate, inspect and bake to editable keys, caches or shared-geometry instances. Emitters, tools and breakable connections live in the same workflow.' if en else 'Твёрдые тела Box3D в Blender: рассчитать, проверить и записать движение в ключи, кэш или инстансы. Эмиттеры, инструменты и разрушаемые связи — в том же рабочем процессе.')
    hero = f'<section id="top" data-title="{"Overview" if en else "Обзор"}"><p class="eyebrow">zhb PhysX · 0.57.0 · Blender 5.2 LTS</p><div class="hero-grid"><div><h1>{intro}</h1><p class="lede">{desc}</p><div class="actions"><a class="button primary" href="#/physx/guide">{guide}<span aria-hidden="true"> ↗</span></a><a class="button" href="#/{"en/" if en else ""}physx?section=numbers">{"Benchmarks" if en else "Сравнение и цифры"}</a></div></div><div class="physics-diagram" role="img" aria-label="{"Collision shapes over a floor" if en else "Формы столкновения над плоскостью"}"><div class="diagram-label">BOX3D / 0.2.0-dev</div><div class="cube c1"></div><div class="cube c2"></div><div class="sphere"></div><div class="floor"></div><span class="diagram-caption">{"Bodies → contacts → motion" if en else "Тела → контакты → движение"}</span></div></div><div class="stats"><div><strong>4</strong><span>{"output modes" if en else "режима вывода"}</span></div><div><strong>6</strong><span>{"collision shapes" if en else "форм коллизии"}</span></div><div><strong>4</strong><span>{"joint types" if en else "типа соединений"}</span></div><div><strong>3</strong><span>{"native platforms" if en else "платформы библиотек"}</span></div></div></section>'
    workflow = cards([('01 / ' + ('Mark' if en else 'Пометить'), 'Active / Passive / Emitter / Trigger / Tool. ' + ('Your own Box3D settings; no Bullet world required.' if en else 'Собственные настройки Box3D, без обязательного мира Bullet.')), ('02 / ' + ('Set up' if en else 'Настроить'), ('Body properties in Physics; quality, range and output in N → zhb PhysX → Симуляция.' if en else 'Свойства тела — в Physics. Качество, диапазон и представление — в N → zhb PhysX → Симуляция.')), ('03 / ' + ('Simulate' if en else 'Рассчитать'), ('Explicit bake, Live Preview or Simulate On Playback. Inspect collisions before the full run.' if en else 'Явный бейк, Live Preview или Simulate On Playback. Сначала проверка коллизий на коротком участке.')), ('04 / ' + ('Verify' if en else 'Проверить'), ('Check readiness and range, inspect motion, save the project and external caches.' if en else 'Проверить актуальность и диапазон, просмотреть движение, сохранить проект и внешний кэш.'))])
    features_ru = [('Тела и коллизии', 'Box, Sphere, Capsule, Convex Hull, Mesh и Compound. Движущаяся вогнутая форма — набор выпуклых частей; Mesh — только статический Passive.'), ('Эмиттеры', 'Поток с поверхности или заполнение замкнутого объёма. Прототип частицы, скорость, наследование движения, Seed и время жизни.'), ('Rigid / Points', 'Полное вращение либо заблокированная ориентация. Points работает на Box3D; отдельный XPBD-слой в эмиссию не подключён.'), ('Четыре соединения', 'Revolute, Spherical, Distance и Weld. Пределы, пружины, моторы и разрыв — в зависимости от типа.'), ('Разрушение', 'Фрагменты Вороного, склейка соседей, прочность, воздействие Shatter и анимация прочности по времени.'), ('Триггеры', 'Enable / Disable Physics, Delete, Shatter, Enable Emission. Фильтр коллекций и каналов; сенсоры без CCD.'), ('Инструменты', 'Attract, Push, Grab & Carry и Impulse. Перенос к цели с дугой, раскладкой, лимитом и действием на прибытии.'), ('Конвейеры и кинематика', 'Скорость поверхности Passive-объекта, ключи и предварительная выборка трансформов ригов через depsgraph.'), ('Материал и оси', 'Собственная масса, трение, упругость, затухание, сопротивление качению и блокировки движения по осям.'), ('Силовые поля', 'Поддерживаются Force и Wind Blender. Влияние на Active и частицы регулируется Field Weight.'), ('Контакты и диагностика', 'Облако ударов с нормалями и скоростью, показ форм, стоимость тел и профиль последнего расчёта.'), ('Вращение ресурсов', 'После физического падения — постановочное игровое вращение монетки или ресурса.'), ('Проверка результата', 'READY / STALE / PARTIAL / MISSING / FAILED, учёт входов и версии движка, отдельная проверка диапазона.'), ('Конвертация', 'Совместимые роли и формы Bullet ↔ Box3D, кэш → ключи, инстансы → объекты. Масса и трение движков не синхронизируются.'), ('Прогрев и остановка', 'Warm-up для улёгшейся стартовой сцены. Stop When Settled сокращает расчёт допустимых сцен, сохраняя длину результата.')]
    features_en = [('Bodies and shapes', 'Box, Sphere, Capsule, Convex Hull, Mesh and Compound. Moving concave objects use convex pieces; Mesh is static-only.'), ('Emitters', 'Surface streams or closed-volume fills, particle objects, inherited velocity, seeds and lifetime.'), ('Rigid / Points', 'Full orientation or locked rotation. Points uses Box3D bodies; the standalone XPBD layer is not wired into emitters.'), ('Four joint types', 'Revolute, Spherical, Distance and Weld, with applicable limits, springs, motors and break thresholds.'), ('Fracture', 'Voronoi pieces, neighbour glue, strength, Shatter zones and animated strength.'), ('Triggers', 'Enable / Disable Physics, Delete, Shatter and Enable Emission. Collection and channel filtering; sensors have no CCD.'), ('Tools', 'Attract, Push, Grab & Carry and Impulse. Carry supports arcs, scatter, capacity and arrival actions.'), ('Conveyors and kinematics', 'Passive surface speed, keyed motion and pre-sampled rig transforms through the dependency graph.'), ('Materials and axes', 'Independent mass, friction, restitution, damping, rolling resistance and axis locks.'), ('Force fields', 'Blender Force and Wind supported; per-body Field Weight controls influence.'), ('Contacts and diagnostics', 'Hit point clouds with normals and speed, collision previews and body profiling.'), ('Game spin', 'Stage a collectible’s rotation after a physical drop.'), ('Result verification', 'READY / STALE / PARTIAL / MISSING / FAILED, source and engine identity, range coverage.'), ('Conversion', 'Compatible Bullet ↔ Box3D roles and shapes, cache to keys and instances to objects. No shared mass or friction.'), ('Warm-up and settling', 'Pre-roll a settled starting pile; early-stop eligible scenes while retaining the complete output range.')]
    outputs = table(['Mode' if en else 'Режим', 'Use it for' if en else 'Когда выбирать', 'Keep in mind' if en else 'Что учитывать'], [('Keyframes', 'Editable animation' if en else 'Редактирование анимации', 'F-curves grow with body/frame count' if en else 'Объём f-кривых растёт с телами и кадрами'), ('Blend Cache', 'Samples inside .blend' if en else 'Сэмплы внутри .blend', 'Requires enabled playback add-on' if en else 'Нужен включённый проигрыватель аддона'), ('Disk Cache', 'Smaller .blend' if en else 'Компактный .blend', 'Include external files in delivery' if en else 'Внешние файлы передаются вместе с проектом'), ('Instanced', 'Thousands of repeated meshes' if en else 'Тысячи повторяющихся мешей', 'Shared geometry and excluded originals matter' if en else 'Важны общая геометрия и исключение оригиналов')])
    update = table(['Area' if en else 'Область', '0.57.0'], [('Box3D', '3fc20f5 → 3362633 · ' + ('24 upstream commits' if en else '24 коммита upstream')), ('Native library' if en else 'Библиотека', '0.2.0 development · ' + ('not an upstream stable release' if en else 'не стабильный релиз upstream')), ('Compatibility' if en else 'Совместимость', 'WorldDef, BodyDef, MeshDef, BoxHullRaw, Profile'), ('Validation' if en else 'Проверки', ('Native commit, size, alignment and field offsets before unsafe C calls' if en else 'Нативный commit, размер, выравнивание и смещения полей до опасных вызовов C')), ('Cache' if en else 'Кэш', ('Engine commit included in source fingerprint; old results remain playable' if en else 'Commit движка включён в отпечаток входов; старый результат может проигрываться')), ('UI', ('Existing controls retained; new engine options are not exposed yet' if en else 'Прежние функции сохранены; новые параметры движка пока не выведены'))])
    update += '<div class="callout"><strong>' + ('Verification scope.' if en else 'Границы проверки.') + '</strong> ' + ('46/46 Blender scripts and the exact z=0.2496 reference in all four output modes passed on Windows / Blender 5.2.2 LTS. Native and upstream tests passed on Windows x86_64, Linux x86_64 and macOS ARM64. A full Linux/macOS Blender run was not performed.' if en else '46/46 Blender-скриптов и точный эталон z=0.2496 в четырёх режимах пройдены на Windows / Blender 5.2.2 LTS. Нативные и upstream-тесты пройдены на Windows x86_64, Linux x86_64 и macOS ARM64. Полного Blender-прогона на Linux/macOS не было.') + '</div>'
    limits = ('<ul><li>Box3D is in development. A pinned commit and native ABI guards are required.</li><li>Native recording/replay, safetyFactor, sleep threshold and restitution solver options are not exposed in the add-on.</li><li>HeightField, ray/shape casts, per-triangle physical materials and seven additional joint types are not integrated.</li><li>Sensors have no continuous collision detection. Mesh collisions are static-only.</li><li>Rigid and Points emitter modes cannot share one output layout; mixed selections fall back to Rigid with a warning.</li><li>Native support is Windows x86_64, Linux x86_64 and macOS ARM64. Other platforms have no bundled binary.</li></ul>' if en else '<ul><li>Box3D развивается; используются фиксированный commit и проверки ABI нативной библиотеки.</li><li>Родная запись/replay, safetyFactor, порог сна и настройки решения отскоков пока не имеют управления в аддоне.</li><li>HeightField, Ray/Shape Cast, физические материалы на треугольник и ещё семь типов соединений не подключены.</li><li>У сенсоров нет непрерывного обнаружения; Mesh-коллизия работает только на статике.</li><li>Points и Rigid эмиттеров не смешиваются: при смешанном выборе расчёт перейдёт в Rigid с предупреждением.</li><li>Готовые библиотеки: Windows x86_64, Linux x86_64, macOS ARM64. Для других платформ сборки не поставляются.</li></ul>')
    install = '<p>' + ('Released for users with repository access. The source repository and its downloads remain private. This public website does not grant download access.' if en else 'Версия выпущена для пользователей с доступом к репозиторию. Исходники и скачивание остаются приватными; публичный сайт не открывает доступ к архивам.') + '</p><div class="actions"><a class="button" href="https://github.com/JustBelieve9/zhb_physx_solver/releases/tag/zhb_physx-v0.57.0">' + ('Release · access required' if en else 'Релиз · нужен доступ') + '</a><a class="button primary" href="#/physx/guide?section=installation">' + ('Installation guide · RU' if en else 'Как установить') + '</a></div>'
    return hero + section('pipeline', 'From setup to verified motion' if en else 'От разметки до проверенного движения', workflow, 'WORKFLOW' if en else 'ПОРЯДОК РАБОТЫ') + section('features', 'What the add-on does today' if en else 'Что умеет аддон сейчас', cards(features_en if en else features_ru), 'FEATURES' if en else 'ВОЗМОЖНОСТИ') + section('output', 'Four ways to store motion' if en else 'Четыре способа записать движение', outputs, 'OUTPUT' if en else 'РЕЗУЛЬТАТ') + section('update', 'The engine update' if en else 'Обновление движка', update, '0.57.0 / 02.11.2026') + section('numbers', 'Numbers, with their conditions' if en else 'Цифры вместе с условиями', benchmarks(en), 'BENCHMARKS' if en else 'ЗАМЕРЫ') + section('limits', 'Engine support ≠ add-on support' if en else 'Возможности движка и границы аддона', limits, 'SCOPE' if en else 'ОГРАНИЧЕНИЯ') + section('install', 'Version and installation' if en else 'Версия и установка', install, 'ACCESS' if en else 'ДОСТУП')


def reference():
    data = json.loads((ROOT / 'data' / 'physx-reference.json').read_text(encoding='utf-8'))
    parts = [f'<p class="muted">Источник: zhb PhysX {data["version"]}; {len(data["operators"])} команд. Снимок исходников зафиксирован при обновлении сайта.</p>']
    parts.append('<details><summary>Все команды аддона</summary>' + table(['Команда', 'Идентификатор', 'Назначение'], [[esc(x['name']), '<code>' + esc(x['id']) + '</code>', esc(x['description'])] for x in data['operators']]) + '</details>')
    for group in data['groups']:
        rows = []
        for p in group['properties']:
            options = '<br>'.join(esc(x) for x in p.get('options', []))
            desc = esc(p['description']) + ('<p class="caption">' + options + '</p>' if options else '')
            rows.append([esc(p['name']) + '<br><code>' + esc(p['id']) + '</code>', desc, esc(p['default'])])
        parts.append('<details><summary>' + esc(group['name']) + f' · {len(rows)}</summary>' + table(['Параметр', 'Значение и варианты', 'По умолчанию'], rows) + '</details>')
    return ''.join(parts)


def build():
    guide = (ROOT / 'content' / 'guide.html').read_text(encoding='utf-8').replace('<!-- GENERATED_REFERENCE -->', reference())
    pages = [('physx', 'ru', physx()), ('physx', 'en', physx(True)), ('physx/guide', 'ru', guide)]
    rendered = []
    for route, lang, content in pages:
        prefix = route.replace('/', '-') + '-' + lang
        content = re.sub(r'<section id="([^"]+)"', lambda match: f'<section id="{prefix}-{match[1]}" data-key="{match[1]}"', content)
        rendered.append(f'<main class="page physx" id="page-{prefix}" data-route="{route}" data-lang="{lang}" {"" if route == "physx" and lang == "ru" else "hidden"}>{content}<footer><span>zhb PhysX · 06.11.2026</span><a href="https://t.me/zhustbieblender">@zhustbie · {"Author’s channel" if lang == "en" else "Канал автора"}</a></footer></main>')
    body = ''.join(rendered)
    template = (ROOT / 'content' / 'shell.html').read_text(encoding='utf-8')
    template = template.replace('<link rel="stylesheet" href="assets/site.css">', '<style>' + (ROOT / 'assets' / 'site.css').read_text(encoding='utf-8') + '</style>')
    template = template.replace('<script src="assets/site.js" defer></script>', '')
    template = template.replace('</body>', '<script>' + (ROOT / 'assets' / 'site.js').read_text(encoding='utf-8') + '</script></body>')
    (ROOT / 'index.html').write_text(template.replace('<!-- PAGES -->', body), encoding='utf-8', newline='\n')
    print(f'Built {len(pages)} pages, {len(data_sections(guide))} guide sections')


def data_sections(content):
    import re
    return re.findall(r'<section\b', content)


if __name__ == '__main__':
    build()
