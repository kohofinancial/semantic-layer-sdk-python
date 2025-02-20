import warnings
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import List

import pytest
from mashumaro.codecs.basic import decode
from enum import Enum

from dbtsl.api.graphql.util import normalize_query
from dbtsl.api.shared.query_params import (
    AdhocQueryParametersStrict,
    OrderByGroupBy,
    OrderByMetric,
    QueryParameters,
    SavedQueryQueryParametersStrict,
    validate_order_by,
    validate_query_parameters,
)
from dbtsl.models.base import BaseModel, GraphQLFragmentMixin, deprecated
from dbtsl.models.base import snake_case_to_camel_case as stc


def test_snake_case_to_camel_case() -> None:
    assert stc("hello") == "hello"
    assert stc("hello_world") == "helloWorld"
    assert stc("Hello_world") == "HelloWorld"
    assert stc("hello world") == "hello world"
    assert stc("helloWorld") == "helloWorld"


def test_base_model_auto_alias() -> None:
    @dataclass
    class SubModel(BaseModel):
        hello_world: str

    BaseModel._register_subclasses()

    data = {
        "helloWorld": "asdf",
    }

    model = SubModel.from_dict(data)
    assert model.hello_world == "asdf"

    codec_model = decode(data, SubModel)
    assert codec_model.hello_world == "asdf"


def test_graphql_fragment_mixin() -> None:
    @dataclass
    class A(BaseModel, GraphQLFragmentMixin):
        foo_bar: str

    @dataclass
    class B(BaseModel, GraphQLFragmentMixin):
        hello_world: str
        baz: str
        a: A
        many_a: List[A]

    a_fragments = A.gql_fragments()
    assert len(a_fragments) == 1
    a_fragment = a_fragments[0]

    a_expect = normalize_query(
        """
    fragment fragmentA on A {
        fooBar
    }
    """
    )
    assert a_fragment.name == "fragmentA"
    assert a_fragment.body == a_expect

    b_fragments = B.gql_fragments()
    assert len(b_fragments) == 2
    b_fragment = b_fragments[0]

    b_expect = normalize_query(
        """
    fragment fragmentB on B {
        helloWorld
        baz
        a {
            ...fragmentA
        }
        manyA {
            ...fragmentA
        }
    }
    """
    )
    assert b_fragment.name == "fragmentB"
    assert b_fragment.body == b_expect
    assert b_fragments[1] == a_fragment


def test_deprecated_with_default_message():
    """Test that @deprecated without arguments uses the class name in the warning."""
    with pytest.warns(DeprecationWarning) as warning_info:

        @deprecated
        class TestEnum(str, Enum):
            VALUE = "value"

        # Access the enum to trigger the warning
        TestEnum.VALUE

    assert len(warning_info) == 1
    assert str(warning_info[0].message) == "TestEnum is deprecated"


def test_deprecated_with_empty_parentheses():
    """Test that @deprecated() behaves the same as @deprecated."""
    with pytest.warns(DeprecationWarning) as warning_info:

        @deprecated()
        class TestEnum(str, Enum):
            VALUE = "value"

        TestEnum.VALUE

    assert len(warning_info) == 1
    assert str(warning_info[0].message) == "TestEnum is deprecated"


def test_deprecated_with_custom_message():
    """Test that @deprecated with custom message uses the provided message."""
    custom_message = "This is a custom deprecation message"
    with pytest.warns(DeprecationWarning) as warning_info:

        @deprecated(custom_message)
        class TestEnum(str, Enum):
            VALUE = "value"

        TestEnum.VALUE

    assert len(warning_info) == 1
    assert str(warning_info[0].message) == custom_message


def test_deprecated_warning_only_once():
    """Test that warning is only raised once per class."""
    with pytest.warns(DeprecationWarning) as warning_info:

        @deprecated
        class TestEnum(str, Enum):
            VALUE1 = "value1"
            VALUE2 = "value2"

        # Access multiple values
        TestEnum.VALUE1
        TestEnum.VALUE2

    # Should only warn once
    assert len(warning_info) == 1


def test_attr_deprecation_warning() -> None:
    msg = "i am deprecated :("

    @dataclass(frozen=True)
    class MyClassWithDeprecatedField(BaseModel):
        its_fine: bool = True
        oh_no: bool = dc_field(default=False, metadata={BaseModel.DEPRECATED: msg})

    BaseModel._register_subclasses()

    m = MyClassWithDeprecatedField()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        _ = m.its_fine
        assert len(w) == 0

        _ = m.oh_no
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert msg == str(w[0].message)


def test_validate_order_by_params_passthrough_OrderByMetric() -> None:
    i = OrderByMetric(name="asdf", descending=True)
    r = validate_order_by([], [], i)
    assert r == i


def test_validate_order_by_params_passthrough_OrderByGroupBy() -> None:
    i = OrderByGroupBy(name="asdf", grain=None, descending=True)
    r = validate_order_by([], [], i)
    assert r == i


def test_validate_order_by_params_ascending() -> None:
    r = validate_order_by(["metric"], [], "+metric")
    assert r == OrderByMetric(name="metric", descending=False)


def test_validate_order_by_params_descending() -> None:
    r = validate_order_by(["metric"], [], "-metric")
    assert r == OrderByMetric(name="metric", descending=True)


def test_validate_order_by_params_metric() -> None:
    r = validate_order_by(["a"], ["b"], "a")
    assert r == OrderByMetric(
        name="a",
        descending=False,
    )


def test_validate_order_by_params_group_by() -> None:
    r = validate_order_by(["a"], ["b"], "b")
    assert r == OrderByGroupBy(
        name="b",
        grain=None,
        descending=False,
    )


def test_validate_order_by_not_found() -> None:
    with pytest.raises(ValueError):
        validate_order_by(["a"], ["b"], "c")


def test_validate_query_params_adhoc_query_valid_metrics_and_groupby() -> None:
    p: QueryParameters = {
        "metrics": ["a", "b"],
        "group_by": ["c", "d"],
        "order_by": ["a"],
        "where": ["1=1"],
        "limit": 1,
        "read_cache": False,
    }
    r = validate_query_parameters(p)
    assert isinstance(r, AdhocQueryParametersStrict)
    assert r.metrics == ["a", "b"]
    assert r.group_by == ["c", "d"]
    assert r.order_by == [OrderByMetric(name="a")]
    assert r.where == ["1=1"]
    assert r.limit == 1
    assert not r.read_cache


def test_validate_query_params_adhoc_query_valid_only_groupby() -> None:
    p: QueryParameters = {"group_by": ["gb"], "limit": 1, "where": ["1=1"], "order_by": ["gb"], "read_cache": False}
    r = validate_query_parameters(p)
    assert isinstance(r, AdhocQueryParametersStrict)
    assert r.metrics is None
    assert r.group_by == ["gb"]
    assert r.order_by == [OrderByGroupBy(name="gb", grain=None)]
    assert r.where == ["1=1"]
    assert r.limit == 1
    assert not r.read_cache


def test_validate_query_params_saved_query_valid() -> None:
    p: QueryParameters = {
        "saved_query": "a",
        "order_by": [OrderByMetric(name="b")],
        "where": ["1=1"],
        "limit": 1,
        "read_cache": False,
    }
    r = validate_query_parameters(p)
    assert isinstance(r, SavedQueryQueryParametersStrict)
    assert r.saved_query == "a"
    assert r.order_by == [OrderByMetric(name="b")]
    assert r.where == ["1=1"]
    assert r.limit == 1
    assert not r.read_cache


def test_validate_query_params_saved_query_group_by() -> None:
    p: QueryParameters = {
        "saved_query": "sq",
        "group_by": ["a", "b"],
    }
    with pytest.raises(ValueError):
        validate_query_parameters(p)


def test_validate_query_params_adhoc_and_saved_query() -> None:
    p: QueryParameters = {"metrics": ["a", "b"], "group_by": ["a", "b"], "saved_query": "a"}
    with pytest.raises(ValueError):
        validate_query_parameters(p)


def test_validate_query_params_no_query() -> None:
    p: QueryParameters = {"limit": 1, "where": ["1=1"], "order_by": ["a"], "read_cache": False}
    with pytest.raises(ValueError):
        validate_query_parameters(p)
