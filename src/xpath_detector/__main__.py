"""Entry point for xpath-detector."""
import logging

from xpath_detector.shell import Shell


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename="xpath_detector.log",
    )
    Shell().run()


if __name__ == "__main__":
    main()
