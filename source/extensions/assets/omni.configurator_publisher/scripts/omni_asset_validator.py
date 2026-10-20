# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import argparse
import asyncio
import inspect
import os
import sys
import traceback
from collections import defaultdict
from functools import lru_cache
from typing import Any, Dict, List, Type

import carb
import omni
import omni.log


@lru_cache(maxsize=1)
def _get_categories() -> List[str]:
    """
    Returns:
        The available categories.
    """
    import omni.asset_validator.core  # Should have been imported by main

    return omni.asset_validator.core.ValidationRulesRegistry.categories()


@lru_cache(maxsize=1)
def _get_rules() -> List[str]:
    """
    Returns:
        All available rules.
    """
    import omni.asset_validator.core  # Should have been imported by main

    rules = []
    for category in _get_categories():
        for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category):
            rules.append(rule.__name__)
    return rules


@lru_cache(maxsize=1)
def _get_default_rules() -> List[str]:
    """
    Returns:
        All default rules.
    """
    import omni.asset_validator.core  # Should have been imported by main

    rules = []
    for category in omni.asset_validator.core.ValidationRulesRegistry.categories(enabledOnly=True):
        for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category, enabledOnly=True):
            rules.append(rule.__name__)
    return rules


@lru_cache(maxsize=1)
def _get_predicates() -> Dict[str, Any]:
    import omni.asset_validator.core  # Should have been imported by main

    return {
        "Any": omni.asset_validator.core.IssuePredicates.Any(),
        "IsFailure": omni.asset_validator.core.IssuePredicates.IsFailure(),
        "IsWarning": omni.asset_validator.core.IssuePredicates.IsWarning(),
        "IsError": omni.asset_validator.core.IssuePredicates.IsError(),
        "HasRootLayer": omni.asset_validator.core.IssuePredicates.HasRootLayer(),
    }


def _with_options(message: str, header: str, options: List[str]) -> str:
    tokens: List[str] = [
        inspect.cleandoc(message),
        inspect.cleandoc(header),
        *map(lambda option: f"  {option}", options),
    ]
    return "\n".join(tokens)


def _log_results(results, predicate) -> None:
    import omni.asset_validator.core  # Should have been imported by main

    omni.log.info(f"Results for Asset '{results.asset}'", channel="omni_asset_validator")
    for issue in results.issues(
        omni.asset_validator.core.IssuePredicates.And(omni.asset_validator.core.IssuePredicates.IsError(), predicate)
    ):
        omni.log.fatal(str(issue), channel="omni_asset_validator")
    for issue in results.issues(
        omni.asset_validator.core.IssuePredicates.And(omni.asset_validator.core.IssuePredicates.IsFailure(), predicate)
    ):
        omni.log.error(str(issue), channel="omni_asset_validator")
    for issue in results.issues(
        omni.asset_validator.core.IssuePredicates.And(omni.asset_validator.core.IssuePredicates.IsWarning(), predicate)
    ):
        omni.log.warn(str(issue), channel="omni_asset_validator")


async def _validate(engine, uri: str, fix: bool, predicate) -> None:
    # Should have been imported by main
    from omni.asset_validator.core import (
        AssetProgress,
        BaseRuleChecker,
        IssueFixer,
        IssueGroupsBy,
        IssueSeverity,
        IssuesList,
        Results,
    )

    asset_progress_cache: Dict[str, int] = {}

    def _asset_progress_fn(progress: AssetProgress) -> None:
        value = int(progress.progress * 100)
        if asset_progress_cache.get(progress.asset, 0) != value:
            asset_progress_cache[progress.asset] = value
            omni.log.info(f"Processing {progress.asset}........{value}%", channel="omni_asset_validator")

    summary_rule: Dict[Type[BaseRuleChecker], Dict] = defaultdict(lambda: defaultdict(int))
    summary_severity: Dict[IssueSeverity, int] = defaultdict(int)

    def _asset_validated_fn(result: Results) -> None:
        _log_results(result, predicate)

        issues: IssuesList = result.issues()
        for per_rule in issues.group_by(IssueGroupsBy.rule()):
            if per_rule:
                rule: Type[BaseRuleChecker] = per_rule.name
                for per_severity in per_rule.group_by(IssueGroupsBy.severity()):
                    summary_severity[per_severity.name] += len(per_severity)
                    summary_rule[rule][per_severity.name] += len(per_severity)

        if fix:
            fixer = IssueFixer(result.asset)
            for item in fixer.fix(result.issues(predicate)):
                omni.log.warn(f"{item.issue.message}........{item.status}", channel="omni_asset_validator")
            fixer.save()

    await engine.validate_with_callbacks(
        asset=uri,
        asset_progress_fn=_asset_progress_fn,
        asset_validated_fn=_asset_validated_fn,
    )

    omni.log.info("-" * 128, channel="omni_asset_validator")
    omni.log.info("Summary per Rule:", channel="omni_asset_validator")
    for rule, severity in summary_rule.items():
        omni.log.info(
            (
                f"{rule.__name__}: "
                f"{severity[IssueSeverity.FAILURE]} Failures / "
                f"{severity[IssueSeverity.WARNING]} Warnings / "
                f"{severity[IssueSeverity.ERROR]} Errors"
            ),
            channel="omni_asset_validator",
        )
    omni.log.info("-" * 128)
    omni.log.info("Summary per Severity:", channel="omni_asset_validator")
    omni.log.info(f"Failures: {summary_severity[IssueSeverity.FAILURE]}", channel="omni_asset_validator")
    omni.log.info(f"Warnings: {summary_severity[IssueSeverity.WARNING]}", channel="omni_asset_validator")
    omni.log.info(f"Errors: {summary_severity[IssueSeverity.ERROR]}", channel="omni_asset_validator")
    omni.log.info("-" * 128, channel="omni_asset_validator")


async def main(args):
    import omni.log

    omni.log.info(f"Running in {os.getcwd()}", channel="omni_asset_validator")

    try:
        import omni.asset_validator.core
    except ModuleNotFoundError:
        omni.log.fatal(
            "Unable to import omni.asset_validator.core module. Did you enable omni.asset_validator.core correctly? "
            f"See traceback for details:\n{traceback.format_exc()}",
            channel="omni_asset_validator",
        )
        return 1

    def __logRule(rule: omni.asset_validator.core.BaseRuleChecker):
        omni.log.info(f"{rule.__name__} : {rule.GetDescription()}\n")

    default_rules: bool = args.defaultRules and not args.category and not args.rule
    engine = omni.asset_validator.core.ValidationEngine(initRules=default_rules)

    if not args.explain and not args.asset:
        omni.log.fatal("An Asset URI must be specified", channel="omni_asset_validator")
        return 1

    if args.explain and default_rules:
        for category in omni.asset_validator.core.ValidationRulesRegistry.categories(enabledOnly=True):
            for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category, enabledOnly=True):
                __logRule(rule)

    for category in args.category:
        for rule in omni.asset_validator.core.ValidationRulesRegistry.rules(category):
            if args.explain:
                __logRule(rule)
            else:
                engine.enableRule(rule)

    for r in args.rule:
        rule = omni.asset_validator.core.ValidationRulesRegistry.rule(r)
        if args.explain:
            __logRule(rule)
        else:
            engine.enableRule(rule)

    if args.explain:
        return 0

    omni.log.info(f"Validating: {args.asset}", channel="omni_asset_validator")

    predicate = _get_predicates()[args.predicate] if args.predicate else omni.asset_validator.core.IssuePredicates.Any()
    await _validate(engine, args.asset, args.fix, predicate)
    return 0


async def _main_wrapper(args):
    result_code = 0
    try:
        result_code = await main(args)
    except Exception as e:
        omni.log.fatal(f"Running validator failed with {str(e)}.", channel="omni_asset_validator")
        traceback.print_exec()
    finally:
        omni.kit.app.get_app().post_quit(result_code)


parser = argparse.ArgumentParser()
parser.description = inspect.cleandoc("""
    Utility for USD validation to ensure layers run smoothly across all Omniverse
    products. Validation is based on the USD ComplianceChecker (i.e. the same
    backend as the usdchecker commandline tool), and has been extended with
    additional rules as follows:

        - Additional "Basic" rules applicable in the broader USD ecosystem.
        - Omniverse centric rules that ensure layer files work well with all
            Omniverse applications & connectors.
        - Configurable end-user rules that can be specific to individual company
            and/or team workflows.
            > Note this level of configuration requires manipulating PYTHONPATH
                prior to launching this tool.
    """)
parser.epilog = "See https://tinyurl.com/omni-asset-validator for more details."

parser.add_argument(
    "asset",
    metavar="URI",
    type=str,
    nargs="?",
    help=inspect.cleandoc("""
        A single Omniverse Asset.
            > Note: This can be a file URI or folder/container URI.
        """),
)
parser.add_argument(
    "-d",
    "--defaultRules",
    metavar="0|1",
    required=False,
    type=int,
    default=1,
    help=_with_options(
        """
        Flag to use the default-enabled validation rules.
        Opt-out of this behavior to gain finer control over
        the rules using the --categories and --rules flags.
        """,
        "The default configuration includes:",
        _get_default_rules(),
    ),
)
parser.add_argument(
    "-c",
    "--category",
    metavar="CATEGORY",
    required=False,
    type=str,
    default=[],
    choices=_get_categories(),
    action="append",
    help=_with_options(
        "Categories to enable, regardless of the --defaultRules flag.",
        "Valid categories are:",
        _get_categories(),
    ),
)
parser.add_argument(
    "-r",
    "--rule",
    metavar="RULE",
    required=False,
    type=str,
    default=[],
    choices=_get_rules(),
    action="append",
    help=_with_options(
        "Rules to enable, regardless of the --defaultRules flag.",
        "Valid rules include:",
        _get_rules(),
    ),
)
parser.add_argument(
    "-e",
    "--explain",
    required=False,
    action="store_true",
    help=inspect.cleandoc("""
        Rather than running the validator, provide descriptions
        for each configured rule.
        """),
)
parser.add_argument(
    "-f",
    "--fix",
    required=False,
    action="store_true",
    help="If this is selected, apply fixes.",
)
parser.add_argument(
    "-p",
    "--predicate",
    metavar="PREDICATE",
    required=False,
    type=str,
    choices=_get_predicates(),
    help=_with_options(
        "Report issues and fix issues that match this predicate.",
        "Valid predicates include:",
        _get_predicates(),
    ),
)

args = parser.parse_args()
log = omni.log.get_log()
log.set_channel_level("carb.settings.plugin", omni.log.Level.FATAL, omni.log.SettingBehavior.OVERRIDE)
log.set_channel_level("omni.core.ITypeFactory", omni.log.Level.ERROR, omni.log.SettingBehavior.OVERRIDE)
carb.get_framework().startup([])

log.set_channel_enabled("omni_asset_validator", True, omni.log.SettingBehavior.OVERRIDE)
log.set_channel_level("omni_asset_validator", omni.log.Level.VERBOSE, omni.log.SettingBehavior.OVERRIDE)
omni.log.info(f"Running in {os.getcwd()}", channel="omni_asset_validator")

asyncio.ensure_future(_main_wrapper(args))
