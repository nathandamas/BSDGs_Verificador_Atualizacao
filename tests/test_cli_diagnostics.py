from __future__ import annotations

from bsdgs_verifier.cli import build_parser


def test_parser_accepts_self_test_file() -> None:
    args = build_parser().parse_args(["--self-test-file", "diagnostico.json"])
    assert args.self_test_file == "diagnostico.json"
