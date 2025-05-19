from arthur_common.tools.aggregation_loader import AggregationLoader


def test_aggregation_loader():
    functions = AggregationLoader.load_aggregations()
    total_expected = 24
    for func in functions:
        print(func)
    assert len(functions) == total_expected

    # Assert all ids are unique
    assert total_expected == len(set([f[0].id for f in functions]))
    # Assert all names are unique
    assert total_expected == len(set([f[0].name for f in functions]))
