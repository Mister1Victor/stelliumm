# astro12 — пакет-обёртка «Школа 12 Планет» (MIT)

Изолированный Python-пакет поверх AGPL-библиотеки **stellium**. Основной
репозиторий stellium **не модифицируется вообще** — проверка: `git diff` в
корне репозитория показывает изменения только внутри `/astro12/`.

## Как изолируется AGPL

| Слой | Зависимости | Лицензия-риск |
|---|---|---|
| `constants.py`, `model.py`, `prompt.py` | stdlib only | нет |
| `ephemeris.py` | pyswisseph (MIT-обёртка C-библиотеки; сама Swiss Ephemeris — двойная лицензия AGPL/коммерческая, данные .se1 бесплатны для SE-расчётов планет) | низкий; при коммерческой продаже закрытого продукта — купить лицензию Swiss Ephemeris (~€500/год или flat) |
| `stellium_adapter.py` | stellium — **optional extra**, lazy import, только публичный API (`ChartBuilder.from_details(...).with_tnos().calculate()`) | обёрта дистрибутируется под MIT и без stellium полностью функциональна (прямой расчёт через pyswisseph с Moshier-fallback без .se1 файлов) |

Важно честно: если финальный SaaS собирает stellium + astro12 в один бэкенд,
AGPL stellium всё равно требует открытия кода бэкенда **или** коммерческой
лицензии. Обёртка это ограничение не отменяет, но позволяет:
1. вынести всю авторскую систему (12 управителей, промпты, модель данных) в
   чистый MIT-код, который можно публиковать/лицензировать как угодно;
2. работать вообще без stellium (прямые эфемериды), т.е. иметь AGPL-free
   конфигурацию продакшена;
3. в мобильном приложении Flutter бэкенд может использовать только astro12
   direct-mode → никаких AGPL-обязательств на клиенте.

## API

```python
import datetime as dt
import astro12

when = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)

# 1) Прямой расчёт 12 тел (только pyswisseph, без stellium)
tc = astro12.calculate(when)
print(tc.get("eris").sign, tc.get("ceres").sign)
d = tc.to_dict()                      # JSON-ready для REST/Flutter

# 2) Полный natal + 12-карта через stellium (дома, ретро-статусы)
schart, tc = astro12.build_chart(when, (55.75, 37.62), name="Тест")

# 3) Адаптер к уже готовому stellium-чарту (duck-typing, импорт stellium не нужен)
tc = astro12.from_stellium_chart(existing_chart)

# 4) Markdown-промпт для LLM-движка Astro12AI
prompt = astro12.chart_to_prompt(tc)
one_aspect = astro12.aspect_prompt(tc, "venus", "saturn", "Trine")
```

Деградация без падения: отсутствующее тело попадает в `tc.missing`
(например, нет файла `s136199.se1` → сработает Moshier-fallback, а если и он
неудачен — список `missing`; промпт пометит его строкой «НЕ рассчитаны»).

## Установка / тесты

```bash
pip install -e ./package            # из каталога astro12/
pytest ./package/tests -q           # 14 тестов, офлайн-safe
```

## Дальше (Фаза 2)
- FastAPI-эндпоинты `/v1/chart12`, `/v1/prompt`, `/v1/interpret` (прокси к
  Astro12AI) поверх `TwelveChart.to_dict()`;
- Flutter-клиент читает тот же JSON;
- монетизация: freemium-карта (direct-mode, бесплатно) → платные LLM-интерпретации.
