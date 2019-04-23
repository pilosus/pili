import logging
import pickle
import sys
import time
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

import redis
from flask import _app_ctx_stack, current_app  # type: ignore

from pili.connectors import BaseConnector

#
# Constants
#

try:
    import ujson as json
except ImportError:
    import json  # type: ignore


#
# Connector class
#


class RedisConnector(BaseConnector):
    """
    Redis Connector as extension

    Usage:
      from pili.connectors import RedisConnector

      redis = RedisConnector()
      app = create_app('config.py')
      redis.init_app(app)

      redis.connection.get('mykey')
    """

    def startup(self):
        connection_kwargs = {
            'host': current_app.config.get('REDIS_HOST', 'localhost'),
            'port': current_app.config.get('REDIS_PORT', 6379),
            'db': current_app.config.get('REDIS_DB', 0),
            'password': current_app.config.get('REDIS_PASSWORD', None),
            'socket_timeout': current_app.config.get('REDIS_TIMEOUT', None),
            'socket_connect_timeout': current_app.config.get(
                'REDIS_CONNECT_TIMEOUT', None
            ),
            'socket_keepalive': current_app.config.get('REDIS_KEEPALIVE', False),
            'socket_keepalive_options': current_app.config.get(
                'REDIS_KEEPALIVE_OPTIONS', None
            ),
            'socket_type': current_app.config.get('REDIS_SOCKET_TYPE', 0),
            'retry_on_timeout': current_app.config.get('REDIS_RETRY_ON_TIMEOUT', False),
            'encoding': current_app.config.get('REDIS_RETRY_ENCODING', 'utf-8'),
            'encoding_errors': current_app.config.get(
                'REDIS_ENCODING_ERRORS', 'strict'
            ),
            'decode_responses': current_app.config.get('REDIS_DECODE_RESPONSES', False),
            'socket_read_size': current_app.config.get('REDIS_READ_SIZE', 65536),
        }

        pool = redis.ConnectionPool(**connection_kwargs)
        return redis.Redis(connection_pool=pool)

    def teardown(self, exception):
        context = _app_ctx_stack.top
        connector_name = self.__class__.__name__
        if hasattr(context, connector_name):
            client = getattr(context, connector_name)
            client.connection_pool.disconnect()

    def get_key(self, key: str):
        """
        Helper function to get key

        Having this method, cache decorator can use any connector implementing it,
        e.g. Redis Sentinel with `get_key` looking for a key in a slave node and
        `set_key` setting a key in master.
        """
        return self.connection.get(key)

    def set_key(self, key: str, value: str, expire_seconds: int = 15 * 60):
        """
        Helper function to set key with expiration time
        """
        return self.connection.set(key, value, ex=expire_seconds)


class RedisConnectorError(Exception):
    pass


#
# Helpers
#


class CacheError(Exception):
    pass


class RateLimitExceededError(Exception):
    pass


def _get_function_full_name(func: Callable[..., Any], delimiter: str = ':') -> str:
    return "{module}{delimiter}{name}".format(
        module=func.__module__, delimiter=delimiter, name=func.__qualname__
    )


def timer(
    func: Callable[..., Any],
    alternative_name: str = None,
    logger: Optional[logging.Logger] = None,
) -> Callable[..., Any]:
    """
    Log function execution time
    """
    if logger is None:
        logger = current_app.logger

    def _args_to_str(l: Iterable[Any]) -> str:
        return ', '.join(map(str, l))

    def _kwargs_to_str(d: Mapping[Any, Any]) -> str:
        return ', '.join(['{}={}'.format(k, v) for k, v in d.items()])

    def _inner(*args: List[Any], **kwargs: Dict[Any, Any]) -> Any:
        start_time = time.time_ns()
        result = func(*args, **kwargs)
        delta_ms = round((time.time_ns() - start_time) / 1_000_000)

        func_name = (
            _get_function_full_name(func) if not alternative_name else alternative_name
        )
        func_str = '({func}({pos}{delim}{keyword}))'.format(
            func=func_name,
            pos=_args_to_str(args),
            delim=', ' if args else '',
            keyword=_kwargs_to_str(kwargs),
        )
        result_bytes = sys.getsizeof(result)

        logger.debug(  # type: ignore
            '{func_str} of size {size} bytes '
            'has been loaded from cache in {delta} '
            'milliseconds'.format(size=result_bytes, func_str=func_str, delta=delta_ms)
        )
        return result

    return _inner


def _generate_function_key(
    func: Callable[..., Any],
    prefix: str,
    postfix_func: Optional[Callable[..., Any]] = None,
) -> Callable[..., Any]:
    """
    Generate string representing a callable to be used as a key for key-value storage

    Use prefix and postfix_func with care. Excessive keys may slow down your app!

    Redis naming conventions for keys used (e.g. 'object-type:id'):
    https://redis.io/topics/data-types-intro
    """
    if func.__name__ == (lambda: None).__name__:
        raise ValueError('Cannot generate key for lambda function')

    full_name = "{prefix}:{name}".format(
        prefix=prefix, name=_get_function_full_name(func)
    )

    def _inner(*args, **kwargs):
        if postfix_func is None:
            return full_name
        return "{name}:{postfix}".format(
            name=full_name, postfix=postfix_func(*args, **kwargs)
        )

    return _inner


def cache(
    expire_seconds: int = 15 * 60,
    *,
    connector: Optional[RedisConnector] = None,
    silent: bool = True,
    key_func: Optional[Callable[..., Any]] = None,
    load_func: Callable[..., Any] = json.loads,
    dump_func: Callable[..., Any] = json.dumps,
    logger: Optional[logging.Logger] = None,
) -> Callable[..., Any]:
    """
    Cache decorator
    """
    if connector is None:
        connector = current_app.connectors.redis

    # Get app's default logger if looger is omitted
    if logger is None:
        logger = connector.app.logger  # type: ignore

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        key_generator = _generate_function_key(
            func=func, prefix='cache', postfix_func=key_func
        )

        @wraps(func)
        def _inner(*args, **kwargs) -> Any:
            cache_miss, result = True, None
            cache_key = key_generator(*args, **kwargs)

            if not current_app.config.get('CACHE_DISABLE'):
                try:
                    connector.get_key = timer(  # type: ignore
                        func=connector.get_key,  # type: ignore
                        alternative_name=func.__name__,
                        logger=logger,
                    )
                    result = load_func(connector.get_key(cache_key))  # type: ignore
                    cache_miss = False
                except TypeError:
                    logger.info(
                        'No cache found for key: {}'.format(cache_key)
                    )  # type: ignore
                except ValueError:
                    message = 'Cache cannot be loaded for key: {}'.format(cache_key)
                    logger.exception(message)  # type: ignore
                    if not silent:
                        raise CacheError(message)
                except redis.RedisError:
                    message = 'Redis connection failed while getting key: {}'.format(
                        cache_key
                    )
                    logger.exception(message)  # type: ignore
                    if not silent:
                        raise RedisConnectorError(message)

            if cache_miss:
                result = func(*args, **kwargs)

                try:
                    connector.set_key(
                        cache_key, dump_func(result), expire_seconds
                    )  # type: ignore
                except (ValueError, pickle.PickleError):
                    message = 'Function \'s `{}` result cannot be serialized'.format(
                        func.__name__
                    )
                    logger.exception(message)  # type: ignore
                    if not silent:
                        raise CacheError(message)
                except redis.RedisError:
                    message = 'Redis connection failed while setting key: {}'.format(
                        cache_key
                    )
                    logger.info(message)  # type: ignore
                    if not silent:
                        raise RedisConnectorError(message)
            return result

        return _inner

    return _decorator


def cache_flask_view(
    expire_seconds: int = 15 * 60,
    *,
    connector: Optional[RedisConnector] = None,
    silent: bool = True,
    key_func: Optional[Callable[..., Any]] = None,
    logger: Optional[logging.Logger] = None,
) -> Callable[..., Any]:
    """
    Cache decorator for Flask function-based views
    """
    return cache(
        expire_seconds=expire_seconds,
        connector=connector,
        silent=silent,
        key_func=key_func,
        load_func=pickle.loads,
        dump_func=pickle.dumps,
        logger=logger,
    )


def rate_limit(
    rps: int,
    *,
    connector: Optional[RedisConnector] = None,
    silent: bool = True,
    key_func: Optional[Callable[..., Any]] = None,
    load_func: Callable[..., Any] = json.loads,
    logger: Optional[logging.Logger] = None,
) -> Callable[..., Any]:
    """
    Rate limit decorator
    """
    # Get app's default logger if looger is omitted
    if logger is None:
        logger = connector.app.logger  # type: ignore

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # You may want to specify key_func to get user's ID or IP address
        # in order to set rate limit per user
        # key_func may ignore view's arguments, getting instead either:
        # flask.request.environ['REMOTE_ADDR'] or
        # flask.request.environ['HTTP_X_FORWARDED_FOR']
        # Rate limit keys may look like:
        # "rate-limit:fully-qualified-func-name:user-IP:timestamp-in-seconds"
        key_generator = _generate_function_key(
            func=func, prefix='rate-limit', postfix_func=key_func
        )

        @wraps(func)
        def _inner(*args, **kwargs) -> Any:
            # attach seconds to a key
            cache_key = key_generator(*args, **kwargs)
            current_unix_time = round(time.time())
            cache_key = '{0}:{1}'.format(cache_key, current_unix_time)

            result = None

            try:
                result = load_func(connector.get_key(cache_key))  # type: ignore
            except TypeError:
                # key doesn't exist yet, keep result as is
                pass
            except ValueError:
                message = 'Cache cannot be loaded for key: {}'.format(cache_key)
                logger.exception(message)  # type: ignore
                if not silent:
                    raise CacheError(message)
            except redis.RedisError:
                message = 'Redis connection failed while getting key: {}'.format(
                    cache_key
                )
                logger.exception(message)  # type: ignore
                if not silent:
                    raise RedisConnectorError(message)

            if result and result > rps:
                raise RateLimitExceededError('Rate limit exceeded')

            # increment key and set expiration atomically
            pipe = connector.connection.pipeline()  # type: ignore
            pipe.incr(cache_key, 1)  # increase RPS counter
            pipe.expire(cache_key, 5)  # drop key in 5 seconds
            pipe.execute()

            return func(*args, **kwargs)

        return _inner

    return _decorator
