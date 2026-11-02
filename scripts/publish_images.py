"""Publish scanned Docker archives, refusing to replace a different immutable tag."""

import json
import os
import re
import subprocess
from pathlib import Path

COMPONENTS = ("frontend", "url-service", "analytics-service")
REGISTRY = "292681319373.dkr.ecr.us-east-1.amazonaws.com"


def remote_image_id(repository: str, tag: str) -> str | None:
    response = json.loads(
        subprocess.check_output(
            [
                "aws",
                "ecr",
                "batch-get-image",
                "--repository-name",
                repository,
                "--image-ids",
                f"imageTag={tag}",
                "--accepted-media-types",
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "--output",
                "json",
            ],
            text=True,
        )
    )
    images = response.get("images", [])
    failures = response.get("failures", [])
    if not images:
        if len(failures) == 1 and failures[0].get("failureCode") == "ImageNotFound":
            return None
        raise RuntimeError(
            f"Could not verify ECR image identity for {repository}:{tag}"
        )
    if failures or len(images) != 1:
        raise RuntimeError(f"Unexpected ECR response for {repository}:{tag}")
    manifest = json.loads(images[0]["imageManifest"])
    digest = manifest.get("config", {}).get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError(f"Unsupported image manifest for {repository}:{tag}")
    return digest


def publish_image(component: str, tag: str, artifact_root: Path) -> None:
    if component not in COMPONENTS or not re.fullmatch(r"[0-9a-f]{40}", tag):
        raise ValueError("Expected a known component and full Git commit SHA")
    repository = f"url-shortner-{component}"
    reference = f"{REGISTRY}/{repository}:{tag}"
    artifact = artifact_root / f"image-{component}"
    expected = (artifact / "image-id.txt").read_text().strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected):
        raise ValueError(f"Invalid saved image identity for {component}")
    subprocess.run(
        ["docker", "load", "--input", str(artifact / "image.tar")], check=True
    )
    local_reference = f"url-shortner-{component}:{tag}"
    actual = subprocess.check_output(
        ["docker", "image", "inspect", local_reference, "--format", "{{.Id}}"],
        text=True,
    ).strip()
    if actual != expected:
        raise RuntimeError(f"Saved image identity mismatch for {component}")
    existing = remote_image_id(repository, tag)
    if existing is not None:
        if existing != expected:
            raise RuntimeError(
                f"Immutable tag {reference} already contains a different image"
            )
        print(
            f"Already published with matching image identity: {reference}", flush=True
        )
        return
    subprocess.run(["docker", "tag", local_reference, reference], check=True)
    subprocess.run(["docker", "push", reference], check=True)
    if remote_image_id(repository, tag) != expected:
        raise RuntimeError(
            f"Published image identity verification failed for {reference}"
        )
    print(f"Published and verified: {reference}", flush=True)


def main() -> None:
    if os.environ.get("ECR_REGISTRY") != REGISTRY:
        raise ValueError("Unexpected ECR registry; refusing to publish")
    tag = os.environ["IMAGE_TAG"]
    for component in COMPONENTS:
        publish_image(component, tag, Path("images"))


if __name__ == "__main__":
    main()
