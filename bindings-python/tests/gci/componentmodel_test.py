import dataclasses
import os
import typing
import unittest

import jsonschema.exceptions
import yaml

import gci.componentmodel as cm
import paths

test_res_dir = paths.test_res_dir


def test_deserialisation():
    with open(os.path.join(test_res_dir, 'component_descriptor_v2.yaml')) as f:
        component_descriptor_dict = yaml.safe_load(f)
    component_descriptor = cm.ComponentDescriptor.from_dict(
        component_descriptor_dict=component_descriptor_dict,
    )

    assert component_descriptor.component.resources[0].type is cm.ResourceType.OCI_IMAGE
    assert isinstance(component_descriptor.component.resources[0].access, cm.OciAccess)
    assert component_descriptor.component.resources[0].access.type is cm.AccessType.OCI_REGISTRY


def test_deserialisation_of_custom_resources():
    with open(os.path.join(test_res_dir, 'component_descriptor_v2_custom.yaml')) as f:
        component_descriptor_dict = yaml.safe_load(f)

    component_descriptor = cm.ComponentDescriptor.from_dict(
        component_descriptor_dict=component_descriptor_dict,
    )
    assert isinstance(component_descriptor.component.resources[0].access, cm.LocalFilesystemBlobAccess)
    assert component_descriptor.component.resources[1].access is None
    assert isinstance(component_descriptor.component.resources[2].access, cm.ResourceAccess)
    assert isinstance(component_descriptor.component.resources[3].access, cm.RelativeOciAccess)


def test_github_access():
    gha = cm.GithubAccess(
        repoUrl='github.com/org/repo',
        ref='refs/heads/master',
        type=cm.AccessType.GITHUB,
    )

    assert gha.repository_name() == 'repo'
    assert gha.org_name() == 'org'
    assert gha.hostname() == 'github.com'


def test_component():
    component = cm.Component(
        name='component-name',
        version='1.2.3',
        repositoryContexts=[
            cm.OciRepositoryContext(baseUrl='old-ctx-url'),
            cm.OciRepositoryContext(baseUrl='current-ctx-url'),
        ],
        provider=None,
        sources=(),
        componentReferences=(),
        resources=(),
        labels=(),
    )

    assert component.current_repository_ctx().baseUrl == 'current-ctx-url'


class TestVersionValidation(unittest.TestCase):

    def _create_test_component_dict(
        self,
        component_version: str,
        resource_version: str,
        source_version: str,
    ):
        return {
            'component': {
                'componentReferences': [],
                'labels': [],
                'name': 'github.test/foo/bar',
                'provider': 'internal',
                'repositoryContexts': [{
                    'baseUrl': 'eu.gcr.io/test/context',
                    'type': 'ociRegistry',
                }],
                'resources': [{
                    'access': {
                        'type': 'None',
                    },
                    'extraIdentity': {},
                    'labels': [],
                    'name': 'test_resource',
                    'relation': 'local',
                    'srcRefs': [],
                    'type': 'ociImage',
                    'version': resource_version,
                }],
                'sources': [{
                    'access': {
                        'ref': 'refs/tags/test',
                        'repoUrl': 'github.test/foo/bar',
                        'type': 'github',
                    },
                    'extraIdentity': {},
                    'labels': [],
                    'name': 'test_source',
                    'type': 'git',
                    'version': source_version,
                }],
                'version': component_version,
            },
            'meta': {
                'schemaVersion': 'v2',
            },
        }

    def test_valid_versions_should_validate_successful(self):
        valid_version_matrix = [
            ['1.2.3',       '2.4.6',    '3.6.9'         ],
            ['1.2.3-foo',   '2.4',      'v3.6.9'        ],
            ['1.2.3+foo',   '2',        'v3.6.9-foo'    ],
            ['v1.2.3+foo',  'v2',       'v3.6.9-foo+bar'],
            ['v1.2.3+foo',  'v2-foo',   'v3.6.9-foo+bar'],
        ]
        for versions in valid_version_matrix:
            test_cd_dict = self._create_test_component_dict(*versions)
            cm.ComponentDescriptor.validate(test_cd_dict, validation_mode=cm.ValidationMode.FAIL)

    def test_validation_fails_on_absent_component_version(self):
        test_cd_dict = self._create_test_component_dict(
            component_version=None,
            resource_version='2.4.6',
            source_version='3.6.9',
        )
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            cm.ComponentDescriptor.validate(test_cd_dict, validation_mode=cm.ValidationMode.FAIL)

    def test_validation_fails_on_absent_resource_version(self):
        test_cd_dict = self._create_test_component_dict(
            component_version='1.2.3',
            resource_version=None,
            source_version='3.6.9',
        )
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            cm.ComponentDescriptor.validate(test_cd_dict, validation_mode=cm.ValidationMode.FAIL)

    def test_validation_fails_on_absent_source_version(self):
        test_cd_dict = self._create_test_component_dict(
            component_version='1.2.3',
            resource_version='2.4.6',
            source_version=None,
        )
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            cm.ComponentDescriptor.validate(test_cd_dict, validation_mode=cm.ValidationMode.FAIL)


def test_set_label():
    lssd_label_name = 'cloud.gardener.cnudie/sdo/lssd'
    processing_rule_name = 'test-processing-rule'

    @dataclasses.dataclass
    class TestCase(unittest.TestCase):
        name: str
        input_labels: typing.List[cm.Label]
        label_to_set: cm.Label
        raise_if_present: bool
        expected_labels: typing.List[cm.Label]
        expected_err_msg: str

    testcases = [
        TestCase(
            name='appends label to empty input_labels list with raise_if_present == True',
            input_labels=[],
            label_to_set=cm.Label(
                name=lssd_label_name,
                value={
                    'processingRules': [
                        processing_rule_name,
                    ],
                },
            ),
            raise_if_present=True,
            expected_labels=[
                cm.Label(
                    name=lssd_label_name,
                    value={
                        'processingRules': [
                            processing_rule_name,
                        ],
                    },
                ),
            ],
            expected_err_msg=''
        ),
        TestCase(
            name='appends label to empty input_labels list with raise_if_present == False',
            input_labels=[],
            label_to_set=cm.Label(
                name=lssd_label_name,
                value={
                    'processingRules': [
                        processing_rule_name,
                    ],
                },
            ),
            raise_if_present=False,
            expected_labels=[
                cm.Label(
                    name=lssd_label_name,
                    value={
                        'processingRules': [
                            processing_rule_name,
                        ],
                    },
                ),
            ],
            expected_err_msg=''
        ),
        TestCase(
            name='throws exception if label exists and raise_if_present == True',
            input_labels=[
                cm.Label(
                    name=lssd_label_name,
                    value={
                        'processingRules': [
                            'first-pipeline',
                        ],
                    },
                ),
            ],
            label_to_set=cm.Label(
                name=lssd_label_name,
                value={
                    'processingRules': [
                        processing_rule_name,
                    ],
                },
            ),
            raise_if_present=True,
            expected_labels=None,
            expected_err_msg=f'label {lssd_label_name} is already present'
        ),
        TestCase(
            name='throws no exception if label exists and raise_if_present == False',
            input_labels=[
                cm.Label(
                    name='test-label',
                    value='test-val',
                ),
                cm.Label(
                    name=lssd_label_name,
                    value={
                        'processingRules': [
                            'first-pipeline',
                        ],
                        'otherOperations': 'test',
                    },
                ),
            ],
            label_to_set=cm.Label(
                name=lssd_label_name,
                value={
                    'processingRules': [
                        processing_rule_name,
                    ],
                },
            ),
            raise_if_present=False,
            expected_labels=[
                cm.Label(
                    name='test-label',
                    value='test-val',
                ),
                cm.Label(
                    name=lssd_label_name,
                    value={
                        'processingRules': [
                            processing_rule_name,
                        ],
                    },
                ),
            ],
            expected_err_msg='',
        ),
    ]

    for testcase in testcases:
        test_resource = cm.Resource(
            name='test-resource',
            version='v0.1.0',
            type=cm.ResourceType.OCI_IMAGE,
            access=cm.OciAccess(
                cm.AccessType.OCI_REGISTRY,
                imageReference='test-repo.com/test-resource:v0.1.0',
            ),
            labels=testcase.input_labels,
        )

        if testcase.expected_err_msg != '':
            with testcase.assertRaises(ValueError) as ctx:
                patched_resource = test_resource.set_label(
                    label=testcase.label_to_set,
                    raise_if_present=testcase.raise_if_present,
                )
            assert str(ctx.exception) == testcase.expected_err_msg
        else:
            patched_resource = test_resource.set_label(
                label=testcase.label_to_set,
                raise_if_present=testcase.raise_if_present,
            )
            testcase.assertListEqual(
                list1=patched_resource.labels,
                list2=testcase.expected_labels,
            )
