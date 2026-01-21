import json
import yaml
import toml
import pytest
from commitcraft.__main__ import merge_configs, load_file


def test_merge_configs_basic():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = merge_configs(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_merge_configs_nested():
    base = {"nested": {"x": 1, "y": 2}, "other": 10}
    override = {"nested": {"y": 3}}
    result = merge_configs(base, override)
    assert result == {"nested": {"x": 1, "y": 3}, "other": 10}


def test_merge_configs_nested_overwrite_non_dict():
    base = {"nested": {"x": 1}}
    override = {"nested": "not_a_dict"}
    result = merge_configs(base, override)
    assert result == {"nested": "not_a_dict"}


def test_load_file_json(tmp_path):
    data = {"foo": "bar"}
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert load_file(str(p)) == data


def test_load_file_yaml(tmp_path):
    data = {"foo": "bar"}
    p = tmp_path / "test.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    assert load_file(str(p)) == data


def test_load_file_toml(tmp_path):
    data = {"foo": "bar"}
    p = tmp_path / "test.toml"
    p.write_text(toml.dumps(data), encoding="utf-8")
    assert load_file(str(p)) == data


def test_load_file_unsupported(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("content")
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_file(str(p))
