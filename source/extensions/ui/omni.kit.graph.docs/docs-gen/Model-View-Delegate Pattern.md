# Model-View-Delegate Pattern

Omni.ui graph widget strictly follows the model-view-delegate pattern. The model is independent of the UI, so that you can have different delegates (looks) for the same model or different models use the same delegate.

We define `GraphModel` as the base class for graph widgets' model, which is the central component of the graph widget and manages the graph data. The node and port themselves could be any type to suit your application.

`AbstractGraphNodeDelegate` is the base class for graph nodes' delegate, which defines the look of the nodes. Each node could have several different expansion states: open, closed, minimized. Moreover, different types of nodes could have different delegates. We use `GraphNodeDelegateRouter` as a condition "map" to assign the delegates based on the condition of the nodes.

`GraphView`, defined in omni.kit.widget.graph, is coordinating the above model and delegate, providing the workflow and managing model and delegates.

Everything needed for the Omni.ui graph is done in Python. There is no C++ required. But the core is in C++ so still quite fast even for large graphs.

![](data/pattern.png)
