# -*- coding: utf-8 -*-
"""plm_facade.py — тонкие обёртки над `plm_queries` (V207: вынесены из engine.py).

Совместимость сохранена: engine реэкспортирует эти имена.
"""


def model_info(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "model_info")(*args, **kwargs)


def mfg_models(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "mfg_models")(*args, **kwargs)


def derived_bases(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "derived_bases")(*args, **kwargs)


def derived_children(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "derived_children")(*args, **kwargs)


def derived_map(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "derived_map")(*args, **kwargs)


def plm_tree_data(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_tree_data")(*args, **kwargs)


def count_tops(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "count_tops")(*args, **kwargs)


def models_info(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "models_info")(*args, **kwargs)


def plm_tops(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_tops")(*args, **kwargs)


def plm_children(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_children")(*args, **kwargs)


def plm_instances(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_instances")(*args, **kwargs)


def plm_parents(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_parents")(*args, **kwargs)


def plm_up_data(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_up_data")(*args, **kwargs)


def plm_down_data(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "plm_down_data")(*args, **kwargs)


def full_tree_lines(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "full_tree_lines")(*args, **kwargs)


def made_of_list(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "made_of_list")(*args, **kwargs)


def do_where(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "do_where")(*args, **kwargs)


def do_tree(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "do_tree")(*args, **kwargs)


def do_rename_plan(*args, **kwargs):
    """ПОСТРОИТЕЛЬ — ВЫНЕСЕН в `plm_queries.py` (V140: сканер не строит).
    Обёртка оставлена для совместимости: старые вызовы работают без правок."""
    import plm_queries as _q
    return getattr(_q, "do_rename_plan")(*args, **kwargs)
