# pyi_rth_no_typeguard.py
# Desactiva typeguard para evitar inspect.getsource en binarios congelados.
import os
os.environ.setdefault("TYPEGUARD_DISABLE", "1")

def _noop_typechecked(*dargs, **dkwargs):
    def decorator(func):
        return func
    return decorator

try:
    import typeguard  # fuerza import temprano
    # Parchea el alias re-exportado: from typeguard import typechecked
    try:
        typeguard.typechecked = _noop_typechecked
    except Exception:
        pass

    # Parchea el origen interno
    try:
        import typeguard._decorators as _dec
        _dec.typechecked = _noop_typechecked
        # Si existe instrument(), lo anulamos también
        if hasattr(_dec, "instrument"):
            _dec.instrument = lambda *a, **k: None
    except Exception:
        pass

    # Algunas versiones exponen flags en config
    try:
        from typeguard import config
        for attr in ("typechecked_imports", "check_parameter_types", "check_return_type", "enabled"):
            if hasattr(config, attr):
                setattr(config, attr, False)
    except Exception:
        pass

except Exception:
    # si no existe typeguard, no pasa nada
    pass
