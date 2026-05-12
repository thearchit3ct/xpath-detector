"""Entry point for xpath-detector."""

import logging
import sys

from xpath_detector.shell import Shell


def main() -> None:
    file_handler = logging.FileHandler("xpath_detector.log")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[file_handler, console_handler],
    )
    Shell().run()


if __name__ == "__main__":
    main()
