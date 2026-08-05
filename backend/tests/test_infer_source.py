from app.services.blocks import infer_source


def test_infer_source():
    assert infer_source("recent papers on AI") == "papers"
    assert infer_source("NBA scores") == "sports"
    assert infer_source("latest Fireship videos") == "youtube"
    assert infer_source("how do volcanoes work") == "web"
