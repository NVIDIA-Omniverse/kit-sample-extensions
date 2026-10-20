# Web Messaging Core

WebRTC messaging utilities for bidirectional communication between Omniverse Kit and web clients via `omni.kit.livestream.messaging`.

## Architecture

The extension provides two layers for WebRTC message handling. `WebMessagingAPI` implements low-level decorator-based event registration with manual message bus subscriptions. `BaseWebMessaging` extends this with automatic handler discovery, allowing subclasses to define message handlers as decorated methods that are automatically registered on initialization.

Messages flow through Kit's message bus event stream, bridging Python code in Kit with TypeScript/JavaScript web clients over WebRTC data channels. The system uses JSON payloads with a standardized format: `{ event_type: string, payload: object }`. Event names map directly between Kit handlers and web client subscriptions without requiring schema definitions or code generation.

## WebMessagingAPI

The low-level API registers individual functions as message handlers. Each instance maintains its own subscriptions and automatically cleans up on destruction. The class implements reference counting for outgoing events, allowing multiple API instances to share the same event types without conflicts during cleanup.

```python
from omni.web.messaging.core import WebMessagingAPI

api = WebMessagingAPI()

# Register incoming handler - receives events from web client
@api.incoming("undo_request")
def handle_undo():
    omni.kit.commands.execute("Undo")

# Register outgoing handler - sends events to web client
@api.outgoing("status_update")
def send_status(message: str, code: int):
    pass  # Event automatically sent when called

# Trigger outgoing event
send_status(message="Operation complete", code=200)

# Cleanup when done
api.cleanup()
```

The `incoming` decorator creates subscriptions to Kit's message bus. When a web client sends a message with matching `event_type`, the decorator extracts the payload dict and unpacks it as keyword arguments to the handler function. Parameters must match the payload keys sent from the web client.

```python
@api.incoming("camera_change_request")
def handle_camera_change(camera: str, viewport_id: int):
    # Receives payload: { camera: "front", viewport_id: 0 }
    print(f"Switching to {camera} in viewport {viewport_id}")
```

The `outgoing` decorator registers events for transmission and wraps the function to automatically push events to the message bus when called. The wrapper preserves the original function's return value and executes its body, allowing side effects like logging or state updates.

```python
@api.outgoing("screenshot_complete")
def send_screenshot(transfer_id: str, url: str):
    carb.log_info(f"Screenshot {transfer_id} complete")
    return transfer_id  # Return value preserved

# Calling this sends event and executes function body
result = send_screenshot(transfer_id="abc123", url="/tmp/shot.png")
```

### Decorator Syntax

Three syntax patterns are supported for both decorators:

```python
# Without parentheses - uses function name as event name
@api.incoming
def process_data(value: int):
    pass  # Event name: "process_data"

# With empty parentheses - also uses function name
@api.incoming()
def handle_request(data: str):
    pass  # Event name: "handle_request"

# With custom name - overrides function name
@api.incoming("customEventName")
def my_handler(param: str):
    pass  # Event name: "customEventName"
```

### Reference Counting

Multiple `WebMessagingAPI` instances can register handlers for the same outgoing event. The class maintains a shared reference count to prevent premature unregistration. When an instance registers an outgoing event, the count increments. During cleanup, the count decrements, and only when it reaches zero does the system unregister the event type from `omni.kit.livestream.messaging`.

```python
api1 = WebMessagingAPI()
api2 = WebMessagingAPI()

@api1.outgoing("shared_event")
def send1(data: str):
    pass

@api2.outgoing("shared_event")
def send2(data: str):
    pass

# Refcount is now 2
api1.cleanup()  # Refcount becomes 1, event stays registered
api2.cleanup()  # Refcount becomes 0, event unregistered
```

## BaseWebMessaging

The class-based API uses class method decorators that are automatically discovered during initialization. Subclasses define handlers as methods decorated with `@BaseWebMessaging.incoming` or `@BaseWebMessaging.outgoing`. The base class scans all methods on instantiation, identifies decorated methods by checking for marker attributes (`_is_incoming_handler`, `_is_outgoing_handler`), and registers them with an internal `WebMessagingAPI` instance.

```python
from omni.web.messaging.core import BaseWebMessaging
import omni.kit.commands

class AppMessaging(BaseWebMessaging):
    def __init__(self):
        self.state = {}
        super().__init__()  # Registers all decorated methods

    @BaseWebMessaging.incoming("undo_request")
    def handle_undo(self):
        omni.kit.commands.execute("Undo")
        self.send_operation_complete(operation="undo")

    @BaseWebMessaging.incoming("save_request")
    def handle_save(self, filename: str):
        # Access instance state and methods
        self.state['last_save'] = filename
        omni.kit.commands.execute("SaveStage", filename=filename)

    @BaseWebMessaging.outgoing("operation_complete")
    def send_operation_complete(self, operation: str):
        carb.log_info(f"Operation {operation} completed")

# Instantiate to activate all handlers
messaging = AppMessaging()
```

Outgoing methods automatically send events when called. The decorator wraps the method to first push an event to the message bus with the method's keyword arguments as payload, then execute the original method body. This allows methods to perform additional work like logging, state updates, or triggering other actions.

```python
class StageMessaging(BaseWebMessaging):
    @BaseWebMessaging.outgoing("node_selected_event")
    def send_node_selected(self, nodeId: str, fromKit: bool):
        # Log selection for debugging
        print(f"Selected: {nodeId} (from Kit: {fromKit})")
        # Event is sent before this code executes

# Calling this sends event AND executes method body
messaging.send_node_selected(nodeId="/World/Cube", fromKit=True)
```

### Lifecycle Management

Subclasses should call `super().destroy()` in their own `destroy()` methods to ensure proper cleanup of both custom resources and base messaging infrastructure. The base class implements `__del__` to automatically call `destroy()`, but explicit cleanup is recommended for deterministic resource management.

```python
class CustomMessaging(BaseWebMessaging):
    def __init__(self):
        self._viewport_sub = None
        super().__init__()

        # Subscribe to viewport events
        viewport = get_active_viewport_window()
        if viewport:
            self._viewport_sub = viewport.subscribe_to_view_change(
                self._on_camera_changed
            )

    def destroy(self):
        # Clean up custom subscriptions first
        if self._viewport_sub:
            self._viewport_sub.destroy()
            self._viewport_sub = None

        # Call base cleanup for message handlers
        super().destroy()
```

## Message Flow Patterns

### Request-Response

Web client sends request, Kit handler processes and sends response event. The pattern requires two event types: one for the request (incoming) and one for the response (outgoing).

```python
class RequestHandler(BaseWebMessaging):
    @BaseWebMessaging.incoming("camera_change_request")
    def handle_camera_request(self, camera: str):
        # Validate and execute
        stage = omni.usd.get_context().get_stage()
        camera_path = f"/OmniverseKit_{camera.capitalize()}"

        if stage.GetPrimAtPath(camera_path):
            omni.kit.commands.execute(
                "SetViewportCamera",
                camera_path=camera_path
            )
            self.send_camera_changed_event(camera=camera.lower())
        else:
            self.send_error_event(
                action="camera_change_request",
                message=f"Camera not found: {camera_path}"
            )

    @BaseWebMessaging.outgoing("camera_changed_event")
    def send_camera_changed_event(self, camera: str):
        pass

    @BaseWebMessaging.outgoing("error_event")
    def send_error_event(self, action: str, message: str):
        pass
```

Web client implementation uses `StreamingEventManager` to subscribe to responses and send requests:

```typescript
import { StreamingEventManager } from './StreamingEventManager';

const eventManager = new StreamingEventManager(streamConfig);

// Subscribe to response
eventManager.on('camera_changed_event', (event) => {
    console.log('Camera changed:', event.payload.camera);
});

// Send request
eventManager.send('camera_change_request', { camera: 'front' });
```

### Server-Initiated Events

Kit can push events to web clients without a prior request. This pattern monitors Kit state changes and broadcasts updates to all connected clients.

```python
class StageMonitoring(BaseWebMessaging):
    def __init__(self):
        super().__init__()

        # Subscribe to USD stage events
        context = omni.usd.get_context()
        events = context.get_stage_event_stream()
        self._stage_sub = events.create_subscription_to_pop(
            self._on_stage_event
        )

    def _on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            context = omni.usd.get_context()
            selected = context.get_selection().get_selected_prim_paths()
            if selected:
                self.send_node_selected_event(
                    nodeId=selected[0],
                    fromKit=True,
                    allSelected=selected
                )

    @BaseWebMessaging.outgoing("node_selected_event")
    def send_node_selected_event(self, nodeId: str, fromKit: bool,
                                  allSelected: list):
        pass
```

### Chunked Data Transfer

Large binary data requires chunking to avoid message size limits. The pattern sends a start event with metadata, followed by numbered chunks containing base64-encoded binary data, and concludes with a complete event.

```python
class ScreenshotMessaging(BaseWebMessaging):
    @BaseWebMessaging.incoming("screenshot_request")
    def handle_screenshot(self, resolution: dict, quality: int):
        asyncio.ensure_future(
            self._capture_async(resolution, quality)
        )

    async def _capture_async(self, resolution, quality):
        transfer_id = str(uuid.uuid4())
        chunks = await capture_viewport_chunks(resolution, quality)

        # Send start
        self.send_screenshot_start_event(
            transfer_id=transfer_id,
            total_chunks=len(chunks),
            width=resolution['width'],
            height=resolution['height'],
            format='jpeg'
        )

        # Send chunks
        for idx, chunk_bytes in enumerate(chunks):
            self.send_screenshot_chunk_event(
                transfer_id=transfer_id,
                chunk_index=idx,
                data=base64.b64encode(chunk_bytes).decode('utf-8')
            )

        # Send complete
        self.send_screenshot_complete_event(transfer_id=transfer_id)

    @BaseWebMessaging.outgoing("screenshot_start_event")
    def send_screenshot_start_event(self, transfer_id: str,
                                     total_chunks: int, width: int,
                                     height: int, format: str):
        pass

    @BaseWebMessaging.outgoing("screenshot_chunk_event")
    def send_screenshot_chunk_event(self, transfer_id: str,
                                     chunk_index: int, data: str):
        pass

    @BaseWebMessaging.outgoing("screenshot_complete_event")
    def send_screenshot_complete_event(self, transfer_id: str):
        pass
```

Web client reassembles chunks by tracking transfer state:

```typescript
const transfers = new Map<string, {
    chunks: Uint8Array[],
    total_chunks: number,
    format: string
}>();

eventManager.on('screenshot_start_event', (event) => {
    const { transfer_id, total_chunks, format } = event.payload;
    transfers.set(transfer_id, {
        chunks: new Array(total_chunks),
        total_chunks,
        format
    });
});

eventManager.on('screenshot_chunk_event', (event) => {
    const { transfer_id, chunk_index, data } = event.payload;
    const transfer = transfers.get(transfer_id);

    // Decode base64 to binary
    const binaryString = atob(data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    transfer.chunks[chunk_index] = bytes;
});

eventManager.on('screenshot_complete_event', (event) => {
    const { transfer_id } = event.payload;
    const transfer = transfers.get(transfer_id);

    // Concatenate all chunks
    const totalSize = transfer.chunks.reduce((sum, c) => sum + c.length, 0);
    const complete = new Uint8Array(totalSize);
    let offset = 0;
    for (const chunk of transfer.chunks) {
        complete.set(chunk, offset);
        offset += chunk.length;
    }

    // Create blob and display
    const blob = new Blob([complete], { type: `image/${transfer.format}` });
    const url = URL.createObjectURL(blob);
    transfers.delete(transfer_id);
});
```

### Streaming Updates

Long-running operations send incremental updates through chunk events. The pattern distinguishes between interim chunks (`done: false`) and final completion (`done: true`).

```python
class ChatMessaging(BaseWebMessaging):
    @BaseWebMessaging.incoming("start_chat_stream_request")
    def start_stream(self, network_id: str):
        asyncio.ensure_future(self._stream_network(network_id))

    async def _stream_network(self, network_id: str):
        network = self._find_network(network_id)

        async for chunk in network.astream():
            # Send interim chunk
            self.send_chat_chunk_event(
                network_id=network_id,
                node_id=chunk.node.uuid(),
                outputs={'content': chunk.content},
                done=False
            )

        # Send completion marker
        self.send_chat_chunk_event(
            network_id=network_id,
            node_id=network.nodes[-1].uuid(),
            outputs={'content': ''},
            done=True
        )

    @BaseWebMessaging.outgoing("chat_chunk_event")
    def send_chat_chunk_event(self, network_id: str, node_id: str,
                               outputs: dict, done: bool):
        pass
```

## Integration Examples

### USD Stage Tree Synchronization

The stage view implementation demonstrates lazy loading with on-demand child expansion. Kit sends only immediate children when a node expands, avoiding transmission of entire scene hierarchies.

```python
from omni.web.messaging.core import BaseWebMessaging

class StageViewMessaging(BaseWebMessaging):
    def __init__(self):
        self._usd_context = omni.usd.get_context()
        self._events = self._usd_context.get_stage_event_stream()

        # Monitor USD events before registering message handlers
        self._stage_sub = self._events.create_subscription_to_pop(
            self._on_stage_event
        )

        super().__init__()

    @BaseWebMessaging.incoming("get_node_children_request")
    def get_node_children(self, parentPath: str):
        stage = self._usd_context.get_stage()
        prim = stage.GetPrimAtPath(parentPath)

        children = []
        for child in prim.GetChildren():
            children.append({
                'id': child.GetName(),
                'type': str(child.GetTypeName()),
                'visible': self._get_visibility(child),
                'hasChildren': len(list(child.GetChildren())) > 0
            })

        self.send_model_tree_updated_event(
            nodes=children,
            parentPath=parentPath,
            clearCache=False
        )

    @BaseWebMessaging.outgoing("model_tree_updated_event")
    def send_model_tree_updated_event(self, nodes: list,
                                       parentPath: str,
                                       clearCache: bool):
        pass
```

Web client maintains a hierarchy cache and requests children on node expansion:

```typescript
class StageViewManager {
    private hierarchyCache = new Map<string, Node[]>();

    requestChildren(parentPath: string): void {
        eventManager.send('get_node_children_request', { parentPath });
    }

    handleTreeUpdate(event: any): void {
        const { nodes, parentPath, clearCache } = event.payload;

        if (clearCache) {
            this.hierarchyCache.clear();
        }

        this.hierarchyCache.set(parentPath, nodes);
        this.reconstructTree();
    }
}
```

### Dynamic Function Registration

Runtime handler registration allows conditional or lazy initialization of message handlers. This pattern works only with `WebMessagingAPI`, not `BaseWebMessaging`, since the latter registers handlers during `__init__`.

```python
api = WebMessagingAPI()

def register_tool_handlers(tools: list):
    for tool in tools:
        # Create handler function dynamically
        def make_handler(tool_instance):
            def handler(**kwargs):
                result = tool_instance.execute(**kwargs)
                return result
            return handler

        # Register with custom event name
        handler_func = make_handler(tool)
        api.incoming(f"tool_{tool.name}_request")(handler_func)

# Register handlers conditionally
if feature_enabled:
    register_tool_handlers(available_tools)
```

### Error Handling

Incoming handlers catch `TypeError` and `ValueError` exceptions when payload parameters don't match function signatures. Errors are logged but don't crash the message handling system. Outgoing handlers catch exceptions during event transmission and log errors without affecting function execution.

```python
@api.incoming("process_data")
def handler(required_param: str, optional_param: int = 0):
    pass

# If web client sends { optional_param: 5 } without required_param:
# - TypeError is caught and logged
# - Handler doesn't execute
# - Other handlers continue working
```

Explicit error handling in handlers allows sending error events back to the client:

```python
class SafeMessaging(BaseWebMessaging):
    @BaseWebMessaging.incoming("risky_operation")
    def handle_operation(self, param: str):
        try:
            result = perform_operation(param)
            self.send_success_event(result=result)
        except Exception as e:
            self.send_error_event(
                action="risky_operation",
                message=str(e),
                code="OPERATION_FAILED"
            )

    @BaseWebMessaging.outgoing("success_event")
    def send_success_event(self, result: any):
        pass

    @BaseWebMessaging.outgoing("error_event")
    def send_error_event(self, action: str, message: str, code: str):
        pass
```

## Web Client Integration

Web clients use `StreamingEventManager` from the frontend codebase to handle bidirectional communication. The manager wraps Kit's streaming infrastructure and provides typed event handling.

```typescript
import { StreamingEventManager } from './lib/StreamingEventManager';
import OVAppStreamer from './react-component/OVAppStreamer';

// Initialize with stream configuration
const eventManager = new StreamingEventManager(streamConfig);

// Subscribe to events from Kit
const unsubscribe = eventManager.on('camera_changed_event', (event) => {
    const { camera } = event.payload;
    updateCameraUI(camera);
});

// Send requests to Kit
eventManager.send('camera_change_request', { camera: 'top' });

// Cleanup
unsubscribe();
eventManager.cleanup();
```

The event manager handles message formatting automatically. Outgoing messages are serialized as `{ event_type: string, payload: object }` and sent via `OVAppStreamer.sendMessage()`. Incoming messages are parsed from Kit's custom event callback and dispatched to registered handlers.

### Multi-Module Architecture

Each functional module (stage view, chat, screenshots) creates its own `StreamingEventManager` instance with module-specific event definitions. This isolation prevents event name conflicts and allows independent initialization.

```typescript
// stage_view/manager.ts
export class StageViewManager {
    private eventManager: StreamingEventManager;

    initialize(streamConfig: any): void {
        this.eventManager = new StreamingEventManager(streamConfig);

        this.eventManager.on('model_tree_updated_event',
            this.handleTreeUpdate.bind(this)
        );
        this.eventManager.on('node_selected_event',
            this.handleNodeSelected.bind(this)
        );
    }
}

// chat_view/manager.ts
export class ChatViewManager {
    private eventManager: StreamingEventManager;

    initialize(streamConfig: any): void {
        this.eventManager = new StreamingEventManager(streamConfig);

        this.eventManager.on('chat_network_event',
            this.handleNetwork.bind(this)
        );
        this.eventManager.on('chat_chunk_event',
            this.handleChunk.bind(this)
        );
    }
}
```
