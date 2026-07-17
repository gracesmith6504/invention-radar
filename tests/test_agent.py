import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import validate_config


def test_validate_config_missing_radar_doc():
    os.environ.pop("RADAR_DOC_ID", None)
    import config
    config.RADAR_DOC_ID = ""
    errors = validate_config()
    assert any("RADAR_DOC_ID" in e for e in errors)


def test_validate_config_missing_oauth():
    import config
    config.RADAR_DOC_ID = "test-doc-id"
    config.GOOGLE_CLIENT_ID = ""
    errors = validate_config()
    assert any("GOOGLE_CLIENT_ID" in e for e in errors)


if __name__ == "__main__":
    test_validate_config_missing_radar_doc()
    print("✓ validate_config missing radar doc")
    test_validate_config_missing_oauth()
    print("✓ validate_config missing oauth")
    print("\nAll agent tests passed.")
