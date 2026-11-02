import hashlib
import io
import json
import tarfile
from unittest.mock import Mock

import pytest

from scripts import publish_images as publisher

TAG = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64
CONFIG_BLOB = b'{"architecture":"amd64","rootfs":{"diff_ids":[]}}'
CONFIG_ID = "sha256:" + hashlib.sha256(CONFIG_BLOB).hexdigest()


@pytest.fixture
def artifact(tmp_path):
    directory = tmp_path / "image-frontend"
    directory.mkdir()
    (directory / "image-id.txt").write_text(IMAGE_ID)
    manifest = json.dumps(
        [
            {
                "Config": "config.json",
                "RepoTags": [f"url-shortner-frontend:{TAG}"],
                "Layers": [],
            }
        ]
    ).encode()
    with tarfile.open(directory / "image.tar", "w") as archive:
        for name, contents in [
            ("manifest.json", manifest),
            ("config.json", CONFIG_BLOB),
        ]:
            member = tarfile.TarInfo(name)
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
    return tmp_path


@pytest.fixture
def docker(monkeypatch):
    run = Mock()
    monkeypatch.setattr(publisher.subprocess, "run", run)
    monkeypatch.setattr(
        publisher.subprocess, "check_output", Mock(return_value=IMAGE_ID)
    )
    return run


def test_existing_matching_tag_is_not_pushed(artifact, docker, monkeypatch):
    monkeypatch.setattr(publisher, "remote_image_id", Mock(return_value=CONFIG_ID))
    publisher.publish_image("frontend", TAG, artifact)
    assert [call.args[0][1] for call in docker.call_args_list] == ["load"]


def test_existing_different_image_is_rejected(artifact, docker, monkeypatch):
    monkeypatch.setattr(
        publisher, "remote_image_id", Mock(return_value="sha256:" + "c" * 64)
    )
    with pytest.raises(RuntimeError, match="different image"):
        publisher.publish_image("frontend", TAG, artifact)
    assert [call.args[0][1] for call in docker.call_args_list] == ["load"]


def test_missing_tag_is_pushed_and_verified(artifact, docker, monkeypatch):
    remote = Mock(side_effect=[None, CONFIG_ID])
    monkeypatch.setattr(publisher, "remote_image_id", remote)
    publisher.publish_image("frontend", TAG, artifact)
    assert [call.args[0][1] for call in docker.call_args_list] == [
        "load",
        "tag",
        "push",
    ]
    assert remote.call_count == 2
    reference = f"{publisher.REGISTRY}/url-shortner-frontend:{TAG}"
    assert docker.call_args_list[-1].args[0] == ["docker", "push", reference]


def test_archive_identity_mismatch_stops_before_ecr(artifact, docker, monkeypatch):
    monkeypatch.setattr(
        publisher.subprocess, "check_output", Mock(return_value="wrong")
    )
    remote = Mock()
    monkeypatch.setattr(publisher, "remote_image_id", remote)
    with pytest.raises(RuntimeError, match="Saved image identity mismatch"):
        publisher.publish_image("frontend", TAG, artifact)
    remote.assert_not_called()
    assert docker.call_count == 1


@pytest.mark.parametrize("component,tag", [("unknown", TAG), ("frontend", "latest")])
def test_invalid_component_or_tag_rejected(component, tag, artifact, docker):
    with pytest.raises(ValueError):
        publisher.publish_image(component, tag, artifact)
    docker.assert_not_called()


@pytest.mark.parametrize(
    "response,expected",
    [
        ({"images": [], "failures": [{"failureCode": "ImageNotFound"}]}, None),
        (
            {
                "images": [
                    {"imageManifest": json.dumps({"config": {"digest": IMAGE_ID}})}
                ]
            },
            IMAGE_ID,
        ),
    ],
)
def test_remote_manifest_identity(monkeypatch, response, expected):
    monkeypatch.setattr(
        publisher.subprocess, "check_output", Mock(return_value=json.dumps(response))
    )
    assert publisher.remote_image_id("url-shortner-frontend", TAG) == expected


@pytest.mark.parametrize(
    "response",
    [
        {"images": [], "failures": [{"failureCode": "AccessDenied"}]},
        {"images": [], "failures": []},
        {"images": [{"imageManifest": json.dumps({"manifests": []})}]},
    ],
)
def test_unverifiable_remote_identity_fails(monkeypatch, response):
    monkeypatch.setattr(
        publisher.subprocess, "check_output", Mock(return_value=json.dumps(response))
    )
    with pytest.raises(RuntimeError):
        publisher.remote_image_id("url-shortner-frontend", TAG)


def test_unexpected_registry_rejected(monkeypatch):
    monkeypatch.setenv("ECR_REGISTRY", "unexpected.example")
    with pytest.raises(ValueError, match="Unexpected ECR registry"):
        publisher.main()


def test_archive_config_digest_is_independent_of_docker_id(artifact):
    digest = publisher.image_config_digest(
        artifact / "image-frontend/image.tar", f"url-shortner-frontend:{TAG}"
    )
    assert digest == CONFIG_ID
    assert digest != IMAGE_ID


def test_archive_reference_must_match(artifact):
    with pytest.raises(ValueError, match="exactly one saved image"):
        publisher.image_config_digest(
            artifact / "image-frontend/image.tar", "different-image:tag"
        )


def test_post_push_identity_mismatch_is_still_rejected(artifact, docker, monkeypatch):
    monkeypatch.setattr(
        publisher, "remote_image_id", Mock(side_effect=[None, "sha256:" + "c" * 64])
    )
    with pytest.raises(
        RuntimeError, match="Published image identity verification failed"
    ):
        publisher.publish_image("frontend", TAG, artifact)
