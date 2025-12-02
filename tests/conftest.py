import sys
import types
from pathlib import Path
from contextlib import contextmanager


# Ensure src/ is importable for integration-style tests
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))


def _install_stub(module_name: str, module_obj: types.ModuleType | types.SimpleNamespace) -> None:
    """Register a lightweight stub if the real dependency is missing."""
    if module_name not in sys.modules:
        sys.modules[module_name] = module_obj


# --- Lightweight stubs for optional heavy deps (keep tests importable) ---
try:  # pragma: no cover - only runs when dep missing
    import dspy  # type: ignore
except Exception:  # pragma: no cover
    class _Field:
        def __init__(self, **kwargs):
            self.desc = kwargs.get("desc")

    class _Signature:
        pass

    class _Module:
        def __call__(self, *args, **kwargs):
            return self.forward(*args, **kwargs)

    class _Predict:
        def __init__(self, signature=None, *_, **__):
            self.signature = signature

        def __call__(self, **kwargs):
            return types.SimpleNamespace(**kwargs)

    class _LM:
        def __init__(self, model=None, **kwargs):
            self.model = model
            for k, v in kwargs.items():
                setattr(self, k, v)

    @contextmanager
    def _context(**kwargs):
        yield

    dspy_stub = types.SimpleNamespace(
        Signature=_Signature,
        Module=_Module,
        Predict=_Predict,
        ChainOfThought=_Predict,
        InputField=_Field,
        OutputField=_Field,
        LM=_LM,
        configure=lambda **kwargs: None,
        context=_context,
        Example=types.SimpleNamespace,
    )
    _install_stub("dspy", dspy_stub)

# Uvicorn is only needed when launching real servers; tests can stub it.
try:  # pragma: no cover
    import uvicorn  # type: ignore
except Exception:  # pragma: no cover
    uvicorn_stub = types.SimpleNamespace(run=lambda *args, **kwargs: None)
    _install_stub("uvicorn", uvicorn_stub)

# FastAPI is required for A2A server helpers; provide a lightweight stub.
try:  # pragma: no cover
    import fastapi  # type: ignore
except Exception:  # pragma: no cover
    class _HTTPException(Exception):
        def __init__(self, status_code: int = 500, detail: str | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _FastAPI:
        def __init__(self, *args, **kwargs):
            self.routes = []

        def get(self, path):
            def decorator(fn):
                return fn
            return decorator

        def post(self, path):
            def decorator(fn):
                return fn
            return decorator

    class _JSONResponse:
        def __init__(self, content=None, status_code: int = 200):
            self.content = content or {}
            self.status_code = status_code

    responses_mod = types.ModuleType("fastapi.responses")
    responses_mod.JSONResponse = _JSONResponse
    fastapi_mod = types.ModuleType("fastapi")
    fastapi_mod.FastAPI = _FastAPI
    fastapi_mod.HTTPException = _HTTPException
    fastapi_mod.responses = responses_mod
    sys.modules["fastapi.responses"] = responses_mod
    _install_stub("fastapi", fastapi_mod)

# rorf is used for the model recommender; stub the controller to avoid heavy deps.
try:  # pragma: no cover
    import rorf  # type: ignore
except Exception:  # pragma: no cover
    class _Controller:
        def __init__(self, router=None, model_a=None, model_b=None, threshold=None):
            self.router = router
            self.model_a = model_a
            self.model_b = model_b
            self.threshold = threshold

        def route(self, _prompt: str):
            return self.model_a or "model_a"

    controller_mod = types.ModuleType("rorf.controller")
    controller_mod.Controller = _Controller
    rorf_mod = types.ModuleType("rorf")
    rorf_mod.controller = controller_mod
    sys.modules["rorf.controller"] = controller_mod
    _install_stub("rorf", rorf_mod)

# google.genai SDK may be absent; provide a lightweight stub for tests.
try:  # pragma: no cover
    from google import genai  # type: ignore
except Exception:  # pragma: no cover
    google_mod = types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")
    types_mod = types.ModuleType("google.genai.types")

    class _DummyHttpOptions:
        def __init__(self, api_version=None):
            self.api_version = api_version

    class _DummyClient:
        def __init__(self, **kwargs):
            self.models = types.SimpleNamespace(generate_content=lambda **kw: None)

    genai_mod.Client = _DummyClient
    types_mod.HttpOptions = _DummyHttpOptions

    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod
