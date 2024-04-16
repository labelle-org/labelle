import os


def is_env_var_true(env_var: str) -> bool:
    val = os.getenv(env_var)
    return val is not None and val.lower() in ("1", "true")


def is_dev_mode_no_margins():
    return is_env_var_true("LABELLE_DEV_MODE_NO_MARGINS")


def is_verbose_env_vars() -> bool:
    return is_env_var_true("LABELLE_VERBOSE")
