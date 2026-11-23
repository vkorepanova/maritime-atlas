from maritime_atlas.processing.routing import split_dateline


def test_dateline_splitting():
    output = split_dateline([[175, 42], [-175, 44]])
    assert output['type'] == 'MultiLineString'
    assert output['coordinates'][0][-1][0] == 180
    assert output['coordinates'][1][0][0] == -180


def test_normal_line():
    output = split_dateline([[10, 35], [17, 36]])
    assert output['type'] == 'LineString'
    assert len(output['coordinates']) == 2
