"""Publish scanned Docker archives, refusing to replace a different immutable tag."""

import hashlib
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path

COMPONENTS = ("frontend", "url-service", "analytics-service")
REGISTRY = (
    f"{os.getenv('AWS_ACCOUNT_ID', '957280466878')}.dkr.ecr."
    f"{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com"
)


def image_config_digest(archive_path: Path, reference: str) -> str:
    # Docker's inspected ID may identify a manifest rather than its config blob.
    # Use the saved config blob for a like-for-like comparison with ECR.
    with tarfile.open(archive_path) as archive:
        manifest_file = archive.extractfile("manifest.json")
        if manifest_file is None:
            raise ValueError("Saved image has no Docker archive manifest")
        manifests = json.load(manifest_file)
        matches = [
            item for item in manifests if reference in (item.get("RepoTags") or [])
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one saved image for {reference}")
        config_file = archive.extractfile(matches[0]["Config"])
        if config_file is None:
            raise ValueError("Saved image has no config blob")
        return "sha256:" + hashlib.sha256(config_file.read()).hexdigest()


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
    local_reference = f"url-shortner-{component}:{tag}"
    expected_config = image_config_digest(artifact / "image.tar", local_reference)
    subprocess.run(
        ["docker", "load", "--input", str(artifact / "image.tar")], check=True
    )
    actual = subprocess.check_output(
        ["docker", "image", "inspect", local_reference, "--format", "{{.Id}}"],
        text=True,
    ).strip()
    if actual != expected:
        raise RuntimeError(f"Saved image identity mismatch for {component}")
    existing = remote_image_id(repository, tag)
    if existing is not None:
        if existing != expected_config:
            raise RuntimeError(
                f"Immutable tag {reference} already contains a different image"
            )
        print(
            f"Already published with matching image identity: {reference}", flush=True
        )
        return
    subprocess.run(["docker", "tag", local_reference, reference], check=True)
    subprocess.run(["docker", "push", reference], check=True)
    if remote_image_id(repository, tag) != expected_config:
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
