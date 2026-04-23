import pytest

from src.common.exceptions import VersionNotFoundError
from src.harness.ab_test import ABTestConfig, ABTestManager
from src.harness.version_manager import VersionManager


@pytest.fixture
def version_manager(tmp_path):
    """Create a version manager with test versions."""
    vm = VersionManager(strategies_dir=tmp_path / "strategies")
    vm.strategies_dir.mkdir(parents=True, exist_ok=True)

    # Create test versions with metadata
    for version in ["v1", "v2"]:
        vm.create_version(version, None, {"system_prompt": "Test prompt"})

    # Set v1 as current
    current_link = vm.strategies_dir / "current"
    if current_link.exists():
        current_link.unlink()
    current_link.symlink_to("v1")

    return vm


@pytest.fixture
def ab_manager(version_manager):
    return ABTestManager(version_manager)


def test_ab_test_config_validation():
    """Test that ABTestConfig validates treatment_ratio."""
    # Valid ratios
    ABTestConfig(control_version="v1", treatment_version="v2", treatment_ratio=0.0)
    ABTestConfig(control_version="v1", treatment_version="v2", treatment_ratio=0.5)
    ABTestConfig(control_version="v1", treatment_version="v2", treatment_ratio=1.0)

    # Invalid ratios
    with pytest.raises(ValueError, match="treatment_ratio must be between"):
        ABTestConfig(control_version="v1", treatment_version="v2", treatment_ratio=-0.1)

    with pytest.raises(ValueError, match="treatment_ratio must be between"):
        ABTestConfig(control_version="v1", treatment_version="v2", treatment_ratio=1.1)


def test_start_test(ab_manager):
    """Test starting an A/B test."""
    ab_manager.start_test(control_version="v1", treatment_version="v2", treatment_ratio=0.3)

    assert ab_manager.is_test_active
    assert ab_manager.active_test is not None
    assert ab_manager.active_test.control_version == "v1"
    assert ab_manager.active_test.treatment_version == "v2"
    assert ab_manager.active_test.treatment_ratio == 0.3


def test_start_test_invalid_version(ab_manager):
    """Test that starting a test with invalid version raises error."""
    with pytest.raises(VersionNotFoundError):
        ab_manager.start_test(control_version="v1", treatment_version="v999", treatment_ratio=0.5)


def test_stop_test(ab_manager):
    """Test stopping an A/B test."""
    ab_manager.start_test(control_version="v1", treatment_version="v2", treatment_ratio=0.5)
    assert ab_manager.is_test_active

    ab_manager.stop_test()
    assert not ab_manager.is_test_active
    assert ab_manager.active_test is None


def test_get_version_no_test(ab_manager):
    """Test getting version when no test is active."""
    version = ab_manager.get_version_for_request()
    assert version == "v1"  # Should return current production version


def test_get_version_with_test_deterministic(ab_manager):
    """Test deterministic routing with request_id."""
    ab_manager.start_test(control_version="v1", treatment_version="v2", treatment_ratio=0.5)

    # Same request_id should always get same version
    request_id = "test-request-123"
    version1 = ab_manager.get_version_for_request(request_id)
    version2 = ab_manager.get_version_for_request(request_id)
    assert version1 == version2

    # Different request_ids may get different versions
    versions = set()
    for i in range(100):
        version = ab_manager.get_version_for_request(f"request-{i}")
        versions.add(version)

    # With 100 requests and 50% split, we should see both versions
    assert len(versions) == 2
    assert "v1" in versions
    assert "v2" in versions


def test_get_version_with_test_random(ab_manager):
    """Test random routing without request_id."""
    ab_manager.start_test(control_version="v1", treatment_version="v2", treatment_ratio=0.5)

    versions = []
    for _ in range(100):
        version = ab_manager.get_version_for_request()
        versions.append(version)

    # With 50% split and 100 requests, we should see both versions
    assert "v1" in versions
    assert "v2" in versions

    # Rough distribution check (not exact due to randomness)
    v2_count = versions.count("v2")
    assert 30 <= v2_count <= 70  # Allow 20% variance


def test_get_version_treatment_ratio_extremes(ab_manager):
    """Test routing with extreme treatment ratios."""
    # 0% treatment - all control
    ab_manager.start_test(control_version="v1", treatment_version="v2", treatment_ratio=0.0)
    versions = [ab_manager.get_version_for_request(f"req-{i}") for i in range(50)]
    assert all(v == "v1" for v in versions)

    # 100% treatment - all treatment
    ab_manager.start_test(control_version="v1", treatment_version="v2", treatment_ratio=1.0)
    versions = [ab_manager.get_version_for_request(f"req-{i}") for i in range(50)]
    assert all(v == "v2" for v in versions)
