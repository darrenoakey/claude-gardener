![](banner.jpg)

# claude-gardener

An autonomous AI agent that performs automated gardening tasks on your codebase and files — quietly tending, maintaining, and organising so you don't have to.

---

## Purpose

claude-gardener is a self-contained autonomous agent that keeps your projects healthy. It handles the repetitive, ongoing maintenance work that accumulates over time — cleaning up, organising, and tending to your code and files in a thoughtful, automated way.

---

## Installation

No manual installation or environment setup is required. claude-gardener is fully self-bootstrapping.

The only prerequisite is a working Python 3 installation on your system.

---

## How to Use

Run the agent directly from the project root:

```bash
./run
```

That's it. On first run, claude-gardener will automatically set itself up and then begin working.

### Running with arguments

You can pass arguments directly to the agent:

```bash
./run [arguments]
```

---

## Examples

### Start the agent

```bash
./run
```

### Run against a specific target

```bash
./run --target /path/to/your/project
```

### Run with verbose output

```bash
./run --verbose
```

---

## Notes

- No `pip install`, `venv` creation, or dependency management is needed on your part — the `run` script handles everything automatically on first launch.
- Subsequent runs are faster as the environment is already in place.
- To reset the environment, delete the `.venv` directory in the project root and run `./run` again.

## License

This project is licensed under [CC BY-NC 4.0](https://darren-static.waft.dev/license) - free to use and modify, but no commercial use without permission.
