"""Internal command-definition package for Kit command registration.

A "command definition" in this extension is a concrete
`omni.kit.commands.Command` implementation with `do/undo` behavior that mutates
USD stage state (prims, ports, connections, metadata, isolation helpers).

These classes are registered during extension startup and executed by name via
Kit's command system. They are internal plumbing; higher-level wrapper APIs in
`scripts.commands.wrappers` provide the external, safer call surface.

Typical consumers: command registry/bootstrap code during extension startup and
wrapper modules that delegate concrete stage mutations to these classes.
"""
