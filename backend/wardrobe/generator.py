"""Bounded, deterministic local outfit ranking. Scores are subjective heuristics."""
import colorsys
from itertools import combinations
from rest_framework.exceptions import ValidationError

DEFAULT_WEIGHTS = {'comfort':35, 'weather':25, 'style':20, 'colors':15, 'preferences':5}
OCCASION_STYLES = {'everyday':['casual'], 'university':['casual','minimalism'], 'work':['business','smart casual'], 'sport':['sport','athleisure'], 'party':['party'], 'formal':['formal','business']}
BEAM_WIDTH = 48


def color_pair(a, b):
    def hsv(value):
        return colorsys.rgb_to_hsv(*(int(value[i:i+2],16)/255 for i in (1,3,5)))
    ah,as_,av = hsv(a); bh,bs,bv = hsv(b)
    if min(as_,bs) < .18 or min(av,bv) < .2:
        return 100.0  # neutral palette
    distance = min(abs(ah-bh), 1-abs(ah-bh))
    return 90.0 if distance < .14 or distance > .42 else 55.0


def mean(values, default=50.0):
    return sum(values)/len(values) if values else default


def evaluate(items, ctx):
    facts = [ctx['facts'][item.pk] for item in items]
    comfort = mean([(item.comfort-1)*25 if item.comfort else 50 for item in items])
    style = mean([100 if row['styles'] & ctx['styles'] else (25 if row['styles'] else 50) for row in facts])
    hues = sorted({color for row in facts for color in row['hex']})
    colors = mean([color_pair(a,b) for a,b in combinations(hues,2)], default=80 if hues else 50)
    known_colors = set().union(*(row['colors'] for row in facts)) if facts else set()
    preference_parts = []
    if ctx['preferred']:
        preference_parts.append(100 if known_colors & ctx['preferred'] else 50)
    if ctx['disliked']:
        preference_parts.append(0 if known_colors & ctx['disliked'] else 100)
    if ctx['fit'] != 'unknown':
        preference_parts.extend(100 if item.fit == ctx['fit'] else (50 if item.fit == 'unknown' else 25) for item in items)
    preferences = mean(preference_parts)
    weather = None
    if ctx['temperature'] is not None:
        temp = ctx['temperature']
        target = 1 if temp >= 25 else 2 if temp >= 18 else 3 if temp >= 10 else 4 if temp >= 0 else 5
        weather = mean([max(0,100-abs(item.warmth-target)*25) if item.warmth else 50 for item in items if item.category.slot not in ('shoes','accessory')])
        if ctx['wet_or_windy']:
            weather = max(0,min(100,weather + (10 if any(item.category.slot == 'outerwear' for item in items) else -15)))
    criteria = {'comfort':round(comfort,2),'weather':round(weather,2) if weather is not None else None,'style':round(style,2),'colors':round(colors,2),'preferences':round(preferences,2)}
    score = round(sum((criteria[key] or 0) * weight for key,weight in ctx['weights'].items())/100,2)
    return {'score':score,'criteria':criteria,'weights':ctx['weights']}


def layer_compatible(items):
    outer = next((item for item in items if item.category.slot == 'outerwear'), None)
    return not (outer and outer.fit == 'slim' and any(item.fit == 'oversized' and item.category.slot in ('top','dress') for item in items))


def generate(items, options, preference=None, profile=None, weather_context=None):
    by_id = {item.pk:item for item in items}
    required = set(options['required_items']); excluded = set(options['excluded_items'])
    if not (required | excluded) <= set(by_id):
        # Same response for foreign, deleted and nonexistent IDs.
        raise ValidationError({'items':'Одна или несколько вещей недоступны в вашем гардеробе.'})
    excluded_categories = {c.pk for c in preference.excluded_categories.all()} if preference else set()
    season = options['season']
    eligible = [item for item in items if item.is_available and item.pk not in excluded and item.category_id not in excluded_categories and (season == 'all' or item.season in ('all',season))]
    if not required <= {item.pk for item in eligible}:
        raise ValidationError({'required_items':'Обязательная вещь недоступна, исключена настройками или не подходит выбранному сезону.'})
    required_slots = {}
    for pk in sorted(required):
        slot = by_id[pk].category.slot
        if slot in required_slots or slot == 'other':
            raise ValidationError({'required_items':'Допускается одна вещь на слот; вещи категории «Другие» сначала нужно уточнить.'})
        required_slots[slot] = by_id[pk]
    if 'dress' in required_slots and ({'top','bottom'} & set(required_slots)):
        raise ValidationError({'required_items':'Платье нельзя объединить с обязательным верхом или низом в этой версии генератора.'})
    if not layer_compatible([by_id[pk] for pk in required]):
        raise ValidationError({'required_items':'Объёмная вещь несовместима с обязательным облегающим внешним слоем.'})
    requested_colors = options.get('preferred_colors')
    preferred = set(requested_colors) if requested_colors is not None else ({c.pk for c in preference.preferred_colors.all()} if preference else set())
    disliked = {c.pk for c in preference.disliked_colors.all()} if preference else set()
    if preferred & disliked:
        raise ValidationError({'preferred_colors':'Предпочтительный цвет исключён вашими настройками. Измените настройки или запрос.'})
    style = options.get('style','').strip()
    styles = {style.casefold()} if style else ({str(s).casefold() for s in preference.styles} if preference and preference.styles else set())
    if not styles and preference and preference.style:
        styles = {preference.style.casefold()}
    if not styles and profile and profile.preferred_style:
        styles = {profile.preferred_style.casefold()}
    if not styles:
        styles = set(OCCASION_STYLES[options['occasion']])
    temperature = options.get('temperature_c')
    if temperature is not None and profile:
        temperature += (profile.heat_sensitivity-3)*2 - (profile.cold_sensitivity-3)*2
    weights = dict(options.get('weights',DEFAULT_WEIGHTS))
    if 'weights' not in options:
        priority = options.get('comfort_priority', preference.comfort_priority if preference else 50)
        comfort_weight = 20 + .3*priority
        weights = {key: value*(100-comfort_weight)/65 for key,value in weights.items() if key != 'comfort'}
        weights['comfort'] = comfort_weight
    if temperature is None:
        weights['weather'] = 0
    total = sum(weights.values())
    if total == 0:
        raise ValidationError({'weights':'Без температуры нельзя использовать только погодный критерий.'})
    weights = {key:round(100*value/total,6) for key,value in weights.items()}
    # Keep the documented normalized weights at exactly 100 after rounding.
    largest = max(weights,key=weights.get)
    weights[largest] = round(weights[largest] + 100-sum(weights.values()),6)
    facts = {item.pk:{'hex':[c.hex_code for c in item.colors.all()], 'colors':{c.pk for c in item.colors.all()}, 'styles':{str(s).casefold() for s in item.styles}} for item in eligible}
    ctx = {'facts':facts,'styles':styles,'preferred':preferred,'disliked':disliked,'fit':preference.preferred_fit if preference else 'unknown','temperature':temperature,'weights':weights,'wet_or_windy':bool(weather_context and (weather_context['precipitation_probability'] >= 60 or weather_context['wind_speed_kmh'] >= 30))}
    pools = {slot:[item for item in eligible if item.category.slot == slot] for slot in ['top','bottom','dress','shoes','outerwear','accessory']}
    notes = []
    if temperature is None:
        notes.append('Температура не указана: погода не оценивалась, её вес перераспределён. Можно указать ручную температуру или включить use_weather.')
    if options.get('notes'):
        notes.append('Свободный текст сохранён, но не интерпретируется алгоритмом. Задайте обязательные ограничения отдельными полями.')
    candidates = {}
    pruned = False
    for base in [('top','bottom','shoes'), ('dress','shoes')]:
        slots = [*base,'outerwear','accessory']
        if not set(required_slots) <= set(slots):
            continue
        beam = [[]]
        for slot in slots:
            if slot in required_slots:
                pool = [required_slots[slot]]
            else:
                pool = list(pools[slot])
                if slot == 'accessory' or (slot == 'outerwear' and (temperature is None or temperature > 10)):
                    pool = [None,*pool]
            expanded = []
            for state in beam:
                for item in pool:
                    option = [*state,item] if item else list(state)
                    if layer_compatible(option):
                        expanded.append((evaluate(option,ctx)['score'],tuple(i.pk for i in option),option))
            expanded.sort(key=lambda row:(-row[0],row[1]))
            pruned |= len(expanded) > BEAM_WIDTH
            beam = [row[2] for row in expanded[:BEAM_WIDTH]]
            if not beam:
                break
        for combination in beam:
            ids = tuple(sorted(item.pk for item in combination))
            if not required <= set(ids):
                continue
            evaluation = evaluate(combination,ctx)
            missing = []
            if any(item.comfort is None for item in combination): missing.append('Не для всех вещей указана оценка комфорта; неизвестные значения оценены нейтрально.')
            if temperature is not None and any(item.warmth is None for item in combination if item.category.slot not in ('shoes','accessory')): missing.append('Теплота части вещей неизвестна; погодная оценка приблизительна.')
            if any(not facts[item.pk]['styles'] for item in combination): missing.append('Стиль части вещей не указан.')
            if any(not facts[item.pk]['colors'] for item in combination): missing.append('Цвета части вещей не указаны.')
            explanation = ['Комплект: '+', '.join(item.name for item in combination)+'.',
                           'Оценка — субъективный рейтинг алгоритма, а не научная оценка стиля.',
                           f"Стиль сравнивался с: {', '.join(sorted(styles))}.",
                           'Категории совместимы: платье или верх с низом, обувь, не более одного внешнего слоя и аксессуара.']
            matched = sum(bool(facts[item.pk]['styles'] & styles) for item in combination)
            known_comfort = sum(item.comfort is not None for item in combination)
            explanation.append(f'Стиль совпал у {matched} из {len(combination)} вещей. Оценка комфорта указана у {known_comfort}; её вес в рейтинге — {weights["comfort"]:.1f}%.')
            used_colors = {color for item in combination for color in facts[item.pk]['colors']}
            if preferred:
                explanation.append(f'Использовано предпочитаемых цветов: {len(used_colors & preferred)}.')
            if disliked & used_colors:
                missing.append('В комплекте есть нежелательный цвет: это мягкое предпочтение. Для строгого запрета исключите вещь.')
            if required:
                explanation.append('Все обязательные вещи включены; исключённые и недоступные вещи не использовались.')
            if temperature is not None:
                if weather_context:
                    explanation.append(f'Учтён прогноз Open-Meteo: ощущается {weather_context["apparent_temperature_c"]} °C, осадки {weather_context["precipitation_probability"]}%, ветер {weather_context["wind_speed_kmh"]} км/ч.')
                    if ctx['wet_or_windy']:
                        missing.append('Возможны осадки или сильный ветер. Внешний слой получает бонус; водостойкость и защита от ветра не проверены.')
                else:
                    explanation.append(f'Учтена указанная вручную температура {options["temperature_c"]} °C с настройками чувствительности. Это приблизительная рекомендация комфорта.')
            evaluation.update(explanation=explanation, warnings=missing, temperature_source='open-meteo' if weather_context else ('manual' if temperature is not None else 'none'), effective_temperature_c=temperature)
            candidates[ids] = {'items':combination,'evaluation':evaluation}
    ranked = sorted(candidates.items(),key=lambda pair:(-pair[1]['evaluation']['score'],pair[0]))
    results = [result for _,result in ranked[:options['count']]]
    if not results:
        notes.append('Недостаточно совместимых вещей: нужны обувь и либо платье, либо верх с низом; при температуре с учётом чувствительности ≤10 °C нужен внешний слой. Проверьте сезон и исключения.')
    elif len(results) < options['count']:
        notes.append(f'Найдено только {len(results)} уникальных комплектов: недостающие варианты не выдумываются.')
    return results, {'count':len(results),'requested_count':options['count'],'messages':notes,'search':{'algorithm':'beam','width':BEAM_WIDTH,'pruned':pruned},'weights':weights}
