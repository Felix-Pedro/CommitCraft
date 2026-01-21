import nox

# Configure nox to use uv by default for faster virtual environment creation
nox.options.default_venv_backend = "uv"

# Define the python versions we want to test against
PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13", "3.14"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run the test suite."""
    # Install test dependencies
    session.install("pytest", "pytest-cov", "pytest-mock")
    # Install the package itself in editable mode
    session.install("-e", ".")

    # Run pytest with coverage
    session.run("pytest", "--cov=commitcraft", "--cov-report=term-missing", "tests/")


@nox.session(python=PYTHON_VERSIONS[0])
def lint(session):
    """Run linters."""
    session.install("ruff")
    session.run("ruff", "check", "--fix", ".")


@nox.session(python=PYTHON_VERSIONS[0])
def format(session):
    """Check code formatting."""
    session.install("ruff")
    session.run("ruff", "format", "--check", ".")


@nox.session(python=PYTHON_VERSIONS[0])
def type_check(session):
    """Run type checking."""
    session.install("mypy", "types-requests", "types-PyYAML", "types-toml")
    # Install the package dependencies for type checking
    session.install(".")

    # Ignore missing imports for some libs that might not have stubs yet
    # and disable some strict error codes to match existing project state
    session.run(
        "mypy",
        "--ignore-missing-imports",
        "--disable-error-code",
        "attr-defined",
        "--disable-error-code",
        "arg-type",
        "--disable-error-code",
        "assignment",
        "--disable-error-code",
        "return-value",
        "--disable-error-code",
        "union-attr",
        "--disable-error-code",
        "call-overload",
        "--disable-error-code",
        "operator",
        "--disable-error-code",
        "valid-type",
        "src/commitcraft",
    )
