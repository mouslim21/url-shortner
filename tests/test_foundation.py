import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_directories_exist() -> None:
    directories = [
        "frontend",
        "services/url-service/app",
        "services/url-service/tests",
        "services/analytics-service/app",
        "services/analytics-service/tests",
        "infrastructure/terraform/bootstrap",
        "infrastructure/terraform/environments/nonprod",
        "infrastructure/helm/url-shortener",
        ".github/workflows",
        "scripts",
    ]
    for directory in directories:
        assert (ROOT / directory).is_dir(), f"Missing directory: {directory}"


def test_ruff_configuration() -> None:
    with (ROOT / "pyproject.toml").open("rb") as config_file:
        ruff = tomllib.load(config_file)["tool"]["ruff"]
    assert ruff["target-version"] == "py312"
    assert ruff["line-length"] == 88
    assert set(ruff["lint"]["select"]) == {"E", "F", "I"}
