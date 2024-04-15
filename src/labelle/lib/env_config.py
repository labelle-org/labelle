import os


def is_env_var_true(env_var: str) -> bool:
    val = os.getenv(env_var)
    return val is not None and val.lower() in ("1", "true")


def is_verbose_env_vars() -> bool:
    return is_env_var_true("DYMOPRINT_VERBOSE")
