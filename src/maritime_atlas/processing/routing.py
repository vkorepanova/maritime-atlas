from copy import deepcopy

from maritime_atlas.common import read_json, write_json


RESTRICTIONS = {
    'aus_chn_iron': ['northwest', 'malacca', 'sunda'],
    'bra_chn_bulk': ['northwest', 'suez', 'panama'],
    'idn_chn_coal': ['northwest'],
    'idn_ind_coal': ['northwest', 'malacca'],
    'aus_jpn_energy': ['northwest'],
    'gin_chn_bauxite': ['northwest', 'suez', 'panama'],
    'gulf_easia_oil': ['northwest'],
    'gulf_ind_oil': ['northwest'],
    'rus_ind_oil': ['northwest', 'south_africa', 'panama'],
    'us_easia_energy': ['northwest', 'suez', 'south_africa'],
    'chn_eur_suez': ['northwest', 'south_africa', 'panama'],
    'chn_eur_cape': ['northwest', 'suez', 'panama'],
    'chn_uswest': ['northwest', 'panama', 'suez'],
    'chn_useast': ['northwest', 'suez', 'south_africa'],
    'us_eur_atl': ['northwest'],
}


def split_dateline(coordinates):
    coordinates = [
        [((float(lon) + 180) % 360) - 180, float(lat)]
        for lon, lat in coordinates
    ]
    lines = [[list(coordinates[0])]]
    for raw in coordinates[1:]:
        nxt = list(raw)
        prev = lines[-1][-1]
        diff = nxt[0] - prev[0]
        if abs(diff) <= 180:
            lines[-1].append(nxt)
            continue
        adjusted_lon = nxt[0] - 360 if diff > 180 else nxt[0] + 360
        seam_lon = 180 if adjusted_lon > prev[0] else -180
        factor = (seam_lon - prev[0]) / (adjusted_lon - prev[0])
        seam_lat = prev[1] + factor * (nxt[1] - prev[1])
        lines[-1].append([seam_lon, seam_lat])
        lines.append([[-seam_lon, seam_lat], nxt])
    return {'type': 'LineString', 'coordinates': lines[0]} if len(lines) == 1 else {'type': 'MultiLineString', 'coordinates': lines}


def rebuild_routes(input_path, output_path):
    import searoute as sr

    collection = deepcopy(read_json(input_path))
    for feature in collection['features']:
        route_id = feature['properties']['route_id']
        geom = feature['geometry']
        old_lines = [geom['coordinates']] if geom['type'] == 'LineString' else geom['coordinates']
        origin, destination = old_lines[0][0], old_lines[-1][-1]
        restrictions = RESTRICTIONS[route_id]
        result = sr.searoute(origin, destination, restrictions=restrictions)
        coordinates = list(result['geometry']['coordinates'])
        if len(coordinates) < 2:
            raise ValueError(f'No sea route for {route_id}')
        feature['geometry'] = split_dateline(coordinates)
        feature['properties'].update({
            'geometry_method': 'searoute_network',
            'geometry_verified': False,
            'routing_restrictions': restrictions,
            'distance_km': round(float(result['properties']['length']), 1),
        })
    collection['metadata'] = {
        'kind': 'corridors',
        'geometry_accuracy': 'Calculated shortest route on searoute-py maritime network; not AIS verified',
        'source': 'https://github.com/genthalili/searoute-py',
        'note': 'Passage restrictions define route alternatives. Review each route before analytical use; routes are not for navigation.',
    }
    write_json(output_path, collection)
    return len(collection['features'])
