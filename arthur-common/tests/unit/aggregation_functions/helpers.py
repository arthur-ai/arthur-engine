from arthur_common.models.metrics import NumericMetric, SketchMetric


def assert_dimension_in_metric(
    metric: NumericMetric | SketchMetric,
    dimension: str,
) -> None:
    results = (
        metric.numeric_series
        if isinstance(metric, NumericMetric)
        else metric.sketch_series
    )
    for res in results:
        dims = {r.name: r.value for r in res.dimensions}
        assert dimension in dims
