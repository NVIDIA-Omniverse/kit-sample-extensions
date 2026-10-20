"""Codeless graph USD schemas and their registered schema identifiers."""

from pathlib import Path

from pxr import Plug

_resources = Path(__file__).resolve().parents[4] / "animGraphSchema" / "resources"
Plug.Registry().RegisterPlugins(str(_resources))

# Use these names with Usd.Prim.IsA/HasAPI/ApplyAPI and Usd.Stage.DefinePrim.
ANIMATION_GRAPH_API = "AnimationGraphAPI"
ANIMATION_GRAPH = "AnimationGraph"
ANIMATION_GRAPH_NODE = "AnimationGraphNode"
READ_VARIABLE = "ReadVariable"
ANIMATION_CLIP = "AnimationClip"
BLEND = "Blend"
MOTION_MATCHING = "MotionMatching"
FILTER = "Filter"
LOOK_AT_IK = "LookAtIK"
TWO_BONE_IK = "TwoBoneIK"
FULL_BODY_IK = "FullBodyIK"
SET_EFFECTOR = "SetEffector"
POSE_PROVIDER = "PoseProvider"
STATE_MACHINE = "StateMachine"
STATE = "State"
TRANSITION = "Transition"
CONDITION_TIME_FRACTION_CROSSED = "ConditionTimeFractionCrossed"
CONDITION_SPEED = "ConditionSpeed"
CONDITION_COMPARE_VARIABLE = "ConditionCompareVariable"
CONDITION_AND = "ConditionAND"
CONDITION_OR = "ConditionOR"
BEHAVIOR_SCRIPT = "BehaviorScript"
