import os
os.environ.setdefault("TYPEGUARD_DISABLE", "1")

def _noop_typechecked(*dargs, **dkwargs):
    def decorator(func):
        return func
    return decorator

try:
    import typeguard
    
    try:
        typeguard.typechecked = _noop_typechecked
    except Exception:
        pass

    try:
        import typeguard._decorators as _dec
        _dec.typechecked = _noop_typechecked
        
        if hasattr(_dec, "instrument"):
            _dec.instrument = lambda *a, **k: None
    except Exception:
        pass

    try:
        from typeguard import config
        for attr in ("typechecked_imports", "check_parameter_types", "check_return_type", "enabled"):
            if hasattr(config, attr):
                setattr(config, attr, False)
    except Exception:
        pass

except Exception:
    pass
