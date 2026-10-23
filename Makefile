.PHONY: test demo scenario syntax check

PYTHON ?= python3
CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Wpedantic -Werror
BUILD_DIR ?= build
DEMO := $(BUILD_DIR)/guard_demo

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s core/tests -p 'test*.py' -v

syntax:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile core/*.py core/tests/*.py

demo: $(DEMO)
	./$(DEMO)

$(DEMO): integration/GuardEvaluator.cpp integration/GuardEvaluator.h integration/main.cpp
	mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) integration/GuardEvaluator.cpp integration/main.cpp -o $(DEMO)

scenario:
	PYTHONPATH=. $(PYTHON) -m core.scenario_runner --scenario scenarios/demo.json

check: test syntax demo scenario
