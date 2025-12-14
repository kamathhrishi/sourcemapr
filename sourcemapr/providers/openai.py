"""
OpenAI provider for SourcemapR.

Instruments OpenAI client:
- Chat completions (v1.x and v0.x)
- Completions (legacy)
"""

import time
from typing import Optional, Dict, Any, List

from sourcemapr.providers.base import BaseProvider
from sourcemapr.store import TraceStore


class OpenAIProvider(BaseProvider):
    """OpenAI instrumentation provider."""

    name = "openai"

    def __init__(self, store: TraceStore):
        super().__init__(store)

    def is_available(self) -> bool:
        try:
            import openai
            return True
        except ImportError:
            return False

    def instrument(self) -> bool:
        if self._instrumented:
            return True

        if not self.is_available():
            return False

        try:
            import openai
            if hasattr(openai, 'OpenAI'):
                self._patch_v1()
            else:
                self._patch_v0()

            self._instrumented = True
            print("[SourcemapR] OpenAI provider enabled")
            return True
        except Exception as e:
            print(f"[SourcemapR] OpenAI provider error: {e}")
            return False

    def _patch_v1(self):
        """Patch OpenAI v1.x client."""
        try:
            from openai.resources.chat import completions as chat_completions
            original_create = chat_completions.Completions.create
            store = self.store

            def patched_create(self_client, *args, **kwargs):
                start = time.time()
                messages = kwargs.get('messages', [])
                model = kwargs.get('model', 'unknown')
                temperature = kwargs.get('temperature')
                max_tokens = kwargs.get('max_tokens')
                stop = kwargs.get('stop')

                try:
                    result = original_create(self_client, *args, **kwargs)
                    duration = (time.time() - start) * 1000

                    response_text = ""
                    finish_reason = None
                    tool_calls_data = None

                    if hasattr(result, 'choices') and result.choices:
                        choice = result.choices[0]
                        if hasattr(choice, 'message'):
                            msg = choice.message
                            response_text = getattr(msg, 'content', '') or ''
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                tool_calls_data = [
                                    {
                                        'id': tc.id,
                                        'type': tc.type,
                                        'function': {
                                            'name': tc.function.name,
                                            'arguments': tc.function.arguments
                                        }
                                    } for tc in msg.tool_calls
                                ]
                        finish_reason = getattr(choice, 'finish_reason', None)

                    usage = getattr(result, 'usage', None)
                    prompt_tokens = getattr(usage, 'prompt_tokens', None) if usage else None
                    completion_tokens = getattr(usage, 'completion_tokens', None) if usage else None
                    total_tokens = getattr(usage, 'total_tokens', None) if usage else None

                    store.log_llm(
                        model=model,
                        duration_ms=duration,
                        messages=[{'role': m.get('role', ''), 'content': m.get('content', '')} for m in messages],
                        response=response_text,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stop=stop if isinstance(stop, list) else [stop] if stop else None,
                        tool_calls=tool_calls_data,
                        finish_reason=finish_reason,
                        provider="openai",
                        api_type="chat"
                    )

                    return result

                except Exception as e:
                    duration = (time.time() - start) * 1000
                    store.log_llm(
                        model=model,
                        duration_ms=duration,
                        messages=[{'role': m.get('role', ''), 'content': m.get('content', '')} for m in messages],
                        error=str(e),
                        provider="openai",
                        api_type="chat"
                    )
                    raise

            chat_completions.Completions.create = patched_create
            self._original_handlers['openai.chat.completions.create'] = original_create

        except Exception as e:
            print(f"[SourcemapR] Warning: Could not patch OpenAI v1: {e}")

    def _patch_v0(self):
        """Patch OpenAI v0.x (legacy) client."""
        try:
            import openai
            store = self.store

            if hasattr(openai, 'ChatCompletion'):
                original_chat = openai.ChatCompletion.create

                def patched_chat(*args, **kwargs):
                    start = time.time()
                    messages = kwargs.get('messages', [])
                    model = kwargs.get('model', 'unknown')

                    try:
                        result = original_chat(*args, **kwargs)
                        duration = (time.time() - start) * 1000

                        response_text = result['choices'][0]['message']['content'] if result.get('choices') else ''
                        usage = result.get('usage', {})

                        store.log_llm(
                            model=model,
                            duration_ms=duration,
                            messages=messages,
                            response=response_text,
                            prompt_tokens=usage.get('prompt_tokens'),
                            completion_tokens=usage.get('completion_tokens'),
                            total_tokens=usage.get('total_tokens'),
                            temperature=kwargs.get('temperature'),
                            max_tokens=kwargs.get('max_tokens'),
                            provider="openai",
                            api_type="chat"
                        )

                        return result
                    except Exception as e:
                        duration = (time.time() - start) * 1000
                        store.log_llm(
                            model=model,
                            duration_ms=duration,
                            messages=messages,
                            error=str(e),
                            provider="openai",
                            api_type="chat"
                        )
                        raise

                openai.ChatCompletion.create = patched_chat
                self._original_handlers['openai.ChatCompletion.create'] = original_chat

        except Exception as e:
            print(f"[SourcemapR] Warning: Could not patch OpenAI v0: {e}")

    def uninstrument(self) -> None:
        """Restore original methods."""
        if 'openai.chat.completions.create' in self._original_handlers:
            try:
                from openai.resources.chat import completions as chat_completions
                chat_completions.Completions.create = self._original_handlers['openai.chat.completions.create']
            except Exception:
                pass

        if 'openai.ChatCompletion.create' in self._original_handlers:
            try:
                import openai
                openai.ChatCompletion.create = self._original_handlers['openai.ChatCompletion.create']
            except Exception:
                pass

        self._original_handlers.clear()
        self._instrumented = False
