"""Interaction-utility package for graph edit gating and menu helpers.

This package contains focused helpers that answer interaction questions
(for example whether backdrop edits are allowed under current cursor/selection
state) without embedding those rules directly into widget code.

Typical consumers: interaction controllers and graph widget behavior gates that
must evaluate editability from cursor/selection state.
"""
