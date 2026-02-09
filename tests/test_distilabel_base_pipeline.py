from training.pipelines.base_pipeline import BaseSyntheticPipeline


def test_base_pipeline_dry_run():
    p = BaseSyntheticPipeline(role="ba", mode="local")
    result = p.run(num_samples=3, batch_size=2, dry_run=True)
    assert result["total_seeds"] == 3
    assert result["generated"] == 0
    assert result["stats"]["dry_run"] is True


def test_base_pipeline_generates_data():
    p = BaseSyntheticPipeline(role="ba", mode="local")
    result = p.run(num_samples=3, batch_size=2)
    assert result["generated"] >= 1
    assert isinstance(result["data"], list)
