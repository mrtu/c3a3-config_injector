Below is a **separate Architecture & Roadmap document** that builds on (but does not re‑state) the previously agreed v0.1 specification. It decomposes the system into testable components, defines their Python‑level APIs, and lays out milestone iterations from 0.1 → GA.

---

# Configuration Wrapping Framework – Architecture & Roadmap

**Doc purpose:** Provide an implementable component architecture, public APIs, testing surfaces, and incremental milestones (with Definitions of Done) for taking the spec from **v0.1 draft** through a production‑ready 1.0 release.

**Audience:** Engineers building the framework; contributors writing providers or injectors; CI integrators.

---

## 1. Architectural Principles

1. **Pure → impure boundary:** Resolve spec, tokens, and values in pure functions (easy unit tests). Defer I/O (env reads, file writes, subprocess spawn) to thin runtime adapters.
2. **Composition via data objects:** Every stage receives a typed object (Pydantic model or dataclass) and returns a *new* structure — no hidden global state.
3. **Deterministic dry‑run:** Same path as live run except final spawn & I/O; enables end‑to‑end testing without side effects.
4. **Small adapters, pluggable:** Providers & injectors register via entry points or mapping dict; simple interfaces keep optional components isolated.
5. **Masking at the edge:** Data inside the core remains cleartext; masking only when rendering logs/output (allows secure transforms and cryptographic checks before display).

---

## 2. High‑Level Component Map

```
          +----------------+
          |  Spec Loader   |
          +-------+--------+
                  |
                  v
          +----------------+
          | Schema Models  |
          | (Pydantic)     |
          +-------+--------+
                  |
                  v
          +----------------+         +------------------+
          | Token Engine   |<------->| Context Builder   |
          +-------+--------+         +------------------+
                  |
                  v
          +----------------+
          | Provider Layer |
          | (env/dotenv/..)|
          +-------+--------+
                  |
                  v
          +----------------+
          | Merge Engine   |  (provider maps merged per rules)
          +-------+--------+
                  |
                  v
          +----------------+
          | Injector Layer |
          | build env/argv |
          +-------+--------+
                  |
         +--------+---------+
         | Stream/Logging   |
         +--------+---------+
                  |
                  v
          +----------------+
          | Executor       |
          +----------------+
```

**Cross‑cutting:** Validation, Masking Renderer, Error Model, CLI, Testing Utilities.

---

## 3. Core Data Types (Shared)

> These are *conceptual* types; concrete signatures appear in component APIs.

```python
from typing import Dict, List, Optional, Any, Sequence, Tuple
EnvMap = Dict[str, str]                    # environment-like maps; always str->str
ProviderMap = Dict[str, str]               # keys from a provider
ProviderMaps = Dict[str, ProviderMap]      # keyed by provider id
InjectionValue = Optional[str]             # resolved final string (post coercion)
Argv = List[str]
Errors = List[str]
```

---

## 4. Component Specifications & APIs

### 4.1 Spec Loader

**Purpose:** Load YAML → `Spec` Pydantic model; minimal path resolution (e.g., relative to file).

**API**

```python
def load_spec(path: Path) -> Spec
```

**Testable:** invalid YAML; schema mismatch; unknown fields.

---

### 4.2 Context Builder

**Purpose:** Build a runtime context used for interpolation: env snapshot, datetimes, PID, HOME, sequence counters.

**API**

```python
@dataclass
class RuntimeContext:
    env: EnvMap
    now: datetime
    pid: int
    home: str
    seq: int  # incremented per invocation
    extra: Dict[str, Any] = field(default_factory=dict)

def build_runtime_context(spec: Spec, *, env: EnvMap = None) -> RuntimeContext
```

If `env` omitted, capture `os.environ`. Used in dry‑run by injecting synthetic env.

**Testable:** injection of fixed datetimes for deterministic tests.

---

### 4.3 Token Engine

**Purpose:** Expand `${...}` tokens inside strings using `RuntimeContext` + provider data (if available). Supports fallback (`|value`), date/time tokens, provider refs, etc.

**API**

```python
class TokenEngine:
    def __init__(self, context: RuntimeContext, provider_maps: ProviderMaps | None = None):
        ...
    def expand(self, template: str) -> str
    def try_expand(self, template: str) -> tuple[str, list[str]]  # value, warnings
```

**Rules:** Single‑level expansion MVP; nested optional later.

**Testable:** unit tests table‑driven: input template, expected output, missing token -> warnings.

---

### 4.4 Provider Layer

Each provider implements a common interface.

**Base Protocol**

```python
class ProviderProtocol(Protocol):
    id: str
    def load(self, context: RuntimeContext) -> ProviderMap
```

**Factory**

```python
def load_providers(spec: Spec, context: RuntimeContext) -> ProviderMaps
```

Responsible for applying `filter_chain` and provider‑level masking metadata (actual masking deferred).

#### env provider

Reads `context.env` (or `os.environ` fallback). Applies filters.

#### dotenv provider

Loads a file (single path). Parser: `KEY=VAL` lines; export semantics.

#### hierarchical dotenv

Walk up directories from `target.working_dir` → `/`. Collect `filename`. Merge per `precedence` (`deep-first` = nearer overrides).

#### bws provider

Lookup secrets (stub for MVP: return env stand‑ins). Real integration later.

**Testable:**

* Provide synthetic FS tree for hierarchical.
* Provide synthetic env.
* Ensure include/exclude logic works in order.

---

### 4.5 Merge Engine (Provider Aggregation)

**Purpose:** Not a separate step for all types, but a helper that:

* Collapses hierarchical dotenv collects into a single ProviderMap.
* Optionally overlays providers if a *composite provider* is defined (future).

**API**

```python
def merge_hierarchical_dotenv(files: Sequence[Path], precedence: str) -> ProviderMap
```

**Testable:** check override order.

---

### 4.6 Injector Layer

Resolves each injector to a final value and maps it to env/argv/file/stdin.

**API**

```python
@dataclass
class ResolvedInjector:
    injector: Injector
    value: Optional[str]
    applied_aliases: List[str]   # env names or flags
    argv_segments: List[str]     # built CLI fragments
    env_updates: EnvMap          # env var name -> value
    files_created: List[Path]    # for cleanup
    skipped: bool
    errors: List[str]

def resolve_injector(
    injector: Injector,
    context: RuntimeContext,
    providers: ProviderMaps,
    token_engine: TokenEngine
) -> ResolvedInjector
```

**Resolution Algorithm** (first\_non\_empty as default):

* Expand each `source` via token engine.
* Accept first non‑empty.
* If empty & default -> use default.
* If required & unresolved -> error.

**Kind behaviors:**

* env\_var: update env per alias.
* named: use first alias (long form if present) unless you later add `preferred_alias`.
* positional: recorded for later sort by `order`.
* file: create temp file, write value, produce path into env or argv (TBD per injector config).
* stdin\_fragment: produce a buffer for aggregator.

**Testable:** simulate providers; confirm value chosen matches precedence; confirm quoting/connector rules.

---

### 4.7 Env/Arg Builder

Aggregates all `ResolvedInjector` outputs into final environment delta & argv list.

**API**

```python
@dataclass
class BuildResult:
    env: EnvMap          # final env for child
    argv: Argv           # final command array
    stdin_data: Optional[bytes]
    files: List[Path]    # created temp files
    errors: Errors

def build_env_and_argv(
    spec: Spec,
    resolved: Sequence[ResolvedInjector],
    context: RuntimeContext
) -> BuildResult
```

**Ordering:**

* Base argv from `spec.target.command`.
* Insert positionals sorted by `order` (stable).
* Append named args in declaration order (or grouped; choose & document).
* `env_passthrough`: start from `context.env`; overlay env\_var injections last.

---

### 4.8 Stream / Logging Manager

Creates paths (expand tokens), opens files (append or truncate), and sets up tee to terminal.

**API**

```python
@dataclass
class StreamConfig:
    path: Optional[Path]
    tee_terminal: bool
    append: bool
    format: Literal['text','json']

def prepare_stream(stream: Stream, context: RuntimeContext, token_engine: TokenEngine) -> StreamConfig
```

At runtime:

```python
class StreamWriter:
    def write_stdout(self, data: bytes) -> None
    def write_stderr(self, data: bytes) -> None
    def close(self) -> None
```

**Testable:** path expansion; collision avoidance; JSON line formatting.

---

### 4.9 Executor

Runs the child process with built env/argv and connected streams.

**API**

```python
@dataclass
class ExecutionResult:
    exit_code: int
    duration_s: float
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]

def execute(spec: Spec, build: BuildResult, streams: StreamWriter) -> ExecutionResult
```

Use `subprocess.Popen` (shell vs none), feed stdin\_data, stream out.

---

### 4.10 Dry‑Run Explainer

Produces human & machine readable preview; never spawns child.

**API**

```python
@dataclass
class DryRunReport:
    providers: ProviderMaps
    resolved: Sequence[ResolvedInjector]
    build: BuildResult
    text_summary: str
    json_summary: dict

def dry_run(spec: Spec, context: RuntimeContext) -> DryRunReport
```

**Testable:** stable output snapshot tests; masking verified.

---

### 4.11 Validation Engine (Semantic)

Layered checks beyond Pydantic.

**API**

```python
def semantic_validate(spec: Spec) -> Errors
```

Rules: unique IDs, alias syntax, required positional ordering, etc.

---

### 4.12 Masking Renderer

Utility applied wherever values are surfaced to logs/dry‑run.

**API**

```python
def mask_value(value: str, enabled: bool, strategy: str = "fixed") -> str
```

Strategies: fixed `***`, length display, hash prefix.

---

### 4.13 Error Model

Normalized structured errors for tooling & programmatic callers.

**API**

```python
@dataclass
class FrameworkError(Exception):
    code: str
    message: str
    context: Dict[str, Any]
```

---

### 4.14 CLI Frontend

Expose subcommands: `dry-run`, `run`, `explain`, `validate`, `print-schema`.

**Example using Typer**

```python
wrapper run spec.yaml
wrapper dry-run spec.yaml
wrapper validate spec.yaml --strict
```

---

## 5. Testing Strategy

| Level              | What                                                      | Tooling            | Notes                               |
| ------------------ | --------------------------------------------------------- | ------------------ | ----------------------------------- |
| Unit               | Token expansion, regex filters, precedence, type coercion | pytest             | pure functions; parametrize heavily |
| Component          | Provider loads w/ temp dirs & env fixtures                | pytest + tmp\_path | hierarchical merge tests            |
| Integration (dry)  | spec → dry\_run; snapshot text/json                       | pytest approvals   | no subprocess spawn                 |
| Integration (live) | spawn trivial echo script; assert env/argv passed         | pytest             | hermetic script fixtures            |
| Security/masking   | ensure sensitive data not in logs/dry-run when masked     | pytest grep        |                                     |

---

## 6. Incremental Roadmap & Milestones

> Each milestone builds on prior; code remains releasable at each stop.

### Milestone v0.1 (Spec MVP Load + Env/NVP Injection)

**Scope**

* Spec Loader + Pydantic models.
* env provider (passthrough true).
* hierarchical dotenv provider (deep-first).
* bws provider stub (values from env).
* Injectors: env\_var, named, positional.
* Token engine minimal (ENV, PROVIDER, DATE, TIME, HOME, PID).
* Build env & argv.
* Simple run (stdout/stderr inherit terminal; no log files).
* Dry‑run summary (text only).

**Definition of Done**

* Load & run the Minimal Working Example Spec (§18 spec doc).
* Required injectors error correctly.
* Unit tests: token engine, provider filters, precedence.
* Integration: sample script sees injected env & args.
* 80% branch coverage of core modules.

---

### Milestone v0.2 (Streams & Logging Paths)

**Adds**

* Stream Manager with path expansion tokens.
* Tee to terminal; file write (text only).
* Collision‑safe naming tokens: TIME ms, PID, SEQ.
* Append vs truncate.

**DoD**

* stdout/stderr properly written to expanded paths.
* Paths unique in quick loop test.
* Unit: path templating, tee mode.
* CLI flag `--dry-run` shows resolved log paths.

---

### Milestone v0.3 (Masking & Sensitive Data)

**Adds**

* Global `mask_defaults`.
* Per provider `mask`, per injector `sensitive`.
* Masking renderer; dry-run redaction.

**DoD**

* Sensitive values not printed in dry-run; appear masked but length preserved.
* Unit: mask\_value strategies.
* Security test: grep logs for secret refuses.

---

### Milestone v0.4 (Type Coercion + Validation Enhancements)

**Adds**

* Injector `type:` coercion (int/bool/path/list/json).
* Semantic validation pass (unique IDs, alias forms, required pos order).
* Improved dry-run: show type conversions & errors.

**DoD**

* Invalid int triggers error.
* List split works; delim configurable global.
* Semantic validator returns structured errors; CLI exit non‑zero.

---

### Milestone v0.5 (File + stdin\_fragment Injectors)

**Adds**

* Write value to temp file; inject path as named arg or env.
* Aggregate stdin fragments; deliver to child stdin.

**DoD**

* Example script reads JSON written from file injector.
* Stdin injection test (cat script reads combined payload).
* Temp files cleanup on success & failure.

---

### Milestone v0.6 (Profiles + Conditional Injection)

**Adds**

* Optional `profiles` keyed by name; CLI `--profile dev`.
* `when:` expressions (simple eval).
* Default fallbacks in tokens (`|fallback`).

**DoD**

* Profile overrides proven (value differs under `--profile prod`).
* `when:` gating verified via env toggle.

---

### Milestone v0.7 (JSON Log Format)

**Adds**

* Stream format json: JSON‑per‑line w/ ts, level, stream, message.
* Structured error events on non‑zero exit.

**DoD**

* JSON logs parseable (json.loads).
* Contains masked values correctly.

---

### Milestone v0.8 (Plugin API for Custom Providers/Injectors)

**Adds**

* Registration mechanism (entry\_points or plugin registry).
* Example `custom` provider and `file` injector extension.

**DoD**

* External package can register plugin; integration test.

---

### Milestone v0.9 (Cross‑Host Runner Preview: ssh sync)

**Adds**

* Minimal `runner: ssh` (sync only).
* Copy spec‑resolved files; run remote; fetch logs.

**DoD**

* Integration test w/ local loopback SSH container.
* Dry-run shows remote command.

---

### Milestone v1.0 (GA)

**Scope**

* Hardened error model; stable CLI; docs & examples.
* Full test matrix across Linux/macOS/Windows (shell none/powershell).
* Versioned schema compatibility (Spec.version gating).

**DoD**

* 90%+ branch coverage core.
* All examples runnable.
* Semantic versioning tags & changelog.
* Backward compatibility tests (0.1 spec loads w/ warning but runs).

---

## 7. Task Backlog per Milestone (Abbreviated)

Below: bullet tasks; each assumed to include unit tests & doc updates.

### v0.1 Tasks

* [ ] Define Pydantic models (#models)
* [ ] Implement YAML loader (#load)
* [ ] Build runtime context (#context)
* [ ] Token engine minimal (#token-mvp)
* [ ] env provider (#prov-env)
* [ ] hierarchical dotenv provider (#prov-dotenv-hier)
* [ ] bws stub provider (#prov-bws-stub)
* [ ] Injector resolution (env\_var/named/positional) (#inj-mvp)
* [ ] Build env+argv aggregator (#build)
* [ ] Execute local process (#exec-mvp)
* [ ] Dry-run text (#dryrun-mvp)
* [ ] Example script + integration test (#it-mvp)

### v0.2 Tasks

* [ ] Stream path expansion (#stream-path)
* [ ] Tee & append (#stream-tee)
* [ ] Collision tokens PID/SEQ (#stream-uniq)
* [ ] Update dry-run to show paths (#dryrun-path)

...(continue similarly through v1.0; omitted here for brevity—happy to expand into full JIRA‑style table if you want.)

---

## 8. Definition of Done Template (Apply to All Tasks)

A task is **Done** when:

1. **Implementation complete** & code type‑checked (mypy or pyright optional).
2. **Unit tests** cover success + at least one failure case.
3. **Docs**: README or inline docstrings updated; if user‑visible behavior changed, spec doc section updated.
4. **Dry‑run verified**: new feature surfaces correctly in dry-run output.
5. **CI green** across supported Python versions.
6. **Masking respected** if applicable (no secrets in captured logs).

You can annotate tasks with `DoD+` items (perf, coverage) as required.

---

## 9. Risk & Mitigation Snapshot

| Risk                              | Phase | Mitigation                                                                   |
| --------------------------------- | ----- | ---------------------------------------------------------------------------- |
| Leaking secrets in logs           | early | masking defaults; redaction tests                                            |
| Complex nested interpolation      | mid   | restrict to 1 level MVP; raise on nested until implemented                   |
| Hierarchical FS walk performance  | low   | no caching by design; restrict depth or bail after root                      |
| Platform quoting differences      | mid   | prefer argv array execve over shell; fallback to `shell:` only when required |
| Provider network failures (vault) | later | timeouts + retry; fallback to env if configured                              |

---

## 10. Quick Implementation Order Graph

```
[models] -> [load] -> [context] -> [token-mvp] -> [prov-env]
                                     |-> [prov-dotenv-hier]
                                     |-> [prov-bws-stub]
-> [inj-mvp] -> [build] -> [exec-mvp] -> [dryrun-mvp]
```

---

## 11. Getting Started Checklist (Dev Env)

* Python 3.11+
* pip install: pydantic, pyyaml, python-dotenv, typer (CLI), rich (pretty dry-run)
* pre-commit hooks: black, ruff, mypy
* pytest + pytest-cov


