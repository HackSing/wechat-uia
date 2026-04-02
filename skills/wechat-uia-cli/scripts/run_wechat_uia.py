from __future__ import annotations

import sys

from run_wechat_skill import main


if __name__ == "__main__":
    raise SystemExit(main(["export-history", *sys.argv[1:]]))
