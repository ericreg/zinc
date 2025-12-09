import json
import logging
import sys
from pathlib import Path

import structlog
from colorama import Back, Fore, Style

from zinc.exceptions import ZincLogLevelError


def get_logger(*args, **initial_values):
    return structlog.get_logger(*args, **initial_values)


def _colorize(level: str, msg: str) -> str:
    # if a critical error, color the background red
    background = Back.LIGHTRED_EX if level == "critical" else Back.RESET

    # always make errors bold
    style = Style.BRIGHT if level in {"critical", "error"} else Style.NORMAL

    color = {
        "critical": Fore.LIGHTWHITE_EX,
        "error": Fore.LIGHTRED_EX,
        "warning": Fore.LIGHTYELLOW_EX,
        "info": Fore.LIGHTGREEN_EX,
        "debug": Fore.LIGHTMAGENTA_EX,
    }.get(level, Fore.RESET)

    return f"{background}{style}{color}{msg}{Style.RESET_ALL}"


def _source_location(_, level, event_dict):
    if "pathname" in event_dict and "lineno" in event_dict:
        pathname = event_dict.pop("pathname")
        lineno = event_dict.pop("lineno")
        abs_path = str(Path(pathname).absolute())
        event_dict["line"] = f"{abs_path}:{lineno}"
    return event_dict


def _json_render(_, level, event_dict):
    json_output = json.dumps(event_dict, indent=2, default=str, ensure_ascii=False)
    return _colorize(level, json_output)


def configure_logging(
    level: str | int | None = "info",
) -> None:
    """
    Configure structured JSON logging using structlog.

    Args:
        level: The log level to use. Defaults to INFO.
    """

    levels_to_name = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }

    name_to_levels = {v: k for k, v in levels_to_name.items()}

    if isinstance(level, str):
        level = name_to_levels.get(level.lower())
        if level is None:
            raise ZincLogLevelError(
                f"Invalid log level: {level}. Must be one of {list(name_to_levels.keys())}"
            )

    elif isinstance(level, int):
        if level not in levels_to_name:
            raise ZincLogLevelError(
                f"Invalid log level: {level}. Must be one of {list(levels_to_name.keys())}"
            )


    processors = [
        structlog.processors.TimeStamper(fmt="iso"),  # Adds timestamp
        structlog.processors.add_log_level,  # Adds log level
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        _source_location,
    ]

    # Select output processors
    if sys.stderr.isatty():
        processors.append(_json_render)
    else:
        processors.extend(
            [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(ensure_ascii=False, sort_keys=True),
            ]
        )

    # Configure structlog to use custom JSON renderer
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set up the root logger to print to stdout
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
