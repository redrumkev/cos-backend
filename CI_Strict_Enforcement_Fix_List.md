# Strict Ruff CI Enforcement — Guided Fix List

Your task:
1. Use the file `CI_Strict_Enforcement_Fix_List.md` at the project root as your master to-do list.
2. Sequentially work through the files in the list, starting from the top or the last file marked as "in progress."
3. For each file:
    - Open it.
    - Fix all Ruff errors and warnings until it is 100% clean.
    - Mark your progress in the `CI_Strict_Enforcement_Fix_List.md` file as follows:
        - `[FIXED] path/to/file.py` when completed
        - `[IN PROGRESS] path/to/file.py` while working (remove this after finishing)
        - Leave untouched files as plain paths.
4. After each batch of 3–5 files, **exit or pause**, commit changes, and save the updated `CI_Strict_Enforcement_Fix_List.md`.
5. On next run, **re-read the list** and continue from the first file **not yet marked as `[FIXED]`**.

## Special Instructions
- DO NOT touch files not in the list.
- Do NOT “fix” already marked `[FIXED]` files.
- If you run into unclear rules, consult Ruff documentation or insert a TODO in the fix list for manual review.
- If the file can’t be auto-fixed, add `[BLOCKED] path/to/file.py` and a short note in the MD file.

## Example Status Format in `CI_Strict_Enforcement_Fix_List.md`:
[FIXED] scripts/run_performance_tests.py
[FIXED] src/common/base_subscriber.py
[IN PROGRESS] src/common/message_format.py
src/common/pubsub.py
src/common/redis_config.py
...

pgsql
Copy
Edit

## Resume Workflow
- **Each run:** Scan the list, pick up from first non-[FIXED] file, repeat.
- **After large changes:** Save and commit the current progress. The same prompt will always resume correctly.

## Your Next Action
- Begin with the next unmarked or `[IN PROGRESS]` file, fix all Ruff CI issues, and update the markdown list.

---

*This workflow ensures you never lose your place, never re-fix, and always move forward with perfect CI focus. When in doubt, always check `CI_Strict_Enforcement_Fix_List.md` for authoritative state.*

------

List to Fix:
[FIXED] scripts/run_performance_tests.py
[FIXED] src/common/base_subscriber.py
[FIXED] src/common/message_format.py
[FIXED] src/common/pubsub.py
[FIXED] src/common/redis_config.py
src/db/migrations/versions/07f2af238b83_fix_timezone_columns_for_cc_tables.py
tests/backend/cc/test_debug_endpoints_enhanced.py
tests/common/test_base_subscriber.py
tests/common/test_message_format.py
tests/common/test_pubsub.py
tests/common/test_pubsub_circuit_breaker.py
tests/common/test_pubsub_simple.py
tests/common/test_redis_config.py
tests/integration/test_redis_foundation.py
tests/integration/test_redis_performance.py
tests/integration/test_redis_performance_final.py
tests/integration/test_redis_performance_simplified.py
tests/integration/test_redis_resilience.py
tests/performance/__init__.py
tests/performance/conftest.py
tests/performance/test_comprehensive_benchmarks.py
tests/performance/test_failure_scenarios.py
tests/performance/test_performance_metrics.py
tests/performance/test_production_readiness.py
tests/performance/test_redis_benchmarks.py
tests/unit/backend/cc/test_logging_redis_publish.py
tests/unit/backend/cc/test_logging_redis_simple.py
tests/unit/common/conftest.py
tests/unit/common/test_base_subscriber_comprehensive.py
tests/unit/common/test_circuit_breaker.py
tests/unit/common/test_circuit_breaker_edge.py
tests/unit/common/test_coverage_check.py
tests/unit/common/test_enhanced_error_handling.py
tests/unit/common/test_enhanced_redis_pubsub_suite.py
tests/unit/common/test_pubsub_failures.py
tests/unit/common/test_pubsub_performance.py
tests/unit/common/test_redis_config_comprehensive.py
tests/unit/common/test_redis_config_matrix.py
tests/unit/common/test_redis_pubsub_comprehensive.py

-----
<latest_ci_output>
ruff.....................................................................Passed
ruff-format..............................................................Passed
mypy.....................................................................Passed
bandit...................................................................Passed
check for added large files..............................................Passed
check yaml...............................................................Passed
check toml...............................................................Passed
check for merge conflicts................................................Passed
trim trailing whitespace.................................................Passed
fix end of files.........................................................Passed
debug statements (python)................................................Passed
detect private key.......................................................Passed
Running strict quality enforcement for new files...
New files detected - applying strict linting:
scripts/run_performance_tests.py
src/common/base_subscriber.py
src/common/message_format.py
src/common/pubsub.py
src/common/redis_config.py
src/db/migrations/versions/07f2af238b83_fix_timezone_columns_for_cc_tables.py
tests/backend/cc/test_debug_endpoints_enhanced.py
tests/common/test_base_subscriber.py
tests/common/test_message_format.py
tests/common/test_pubsub.py
tests/common/test_pubsub_circuit_breaker.py
tests/common/test_pubsub_simple.py
tests/common/test_redis_config.py
tests/integration/test_redis_foundation.py
tests/integration/test_redis_performance.py
tests/integration/test_redis_performance_final.py
tests/integration/test_redis_performance_simplified.py
tests/integration/test_redis_resilience.py
tests/performance/__init__.py
tests/performance/conftest.py
tests/performance/test_comprehensive_benchmarks.py
tests/performance/test_failure_scenarios.py
tests/performance/test_performance_metrics.py
tests/performance/test_production_readiness.py
tests/performance/test_redis_benchmarks.py
tests/unit/backend/cc/test_logging_redis_publish.py
tests/unit/backend/cc/test_logging_redis_simple.py
tests/unit/common/conftest.py
tests/unit/common/test_base_subscriber_comprehensive.py
tests/unit/common/test_circuit_breaker.py
tests/unit/common/test_circuit_breaker_edge.py
tests/unit/common/test_coverage_check.py
tests/unit/common/test_enhanced_error_handling.py
tests/unit/common/test_enhanced_redis_pubsub_suite.py
tests/unit/common/test_pubsub_failures.py
tests/unit/common/test_pubsub_performance.py
tests/unit/common/test_redis_config_comprehensive.py
tests/unit/common/test_redis_config_matrix.py
tests/unit/common/test_redis_pubsub_comprehensive.py
warning: `incorrect-blank-line-before-class` (D203) and `no-blank-line-before-class` (D211) are incompatible. Ignoring `incorrect-blank-line-before-class`.
warning: `multi-line-summary-first-line` (D212) and `multi-line-summary-second-line` (D213) are incompatible. Ignoring `multi-line-summary-second-line`.
scripts/run_performance_tests.py:8:1: PGH004 Use specific rule codes when using `ruff: noqa`
   |
 6 | """
 7 |
 8 | # ruff: noqa
   | ^^^^^^^^^^^^ PGH004
 9 |
10 | from __future__ import annotations
   |
src/common/base_subscriber.py:1:1: RUF100 [*] Unused `noqa` directive (unused: `I001`)
  |
1 | # ruff: noqa: I001
  | ^^^^^^^^^^^^^^^^^^ RUF100
2 | """Base subscriber for Redis Pub/Sub with async iterator support and reliability features.
  |
  = help: Remove unused `noqa` directive
src/common/base_subscriber.py:35:11: D101 Missing docstring in public class
   |
34 |     # Create a dummy module for type checking
35 |     class DummyAsyncTimeout:
   |           ^^^^^^^^^^^^^^^^^ D101
36 |         @staticmethod
37 |         def timeout(seconds: float) -> object:
   |
src/common/base_subscriber.py:37:13: D102 Missing docstring in public method
   |
35 |     class DummyAsyncTimeout:
36 |         @staticmethod
37 |         def timeout(seconds: float) -> object:
   |             ^^^^^^^ D102
38 |             return None
   |
src/common/base_subscriber.py:37:21: ARG004 Unused static method argument: `seconds`
   |
35 |     class DummyAsyncTimeout:
36 |         @staticmethod
37 |         def timeout(seconds: float) -> object:
   |                     ^^^^^^^ ARG004
38 |             return None
   |
src/common/base_subscriber.py:72:9: PLR0913 Too many arguments in function definition (7 > 5)
   |
70 |     """
71 |
72 |     def __init__(
   |         ^^^^^^^^ PLR0913
73 |         self,
74 |         *,
   |
src/common/base_subscriber.py:158:20: BLE001 Do not catch blind exception: `Exception`
    |
156 |                 result = await self.process_message(message)
157 |                 results.append(result)
158 |             except Exception:
    |                    ^^^^^^^^^ BLE001
159 |                 results.append(False)
160 |         return results
    |
src/common/base_subscriber.py:172:28: G004 Logging statement uses f-string
    |
170 |         """
171 |         if channel in self._channels:
172 |             logger.warning(f"Already consuming from channel '{channel}'")
    |                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
173 |             return
    |
src/common/base_subscriber.py:186:21: G004 Logging statement uses f-string
    |
184 |             self._batch_task = asyncio.create_task(self._batch_processing_loop(), name="batch-processor")
185 |
186 |         logger.info(f"Started consuming from channel '{channel}'")
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
187 |
188 |     async def stop_consuming(self) -> None:
    |
src/common/base_subscriber.py:248:51: ARG005 Unused lambda argument: `t`
    |
246 |                     task = asyncio.create_task(self._handle_single_message(message))
247 |                     # Don't await, let it run in background
248 |                     task.add_done_callback(lambda t: None)
    |                                                   ^ ARG005
249 |
250 |         except asyncio.CancelledError:
    |
src/common/base_subscriber.py:251:26: G004 Logging statement uses f-string
    |
250 |         except asyncio.CancelledError:
251 |             logger.debug(f"Consumer loop for channel '{channel}' was cancelled")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
252 |             raise
253 |         except Exception as e:
    |
src/common/base_subscriber.py:253:16: BLE001 Do not catch blind exception: `Exception`
    |
251 |             logger.debug(f"Consumer loop for channel '{channel}' was cancelled")
252 |             raise
253 |         except Exception as e:
    |                ^^^^^^^^^ BLE001
254 |             logger.error(f"Error in consumer loop for channel '{channel}': {e}")
255 |         finally:
    |
src/common/base_subscriber.py:254:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
252 |             raise
253 |         except Exception as e:
254 |             logger.error(f"Error in consumer loop for channel '{channel}': {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
255 |         finally:
256 |             if channel in self._channels:
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:254:26: G004 Logging statement uses f-string
    |
252 |             raise
253 |         except Exception as e:
254 |             logger.error(f"Error in consumer loop for channel '{channel}': {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
255 |         finally:
256 |             if channel in self._channels:
    |
src/common/base_subscriber.py:272:16: BLE001 Do not catch blind exception: `Exception`
    |
270 |             logger.debug("Batch processing loop was cancelled")
271 |             raise
272 |         except Exception as e:
    |                ^^^^^^^^^ BLE001
273 |             logger.error(f"Error in batch processing loop: {e}")
    |
src/common/base_subscriber.py:273:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
271 |             raise
272 |         except Exception as e:
273 |             logger.error(f"Error in batch processing loop: {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
274 |
275 |     async def _process_batch_buffer(self) -> None:
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:273:26: G004 Logging statement uses f-string
    |
271 |             raise
272 |         except Exception as e:
273 |             logger.error(f"Error in batch processing loop: {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
274 |
275 |     async def _process_batch_buffer(self) -> None:
    |
src/common/base_subscriber.py:286:39: ARG005 Unused lambda argument: `t`
    |
284 |         task = asyncio.create_task(self._handle_message_batch(batch))
285 |         # Don't await, let it run in background
286 |         task.add_done_callback(lambda t: None)
    |                                       ^ ARG005
287 |
288 |     async def _handle_message_batch(self, messages: list[MessageDict]) -> None:
    |
src/common/base_subscriber.py:313:104: COM812 [*] Trailing comma missing
    |
311 |             else:
312 |                 results = await asyncio.wait_for(
313 |                     self._with_circuit_breaker(self.process_batch)(messages), timeout=self._ack_timeout
    |                                                                                                        ^ COM812
314 |                 )
    |
    = help: Add trailing comma
src/common/base_subscriber.py:322:30: G004 Logging statement uses f-string
    |
321 |         except Exception as e:
322 |             logger.exception(f"Error processing message batch: {e}")
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
323 |             # Handle all messages as failed
324 |             for message, processing_key in zip(messages, processing_keys, strict=False):  # type: ignore[assignment]
    |
src/common/base_subscriber.py:322:65: TRY401 Redundant exception object included in `logging.exception` call
    |
321 |         except Exception as e:
322 |             logger.exception(f"Error processing message batch: {e}")
    |                                                                 ^ TRY401
323 |             # Handle all messages as failed
324 |             for message, processing_key in zip(messages, processing_keys, strict=False):  # type: ignore[assignment]
    |
src/common/base_subscriber.py:325:60: FBT003 Boolean positional value in function call
    |
323 |             # Handle all messages as failed
324 |             for message, processing_key in zip(messages, processing_keys, strict=False):  # type: ignore[assignment]
325 |                 await self._handle_message_result(message, False, processing_key)
    |                                                            ^^^^^ FBT003
326 |                 self._failed_count += 1
327 |         finally:
    |
src/common/base_subscriber.py:348:105: COM812 [*] Trailing comma missing
    |
346 |             else:
347 |                 result = await asyncio.wait_for(
348 |                     self._with_circuit_breaker(self.process_message)(message), timeout=self._ack_timeout
    |                                                                                                         ^ COM812
349 |                 )
    |
    = help: Add trailing comma
src/common/base_subscriber.py:355:30: G004 Logging statement uses f-string
    |
354 |         except Exception as e:
355 |             logger.exception(f"Error processing message: {e}", extra={"message": message})
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
356 |             await self._handle_message_result(message, False, processing_key)
357 |             self._failed_count += 1
    |
src/common/base_subscriber.py:355:59: TRY401 Redundant exception object included in `logging.exception` call
    |
354 |         except Exception as e:
355 |             logger.exception(f"Error processing message: {e}", extra={"message": message})
    |                                                           ^ TRY401
356 |             await self._handle_message_result(message, False, processing_key)
357 |             self._failed_count += 1
    |
src/common/base_subscriber.py:355:71: G101 Logging statement uses an `extra` field that clashes with a `LogRecord` field: `message`
    |
354 |         except Exception as e:
355 |             logger.exception(f"Error processing message: {e}", extra={"message": message})
    |                                                                       ^^^^^^^^^ G101
356 |             await self._handle_message_result(message, False, processing_key)
357 |             self._failed_count += 1
    |
src/common/base_subscriber.py:356:56: FBT003 Boolean positional value in function call
    |
354 |         except Exception as e:
355 |             logger.exception(f"Error processing message: {e}", extra={"message": message})
356 |             await self._handle_message_result(message, False, processing_key)
    |                                                        ^^^^^ FBT003
357 |             self._failed_count += 1
358 |         finally:
    |
src/common/base_subscriber.py:361:66: FBT001 Boolean-typed positional argument in function definition
    |
359 |             self._sem.release()
360 |
361 |     async def _handle_message_result(self, message: MessageDict, success: bool, processing_key: str | None) -> None:
    |                                                                  ^^^^^^^ FBT001
362 |         """Handle the result of message processing."""
363 |         if success:
    |
src/common/base_subscriber.py:378:28: SLF001 Private member accessed: `_redis`
    |
376 |         try:
377 |             pubsub = await get_pubsub()
378 |             redis_client = pubsub._redis
    |                            ^^^^^^^^^^^^^ SLF001
379 |             if redis_client:
380 |                 await redis_client.setex(processing_key, self._message_ttl, "1")
    |
src/common/base_subscriber.py:381:13: TRY300 Consider moving this statement to an `else` block
    |
379 |             if redis_client:
380 |                 await redis_client.setex(processing_key, self._message_ttl, "1")
381 |             return processing_key
    |             ^^^^^^^^^^^^^^^^^^^^^ TRY300
382 |         except Exception as e:
383 |             logger.error(f"Failed to set processing state for {message_id}: {e}")
    |
src/common/base_subscriber.py:382:16: BLE001 Do not catch blind exception: `Exception`
    |
380 |                 await redis_client.setex(processing_key, self._message_ttl, "1")
381 |             return processing_key
382 |         except Exception as e:
    |                ^^^^^^^^^ BLE001
383 |             logger.error(f"Failed to set processing state for {message_id}: {e}")
384 |             return processing_key
    |
src/common/base_subscriber.py:383:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
381 |             return processing_key
382 |         except Exception as e:
383 |             logger.error(f"Failed to set processing state for {message_id}: {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
384 |             return processing_key
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:383:26: G004 Logging statement uses f-string
    |
381 |             return processing_key
382 |         except Exception as e:
383 |             logger.error(f"Failed to set processing state for {message_id}: {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
384 |             return processing_key
    |
src/common/base_subscriber.py:390:28: SLF001 Private member accessed: `_redis`
    |
388 |         try:
389 |             pubsub = await get_pubsub()
390 |             redis_client = pubsub._redis
    |                            ^^^^^^^^^^^^^ SLF001
391 |             if redis_client:
392 |                 result = await redis_client.delete(processing_key)
    |
src/common/base_subscriber.py:397:16: BLE001 Do not catch blind exception: `Exception`
    |
395 |                 else:
396 |                     self._ack_failed_count += 1
397 |         except Exception as e:
    |                ^^^^^^^^^ BLE001
398 |             logger.error(f"Failed to acknowledge message {processing_key}: {e}")
399 |             self._ack_failed_count += 1
    |
src/common/base_subscriber.py:398:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
396 |                     self._ack_failed_count += 1
397 |         except Exception as e:
398 |             logger.error(f"Failed to acknowledge message {processing_key}: {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
399 |             self._ack_failed_count += 1
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:398:26: G004 Logging statement uses f-string
    |
396 |                     self._ack_failed_count += 1
397 |         except Exception as e:
398 |             logger.error(f"Failed to acknowledge message {processing_key}: {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
399 |             self._ack_failed_count += 1
    |
src/common/base_subscriber.py:413:20: BLE001 Do not catch blind exception: `Exception`
    |
411 |                 await self._dlq_publish(dlq_message)
412 |                 self._dlq_count += 1
413 |             except Exception as e:
    |                    ^^^^^^^^^ BLE001
414 |                 logger.error(f"Failed to send message to DLQ: {e}", extra={"message": message})
    |
src/common/base_subscriber.py:414:17: TRY400 Use `logging.exception` instead of `logging.error`
    |
412 |                 self._dlq_count += 1
413 |             except Exception as e:
414 |                 logger.error(f"Failed to send message to DLQ: {e}", extra={"message": message})
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
415 |
416 |     def _with_circuit_breaker(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:414:30: G004 Logging statement uses f-string
    |
412 |                 self._dlq_count += 1
413 |             except Exception as e:
414 |                 logger.error(f"Failed to send message to DLQ: {e}", extra={"message": message})
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
415 |
416 |     def _with_circuit_breaker(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    |
src/common/base_subscriber.py:414:76: G101 Logging statement uses an `extra` field that clashes with a `LogRecord` field: `message`
    |
412 |                 self._dlq_count += 1
413 |             except Exception as e:
414 |                 logger.error(f"Failed to send message to DLQ: {e}", extra={"message": message})
    |                                                                            ^^^^^^^^^ G101
415 |
416 |     def _with_circuit_breaker(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    |
src/common/base_subscriber.py:421:34: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `*args`
    |
419 |             return func
420 |
421 |         async def wrapper(*args: Any, **kwargs: Any) -> Any:
    |                                  ^^^ ANN401
422 |             # We know _circuit_breaker is not None due to the check above
423 |             return await self._circuit_breaker.call(func, *args, **kwargs)  # type: ignore
    |
src/common/base_subscriber.py:421:49: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `**kwargs`
    |
419 |             return func
420 |
421 |         async def wrapper(*args: Any, **kwargs: Any) -> Any:
    |                                                 ^^^ ANN401
422 |             # We know _circuit_breaker is not None due to the check above
423 |             return await self._circuit_breaker.call(func, *args, **kwargs)  # type: ignore
    |
src/common/base_subscriber.py:421:57: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `wrapper`
    |
419 |             return func
420 |
421 |         async def wrapper(*args: Any, **kwargs: Any) -> Any:
    |                                                         ^^^ ANN401
422 |             # We know _circuit_breaker is not None due to the check above
423 |             return await self._circuit_breaker.call(func, *args, **kwargs)  # type: ignore
    |
src/common/base_subscriber.py:423:77: PGH003 Use specific rule codes when ignoring type issues
    |
421 |         async def wrapper(*args: Any, **kwargs: Any) -> Any:
422 |             # We know _circuit_breaker is not None due to the check above
423 |             return await self._circuit_breaker.call(func, *args, **kwargs)  # type: ignore
    |                                                                             ^^^^^^^^^^^^^^ PGH003
424 |
425 |         return wrapper
    |
src/common/base_subscriber.py:483:31: ARG001 Unused function argument: `ch`
    |
481 |     message_queue: asyncio.Queue[MessageDict] = asyncio.Queue()
482 |
483 |     async def message_handler(ch: str, message: MessageDict) -> None:
    |                               ^^ ARG001
484 |         """Put messages in the queue."""
485 |         await message_queue.put(message)
    |
src/common/base_subscriber.py:504:30: G004 Logging statement uses f-string
    |
502 |             except TimeoutError:
503 |                 # Timeout reached with no messages - exit gracefully
504 |                 logger.debug(f"No messages received on channel '{channel}' for {max_idle_time}s, exiting iterator")
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
505 |                 break
506 |             except Exception as e:
    |
src/common/base_subscriber.py:506:20: BLE001 Do not catch blind exception: `Exception`
    |
504 |                 logger.debug(f"No messages received on channel '{channel}' for {max_idle_time}s, exiting iterator")
505 |                 break
506 |             except Exception as e:
    |                    ^^^^^^^^^ BLE001
507 |                 # Other errors - log and exit gracefully
508 |                 logger.error(f"Error in subscribe_to_channel for '{channel}': {e}")
    |
src/common/base_subscriber.py:508:17: TRY400 Use `logging.exception` instead of `logging.error`
    |
506 |             except Exception as e:
507 |                 # Other errors - log and exit gracefully
508 |                 logger.error(f"Error in subscribe_to_channel for '{channel}': {e}")
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
509 |                 break
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:508:30: G004 Logging statement uses f-string
    |
506 |             except Exception as e:
507 |                 # Other errors - log and exit gracefully
508 |                 logger.error(f"Error in subscribe_to_channel for '{channel}': {e}")
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
509 |                 break
    |
src/common/base_subscriber.py:516:26: G004 Logging statement uses f-string
    |
514 |         try:
515 |             await pubsub.unsubscribe(channel, message_handler)
516 |             logger.debug(f"Unsubscribed from channel '{channel}'")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
517 |         except Exception as e:
518 |             logger.error(f"Error during unsubscribe from '{channel}': {e}")
    |
src/common/base_subscriber.py:517:16: BLE001 Do not catch blind exception: `Exception`
    |
515 |             await pubsub.unsubscribe(channel, message_handler)
516 |             logger.debug(f"Unsubscribed from channel '{channel}'")
517 |         except Exception as e:
    |                ^^^^^^^^^ BLE001
518 |             logger.error(f"Error during unsubscribe from '{channel}': {e}")
    |
src/common/base_subscriber.py:518:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
516 |             logger.debug(f"Unsubscribed from channel '{channel}'")
517 |         except Exception as e:
518 |             logger.error(f"Error during unsubscribe from '{channel}': {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
    |
    = help: Replace with `exception`
src/common/base_subscriber.py:518:26: G004 Logging statement uses f-string
    |
516 |             logger.debug(f"Unsubscribed from channel '{channel}'")
517 |         except Exception as e:
518 |             logger.error(f"Error during unsubscribe from '{channel}': {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
    |
src/common/base_subscriber.py:546:17: G004 Logging statement uses f-string
    |
544 |     await pubsub.publish(dlq_channel, dlq_message)
545 |
546 |     logger.info(f"Published message to DLQ channel '{dlq_channel}'")
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
    |
src/common/message_format.py:89:41: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `**kwargs`
   |
87 |     }
88 |
89 |     def model_dump_json(self, **kwargs: Any) -> str:
   |                                         ^^^ ANN401
90 |         """Serialize to JSON string with optimal performance.
   |
src/common/message_format.py:111:9: RET505 [*] Unnecessary `else` after `return` statement
    |
109 |             json_bytes: bytes = orjson.dumps(data)
110 |             return json_bytes.decode("utf-8")
111 |         else:
    |         ^^^^ RET505
112 |             # Fall back to Pydantic's standard serialization
113 |             return super().model_dump_json(by_alias=True, **kwargs)
    |
    = help: Remove unnecessary `else`
src/common/message_format.py:116:5: PLR0913 Too many arguments in function definition (7 > 5)
    |
116 | def build_message(
    |     ^^^^^^^^^^^^^ PLR0913
117 |     *,
118 |     base_log_id: uuid.UUID,
    |
src/common/pubsub.py:30:5: TC005 [*] Found empty type-checking block
   |
28 | if TYPE_CHECKING:
29 |     # These imports are only for type checking and won't be resolved by linter
30 |     pass
   |     ^^^^ TC005
31 |
32 | logger = logging.getLogger(__name__)
   |
   = help: Delete empty type-checking block
src/common/pubsub.py:64:30: FBT001 Boolean-typed positional argument in function definition
   |
62 |     circuit_breaker_state: str | None = None
63 |
64 |     def mark_completed(self, success: bool = True, error: Exception | None = None) -> None:
   |                              ^^^^^^^ FBT001
65 |         """Mark operation as completed and calculate duration."""
66 |         self.duration_ms = (time.perf_counter() - self.start_time) * 1000
   |
src/common/pubsub.py:64:30: FBT002 Boolean default positional argument in function definition
   |
62 |     circuit_breaker_state: str | None = None
63 |
64 |     def mark_completed(self, success: bool = True, error: Exception | None = None) -> None:
   |                              ^^^^^^^ FBT002
65 |         """Mark operation as completed and calculate duration."""
66 |         self.duration_ms = (time.perf_counter() - self.start_time) * 1000
   |
src/common/pubsub.py:217:9: RET505 [*] Unnecessary `elif` after `return` statement
    |
215 |         if self._state == CircuitBreakerState.CLOSED:
216 |             return True
217 |         elif self._state == CircuitBreakerState.OPEN:
    |         ^^^^ RET505
218 |             # Check if recovery timeout has elapsed
219 |             if self._next_attempt_time is not None and current_time >= self._next_attempt_time:
    |
    = help: Remove unnecessary `elif`
src/common/pubsub.py:248:17: G004 Logging statement uses f-string
    |
247 |               logger.warning(
248 | /                 f"Circuit breaker opened after {self._failure_count} failures. "
249 | |                 f"Next attempt at {self._next_attempt_time}"
    | |____________________________________________________________^ G004
250 |               )
    |
src/common/pubsub.py:249:61: COM812 [*] Trailing comma missing
    |
247 |             logger.warning(
248 |                 f"Circuit breaker opened after {self._failure_count} failures. "
249 |                 f"Next attempt at {self._next_attempt_time}"
    |                                                             ^ COM812
250 |             )
    |
    = help: Add trailing comma
src/common/pubsub.py:316:70: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `*args`
    |
314 |             )
315 |
316 |     async def call(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    |                                                                      ^^^ ANN401
317 |         """Execute a function with circuit breaker protection.
    |
src/common/pubsub.py:316:85: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `**kwargs`
    |
314 |             )
315 |
316 |     async def call(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    |                                                                                     ^^^ ANN401
317 |         """Execute a function with circuit breaker protection.
    |
src/common/pubsub.py:316:93: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `call`
    |
314 |             )
315 |
316 |     async def call(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    |                                                                                             ^^^ ANN401
317 |         """Execute a function with circuit breaker protection.
    |
src/common/pubsub.py:338:23: TRY003 Avoid specifying long messages outside the exception class
    |
336 |               # Check if request can be attempted
337 |               if not await self._can_attempt_request():
338 |                   raise CircuitBreakerError(
    |  _______________________^
339 | |                     f"Circuit breaker is {self._state.value}. Next attempt at {self._next_attempt_time}"
340 | |                 )
    | |_________________^ TRY003
341 |
342 |           try:
    |
src/common/pubsub.py:339:21: EM102 Exception must not use an f-string literal, assign to variable first
    |
337 |             if not await self._can_attempt_request():
338 |                 raise CircuitBreakerError(
339 |                     f"Circuit breaker is {self._state.value}. Next attempt at {self._next_attempt_time}"
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
340 |                 )
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:339:105: COM812 [*] Trailing comma missing
    |
337 |             if not await self._can_attempt_request():
338 |                 raise CircuitBreakerError(
339 |                     f"Circuit breaker is {self._state.value}. Next attempt at {self._next_attempt_time}"
    |                                                                                                         ^ COM812
340 |                 )
    |
    = help: Add trailing comma
src/common/pubsub.py:350:13: TRY300 Consider moving this statement to an `else` block
    |
348 |                 await self._record_success()
349 |
350 |             return result
    |             ^^^^^^^^^^^^^ TRY300
351 |
352 |         except self.expected_exception:
    |
src/common/pubsub.py:392:19: TRY003 Avoid specifying long messages outside the exception class
    |
390 |         """Initialize Redis Pub/Sub client with optimized connection pool and circuit breaker."""
391 |         if not _REDIS_AVAILABLE:
392 |             raise PubSubError("Redis package is required for pub/sub functionality. Install with: pip install redis")
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
393 |
394 |         self._config = get_redis_config()
    |
src/common/pubsub.py:392:31: EM101 Exception must not use a string literal, assign to variable first
    |
390 |         """Initialize Redis Pub/Sub client with optimized connection pool and circuit breaker."""
391 |         if not _REDIS_AVAILABLE:
392 |             raise PubSubError("Redis package is required for pub/sub functionality. Install with: pip install redis")
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM101
393 |
394 |         self._config = get_redis_config()
    |
    = help: Assign to variable; remove string literal
src/common/pubsub.py:418:19: TRY003 Avoid specifying long messages outside the exception class
    |
417 |         if not _REDIS_AVAILABLE:
418 |             raise PubSubError("Redis package is required for connection")
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
419 |
420 |         async def _connect_operation() -> None:
    |
src/common/pubsub.py:418:31: EM101 Exception must not use a string literal, assign to variable first
    |
417 |         if not _REDIS_AVAILABLE:
418 |             raise PubSubError("Redis package is required for connection")
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM101
419 |
420 |         async def _connect_operation() -> None:
    |
    = help: Assign to variable; remove string literal
src/common/pubsub.py:422:13: S101 Use of `assert` detected
    |
420 |         async def _connect_operation() -> None:
421 |             # Create optimized connection pool
422 |             assert ConnectionPool is not None, "Redis ConnectionPool not available"  # nosec B101
    |             ^^^^^^ S101
423 |             redis_url_str = self._config.redis_url
424 |             self._pool = ConnectionPool.from_url(
    |
src/common/pubsub.py:437:13: S101 Use of `assert` detected
    |
435 |             )
436 |
437 |             assert redis is not None, "Redis client not available"  # nosec B101
    |             ^^^^^^ S101
438 |             self._redis = redis.Redis(
439 |                 connection_pool=self._pool,
    |
src/common/pubsub.py:444:13: S101 Use of `assert` detected
    |
443 |             # Test connection
444 |             assert self._redis is not None  # mypy assertion  # nosec B101  # nosec B101
    |             ^^^^^^ S101
445 |             await self._redis.ping()
    |
src/common/pubsub.py:454:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
453 |         except CircuitBreakerError as e:
454 |             logger.error(f"Circuit breaker prevented Redis connection: {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
455 |             raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
456 |         except RedisError as e:
    |
    = help: Replace with `exception`
src/common/pubsub.py:454:26: G004 Logging statement uses f-string
    |
453 |         except CircuitBreakerError as e:
454 |             logger.error(f"Circuit breaker prevented Redis connection: {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
455 |             raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
456 |         except RedisError as e:
    |
src/common/pubsub.py:455:19: TRY003 Avoid specifying long messages outside the exception class
    |
453 |         except CircuitBreakerError as e:
454 |             logger.error(f"Circuit breaker prevented Redis connection: {e}")
455 |             raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
456 |         except RedisError as e:
457 |             logger.error(f"Failed to connect to Redis: {e}")
    |
src/common/pubsub.py:455:31: EM102 Exception must not use an f-string literal, assign to variable first
    |
453 |         except CircuitBreakerError as e:
454 |             logger.error(f"Circuit breaker prevented Redis connection: {e}")
455 |             raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
456 |         except RedisError as e:
457 |             logger.error(f"Failed to connect to Redis: {e}")
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:457:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
455 |             raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
456 |         except RedisError as e:
457 |             logger.error(f"Failed to connect to Redis: {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
458 |             raise PubSubError(f"Redis connection failed: {e}") from e
    |
    = help: Replace with `exception`
src/common/pubsub.py:457:26: G004 Logging statement uses f-string
    |
455 |             raise PubSubError(f"Redis connection blocked by circuit breaker: {e}") from e
456 |         except RedisError as e:
457 |             logger.error(f"Failed to connect to Redis: {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
458 |             raise PubSubError(f"Redis connection failed: {e}") from e
    |
src/common/pubsub.py:458:19: TRY003 Avoid specifying long messages outside the exception class
    |
456 |         except RedisError as e:
457 |             logger.error(f"Failed to connect to Redis: {e}")
458 |             raise PubSubError(f"Redis connection failed: {e}") from e
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
459 |
460 |     async def disconnect(self) -> None:
    |
src/common/pubsub.py:458:31: EM102 Exception must not use an f-string literal, assign to variable first
    |
456 |         except RedisError as e:
457 |             logger.error(f"Failed to connect to Redis: {e}")
458 |             raise PubSubError(f"Redis connection failed: {e}") from e
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
459 |
460 |     async def disconnect(self) -> None:
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:493:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
492 |         except RedisError as e:
493 |             logger.error(f"Error during Redis disconnect: {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
494 |
495 |     async def publish(self, channel: str, message: MessageData, correlation_id: str | None = None) -> int:
    |
    = help: Replace with `exception`
src/common/pubsub.py:493:26: G004 Logging statement uses f-string
    |
492 |         except RedisError as e:
493 |             logger.error(f"Error during Redis disconnect: {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
494 |
495 |     async def publish(self, channel: str, message: MessageData, correlation_id: str | None = None) -> int:
    |
src/common/pubsub.py:495:15: C901 `publish` is too complex (16 > 10)
    |
493 |             logger.error(f"Error during Redis disconnect: {e}")
494 |
495 |     async def publish(self, channel: str, message: MessageData, correlation_id: str | None = None) -> int:
    |               ^^^^^^^ C901
496 |         """Publish message to Redis channel with <1ms latency target and comprehensive observability.
    |
src/common/pubsub.py:495:15: PLR0912 Too many branches (13 > 12)
    |
493 |             logger.error(f"Error during Redis disconnect: {e}")
494 |
495 |     async def publish(self, channel: str, message: MessageData, correlation_id: str | None = None) -> int:
    |               ^^^^^^^ PLR0912
496 |         """Publish message to Redis channel with <1ms latency target and comprehensive observability.
    |
src/common/pubsub.py:495:15: PLR0915 Too many statements (69 > 50)
    |
493 |             logger.error(f"Error during Redis disconnect: {e}")
494 |
495 |     async def publish(self, channel: str, message: MessageData, correlation_id: str | None = None) -> int:
    |               ^^^^^^^ PLR0915
496 |         """Publish message to Redis channel with <1ms latency target and comprehensive observability.
    |
src/common/pubsub.py:530:95: COM812 [*] Trailing comma missing
    |
528 |         if _LOGFIRE_AVAILABLE:
529 |             span_context: Any = logfire.span(
530 |                 span_name, channel=channel, correlation_id=correlation_id, operation="publish"
    |                                                                                               ^ COM812
531 |             )
532 |         else:
    |
    = help: Add trailing comma
src/common/pubsub.py:540:17: S101 Use of `assert` detected
    |
538 |                     await self.connect()
539 |
540 |                 assert self._redis is not None  # mypy assertion  # nosec B101
    |                 ^^^^^^ S101
541 |
542 |                 # Pre-serialize JSON for performance
    |
src/common/pubsub.py:548:21: TRY400 Use `logging.exception` instead of `logging.error`
    |
546 |                 except (json.JSONDecodeError, TypeError) as e:
547 |                     error_msg = f"Failed to serialize message for channel '{channel}': {e}"
548 |                     logger.error(error_msg)
    |                     ^^^^^^^^^^^^^^^^^^^^^^^ TRY400
549 |                     metrics.mark_completed(success=False, error=e)
    |
    = help: Replace with `exception`
src/common/pubsub.py:556:27: TRY003 Avoid specifying long messages outside the exception class
    |
554 |                         logfire.error("Message serialization failed", extra=metrics.to_dict())
555 |
556 |                     raise PublishError(f"Failed to serialize message: {e}") from e
    |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
557 |
558 |                 async def _publish_operation() -> int:
    |
src/common/pubsub.py:556:40: EM102 Exception must not use an f-string literal, assign to variable first
    |
554 |                         logfire.error("Message serialization failed", extra=metrics.to_dict())
555 |
556 |                     raise PublishError(f"Failed to serialize message: {e}") from e
    |                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
557 |
558 |                 async def _publish_operation() -> int:
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:569:40: G004 Logging statement uses f-string
    |
567 |                     # Log performance warning if >1ms
568 |                     if elapsed > 1.0:
569 |                         logger.warning(f"Publish latency {elapsed:.2f}ms exceeded 1ms target for channel '{channel}'")
    |                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
570 |                         if _LOGFIRE_AVAILABLE:
571 |                             logfire.warning(
    |
src/common/pubsub.py:579:34: G004 Logging statement uses f-string
    |
577 |                             )
578 |
579 |                     logger.debug(f"Published to '{channel}' in {elapsed:.3f}ms, {result} subscribers")
    |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
580 |                     return int(result)
    |
src/common/pubsub.py:597:17: TRY400 Use `logging.exception` instead of `logging.error`
    |
595 |             except CircuitBreakerError as e:
596 |                 error_msg = f"Circuit breaker prevented publish to channel '{channel}': {e}"
597 |                 logger.error(error_msg)
    |                 ^^^^^^^^^^^^^^^^^^^^^^^ TRY400
598 |                 metrics.mark_completed(success=False, error=e)
    |
    = help: Replace with `exception`
src/common/pubsub.py:605:23: TRY003 Avoid specifying long messages outside the exception class
    |
603 |                     logfire.error("Publish blocked by circuit breaker", extra=metrics.to_dict())
604 |
605 |                 raise PublishError(f"Publish blocked by circuit breaker: {e}") from e
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
606 |
607 |             except RedisError as e:
    |
src/common/pubsub.py:605:36: EM102 Exception must not use an f-string literal, assign to variable first
    |
603 |                     logfire.error("Publish blocked by circuit breaker", extra=metrics.to_dict())
604 |
605 |                 raise PublishError(f"Publish blocked by circuit breaker: {e}") from e
    |                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
606 |
607 |             except RedisError as e:
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:609:17: TRY400 Use `logging.exception` instead of `logging.error`
    |
607 |             except RedisError as e:
608 |                 error_msg = f"Failed to publish to channel '{channel}': {e}"
609 |                 logger.error(error_msg)
    |                 ^^^^^^^^^^^^^^^^^^^^^^^ TRY400
610 |                 metrics.mark_completed(success=False, error=e)
    |
    = help: Replace with `exception`
src/common/pubsub.py:617:23: TRY003 Avoid specifying long messages outside the exception class
    |
615 |                     logfire.error("Redis publish operation failed", extra=metrics.to_dict())
616 |
617 |                 raise PublishError(f"Failed to publish message: {e}") from e
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
618 |
619 |             except Exception as e:
    |
src/common/pubsub.py:617:36: EM102 Exception must not use an f-string literal, assign to variable first
    |
615 |                     logfire.error("Redis publish operation failed", extra=metrics.to_dict())
616 |
617 |                 raise PublishError(f"Failed to publish message: {e}") from e
    |                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
618 |
619 |             except Exception as e:
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:622:17: TRY400 Use `logging.exception` instead of `logging.error`
    |
620 |                 # Handle unexpected errors
621 |                 error_msg = f"Unexpected error publishing to channel '{channel}': {e}"
622 |                 logger.error(error_msg)
    |                 ^^^^^^^^^^^^^^^^^^^^^^^ TRY400
623 |                 metrics.mark_completed(success=False, error=e)
    |
    = help: Replace with `exception`
src/common/pubsub.py:630:23: TRY003 Avoid specifying long messages outside the exception class
    |
628 |                     logfire.error("Unexpected publish error", extra=metrics.to_dict())
629 |
630 |                 raise PublishError(f"Unexpected publish error: {e}") from e
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY003
631 |
632 |     async def subscribe(self, channel: str, handler: MessageHandler) -> None:
    |
src/common/pubsub.py:630:36: EM102 Exception must not use an f-string literal, assign to variable first
    |
628 |                     logfire.error("Unexpected publish error", extra=metrics.to_dict())
629 |
630 |                 raise PublishError(f"Unexpected publish error: {e}") from e
    |                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EM102
631 |
632 |     async def subscribe(self, channel: str, handler: MessageHandler) -> None:
    |
    = help: Assign to variable; remove f-string literal
src/common/pubsub.py:648:9: S101 Use of `assert` detected
    |
646 |             await self.connect()
647 |
648 |         assert self._redis is not None  # mypy assertion  # nosec B101
    |         ^^^^^^ S101
649 |         try:
650 |             # Initialize pubsub if needed
    |
src/common/pubsub.py:661:17: S101 Use of `assert` detected
    |
659 |             # Subscribe to channel if not already subscribed
660 |             if channel not in self._subscribers:
661 |                 assert self._pubsub is not None  # mypy assertion  # nosec B101
    |                 ^^^^^^ S101
662 |                 await self._pubsub.subscribe(channel)
663 |                 self._subscribers.add(channel)
    |
src/common/pubsub.py:664:29: G004 Logging statement uses f-string
    |
662 |                 await self._pubsub.subscribe(channel)
663 |                 self._subscribers.add(channel)
664 |                 logger.info(f"Subscribed to channel '{channel}'")
    |                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
665 |
666 |             # Start listening task if not already running
    |
src/common/pubsub.py:671:13: TRY400 Use `logging.exception` instead of `logging.error`
    |
670 |         except RedisError as e:
671 |             logger.error(f"Failed to subscribe to channel '{channel}': {e}")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TRY400
672 |             raise SubscribeError(f"Failed to subscribe: {e}") from e
    |
    = help: Replace with `exception`
src/common/pubsub.py:671:26: G004 Logging statement uses f-string
    |
670 |         except RedisError as e:
671 |             logger.error(f"Failed to subscribe to channel '{channel}': {e}")
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ G004
672 |             raise SubscribeError(f"Failed to subscribe: {e}") from e
    |
tests/unit/common/test_redis_config_matrix.py:209:9: S101 Use of `assert` detected
    |
208 |         assert config.redis_max_connections == int(max_conn)
209 |         assert config.redis_socket_connect_timeout == int(conn_timeout)
    |         ^^^^^^ S101
210 |
211 |         # Test boolean conversion (Pydantic handles this automatically)
    |
tests/unit/common/test_redis_config_matrix.py:215:9: S101 Use of `assert` detected
    |
213 |         expected_retry = retry.lower() in ("true", "1", "yes", "on")
214 |
215 |         assert config.redis_socket_keepalive == expected_keepalive
    |         ^^^^^^ S101
216 |         assert config.redis_retry_on_timeout == expected_retry
217 |         assert config.redis_health_check_interval == int(health_interval)
    |
tests/unit/common/test_redis_config_matrix.py:216:9: S101 Use of `assert` detected
    |
215 |         assert config.redis_socket_keepalive == expected_keepalive
216 |         assert config.redis_retry_on_timeout == expected_retry
    |         ^^^^^^ S101
217 |         assert config.redis_health_check_interval == int(health_interval)
    |
tests/unit/common/test_redis_config_matrix.py:217:9: S101 Use of `assert` detected
    |
215 |         assert config.redis_socket_keepalive == expected_keepalive
216 |         assert config.redis_retry_on_timeout == expected_retry
217 |         assert config.redis_health_check_interval == int(health_interval)
    |         ^^^^^^ S101
218 |
219 |     async def test_invalid_configuration_handling(
    |
tests/unit/common/test_redis_config_matrix.py:221:9: ARG002 Unused method argument: `clean_env`
    |
219 |     async def test_invalid_configuration_handling(
220 |         self,
221 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
222 |         monkeypatch: Any,
223 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:222:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
220 |         self,
221 |         clean_env: None,
222 |         monkeypatch: Any,
    |                      ^^^ ANN401
223 |     ) -> None:
224 |         """Test handling of invalid configuration values."""
    |
tests/unit/common/test_redis_config_matrix.py:241:9: ARG002 Unused method argument: `clean_env`
    |
239 |     async def test_configuration_caching_and_reload(
240 |         self,
241 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
242 |         monkeypatch: Any,
243 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:242:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
240 |         self,
241 |         clean_env: None,
242 |         monkeypatch: Any,
    |                      ^^^ ANN401
243 |     ) -> None:
244 |         """Test that configuration caching and reloading works correctly."""
    |
tests/unit/common/test_redis_config_matrix.py:250:9: S101 Use of `assert` detected
    |
249 |         config1 = get_redis_config()
250 |         assert "initial-host" in config1.redis_url
    |         ^^^^^^ S101
251 |
252 |         # Change environment (simulating runtime config change)
    |
tests/unit/common/test_redis_config_matrix.py:257:9: S101 Use of `assert` detected
    |
255 |         # Should get cached version first
256 |         config2 = get_redis_config()
257 |         assert config2 is config1  # Same object reference
    |         ^^^^^^ S101
258 |
259 |         # Force reload by clearing cache
    |
tests/unit/common/test_redis_config_matrix.py:262:9: S101 Use of `assert` detected
    |
260 |         get_redis_config.cache_clear()
261 |         config3 = get_redis_config()
262 |         assert "updated-host" in config3.redis_url
    |         ^^^^^^ S101
263 |
264 |     @pytest.mark.parametrize(
    |
tests/unit/common/test_redis_config_matrix.py:265:9: PT006 Wrong type passed to first argument of `pytest.mark.parametrize`; expected `tuple`
    |
264 |     @pytest.mark.parametrize(
265 |         "missing_vars,expected_fallbacks",
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ PT006
266 |         [
267 |             (["REDIS_HOST"], {"host": "localhost"}),
    |
    = help: Use a `tuple` for the first argument
tests/unit/common/test_redis_config_matrix.py:276:9: ARG002 Unused method argument: `clean_env`
    |
274 |     async def test_fallback_behavior(
275 |         self,
276 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
277 |         monkeypatch: Any,
278 |         missing_vars: list[str],
    |
tests/unit/common/test_redis_config_matrix.py:277:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
275 |         self,
276 |         clean_env: None,
277 |         monkeypatch: Any,
    |                      ^^^ ANN401
278 |         missing_vars: list[str],
279 |         expected_fallbacks: dict[str, Any],
    |
tests/unit/common/test_redis_config_matrix.py:291:9: PLC0206 Extracting value from dictionary without calling `.items()`
    |
290 |           # Remove specific variables to test fallbacks
291 | /         for var in base_vars:
292 | |             if var not in missing_vars:
293 | |                 monkeypatch.setenv(var, base_vars[var])
    | |_______________________________________________________^ PLC0206
294 |
295 |           config = get_redis_config()
    |
tests/unit/common/test_redis_config_matrix.py:300:13: S101 Use of `assert` detected
    |
298 |         # Verify fallbacks are applied
299 |         if "host" in expected_fallbacks:
300 |             assert expected_fallbacks["host"] in redis_url
    |             ^^^^^^ S101
301 |         if "port" in expected_fallbacks:
302 |             assert str(expected_fallbacks["port"]) in redis_url
    |
tests/unit/common/test_redis_config_matrix.py:302:13: S101 Use of `assert` detected
    |
300 |             assert expected_fallbacks["host"] in redis_url
301 |         if "port" in expected_fallbacks:
302 |             assert str(expected_fallbacks["port"]) in redis_url
    |             ^^^^^^ S101
303 |         if expected_fallbacks.get("password") is None:
304 |             assert "@" not in redis_url or ":@" in redis_url
    |
tests/unit/common/test_redis_config_matrix.py:304:13: S101 Use of `assert` detected
    |
302 |             assert str(expected_fallbacks["port"]) in redis_url
303 |         if expected_fallbacks.get("password") is None:
304 |             assert "@" not in redis_url or ":@" in redis_url
    |             ^^^^^^ S101
305 |         if "db" in expected_fallbacks and expected_fallbacks["db"] == 0:
306 |             assert redis_url.endswith(":6379/0") or not redis_url.endswith("/1")
    |
tests/unit/common/test_redis_config_matrix.py:306:13: S101 Use of `assert` detected
    |
304 |             assert "@" not in redis_url or ":@" in redis_url
305 |         if "db" in expected_fallbacks and expected_fallbacks["db"] == 0:
306 |             assert redis_url.endswith(":6379/0") or not redis_url.endswith("/1")
    |             ^^^^^^ S101
    |
tests/unit/common/test_redis_config_matrix.py:319:9: ARG002 Unused method argument: `clean_env`
    |
317 |     async def test_docker_compose_service_discovery(
318 |         self,
319 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
320 |         monkeypatch: Any,
321 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:320:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
318 |         self,
319 |         clean_env: None,
320 |         monkeypatch: Any,
    |                      ^^^ ANN401
321 |     ) -> None:
322 |         """Test Redis configuration using Docker Compose service names."""
    |
tests/unit/common/test_redis_config_matrix.py:329:9: S101 Use of `assert` detected
    |
328 |         config = get_redis_config()
329 |         assert config.redis_url == "redis://redis:6379/0"
    |         ^^^^^^ S101
330 |
331 |         # Should use development defaults for connection pooling
    |
tests/unit/common/test_redis_config_matrix.py:332:9: S101 Use of `assert` detected
    |
331 |         # Should use development defaults for connection pooling
332 |         assert config.redis_max_connections == 10
    |         ^^^^^^ S101
333 |
334 |     async def test_kubernetes_environment_variables(
    |
tests/unit/common/test_redis_config_matrix.py:332:48: PLR2004 Magic value used in comparison, consider replacing `10` with a constant variable
    |
331 |         # Should use development defaults for connection pooling
332 |         assert config.redis_max_connections == 10
    |                                                ^^ PLR2004
333 |
334 |     async def test_kubernetes_environment_variables(
    |
tests/unit/common/test_redis_config_matrix.py:336:9: ARG002 Unused method argument: `clean_env`
    |
334 |     async def test_kubernetes_environment_variables(
335 |         self,
336 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
337 |         monkeypatch: Any,
338 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:337:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
335 |         self,
336 |         clean_env: None,
337 |         monkeypatch: Any,
    |                      ^^^ ANN401
338 |     ) -> None:
339 |         """Test Redis configuration with Kubernetes-style environment variables."""
    |
tests/unit/common/test_redis_config_matrix.py:353:9: S101 Use of `assert` detected
    |
352 |         config = get_redis_config()
353 |         assert config.redis_url == "redis://10.96.0.100:6379/0"
    |         ^^^^^^ S101
354 |         assert config.redis_max_connections == 20  # Production defaults
    |
tests/unit/common/test_redis_config_matrix.py:354:9: S101 Use of `assert` detected
    |
352 |         config = get_redis_config()
353 |         assert config.redis_url == "redis://10.96.0.100:6379/0"
354 |         assert config.redis_max_connections == 20  # Production defaults
    |         ^^^^^^ S101
355 |
356 |     async def test_cloud_provider_configurations(
    |
tests/unit/common/test_redis_config_matrix.py:354:48: PLR2004 Magic value used in comparison, consider replacing `20` with a constant variable
    |
352 |         config = get_redis_config()
353 |         assert config.redis_url == "redis://10.96.0.100:6379/0"
354 |         assert config.redis_max_connections == 20  # Production defaults
    |                                                ^^ PLR2004
355 |
356 |     async def test_cloud_provider_configurations(
    |
tests/unit/common/test_redis_config_matrix.py:358:9: ARG002 Unused method argument: `clean_env`
    |
356 |     async def test_cloud_provider_configurations(
357 |         self,
358 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
359 |         monkeypatch: Any,
360 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:359:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
357 |         self,
358 |         clean_env: None,
359 |         monkeypatch: Any,
    |                      ^^^ ANN401
360 |     ) -> None:
361 |         """Test Redis configuration for various cloud providers."""
    |
tests/unit/common/test_redis_config_matrix.py:392:13: S101 Use of `assert` detected
    |
391 |             config = get_redis_config()
392 |             assert config.redis_url == cloud_config["url"]
    |             ^^^^^^ S101
393 |
394 |             # Should use production settings for cloud environments
    |
tests/unit/common/test_redis_config_matrix.py:395:13: S101 Use of `assert` detected
    |
394 |             # Should use production settings for cloud environments
395 |             assert config.redis_max_connections >= 20
    |             ^^^^^^ S101
396 |             assert config.redis_socket_connect_timeout >= 5
397 |             assert config.redis_socket_keepalive is True
    |
tests/unit/common/test_redis_config_matrix.py:395:52: PLR2004 Magic value used in comparison, consider replacing `20` with a constant variable
    |
394 |             # Should use production settings for cloud environments
395 |             assert config.redis_max_connections >= 20
    |                                                    ^^ PLR2004
396 |             assert config.redis_socket_connect_timeout >= 5
397 |             assert config.redis_socket_keepalive is True
    |
tests/unit/common/test_redis_config_matrix.py:396:13: S101 Use of `assert` detected
    |
394 |             # Should use production settings for cloud environments
395 |             assert config.redis_max_connections >= 20
396 |             assert config.redis_socket_connect_timeout >= 5
    |             ^^^^^^ S101
397 |             assert config.redis_socket_keepalive is True
    |
tests/unit/common/test_redis_config_matrix.py:396:59: PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
    |
394 |             # Should use production settings for cloud environments
395 |             assert config.redis_max_connections >= 20
396 |             assert config.redis_socket_connect_timeout >= 5
    |                                                           ^ PLR2004
397 |             assert config.redis_socket_keepalive is True
    |
tests/unit/common/test_redis_config_matrix.py:397:13: S101 Use of `assert` detected
    |
395 |             assert config.redis_max_connections >= 20
396 |             assert config.redis_socket_connect_timeout >= 5
397 |             assert config.redis_socket_keepalive is True
    |             ^^^^^^ S101
    |
tests/unit/common/test_redis_config_matrix.py:410:9: ARG002 Unused method argument: `clean_env`
    |
408 |     async def test_password_url_encoding(
409 |         self,
410 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
411 |         monkeypatch: Any,
412 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:411:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
409 |         self,
410 |         clean_env: None,
411 |         monkeypatch: Any,
    |                      ^^^ ANN401
412 |     ) -> None:
413 |         """Test that passwords with special characters are properly URL encoded."""
    |
tests/unit/common/test_redis_config_matrix.py:435:13: S101 Use of `assert` detected
    |
434 |             # URL should contain encoded password
435 |             assert redis_url.startswith("redis://:")
    |             ^^^^^^ S101
436 |             assert "@localhost:6379" in redis_url
    |
tests/unit/common/test_redis_config_matrix.py:436:13: S101 Use of `assert` detected
    |
434 |             # URL should contain encoded password
435 |             assert redis_url.startswith("redis://:")
436 |             assert "@localhost:6379" in redis_url
    |             ^^^^^^ S101
437 |
438 |             # Verify we can extract the password from URL
    |
tests/unit/common/test_redis_config_matrix.py:439:13: PLC0415 `import` should be at the top-level of a file
    |
438 |             # Verify we can extract the password from URL
439 |             import urllib.parse
    |             ^^^^^^^^^^^^^^^^^^^ PLC0415
440 |
441 |             parsed = urllib.parse.urlparse(redis_url)
    |
tests/unit/common/test_redis_config_matrix.py:443:13: S101 Use of `assert` detected
    |
441 |             parsed = urllib.parse.urlparse(redis_url)
442 |             decoded_password = urllib.parse.unquote(parsed.password or "")
443 |             assert decoded_password == password
    |             ^^^^^^ S101
444 |
445 |     async def test_credential_masking_in_logs(
    |
tests/unit/common/test_redis_config_matrix.py:447:9: ARG002 Unused method argument: `clean_env`
    |
445 |     async def test_credential_masking_in_logs(
446 |         self,
447 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
448 |         monkeypatch: Any,
449 |         caplog: Any,
    |
tests/unit/common/test_redis_config_matrix.py:448:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
446 |         self,
447 |         clean_env: None,
448 |         monkeypatch: Any,
    |                      ^^^ ANN401
449 |         caplog: Any,
450 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:449:9: ARG002 Unused method argument: `caplog`
    |
447 |         clean_env: None,
448 |         monkeypatch: Any,
449 |         caplog: Any,
    |         ^^^^^^ ARG002
450 |     ) -> None:
451 |         """Test that credentials are masked in log output."""
    |
tests/unit/common/test_redis_config_matrix.py:449:17: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `caplog`
    |
447 |         clean_env: None,
448 |         monkeypatch: Any,
449 |         caplog: Any,
    |                 ^^^ ANN401
450 |     ) -> None:
451 |         """Test that credentials are masked in log output."""
    |
tests/unit/common/test_redis_config_matrix.py:460:9: S101 Use of `assert` detected
    |
459 |         # Should not contain the actual password
460 |         assert "secret123" not in config_str
    |         ^^^^^^ S101
461 |         # Note: The original implementation doesn't have masking, so this test expects no masking
462 |         # In a real implementation, you'd want to add __str__ method that masks passwords
    |
tests/unit/common/test_redis_config_matrix.py:466:9: ARG002 Unused method argument: `clean_env`
    |
464 |     async def test_configuration_validation(
465 |         self,
466 |         clean_env: None,
    |         ^^^^^^^^^ ARG002
467 |         monkeypatch: Any,
468 |     ) -> None:
    |
tests/unit/common/test_redis_config_matrix.py:467:22: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
    |
465 |         self,
466 |         clean_env: None,
467 |         monkeypatch: Any,
    |                      ^^^ ANN401
468 |     ) -> None:
469 |         """Test validation of Redis configuration parameters."""
    |
tests/unit/common/test_redis_pubsub_comprehensive.py:1:1: INP001 File `tests/unit/common/test_redis_pubsub_comprehensive.py` is part of an implicit namespace package. Add an `__init__.py`.
tests/unit/common/test_redis_pubsub_comprehensive.py:30:47: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `mock_redis_config`
   |
29 |     @pytest.fixture
30 |     async def pubsub(self, mock_redis_config: Any, monkeypatch: Any) -> RedisPubSub:
   |                                               ^^^ ANN401
31 |         """Create RedisPubSub instance with mocked dependencies."""
32 |         monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", True)
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:30:65: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
   |
29 |     @pytest.fixture
30 |     async def pubsub(self, mock_redis_config: Any, monkeypatch: Any) -> RedisPubSub:
   |                                                                 ^^^ ANN401
31 |         """Create RedisPubSub instance with mocked dependencies."""
32 |         monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", True)
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:37:71: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `fake_redis`
   |
36 |     @pytest.fixture
37 |     async def connected_pubsub(self, pubsub: RedisPubSub, fake_redis: Any) -> AsyncGenerator[RedisPubSub, None]:
   |                                                                       ^^^ ANN401
38 |         """Create connected RedisPubSub instance with fake Redis."""
39 |         # Mock the connection setup
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:50:13: SLF001 Private member accessed: `_redis`
   |
49 |             await pubsub.connect()
50 |             pubsub._redis = fake_redis
   |             ^^^^^^^^^^^^^ SLF001
51 |             yield pubsub
52 |             await pubsub.disconnect()
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:54:68: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `monkeypatch`
   |
52 |             await pubsub.disconnect()
53 |
54 |     async def test_init_without_redis_available(self, monkeypatch: Any) -> None:
   |                                                                    ^^^ ANN401
55 |         """Test initialization when Redis is not available."""
56 |         monkeypatch.setattr("src.common.pubsub._REDIS_AVAILABLE", False)
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:70:9: S101 Use of `assert` detected
   |
68 |                 await pubsub.connect()
69 |
70 |         assert not pubsub._connected
   |         ^^^^^^ S101
71 |
72 |     async def test_connect_circuit_breaker_open(self, pubsub: RedisPubSub) -> None:
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:70:20: SLF001 Private member accessed: `_connected`
   |
68 |                 await pubsub.connect()
69 |
70 |         assert not pubsub._connected
   |                    ^^^^^^^^^^^^^^^^^ SLF001
71 |
72 |     async def test_connect_circuit_breaker_open(self, pubsub: RedisPubSub) -> None:
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:75:9: SLF001 Private member accessed: `_circuit_breaker`
   |
73 |         """Test connection when circuit breaker is open."""
74 |         # Force circuit breaker to OPEN state
75 |         pubsub._circuit_breaker._state = CircuitBreakerState.OPEN
   |         ^^^^^^^^^^^^^^^^^^^^^^^ SLF001
76 |         pubsub._circuit_breaker._next_attempt_time = time.time() + 3600
   |
tests/unit/common/test_redis_pubsub_comprehensive.py:75:9: SLF001 Private member accessed: `_state`
   |
73 |         """Test connection when circuit breaker is open."""
74 |         # Force circuit breaker to OPEN state
</latest_ci_output>
