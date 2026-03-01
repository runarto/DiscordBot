"""Tests for pure utility functions in misc/utils.py."""

from misc.utils import check_similarity, split_message_blocks


class TestCheckSimilarity:
    def test_identical_strings(self):
        assert check_similarity("Rosenborg", "Rosenborg") == 1.0

    def test_completely_different(self):
        assert check_similarity("Brann", "xyz") == 0.0

    def test_partial_match(self):
        ratio = check_similarity("Rosenborg", "Rosenberg")
        assert 0.8 < ratio < 1.0

    def test_empty_strings(self):
        assert check_similarity("", "") == 1.0

    def test_case_sensitive(self):
        # SequenceMatcher is case-sensitive
        assert check_similarity("BRANN", "brann") < 1.0

    def test_symmetry(self):
        assert check_similarity("Molde", "Viking") == check_similarity("Viking", "Molde")


class TestSplitMessageBlocks:
    def test_short_lines_fit_in_one_block(self):
        lines = ["line1", "line2", "line3"]
        blocks = split_message_blocks(lines, max_length=200)
        assert len(blocks) == 1
        assert "line1" in blocks[0]
        assert "line3" in blocks[0]

    def test_splits_when_content_exceeds_max_length(self):
        # Each line is 100 chars; 3 lines + newlines exceed 150
        lines = ["a" * 100, "b" * 100, "c" * 100]
        blocks = split_message_blocks(lines, max_length=150)
        assert len(blocks) > 1

    def test_all_lines_appear_across_blocks(self):
        lines = ["alpha", "beta", "gamma"]
        blocks = split_message_blocks(lines, max_length=10)
        combined = "\n".join(blocks)
        for line in lines:
            assert line in combined

    def test_empty_input_returns_empty_list(self):
        assert split_message_blocks([]) == []

    def test_single_line_returns_single_block(self):
        blocks = split_message_blocks(["hello"], max_length=100)
        assert blocks == ["hello"]

    def test_no_trailing_whitespace_on_blocks(self):
        lines = ["line1", "line2"]
        blocks = split_message_blocks(lines, max_length=200)
        for block in blocks:
            assert not block.endswith("\n")
            assert not block.endswith(" ")

    def test_default_max_length_is_2000(self):
        # 21 lines of 100 chars each exceeds 2000; should split
        lines = ["a" * 100] * 21
        blocks = split_message_blocks(lines)
        assert len(blocks) > 1

    def test_block_does_not_exceed_max_length(self):
        lines = ["x" * 50] * 10
        max_length = 120
        blocks = split_message_blocks(lines, max_length=max_length)
        for block in blocks:
            assert len(block) <= max_length
