from commitcraft.CommitCraft import filter_diff, get_context_size

def test_filter_diff_basic():
    diff = "diff --git a/file1.txt b/file1.txt\nindex 123..456 100644\n--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-foo\n+bar\n"
    filtered = filter_diff(diff, [])
    # filter_diff uses splitlines and join, effectively removing the last newline if input ended with one
    assert filtered == diff.strip()

def test_filter_diff_ignore_extension():
    diff = """diff --git a/file1.txt b/file1.txt
index 123..456 100644
--- a/file1.txt
+++ b/file1.txt
@@ -1 +1 @@
-foo
+bar
diff --git a/file2.lock b/file2.lock
index 123..456 100644
--- a/file2.lock
+++ b/file2.lock
@@ -1 +1 @@
-lock
+lock
"""
    filtered = filter_diff(diff, ["*.lock"])
    assert "file1.txt" in filtered
    assert "file2.lock" not in filtered

def test_filter_diff_ignore_pattern():
    diff = """diff --git a/src/main.py b/src/main.py
...
diff --git a/dist/bundle.js b/dist/bundle.js
...
"""
    filtered = filter_diff(diff, ["dist/*"])
    assert "src/main.py" in filtered
    assert "dist/bundle.js" not in filtered

def test_get_context_size():
    diff = "small diff"
    system = "small prompt"
    # Should hit min context 1024
    assert get_context_size(diff, system) == 1024

    # Large diff
    large_diff = "a" * 50000
    large_prompt = "b" * 1000
    # (51000 * 2.64) = 134640 > 128000 -> capped at 128000
    assert get_context_size(large_diff, large_prompt) == 128000
