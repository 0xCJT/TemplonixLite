import functools
import logging
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Type variables for decorators
F = TypeVar("F", bound=Callable[..., Any])


#############################################################################################
# Provides enhanced error handling and recovery capabilities. 
#############################################################################################
class ErrorHandler:
    def __init__(self) -> None:
        self.logger = logging.getLogger("ErrorHandler")

    # ########################################################################################
    # Decorator that retries a function on failure with exponential backoff.
    # #########################################################################################
    def with_retry(
        self,
        max_retries: int = 3,
        retry_exceptions: tuple = (Exception,),
        backoff_factor: float = 1.5,
    ) -> Callable[[F], F]:
        """
        Args:
            max_retries: Maximum number of retry attempts
            retry_exceptions: Exception types that trigger retries
            backoff_factor: Multiplier for backoff time between retries

        Example:
            @error_handler.with_retry(max_retries=3)
            def process_file(file_path):
                # Implementation that might fail
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                import time

                last_exception: Optional[BaseException] = None
                for attempt in range(max_retries + 1):
                    try:
                        if attempt > 0:
                            self.logger.info(
                                f"Retry attempt {attempt}/{max_retries} for {func.__name__}"
                            )
                        return func(*args, **kwargs)
                    except retry_exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            backoff_time = backoff_factor**attempt
                            self.logger.warning(
                                f"Retry in {backoff_time:.2f}s after error in {func.__name__}: {e}"
                            )
                            time.sleep(backoff_time)
                        else:
                            self.logger.error(
                                f"All {max_retries} retries failed for {func.__name__}"
                            )
                raise cast(BaseException, last_exception)  # Fix for mypy

            return cast(F, wrapper)

        return decorator

    # #########################################################################################
    # Decorator that provides a fallback value when a function fails.
    # #########################################################################################
    def with_fallback(self, fallback_value: Any) -> Callable[[F], F]:
        """
        Args:
            fallback_value: Value to return on failure

        Example:
            @error_handler.with_fallback([])
            def get_items():
                # Implementation that might fail
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.logger.warning(
                        f"Using fallback for {func.__name__} after error: {e}"
                    )
                    return fallback_value

            return cast(F, wrapper)

        return decorator