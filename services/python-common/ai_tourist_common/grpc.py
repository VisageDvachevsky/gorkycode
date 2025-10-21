"""gRPC interceptors for propagating trace ids."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

import grpc

from .tracing import ensure_trace_id, reset_trace_id, set_trace_id

Handler = grpc.aio.RpcMethodHandler
Continuation = Callable[[grpc.HandlerCallDetails], Awaitable[Optional[Handler]]]


class TraceIdInterceptor(grpc.aio.ServerInterceptor):
    """Assigns a trace id for each RPC and exposes it via trailing metadata."""

    async def intercept_service(
        self, continuation: Continuation, handler_call_details: grpc.HandlerCallDetails
    ) -> Optional[Handler]:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        metadata = tuple(handler_call_details.invocation_metadata or ())
        trace_id = ensure_trace_id(headers=((item.key, item.value) for item in metadata))

        if handler.unary_unary:
            return self._wrap_unary_unary(handler, trace_id)
        if handler.unary_stream:
            return self._wrap_unary_stream(handler, trace_id)
        if handler.stream_unary:
            return self._wrap_stream_unary(handler, trace_id)
        if handler.stream_stream:
            return self._wrap_stream_stream(handler, trace_id)
        return handler

    def _wrap_unary_unary(self, handler: Handler, trace_id: str) -> Handler:
        async def call(request, context):  # noqa: ANN001 - gRPC signature
            token = set_trace_id(trace_id)
            context.set_trailing_metadata((("x-trace-id", trace_id),))
            try:
                return await handler.unary_unary(request, context)
            finally:
                reset_trace_id(token)

        return grpc.aio.unary_unary_rpc_method_handler(
            call,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    def _wrap_unary_stream(self, handler: Handler, trace_id: str) -> Handler:
        async def call(request, context):  # noqa: ANN001 - gRPC signature
            token = set_trace_id(trace_id)
            context.set_trailing_metadata((("x-trace-id", trace_id),))
            try:
                async for item in handler.unary_stream(request, context):
                    yield item
            finally:
                reset_trace_id(token)

        return grpc.aio.unary_stream_rpc_method_handler(
            call,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    def _wrap_stream_unary(self, handler: Handler, trace_id: str) -> Handler:
        async def call(request_iterator, context):  # noqa: ANN001 - gRPC signature
            token = set_trace_id(trace_id)
            context.set_trailing_metadata((("x-trace-id", trace_id),))
            try:
                return await handler.stream_unary(request_iterator, context)
            finally:
                reset_trace_id(token)

        return grpc.aio.stream_unary_rpc_method_handler(
            call,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    def _wrap_stream_stream(self, handler: Handler, trace_id: str) -> Handler:
        async def call(request_iterator, context):  # noqa: ANN001 - gRPC signature
            token = set_trace_id(trace_id)
            context.set_trailing_metadata((("x-trace-id", trace_id),))
            try:
                async for item in handler.stream_stream(request_iterator, context):
                    yield item
            finally:
                reset_trace_id(token)

        return grpc.aio.stream_stream_rpc_method_handler(
            call,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
