# Contributing to Renesas ADAS Guard

Thanks for helping improve the project. Contributions should preserve the deterministic behavior of the Python and C++ evaluators and keep the hardware boundary explicit.

## Before you start

1. Read the [README](README.md), especially the limitations and safety disclaimer.
2. Search existing issues and pull requests before opening a new one.
3. For a security vulnerability, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Development setup

The reference implementation has no third-party Python dependencies. Install Python 3.8+ and a C++17 compiler.

Run the same checks used by CI from the repository root:

```bash
python3 -m unittest discover -s core/tests -p 'test*.py' -v
mkdir -p build
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror \
  integration/GuardEvaluator.cpp integration/main.cpp \
  -o build/guard_demo
./build/guard_demo
```

Use `python` instead of `python3` where appropriate. Kotlin changes should be checked in the consuming Android project because this repository does not include a Gradle build.

## Coding expectations

- Keep the Python evaluator dependency-free and deterministic.
- Keep Python and C++ policy thresholds, reason precedence, score behavior, and hysteresis aligned; update both implementations and the protocol documentation when policy changes.
- Validate units and numeric ranges at integration boundaries.
- Prefer small, focused changes with clear failure behavior.
- Add or update meaningful tests for evaluator behavior and boundary conditions.
- Use 4-space indentation in Python, the existing C++ formatting style, and standard Kotlin formatting.
- Do not commit generated files, build outputs, credentials, vehicle data, or proprietary SDK artifacts.
- Do not describe the scaffold as safety-certified or production-ready.

## Pull requests

A pull request should:

- explain the user-visible or integration-facing change;
- identify any protocol, threshold, or hardware assumptions;
- include tests or a clear reason a test is not applicable;
- include the exact local commands run and their results;
- update documentation when behavior, defaults, or integration steps change;
- keep unrelated formatting and refactoring out of the change.

A maintainer may request evidence from the Python reference evaluator, the C++ demo, or a target-board test before merging changes that affect trust decisions or output behavior.
