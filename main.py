from __future__ import annotations

import sys

from bsdgs_verifier.cli import build_parser, run_cli


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    cli_result = run_cli(args)
    if cli_result >= 0:
        return cli_result

    from bsdgs_verifier.gui import Application

    app = Application()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
