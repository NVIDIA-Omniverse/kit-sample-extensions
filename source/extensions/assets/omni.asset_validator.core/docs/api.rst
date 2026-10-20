Python API
##########

`omni.asset_validator.core` API
###############################

.. automodule:: omni.asset_validator.core
    :platform: Windows-x86_64, Linux-x86_64
    :no-index:
    :members: AssetType,
              AssetProgress,
              AssetLocatedCallback,
              AssetValidatedCallback,
              AssetProgressCallback,
              Results,
              ResultsList,
              RepeatedValuesSet,
              ValidationStats,
              Issue,
              IssueSeverity,
              AtType,
              AttributeId,
              Identifier,
              LayerId,
              PrimId,
              PropertyId,
              SpecId,
              SpecIdList,
              StageId,
              SchemaBaseId,
              Suggestion,
              VariantIdMixin,
              to_identifier,
              to_identifiers,
              BaseRuleChecker,
              IssueCSVData,
              IssueJSONEncoder,
              IssuesList,
              IssueGroupBy,
              IssuePredicate,
              IssueGroupsBy,
              IssuePredicates,
              AuthoringLayers,
              FixResult,
              FixStatus,
              IssueFixer,
              get_version,
              export_json_file,
              Requirement,
              RequirementProtocol,
              RequirementRefProtocol,
              RequirementsRegistry,
              register_requirements,
              CapabilityRegistry,
              Capability,
              ProfileRegistry,
              Profile,
              is_omni_path,
              create_validation_parser,
              ValidationArgsExec,
              ValidationEngine,
              ValidationRulesRegistry,
              registerRule,
              add_registry_rule_callback,
              is_omni_skel_upgrade_disabled,
              normalize_url
    :member-order: alphabetical

`omni.asset_validator.core.tests` API
#####################################

.. automodule:: omni.asset_validator.core.tests
    :platform: Windows-x86_64, Linux-x86_64
    :no-index:
    :members: IsAnIssue,
          IsAFailure,
          IsAWarning,
          IsAnError,
          IsAnInfo,
          Failure,
          ValidationTestCaseMixin,
          AsyncioValidationTestCaseMixin,
          ValidationRuleTestCase,
          AsyncValidationRuleTestCase
    :member-order: alphabetical
