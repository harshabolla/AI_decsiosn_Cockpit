from app.semantic.semantic_layer import get_semantic_layer


def test_resolve_metric_direct():
    sl = get_semantic_layer()
    metric = sl.resolve_metric("net_sales")
    assert metric is not None
    assert metric["name"] == "Net Sales"
    assert metric["unit"] == "USD"


def test_resolve_metric_alias():
    sl = get_semantic_layer()
    metric = sl.resolve_metric("revenue")
    assert metric is not None
    assert metric["name"] == "Net Sales"


def test_resolve_dimension_alias():
    sl = get_semantic_layer()
    dim = sl.resolve_dimension("brand")
    assert dim is not None
    assert dim["physical_table"] == "dim_product"


def test_schema_context():
    sl = get_semantic_layer()
    ctx = sl.get_schema_context(metrics=["net_sales"], dimensions=["product"])
    assert "fact_sales" in ctx
    assert "dim_product" in ctx
