# Driver Layer – Programming Targets

## Purpose
Provide a uniform way to describe supported stacks (backend, frontend, mobile, embedded, GPU) so each role in the pipeline knows which templates, build tools, and test commands to apply. The feature will be implemented on a new branch (e.g., `feature/driver-layer`) to keep changes isolated until the full workflow is wired.

---

## Estado de Implementación

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 1** | Infraestructura (registry, dataclasses, schema) | ⏳ Pendiente |
| **Fase 2** | Drivers backend/frontend básicos | ⏳ Pendiente |
| **Fase 3** | Integración con orchestrator y roles | ⏳ Pendiente |
| **Fase 4** | Drivers embedded (ESP32, Zephyr) | ⏳ Pendiente |
| **Fase 5** | Drivers GPU (CUDA, ROCm) | ⏳ Pendiente |
| **Fase 6** | Tests y documentación | ⏳ Pendiente |

---

## Driver Taxonomy

```
drivers/
  backend/   (FastAPI, Express, Spring…)
  frontend/  (Next.js, Nuxt, Angular…)
  mobile/    (React Native, Flutter, Kotlin MPP…)
  embedded/  (Zephyr C, ESP32-C3 RISC-V, MicroPython…)
  gpu/       (CUDA Jetson, ROCm Edge…)
```

Each driver is a YAML file with the following structure:

```yaml
id: fastapi
category: backend
language: python
framework: fastapi
templates:
  - path: app/main.py
    source: drivers/backend/fastapi/templates/main.py
build:
  command: uvicorn app.main:app --reload
test:
  command: pytest project/backend-fastapi/tests
lint:
  command: ruff check project/backend-fastapi
artifact_paths:
  - project/backend-fastapi/app
quality_gates:
  min_coverage: 0.85
metadata:
  db_support: postgres
  auth: jwt
```

Mandatory sections:
- `templates`: scaffolding files to copy into `project/`.
- `build`, `test`, `lint`: commands the Dev/QA roles will run.
- `artifact_paths`: directories to snapshot after each loop.
- `metadata`: role-specific hints (framework quirks, default DB, etc.).

## Categories & Examples

### Backend
- `fastapi`, `express`, `spring_boot`, `fiber_go`.
- Traits: language, framework, DB adapters, test runner, packaging.

### Frontend
- `next_js`, `nuxt`, `angular_cli`.
- Traits: routing mode, package manager (`npm`, `pnpm`, `yarn`), test runner (Jest/Vitest), build command.

### Mobile
- `react_native`, `flutter`, `kotlin_mpp`.
- Traits: device targets (Android/iOS), emulator commands, navigation boilerplate, integration tests (Detox/Flutter driver).

### Embedded
- `zephyr_c`: West build, board parameter, `twister` tests, flashing via `openocd`.
- `esp32c3_riscv`: ESP-IDF toolchain (`idf.py set-target esp32c3`), FreeRTOS templates, monitor command.
- `micropython_esp32`: `mpremote` deploy, host-side pytest for logic.

### GPU
- `cuda_jetson`: NVCC builds, TensorRT deployment, profiling hooks (`nvidia-smi`, `nsys`).
- `rocm_edge`: hipcc builds, `rocminfo` diagnostics, unit tests for kernels.

## Driver Dataclass

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

@dataclass
class TemplateEntry:
    path: str           # Destination path in project/
    source: str         # Source template path in drivers/

@dataclass
class CommandSpec:
    command: str
    working_dir: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 300

@dataclass
class QualityGates:
    min_coverage: float = 0.0
    max_complexity: Optional[int] = None
    required_tests: bool = True

@dataclass
class Driver:
    id: str
    category: str       # backend, frontend, mobile, embedded, gpu
    language: str
    framework: str
    templates: List[TemplateEntry]
    build: CommandSpec
    test: CommandSpec
    lint: Optional[CommandSpec] = None
    artifact_paths: List[str] = field(default_factory=list)
    quality_gates: QualityGates = field(default_factory=QualityGates)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Embedded/GPU specific
    board: Optional[str] = None           # e.g., "esp32c3", "nrf52840"
    flash_command: Optional[str] = None
    monitor_command: Optional[str] = None
    gpu_arch: Optional[str] = None        # e.g., "sm_87" for Jetson
    profiler_command: Optional[str] = None
```

## Driver Registry

Create `drivers/registry.py` to load all YAMLs:
```python
from pathlib import Path
from typing import Optional
import yaml

DRIVER_ROOT = Path("drivers")
_driver_cache: Dict[str, Driver] = {}

class DriverNotFoundError(Exception):
    """Raised when a driver YAML does not exist."""
    pass

class DriverValidationError(Exception):
    """Raised when a driver YAML has invalid structure."""
    pass

def load_driver(category: str, driver_id: str) -> Driver:
    """Load a driver by category and ID with caching."""
    cache_key = f"{category}/{driver_id}"
    if cache_key in _driver_cache:
        return _driver_cache[cache_key]

    path = DRIVER_ROOT / category / f"{driver_id}.yaml"
    if not path.exists():
        raise DriverNotFoundError(f"Driver not found: {path}")

    try:
        data = yaml.safe_load(path.read_text())
        driver = _parse_driver(data)
        _driver_cache[cache_key] = driver
        return driver
    except Exception as e:
        raise DriverValidationError(f"Invalid driver {path}: {e}")

def _parse_driver(data: dict) -> Driver:
    """Parse raw YAML dict into Driver dataclass with validation."""
    # Parse nested structures
    templates = [TemplateEntry(**t) for t in data.get("templates", [])]
    build = CommandSpec(**data["build"]) if "build" in data else None
    test = CommandSpec(**data["test"]) if "test" in data else None
    lint = CommandSpec(**data["lint"]) if "lint" in data else None
    quality_gates = QualityGates(**data.get("quality_gates", {}))

    return Driver(
        id=data["id"],
        category=data["category"],
        language=data["language"],
        framework=data["framework"],
        templates=templates,
        build=build,
        test=test,
        lint=lint,
        artifact_paths=data.get("artifact_paths", []),
        quality_gates=quality_gates,
        metadata=data.get("metadata", {}),
        board=data.get("board"),
        flash_command=data.get("flash_command"),
        monitor_command=data.get("monitor_command"),
        gpu_arch=data.get("gpu_arch"),
        profiler_command=data.get("profiler_command"),
    )

def list_drivers(category: Optional[str] = None) -> List[str]:
    """List available driver IDs, optionally filtered by category."""
    drivers = []
    search_path = DRIVER_ROOT / category if category else DRIVER_ROOT
    for yaml_file in search_path.rglob("*.yaml"):
        if yaml_file.name != "schema.yaml":
            drivers.append(yaml_file.stem)
    return sorted(drivers)
```

Expose role-specific helpers:
```python
def get_build_command(driver: Driver) -> str:
    return driver.build.command if driver.build else ""

def get_test_command(driver: Driver) -> str:
    return driver.test.command if driver.test else ""

def get_templates(driver: Driver) -> List[TemplateEntry]:
    return driver.templates

def get_project_path(driver: Driver) -> str:
    """Return standardized project path based on category and framework."""
    return f"project/{driver.category}-{driver.framework}"
```

## Pipeline Integration

1. **Configuration**
   - Extend `config.yaml` with `project.targets`:
     ```yaml
     project:
       targets:
         backend: fastapi
         frontend: next_js
         mobile: none
         embedded: esp32c3_riscv
         gpu: cuda_jetson
     ```
   - Orchestrator stores these targets in the DB/project metadata.

2. **Orchestrator**
   - For each role invocation, attach the resolved driver objects to the role context.
   - During artifact bundling, include driver metadata (build commands, board info, GPU arch) in the iteration snapshot.

3. **BA / Product Owner**
   - Minimal change: just ensure `requirements.yaml` / `product_vision.yaml` mention the selected targets so downstream roles have context (e.g., “Architecture must support FastAPI backend + Next.js frontend + ESP32-C3 device + CUDA Jetson inference”).

4. **Architect**
   - Read driver metadata to tailor stories and architecture (e.g., specify RTOS tasks for Zephyr, GPU memory budgets for CUDA driver).
   - When `embedded` or `gpu` drivers are present, include device constraints and deployment steps in the architecture YAML.

5. **Developer**
   - Before code generation, apply the driver templates to scaffold folders (`project/backend-fastapi/app`, `project/web-express/src`, `project/embedded-esp32c3/` etc.).
   - Run the driver’s `build/test/lint` commands automatically after generation.
   - For embedded/gpu drivers, trigger flashing or simulation steps as defined.

6. **QA**
   - Use the driver’s `test` section to know which toolchain to run (Jest for frontend, `west twister` for Zephyr, CUDA functional tests, etc.).
   - Record driver IDs inside QA reports for traceability.

## Branch & Implementation Outline

- Create branch `feature/driver-layer`.
- Deliverables:
  1. `drivers/` directory with initial YAMLs and templates.
  2. `drivers/registry.py` + dataclasses.
  3. Updates to `config.yaml` schema (new `project.targets`).
  4. Orchestrator changes to load/pass drivers.
  5. Dev/QA role adjustments to honor build/test commands.
  6. Documentation updates (README + per-driver docs).

- Rollout plan:
  1. Start with backend/frontend drivers to validate the registry.
  2. Add embedded (ESP32-C3, Zephyr) and gpu drivers once the pattern is stable.
  3. Backfill tests that ensure templates are applied and commands run.
  4. Merge branch after verifying the full loop picks up driver-specific behavior.

---

## Path Naming Conventions

Standardized naming for project directories:

```
project/
├── backend-fastapi/       # {category}-{framework}
├── backend-express/
├── frontend-nextjs/
├── frontend-nuxt/
├── mobile-flutter/
├── mobile-reactnative/
├── embedded-esp32c3/      # {category}-{board}
├── embedded-zephyr-nrf52/
├── gpu-cuda-jetson/       # {category}-{toolchain}-{platform}
└── gpu-rocm-edge/
```

Rules:
- **Backend/Frontend/Mobile**: `{category}-{framework}` (lowercase, no underscores)
- **Embedded**: `{category}-{board}` or `{category}-{rtos}-{board}`
- **GPU**: `{category}-{toolchain}-{platform}`

The `get_project_path(driver)` helper enforces this convention.

---

## Testing Strategy

### Unit Tests (`tests/test_driver_registry.py`)

```python
import pytest
from drivers.registry import (
    load_driver, list_drivers,
    DriverNotFoundError, DriverValidationError
)

class TestDriverRegistry:
    def test_load_valid_driver(self, tmp_drivers):
        """Test loading a valid driver YAML."""
        driver = load_driver("backend", "fastapi")
        assert driver.id == "fastapi"
        assert driver.category == "backend"
        assert driver.build.command == "uvicorn app.main:app --reload"

    def test_load_nonexistent_driver_raises(self):
        """Test that missing driver raises DriverNotFoundError."""
        with pytest.raises(DriverNotFoundError):
            load_driver("backend", "nonexistent")

    def test_load_invalid_yaml_raises(self, tmp_drivers_invalid):
        """Test that malformed YAML raises DriverValidationError."""
        with pytest.raises(DriverValidationError):
            load_driver("backend", "malformed")

    def test_driver_caching(self, tmp_drivers):
        """Test that drivers are cached after first load."""
        d1 = load_driver("backend", "fastapi")
        d2 = load_driver("backend", "fastapi")
        assert d1 is d2  # Same object reference

    def test_list_drivers_by_category(self, tmp_drivers):
        """Test listing drivers filtered by category."""
        backend_drivers = list_drivers("backend")
        assert "fastapi" in backend_drivers
        assert "express" in backend_drivers

    def test_embedded_driver_has_flash_command(self, tmp_drivers):
        """Test embedded driver has required fields."""
        driver = load_driver("embedded", "esp32c3")
        assert driver.board == "esp32c3"
        assert driver.flash_command is not None

    def test_gpu_driver_has_arch(self, tmp_drivers):
        """Test GPU driver has architecture field."""
        driver = load_driver("gpu", "cuda_jetson")
        assert driver.gpu_arch == "sm_87"
```

### Integration Tests (`tests/test_driver_integration.py`)

```python
class TestDriverIntegration:
    def test_dev_role_applies_templates(self, mock_driver, tmp_project):
        """Test that Dev role scaffolds from driver templates."""
        # Given a driver with templates
        driver = load_driver("backend", "fastapi")

        # When Dev role runs
        apply_templates(driver, tmp_project)

        # Then project has expected structure
        assert (tmp_project / "app" / "main.py").exists()

    def test_qa_role_uses_driver_test_command(self, mock_driver):
        """Test that QA role executes driver's test command."""
        driver = load_driver("backend", "fastapi")
        result = run_qa_with_driver(driver)
        assert "pytest" in result.command_executed

    def test_orchestrator_stores_driver_metadata(self, db_ctx):
        """Test that driver info is stored in iteration snapshot."""
        driver = load_driver("backend", "fastapi")
        db_ctx.start_iteration(driver_metadata=driver.metadata)

        iteration = db_ctx.get_current_iteration()
        assert "fastapi" in iteration.config_snapshot
```

### Fixtures (`tests/conftest.py`)

```python
@pytest.fixture
def tmp_drivers(tmp_path):
    """Create temporary driver YAMLs for testing."""
    drivers_dir = tmp_path / "drivers" / "backend"
    drivers_dir.mkdir(parents=True)

    fastapi_yaml = drivers_dir / "fastapi.yaml"
    fastapi_yaml.write_text('''
id: fastapi
category: backend
language: python
framework: fastapi
templates:
  - path: app/main.py
    source: drivers/backend/fastapi/templates/main.py
build:
  command: uvicorn app.main:app --reload
test:
  command: pytest project/backend-fastapi/tests
''')
    return tmp_path
```

---

## Error Handling

### Error Types

| Error | Cause | Recovery |
|-------|-------|----------|
| `DriverNotFoundError` | YAML file doesn't exist | Fall back to default driver or fail with clear message |
| `DriverValidationError` | YAML structure invalid | Log validation errors, suggest fixes |
| `TemplateNotFoundError` | Template source missing | Skip template with warning, continue |
| `CommandExecutionError` | Build/test command fails | Retry with fallback, log full output |

### Graceful Degradation

```python
def get_driver_safe(category: str, driver_id: str) -> Optional[Driver]:
    """Load driver with graceful fallback."""
    try:
        return load_driver(category, driver_id)
    except DriverNotFoundError:
        logger.warning(f"Driver {category}/{driver_id} not found, using defaults")
        return get_default_driver(category)
    except DriverValidationError as e:
        logger.error(f"Invalid driver config: {e}")
        return None

def apply_templates_safe(driver: Driver, project_path: Path) -> List[str]:
    """Apply templates with error collection."""
    errors = []
    for template in driver.templates:
        try:
            copy_template(template, project_path)
        except FileNotFoundError:
            errors.append(f"Template not found: {template.source}")
            logger.warning(f"Skipping missing template: {template.source}")
    return errors
```

---

## Complete Driver Examples

### Embedded: ESP32-C3 RISC-V

```yaml
id: esp32c3_riscv
category: embedded
language: c
framework: esp-idf
board: esp32c3

templates:
  - path: main/main.c
    source: drivers/embedded/esp32c3/templates/main.c
  - path: CMakeLists.txt
    source: drivers/embedded/esp32c3/templates/CMakeLists.txt
  - path: sdkconfig.defaults
    source: drivers/embedded/esp32c3/templates/sdkconfig.defaults

build:
  command: idf.py build
  working_dir: project/embedded-esp32c3
  env:
    IDF_TARGET: esp32c3
  timeout_seconds: 600

test:
  command: idf.py pytest --target esp32c3
  working_dir: project/embedded-esp32c3

flash_command: idf.py -p /dev/ttyUSB0 flash
monitor_command: idf.py -p /dev/ttyUSB0 monitor

artifact_paths:
  - project/embedded-esp32c3/build/*.bin
  - project/embedded-esp32c3/build/*.elf

quality_gates:
  min_coverage: 0.70
  required_tests: true

metadata:
  chip: ESP32-C3
  architecture: RISC-V
  flash_size: 4MB
  ram_size: 400KB
  rtos: FreeRTOS
  peripherals: [WiFi, BLE, GPIO, I2C, SPI, UART]
```

### Embedded: Zephyr RTOS (nRF52840)

```yaml
id: zephyr_nrf52
category: embedded
language: c
framework: zephyr
board: nrf52840dk_nrf52840

templates:
  - path: src/main.c
    source: drivers/embedded/zephyr/templates/main.c
  - path: prj.conf
    source: drivers/embedded/zephyr/templates/prj.conf
  - path: CMakeLists.txt
    source: drivers/embedded/zephyr/templates/CMakeLists.txt

build:
  command: west build -b nrf52840dk_nrf52840
  working_dir: project/embedded-zephyr-nrf52
  timeout_seconds: 300

test:
  command: west twister -T tests/ -p nrf52840dk_nrf52840
  working_dir: project/embedded-zephyr-nrf52

flash_command: west flash
monitor_command: west attach

artifact_paths:
  - project/embedded-zephyr-nrf52/build/zephyr/zephyr.hex
  - project/embedded-zephyr-nrf52/build/zephyr/zephyr.elf

quality_gates:
  min_coverage: 0.75
  required_tests: true

metadata:
  chip: nRF52840
  architecture: ARM Cortex-M4
  flash_size: 1MB
  ram_size: 256KB
  rtos: Zephyr
  peripherals: [BLE, Thread, Zigbee, USB, NFC, GPIO]
```

### GPU: CUDA Jetson

```yaml
id: cuda_jetson
category: gpu
language: cuda
framework: cuda
gpu_arch: sm_87

templates:
  - path: src/kernel.cu
    source: drivers/gpu/cuda_jetson/templates/kernel.cu
  - path: src/main.cpp
    source: drivers/gpu/cuda_jetson/templates/main.cpp
  - path: CMakeLists.txt
    source: drivers/gpu/cuda_jetson/templates/CMakeLists.txt

build:
  command: cmake -B build && cmake --build build
  working_dir: project/gpu-cuda-jetson
  env:
    CUDA_ARCHITECTURES: "87"
  timeout_seconds: 600

test:
  command: ./build/tests/run_tests
  working_dir: project/gpu-cuda-jetson

lint:
  command: cuda-memcheck ./build/app
  working_dir: project/gpu-cuda-jetson

profiler_command: nsys profile ./build/app

artifact_paths:
  - project/gpu-cuda-jetson/build/*.so
  - project/gpu-cuda-jetson/build/app

quality_gates:
  min_coverage: 0.60
  required_tests: true

metadata:
  platform: Jetson Orin
  cuda_version: "12.2"
  tensorrt: true
  compute_capability: "8.7"
  memory: 32GB
  power_modes: [15W, 30W, 50W]
```

### GPU: ROCm Edge

```yaml
id: rocm_edge
category: gpu
language: hip
framework: rocm
gpu_arch: gfx1030

templates:
  - path: src/kernel.hip
    source: drivers/gpu/rocm/templates/kernel.hip
  - path: src/main.cpp
    source: drivers/gpu/rocm/templates/main.cpp
  - path: CMakeLists.txt
    source: drivers/gpu/rocm/templates/CMakeLists.txt

build:
  command: cmake -B build -DCMAKE_CXX_COMPILER=hipcc && cmake --build build
  working_dir: project/gpu-rocm-edge
  timeout_seconds: 600

test:
  command: ./build/tests/run_tests
  working_dir: project/gpu-rocm-edge

profiler_command: rocprof --stats ./build/app

artifact_paths:
  - project/gpu-rocm-edge/build/*.so
  - project/gpu-rocm-edge/build/app

quality_gates:
  min_coverage: 0.60
  required_tests: true

metadata:
  platform: AMD Radeon
  rocm_version: "5.7"
  architecture: RDNA2
  memory: 16GB
```

---

## Database Integration

Driver metadata should be stored in the database for traceability:

```python
# In orchestrator when starting iteration
db_ctx.start_iteration(
    config_snapshot=json.dumps({
        "targets": {
            "backend": "fastapi",
            "embedded": "esp32c3_riscv",
            "gpu": "cuda_jetson"
        },
        "driver_versions": {
            "fastapi": "1.0",
            "esp32c3_riscv": "1.0",
            "cuda_jetson": "1.0"
        }
    })
)

# In story_attempts, record which driver was used
db_ctx.log_attempt(
    story_id=story_id,
    role="dev",
    metadata={
        "driver": driver.id,
        "driver_category": driver.category,
        "build_command": driver.build.command
    }
)
```

---

## Próximos Pasos

1. ⏳ **Fase 1**: Crear `drivers/registry.py` con dataclasses y validación
2. ⏳ **Fase 2**: Implementar drivers `fastapi` y `nextjs` como prueba de concepto
3. ⏳ **Fase 3**: Integrar registry en orchestrator y roles (Dev, QA)
4. ⏳ **Fase 4**: Agregar drivers embedded (`esp32c3`, `zephyr_nrf52`)
5. ⏳ **Fase 5**: Agregar drivers GPU (`cuda_jetson`, `rocm_edge`)
6. ⏳ **Fase 6**: Tests unitarios e integración, documentación

---

## Archivos a Crear

```
drivers/
├── __init__.py
├── registry.py              # Driver loading and caching
├── dataclasses.py           # Driver, CommandSpec, etc.
├── exceptions.py            # DriverNotFoundError, etc.
├── backend/
│   ├── fastapi.yaml
│   ├── express.yaml
│   └── templates/
│       └── fastapi/
│           └── main.py
├── frontend/
│   ├── nextjs.yaml
│   └── templates/
├── embedded/
│   ├── esp32c3.yaml
│   ├── zephyr_nrf52.yaml
│   └── templates/
└── gpu/
    ├── cuda_jetson.yaml
    ├── rocm_edge.yaml
    └── templates/

tests/
├── test_driver_registry.py
├── test_driver_integration.py
└── conftest.py              # Driver fixtures
```
